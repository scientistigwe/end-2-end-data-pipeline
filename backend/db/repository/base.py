from typing import TypeVar, Generic, Dict, List, Any, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete, desc
from datetime import datetime
from uuid import UUID
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """
    Base repository providing fundamental database operations with comprehensive
    error handling, logging, and audit trailing.
    """

    def __init__(self, db_session: AsyncSession):
        if not isinstance(db_session, AsyncSession):
            raise ValueError(f"db_session must be AsyncSession, got {type(db_session)}")
        self.db_session = db_session

    async def create(self, data: Dict[str, Any], model_class: T) -> T:
        """
        Create a new instance with proper error handling and audit trailing.

        Args:
            data: Dictionary containing model data
            model_class: The model class to instantiate

        Returns:
            Created instance

        Raises:
            Exception: If creation fails
        """
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
        """
        Retrieve instance by ID with soft delete handling.

        Args:
            id: Instance ID
            model_class: Model class to query
            include_deleted: Whether to include soft-deleted instances

        Returns:
            Instance if found, None otherwise
        """
        try:
            query = select(model_class).where(model_class.id == id)

            if hasattr(model_class, 'is_deleted') and not include_deleted:
                query = query.where(model_class.is_deleted == False)

            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving {model_class.__name__} by ID: {str(e)}")
            raise

    async def list_all(
            self,
            model_class: T,
            filters: Optional[Dict[str, Any]] = None,
            sort_by: Optional[str] = None,
            page: int = 1,
            page_size: int = 50
    ) -> Tuple[List[T], int]:
        """
        List instances with filtering, sorting and pagination.

        Args:
            model_class: Model class to query
            filters: Optional filter criteria
            sort_by: Optional sort field
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (items list, total count)
        """
        try:
            query = select(model_class)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if hasattr(model_class, key):
                        query = query.where(getattr(model_class, key) == value)

            # Get total count
            count_result = await self.db_session.execute(
                select(func.count()).select_from(query.subquery())
            )
            total_count = count_result.scalar_one()

            # Apply sorting
            if sort_by and hasattr(model_class, sort_by):
                query = query.order_by(desc(getattr(model_class, sort_by)))

            # Apply pagination
            query = query.offset((page - 1) * page_size).limit(page_size)

            result = await self.db_session.execute(query)
            items = result.scalars().all()

            return items, total_count
        except Exception as e:
            logger.error(f"Error listing {model_class.__name__}: {str(e)}")
            raise

    async def update(
            self,
            id: UUID,
            data: Dict[str, Any],
            model_class: T
    ) -> Optional[T]:
        """
        Update instance with audit trailing.

        Args:
            id: Instance ID
            data: Update data
            model_class: Model class

        Returns:
            Updated instance if found
        """
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
        """
        Delete instance with soft delete support.

        Args:
            id: Instance ID
            model_class: Model class
            soft_delete: Whether to use soft delete

        Returns:
            True if deleted successfully
        """
        try:
            instance = await self.get_by_id(id, model_class)
            if instance:
                if soft_delete and hasattr(instance, 'is_deleted'):
                    instance.is_deleted = True
                    instance.deleted_at = datetime.utcnow()
                    await self.db_session.commit()
                else:
                    await self.db_session.delete(instance)
                    await self.db_session.commit()

                logger.info(
                    f"{'Soft' if soft_delete else 'Hard'} deleted "
                    f"{model_class.__name__} {id}"
                )
                return True
            return False
        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Error deleting {model_class.__name__} {id}: {str(e)}")
            raise

    async def exists(self, id: UUID, model_class: T) -> bool:
        """
        Check if instance exists.

        Args:
            id: Instance ID
            model_class: Model class

        Returns:
            True if exists
        """
        try:
            query = select(model_class.id).where(model_class.id == id)
            result = await self.db_session.execute(query)
            return result.scalar_one_or_none() is not None
        except Exception as e:
            logger.error(f"Error checking existence of {model_class.__name__}: {str(e)}")
            raise

    async def count(
            self,
            model_class: T,
            filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count instances with optional filtering.

        Args:
            model_class: Model class
            filters: Optional filter criteria

        Returns:
            Count of matching instances
        """
        try:
            query = select(func.count()).select_from(model_class)

            if filters:
                for key, value in filters.items():
                    if hasattr(model_class, key):
                        query = query.where(getattr(model_class, key) == value)

            result = await self.db_session.execute(query)
            return result.scalar_one()
        except Exception as e:
            logger.error(f"Error counting {model_class.__name__}: {str(e)}")
            raise

    async def begin(self) -> None:
        """Begin a transaction."""
        await self.db_session.begin()

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self.db_session.commit()

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        await self.db_session.rollback()

    async def cleanup(self) -> None:
        """Clean up database resources."""
        await self.db_session.close()