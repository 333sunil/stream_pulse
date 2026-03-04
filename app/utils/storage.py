import shutil
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import aiofiles
import boto3
from botocore.exceptions import ClientError
from fastapi import UploadFile
from loguru import logger

from app.core.config import settings


class StorageService(ABC):
    """Base class for storage services"""

    @abstractmethod
    async def save_file(self, file: UploadFile) -> dict:
        """Save file to storage"""
        pass

    @abstractmethod
    async def delete_file(self, file_path: str) -> bool:
        """Delete file from storage"""
        pass

    @abstractmethod
    async def get_file_stream(
        self, file_path: str, chunk_size: int = 1024 * 1024
    ) -> AsyncGenerator[bytes, None]:
        """Get file stream from storage"""
        pass


class FileStorageService(StorageService):
    def __init__(self, upload_dir: str = "static/uploads"):
        self.upload_dir = Path(upload_dir).resolve()
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, file: UploadFile) -> dict:
        """
        Saves file to local filesystem.
        """
        # Generate unique folder and keep original filename
        unique_folder = str(uuid.uuid4())
        folder_path = self.upload_dir / unique_folder
        folder_path.mkdir(parents=True, exist_ok=True)
        unique_name = file.filename  # keep original filename
        file_path = folder_path / unique_name

        # Stream file to disk
        try:
            with file_path.open("wb") as buffer:
                # Use shutil to copy the file-like object efficiently
                shutil.copyfileobj(file.file, buffer)

            return {
                "file_path": str(file_path),
                "file_size": file_path.stat().st_size,
                "file_type": file.content_type,
                "file_name": unique_name,
                "uuid": unique_folder,
            }
        except Exception as e:
            if file_path.exists():
                file_path.unlink()
            raise e from e
        finally:
            await file.close()

    async def delete_file(self, file_path: str) -> bool:
        """
        Deletes a file from the filesystem.
        In the future, you can swap this logic to delete from S3/MinIO.
        """
        path = Path(file_path)
        if path.exists():
            path.unlink()
            return True
        raise FileNotFoundError(f"File {file_path} not found for deletion.")

    async def get_file_stream(
        self, file_path: str, chunk_size: int = 1024 * 1024
    ) -> AsyncGenerator[bytes, None]:
        # Handle local paths using aiofiles for non-blocking I/O
        async with aiofiles.open(file_path, mode="rb") as f:
            while chunk := await f.read(chunk_size):
                yield chunk


class S3StorageService(StorageService):
    """S3-compatible storage service using boto3 (works with MinIO, AWS S3, etc.)"""

    def __init__(
        self,
        endpoint: str,
        access_key: str = None,
        secret_key: str = None,
        bucket_name: str = "media",
        use_ssl: bool = False,
    ):
        # Configure boto3 S3 client
        endpoint_url = f"{'https' if use_ssl else 'http'}://{endpoint}"
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",  # Required but not used by MinIO
        )
        self.bucket_name = bucket_name
        self.endpoint = endpoint
        self.use_ssl = use_ssl

        # Ensure bucket exists
        try:
            self.client.head_bucket(Bucket=bucket_name)
        except ClientError:
            self.client.create_bucket(Bucket=bucket_name)

    async def save_file(self, file: UploadFile) -> dict:
        """
        Saves file to S3-compatible storage.
        """
        try:
            # Generate unique folder and keep original filename
            unique_folder = str(uuid.uuid4())
            unique_name = file.filename or "file"
            object_name = f"{unique_folder}/{unique_name}"

            # Read file content
            content = await file.read()
            file_size = len(content)

            # Upload to S3
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=object_name,
                Body=BytesIO(content),
                ContentLength=file_size,
                ContentType=file.content_type,
            )

            file_url = self._build_file_url(object_name)

            return {
                "file_path": file_url,
                "file_size": file_size,
                "file_type": file.content_type,
                "file_name": unique_name,
                "uuid": unique_folder,
            }
        except ClientError as e:
            logger.error(f"ClientError during file upload: {e}")
            raise e from e
        finally:
            await file.close()

    async def delete_file(self, file_path: str) -> bool:
        """
        Deletes a file from S3-compatible storage.
        """
        try:
            object_name = self._normalize_object_name(file_path)
            self.client.delete_object(Bucket=self.bucket_name, Key=object_name)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                raise FileNotFoundError(
                    f"File {file_path} not found in storage."
                ) from e
            raise e from e

    async def get_file_stream(
        self, file_path: str, chunk_size: int = 1024 * 1024
    ) -> AsyncGenerator[bytes, None]:
        """
        Streams file from S3-compatible storage.
        """
        try:
            object_name = self._normalize_object_name(file_path)
            response = self.client.get_object(Bucket=self.bucket_name, Key=object_name)
            stream = response["Body"]
            while True:
                chunk = stream.read(chunk_size)
                if not chunk:
                    break
                yield chunk
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "NoSuchKey":
                raise FileNotFoundError(
                    f"File {file_path} not found in storage."
                ) from e
            raise e from e
        finally:
            stream.close()

    def _build_file_url(self, object_name: str) -> str:
        scheme = "https" if self.use_ssl else "http"
        return f"{scheme}://{self.endpoint}/{self.bucket_name}/{object_name}"

    def _normalize_object_name(self, file_path: str) -> str:
        if file_path.startswith("http://") or file_path.startswith("https://"):
            parsed = urlparse(file_path)
            path = parsed.path.lstrip("/")
            prefix = f"{self.bucket_name}/"
            if path.startswith(prefix):
                return path[len(prefix) :]
            return path
        return file_path


# Instantiate once to use across the app
endpoint = getattr(settings, "ENDPOINT", None)
access_key = getattr(settings, "ACCESS_KEY", None)
secret_key = getattr(settings, "SECRET_KEY", None)
bucket_name = getattr(settings, "BUCKET_NAME", None)
use_ssl = getattr(settings, "USE_SSL", None)

if endpoint:
    storage_service = S3StorageService(
        endpoint=endpoint,
        access_key=access_key or None,
        secret_key=secret_key or None,
        bucket_name=bucket_name or "media",
        use_ssl=use_ssl or False,
    )
else:
    storage_service = FileStorageService(settings.MEDIA_PATH)
