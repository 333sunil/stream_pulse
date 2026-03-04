from typing import Annotated

from fastapi import Depends
from loguru import logger
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models.media import Media


class MediaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_media_by_title(self, title: str | None = None) -> list[Media]:
        try:
            query = select(Media)

            if title:
                # Better: use func.lower on both sides for true case-insensitivity
                pattern = f"%{title.lower()}%"
                query = query.where(func.lower(Media.title).like(pattern))
                logger.debug(f"Searching media with title pattern: {title}")
            else:
                logger.debug("Retrieving all media items")

            # Execute the query
            result = await self.db.execute(query)

            # .scalars() returns the objects, .all() converts to a list
            media_items = list(result.scalars().all())
            logger.info(
                f"Found {len(media_items)} media items"
                + (f" matching title pattern '{title}'" if title else "")
            )
            return media_items
        except Exception as e:
            logger.error(
                f"Error retrieving media by title '{title}': {str(e)}", exc_info=True
            )
            raise

    async def store_media(self, media: Media) -> Media:
        """
        Handles the logic for storing media metadata in the database.
        """
        try:
            logger.debug(f"Storing media: id={media.id}, title={media.title}")
            self.db.add(media)
            await self.db.commit()
            await self.db.refresh(media)
            logger.info(f"Successfully stored media with id: {media.id}")
            return media
        except Exception as e:
            logger.error(f"Error storing media: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise

    async def delete_media_by_id(self, media_id: str) -> tuple[Media | None, bool]:
        """
        Handles the logic for deleting media metadata from the database.
        """
        try:
            logger.debug(f"Attempting to delete media with id: {media_id}")
            query = select(Media).where(Media.id == media_id)
            result = await self.db.execute(query)
            media_item = result.scalar_one_or_none()

            if not media_item:
                logger.warning(f"Media not found for deletion with id: {media_id}")
                return None, False

            await self.db.delete(media_item)
            await self.db.commit()
            logger.info(f"Successfully deleted media with id: {media_id}")
            return media_item, True
        except Exception as e:
            logger.error(
                f"Error deleting media with id {media_id}: {str(e)}", exc_info=True
            )
            await self.db.rollback()
            raise

    async def get_media_by_id(self, media_id: str) -> Media | None:
        """
        Handles the logic for retrieving a single media item by ID.
        """
        try:
            logger.debug(f"Retrieving media with id: {media_id}")
            query = select(Media).where(Media.id == media_id)
            result = await self.db.execute(query)
            media_item = result.scalar_one_or_none()

            if media_item:
                logger.debug(f"Found media with id: {media_id}")
            else:
                logger.warning(f"Media not found for id: {media_id}")

            return media_item
        except Exception as e:
            logger.error(
                f"Error retrieving media with id {media_id}: {str(e)}", exc_info=True
            )
            raise


# Helper function to get the repository instance via Dependency Injection
async def get_media_repo(db: Annotated[AsyncSession, Depends(get_db)]):
    return MediaRepository(db)
