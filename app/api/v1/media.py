from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from loguru import logger

from app.crud.media import MediaRepository, get_media_repo
from app.models.media import Media
from app.schemas.media import MediaRead
from app.utils.storage import storage_service

router = APIRouter()


@router.get("/search", response_model=list[MediaRead])
async def search_media(
    repo: Annotated[MediaRepository, Depends(get_media_repo)],
    title: Annotated[str, Query(...)],
):
    logger.info(f"Searching media with title: {title}")
    return await repo.get_media_by_title(title=title)


@router.post("/upload", response_model=MediaRead, status_code=status.HTTP_201_CREATED)
async def create_media(
    repo: Annotated[MediaRepository, Depends(get_media_repo)],
    file: Annotated[UploadFile, File(...)],
):
    # 1. Use the helper to handle file operations
    try:
        file_info = await storage_service.save_file(file)
    except Exception as e:
        logger.error(f"Failed to store media file: {e}")
        raise HTTPException(status_code=500, detail="Failed to store media file") from e

    # 2. Save to Database
    new_media = Media(
        title=file_info["file_name"],
        file_type=file_info["file_type"],
        file_size=file_info["file_size"],
        file_path=file_info["file_path"],
        id=file_info["uuid"],
    )

    return await repo.store_media(new_media)


@router.get("/download/{media_id}", response_class=StreamingResponse)
async def download_file(
    media_id: str, repo: Annotated[MediaRepository, Depends(get_media_repo)]
):
    media_item = await get_media_details(media_id, repo)

    # We pass the async generator directly to StreamingResponse
    return StreamingResponse(
        storage_service.get_file_stream(media_item.file_path),
        media_type=media_item.file_type,
        headers={"Content-Disposition": f"attachment; filename={media_item.title}"},
    )


@router.get("/info/{media_id}", response_model=MediaRead)
async def get_media_details(
    media_id: str, repo: Annotated[MediaRepository, Depends(get_media_repo)]
):
    logger.info(f"checking media with id {media_id}")
    media_item = await repo.get_media_by_id(media_id)
    if not media_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media resource not found"
        )
    return media_item


@router.delete("/delete/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_by_id(
    media_id: str, repo: Annotated[MediaRepository, Depends(get_media_repo)]
):
    media_item, deleted = await repo.delete_media_by_id(media_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media resource not found"
        )
    else:
        # Also delete the file from storage
        try:
            await storage_service.delete_file(media_item.file_path)
        except FileNotFoundError:
            logger.warning(
                f"File for media id {media_id} not found in storage during deletion."
            )
        except Exception as e:
            logger.error(f"Error deleting file for media id {media_id}: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to delete media file"
            ) from e
