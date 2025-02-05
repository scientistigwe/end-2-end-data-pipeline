# backend/db/repository/staging_repository.py

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import and_, or_, desc, func, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from .base_repository import BaseRepository
from ..models.staging.base_staging_model import BaseStagedOutput
from ..models.staging.staging_control_model import StagingControlPoint
from ..models.staging.staging_history_model import StagingProcessingHistory

logger = logging.getLogger(__name__)


class StagingRepository(BaseRepository[BaseStagedOutput]):
    """Repository for staging operations with enhanced error handling and logging"""

    def __init__(self, db_session: AsyncSession):
        """
        Initialize the repository with an async database session

        Args:
            db_session (AsyncSession): Async SQLAlchemy session
        """
        super().__init__(db_session)

    async def store_staged_resource(
            self,
            pipeline_id: UUID,
            data: Dict[str, Any],
            user_id: Optional[UUID] = None
    ) -> BaseStagedOutput:
        """Store staged resource with proper tracking"""
        try:
            # Create staged resource
            resource_data = {
                'pipeline_id': pipeline_id,
                'stage_key': data['stage_key'],
                'name': data.get('name'),
                'resource_type': data['resource_type'],
                'format': data.get('format'),
                'storage_location': data['storage_location'],
                'size_bytes': data.get('size_bytes'),
                'checksum': data.get('checksum'),
                'requires_approval': data.get('requires_approval', True),
                'owner_id': user_id,
                'metadata': data.get('metadata', {}),
                'tags': data.get('tags', [])
            }

            resource = await self.create(resource_data, BaseStagedOutput)

            # Track history
            await self.create({
                'staged_output_id': resource.id,
                'event_type': 'resource_created',
                'status': resource.status,
                'details': {
                    'user_id': str(user_id) if user_id else None,
                    'resource_type': data['resource_type']
                }
            }, StagingProcessingHistory)

            return resource

        except Exception as e:
            logger.error(f"Failed to store staged resource: {str(e)}")
            raise

    async def get_pipeline_resources(
            self,
            pipeline_id: UUID,
            status: Optional[str] = None,
            resource_type: Optional[str] = None
    ) -> List[BaseStagedOutput]:
        """Get pipeline resources with filtering"""
        try:
            # Construct query using select
            query = select(BaseStagedOutput).where(
                BaseStagedOutput.pipeline_id == pipeline_id
            )

            if status:
                query = query.where(BaseStagedOutput.status == status)
            if resource_type:
                query = query.where(BaseStagedOutput.resource_type == resource_type)

            # Execute query and return results
            result = await self.db_session.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error retrieving pipeline resources: {str(e)}")
            raise

    async def get_staging_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive staging metrics.
        """
        try:
            # Get current time for calculations
            current_time = datetime.utcnow()

            # Count resources by status
            status_count_query = select(
                BaseStagedOutput.status,
                func.count(BaseStagedOutput.id)
            ).group_by(BaseStagedOutput.status)
            status_counts_result = await self.db_session.execute(status_count_query)
            status_counts = status_counts_result.all()

            # Count resources by type
            type_count_query = select(
                BaseStagedOutput.resource_type,
                func.count(BaseStagedOutput.id)
            ).group_by(BaseStagedOutput.resource_type)
            type_counts_result = await self.db_session.execute(type_count_query)
            type_counts = type_counts_result.all()

            # Calculate average processing time for completed resources
            processing_time_query = select(
                func.avg(
                    func.extract('epoch', BaseStagedOutput.updated_at) -
                    func.extract('epoch', BaseStagedOutput.created_at)
                )
            ).where(BaseStagedOutput.status == 'completed')
            processing_times_result = await self.db_session.execute(processing_time_query)
            processing_times = processing_times_result.scalar()

            return {
                'resource_counts': {
                    'by_status': dict(status_counts),
                    'by_type': dict(type_counts)
                },
                'processing_metrics': {
                    'avg_processing_time': processing_times,
                    'active_resources': dict(status_counts).get('pending', 0),
                    'expired_resources': dict(status_counts).get('expired', 0)
                },
                'timestamp': current_time.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get staging metrics: {str(e)}")
            raise

    async def list_resources(
            self,
            query_params: Dict[str, Any],
            sort_params: Optional[List[Tuple[str, int]]] = None
    ) -> List[BaseStagedOutput]:
        """
        Get all resources matching query parameters with sorting

        Args:
            query_params: Dictionary of query parameters
            sort_params: List of tuples (field, direction) for sorting

        Returns:
            List[BaseStagedOutput]: List of matched resources
        """
        try:
            # Start with base query
            query = select(BaseStagedOutput)

            # Apply filters
            for key, value in query_params.items():
                if hasattr(BaseStagedOutput, key):
                    query = query.where(getattr(BaseStagedOutput, key) == value)
                elif key == 'resource_type':
                    query = query.where(BaseStagedOutput.resource_type == value)
                elif key == 'user_id':
                    query = query.where(BaseStagedOutput.owner_id == UUID(value))

            # Apply sorting
            if sort_params:
                for field, direction in sort_params:
                    if hasattr(BaseStagedOutput, field):
                        sort_field = getattr(BaseStagedOutput, field)
                        query = query.order_by(
                            desc(sort_field) if direction == -1 else sort_field
                        )

            # Execute query
            result = await self.db_session.execute(query)
            return result.scalars().all()

        except Exception as e:
            logger.error(f"Error listing resources: {str(e)}")
            return []

    async def delete_resource(self, resource_id: str) -> bool:
        """
        Delete a resource by ID

        Args:
            resource_id: ID of the resource to delete

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create async select statement
            stmt = select(BaseStagedOutput).filter(
                BaseStagedOutput.id == UUID(resource_id)
            )

            # Execute query asynchronously
            result = await self.db_session.execute(stmt)
            resource = result.scalar_one_or_none()

            if resource:
                # Delete the resource asynchronously
                await self.db_session.delete(resource)
                await self.db_session.commit()
                return True

            return False

        except Exception as e:
            logger.error(f"Error deleting resource: {str(e)}")
            await self.db_session.rollback()
            return False

    async def update_resource_metadata(
            self,
            resource_id: str,
            metadata_updates: Dict[str, Any]
    ) -> None:
        """
        Update resource metadata with proper tracking.

        Args:
            resource_id (str): ID of the resource to update
            metadata_updates (Dict[str, Any]): Metadata fields to update
        """
        try:
            resource = await self.db_session.query(BaseStagedOutput).filter(
                BaseStagedOutput.id == UUID(resource_id)
            ).first()

            if not resource:
                raise ValueError(f"Resource not found: {resource_id}")

            # Update metadata
            current_metadata = resource.metadata or {}
            current_metadata.update(metadata_updates)
            resource.metadata = current_metadata
            resource.updated_at = datetime.utcnow()

            # Track metadata update
            await self.create({
                'staged_output_id': resource.id,
                'event_type': 'metadata_updated',
                'status': resource.status,
                'details': {
                    'updated_fields': list(metadata_updates.keys()),
                    'update_time': datetime.utcnow().isoformat()
                }
            }, StagingProcessingHistory)

            await self.db_session.commit()

        except Exception as e:
            logger.error(f"Failed to update resource metadata: {str(e)}")
            await self.db_session.rollback()
            raise

    async def get_all_resources(
            self,
            filters: Optional[Dict[str, Any]] = None,
            sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[BaseStagedOutput]:
        """
        Get all resources matching the given filters (alias for list_resources)

        Args:
            filters (Optional[Dict]): Filter criteria for resources
            sort (Optional[List[Tuple[str, int]]]): List of (field, direction) tuples for sorting

        Returns:
            List[BaseStagedOutput]: List of matching resources
        """
        try:
            # Convert filters to query params format
            query_params = filters or {}

            # Call the existing list_resources method
            return await self.list_resources(
                query_params=query_params,
                sort_params=sort
            )

        except Exception as e:
            logger.error(f"Error getting resources: {str(e)}", exc_info=True)
            return []

    async def list_data(
            self,
            filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        List data with filters (alias for compatibility with staging manager)

        Args:
            filters (Optional[Dict]): Filter criteria

        Returns:
            List[Dict[str, Any]]: List of resources as dictionaries
        """
        try:
            resources = await self.get_all_resources(filters=filters)

            # Convert SQLAlchemy models to dictionaries
            return [
                {
                    'id': str(resource.id),
                    'status': resource.status,
                    'created_at': resource.created_at.isoformat(),
                    'metadata': resource.metadata or {},
                    'resource_type': resource.resource_type,
                    'storage_location': resource.storage_location
                }
                for resource in resources
            ]

        except Exception as e:
            logger.error(f"Error listing data: {str(e)}", exc_info=True)
            return []

    async def create_control_point(
            self,
            data: Dict[str, Any],
            user_id: Optional[UUID] = None
    ) -> StagingControlPoint:
        """Create staging control point with tracking"""
        try:
            control_point = await self.create(data, StagingControlPoint)

            # Track control point creation
            await self.create({
                'staged_output_id': control_point.resource_id,
                'event_type': 'control_point_created',
                'status': 'created',
                'details': {
                    'control_point_id': str(control_point.id),
                    'user_id': str(user_id) if user_id else None
                }
            }, StagingProcessingHistory)

            return control_point

        except Exception as e:
            logger.error(f"Failed to create control point: {str(e)}")
            raise

    async def get_resource_history(
            self,
            resource_id: UUID,
            event_type: Optional[str] = None
    ) -> List[StagingProcessingHistory]:
        """Get resource history with optional filtering"""
        try:
            query = self.db_session.query(StagingProcessingHistory) \
                .filter(StagingProcessingHistory.staged_output_id == resource_id)

            if event_type:
                query = query.filter(StagingProcessingHistory.event_type == event_type)

            return await query.order_by(StagingProcessingHistory.created_at).all()

        except Exception as e:
            logger.error(f"Error retrieving resource history: {str(e)}")
            raise

    async def cleanup_expired_resources(self) -> List[UUID]:
        """Cleanup expired resources with proper tracking"""
        try:
            current_time = datetime.utcnow()
            expired_resources = await self.db_session.query(BaseStagedOutput) \
                .filter(
                BaseStagedOutput.expires_at <= current_time,
                BaseStagedOutput.status.in_(['pending', 'awaiting_decision'])
            ).all()

            expired_ids = []
            for resource in expired_resources:
                resource.status = 'expired'
                expired_ids.append(resource.id)

                # Track expiration
                await self.create({
                    'staged_output_id': resource.id,
                    'event_type': 'resource_expired',
                    'status': 'expired',
                    'details': {
                        'expiry_time': resource.expires_at.isoformat()
                    }
                }, StagingProcessingHistory)

            await self.db_session.commit()
            return expired_ids

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to cleanup expired resources: {str(e)}")
            raise

    async def list_user_files(self, user_id: str) -> List[BaseStagedOutput]:
        """
        List all files for a specific user

        Args:
            user_id: ID of the user

        Returns:
            List[BaseStagedOutput]: List of user's files
        """
        try:
            return await self.list_resources({
                'user_id': user_id,
                'resource_type': 'file'
            }, sort_params=[('created_at', -1)])

        except Exception as e:
            logger.error(f"Error listing user files: {str(e)}")
            return []

    async def get_expired_resources(self, expiry_time: datetime) -> List[str]:
        """Get list of expired resource IDs based on expiry time."""
        try:
            # Remove stage_key from the query
            query = select(BaseStagedOutput).where(
                and_(
                    BaseStagedOutput.expires_at <= expiry_time,
                    BaseStagedOutput.status.in_(['pending', 'awaiting_decision'])
                )
            )

            result = await self.db_session.execute(query)
            expired_resources = result.scalars().all()

            # Track expiry check in history
            expired_ids = []
            for resource in expired_resources:
                resource.status = 'expired'
                resource.updated_at = datetime.utcnow()
                expired_ids.append(str(resource.id))

                # Track in history
                await self.create({
                    'staged_output_id': resource.id,
                    'event_type': 'expiry_check',
                    'status': 'expired',
                    'details': {
                        'expiry_time': expiry_time.isoformat(),
                        'previous_status': resource.status
                    }
                }, StagingProcessingHistory)

            if expired_ids:
                await self.db_session.commit()

            return expired_ids

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to get expired resources: {e}")
            raise

    async def cleanup_pending(self) -> List[str]:
        """Cleanup pending resources"""
        try:
            # Modified query without stage_key
            query = select(BaseStagedOutput).where(
                and_(
                    BaseStagedOutput.status == 'pending',
                    BaseStagedOutput.expires_at <= datetime.utcnow()
                )
            )

            result = await self.db_session.execute(query)
            pending_resources = result.scalars().all()

            cleaned_ids = []
            for resource in pending_resources:
                resource.status = 'expired'
                resource.updated_at = datetime.utcnow()
                cleaned_ids.append(resource.id)

                # Track cleanup in history
                await self.create({
                    'staged_output_id': resource.id,
                    'event_type': 'cleanup_pending',
                    'status': 'expired',
                    'details': {
                        'cleanup_time': datetime.utcnow().isoformat(),
                        'previous_status': 'pending'
                    }
                }, StagingProcessingHistory)

            if cleaned_ids:
                await self.db_session.commit()
                logger.info(f"Cleaned up {len(cleaned_ids)} pending resources")

            return cleaned_ids

        except Exception as e:
            await self.db_session.rollback()
            logger.error(f"Failed to cleanup pending resources: {e}")
            raise