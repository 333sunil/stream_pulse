from uuid import UUID

from pydantic import BaseModel, ConfigDict


class MediaBase(BaseModel):
    title: str
    file_type: str  # e.g., "video/mp4"
    file_size: int  # in bytes
    file_path: str  # path to the stored file on disk


class MediaCreate(MediaBase):
    pass  # Used for incoming POST data


class MediaRead(MediaBase):
    id: UUID
    model_config = ConfigDict(
        from_attributes=True
    )  # Allows Pydantic to read SQLAlchemy objects
