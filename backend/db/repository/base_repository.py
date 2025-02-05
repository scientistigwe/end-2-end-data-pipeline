# backend/db/repository/base_repository.py

from typing import TypeVar, Generic, Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from uuid import UUID
from sqlalchemy import desc, select
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')

class BaseRepository(Generic[T]):
    """Base repository with common database operations"""

    def __init__(self, db_session: AsyncSession):
        print(f"db_session type: {type(db_session)}")
        print(f"Is AsyncSession: {isinstance(db_session, AsyncSession)}")

        if not isinstance(db_session, AsyncSession):
            raise ValueError(f"db_session must be an AsyncSession instance, got {type(db_session)}")

        self.db_session = db_session

    async def create(self, data: Dict[str, Any], model_class: T) -> T:
        """Create new instance with error handling and logging"""
        try:
            instance = model_class(**data)
            self.db_session.add(instance)
            await self.db_session.flush()
            await self.db_session.commit()
            await self.db_session.refresh(instance)
            logger.info(f"Created new {model_class.__name__} instance")
            return instance
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error creating {model_class.__name__}: {str(e)}")
            raise

    async def get_by_id(
            self,
            id: UUID,
            model_class: T,
            include_deleted: bool = False
    ) -> Optional[T]:
        """Get instance by ID with soft delete handling"""
        try:
            query = select(model_class)
            if hasattr(model_class, 'is_deleted') and not include_deleted:
                query = query.filter_by(is_deleted=False)
            query = query.filter(model_class.id == id)
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting {model_class.__name__} by ID: {str(e)}")
            raise

    async def update(
            self,
            id: UUID,
            data: Dict[str, Any],
            model_class: T
    ) -> Optional[T]:
        """Update instance with metadata tracking"""
        try:
            instance = await self.get_by_id(id, model_class)
            if instance:
                for key, value in data.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                if hasattr(instance, 'updated_at'):
                    instance.updated_at = datetime.utcnow()
                await self.db_session.commit()
                await self.db_session.refresh(instance)
                logger.info(f"Updated {model_class.__name__} instance {id}")
            return instance
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error updating {model_class.__name__} {id}: {str(e)}")
            raise

    async def delete(
            self,
            id: UUID,
            model_class: T,
            soft_delete: bool = True
    ) -> bool:
        """Delete instance with soft delete support"""
        try:
            instance = await self.get_by_id(id, model_class)
            if instance:
                if soft_delete and hasattr(instance, 'is_deleted'):
                    instance.is_deleted = True
                    instance.deleted_at = datetime.utcnow()
                    await self.db_session.commit()
                else:
                    self.db_session.delete(instance)
                    await self.db_session.commit()
                logger.info(f"{'Soft' if soft_delete else 'Hard'} deleted {model_class.__name__} {id}")
                return True
            return False
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error deleting {model_class.__name__} {id}: {str(e)}")
            raise

    async def begin(self):
        """Begin a transaction"""
        return await self.db_session.begin()

    async def commit(self):
        """Commit the current transaction"""
        await self.db_session.commit()

    async def rollback(self):
        """Rollback the current transaction"""
        await self.db_session.rollback()