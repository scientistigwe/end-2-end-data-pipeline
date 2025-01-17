# backend/db/repository/staging_repository.py

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy import and_, or_, desc, func

from .base_repository import BaseRepository
from ..models.staging.base_staging_model import BaseStagedOutput
from ..models.staging.staging_control_model import StagingControlPoint
from ..models.staging.staging_history_model import StagingProcessingHistory

logger = logging.getLogger(__name__)


class StagingRepository(BaseRepository[BaseStagedOutput]):
    """Repository for staging operations with enhanced error handling and logging"""

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
            query = self.db_session.query(BaseStagedOutput) \
                .filter(BaseStagedOutput.pipeline_id == pipeline_id)

            if status:
                query = query.filter(BaseStagedOutput.status == status)
            if resource_type:
                query = query.filter(BaseStagedOutput.resource_type == resource_type)

            return await query.all()

        except Exception as e:
            logger.error(f"Error retrieving pipeline resources: {str(e)}")
            raise

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