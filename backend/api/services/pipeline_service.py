# backend/api/services/pipeline_service.py

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType, ProcessingStage, ProcessingStatus,
    ModuleIdentifier, ComponentType, ProcessingMessage
)
from backend.core.control.cpm import ControlPointManager
from backend.core.staging.staging_manager import StagingManager
from backend.db.repository.pipeline_repository import PipelineRepository

logger = logging.getLogger(__name__)


class PipelineService:
    """Service for coordinating data processing pipelines"""

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager,
            cpm: ControlPointManager,
            repository: PipelineRepository
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.cpm = cpm
        self.repository = repository

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="pipeline_service",
            component_type=ComponentType.SERVICE,
            department="pipeline",
            role="service"
        )

    async def create_pipeline(
            self,
            config: Dict[str, Any],
            user_id: str
    ) -> Dict[str, Any]:
        """Create new pipeline"""
        try:
            # Validate configuration
            if not self._validate_pipeline_config(config):
                raise ValueError("Invalid pipeline configuration")

            # Create pipeline record
            pipeline = await self.repository.create_pipeline({
                **config,
                'user_id': user_id,
                'status': 'created'
            })

            # Create initial control point
            control_point = await self.cpm.create_control_point(
                stage=ProcessingStage.RECEPTION,
                metadata={
                    'pipeline_id': pipeline['id'],
                    'config': config
                }
            )

            return {
                'status': 'success',
                'pipeline_id': pipeline['id'],
                'control_point_id': control_point.id
            }

        except Exception as e:
            logger.error(f"Pipeline creation error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def start_pipeline(
            self,
            pipeline_id: UUID,
            user_id: str,
            staged_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Start pipeline processing"""
        try:
            # Verify pipeline
            pipeline = await self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")

            if pipeline['user_id'] != user_id:
                raise ValueError("Unauthorized")

            # Get staged data if provided
            staged_data = None
            if staged_id:
                staged_data = await self.staging_manager.get_data(staged_id)
                if not staged_data:
                    raise ValueError("Staged data not found")

            # Create processing control point
            control_point = await self.cpm.create_control_point(
                stage=ProcessingStage.QUALITY_CHECK,
                metadata={
                    'pipeline_id': str(pipeline_id),
                    'staged_id': staged_id,
                    'config': pipeline['config'],
                    'data_info': staged_data['metadata'] if staged_data else None
                }
            )

            # Update pipeline status
            await self.repository.update_pipeline_status(
                pipeline_id,
                'running',
                {
                    'started_at': datetime.utcnow().isoformat(),
                    'control_point_id': control_point.id
                }
            )

            return {
                'status': 'success',
                'pipeline_id': str(pipeline_id),
                'control_point_id': control_point.id
            }

        except Exception as e:
            logger.error(f"Pipeline start error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def get_pipeline_status(
            self,
            pipeline_id: UUID,
            user_id: str
    ) -> Dict[str, Any]:
        """Get pipeline status with component details"""
        try:
            # Get pipeline
            pipeline = await self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")

            if pipeline['user_id'] != user_id:
                raise ValueError("Unauthorized")

            # Get control point status
            control_status = None
            if pipeline.get('control_point_id'):
                control_status = await self.cpm.get_status(
                    pipeline['control_point_id']
                )

            # Get staging status if available
            staging_status = None
            if pipeline.get('staged_id'):
                staged_data = await self.staging_manager.get_data(
                    pipeline['staged_id']
                )
                if staged_data:
                    staging_status = {
                        'status': staged_data['status'],
                        'metadata': staged_data['metadata']
                    }

            return {
                'status': 'success',
                'pipeline_status': pipeline['status'],
                'control_status': control_status,
                'staging_status': staging_status,
                'metadata': pipeline['metadata'],
                'last_updated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Status retrieval error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def list_pipelines(
            self,
            user_id: str,
            filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """List pipelines for user"""
        try:
            pipelines = await self.repository.list_pipelines(
                user_id=user_id,
                filters=filters
            )

            return {
                'status': 'success',
                'pipelines': [
                    {
                        'id': str(p['id']),
                        'name': p['name'],
                        'status': p['status'],
                        'created_at': p['created_at'],
                        'last_run': p.get('last_run'),
                        'config': p['config']
                    }
                    for p in pipelines
                ]
            }

        except Exception as e:
            logger.error(f"Pipeline listing error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def handle_component_complete(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle component completion"""
        try:
            # Extract information
            pipeline_id = message.metadata.get('pipeline_id')
            component_type = message.metadata.get('component_type')

            if not pipeline_id or not component_type:
                logger.error("Missing required metadata")
                return

            # Get pipeline
            pipeline = await self.repository.get_pipeline(UUID(pipeline_id))
            if not pipeline:
                logger.error(f"Pipeline not found: {pipeline_id}")
                return

            # Store component output
            if message.content.get('output'):
                await self.staging_manager.store_data(
                    data=message.content['output'],
                    metadata={
                        'pipeline_id': pipeline_id,
                        'component_type': component_type,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    source_type=component_type
                )

            # Update pipeline status
            await self._update_pipeline_status(
                UUID(pipeline_id),
                message
            )

        except Exception as e:
            logger.error(f"Component completion handling error: {str(e)}")

    async def _update_pipeline_status(
            self,
            pipeline_id: UUID,
            message: ProcessingMessage
    ) -> None:
        """Update pipeline status based on component completion"""
        try:
            # Get pipeline stage sequence
            pipeline = await self.repository.get_pipeline(pipeline_id)
            if not pipeline:
                return

            current_stage = message.metadata.get('processing_stage')
            if not current_stage:
                return

            # Determine next stage
            next_stage = self._get_next_stage(
                current_stage,
                pipeline['config'].get('stage_sequence', [])
            )

            # Update status
            if next_stage:
                await self.repository.update_pipeline_status(
                    pipeline_id,
                    'running',
                    {
                        'current_stage': next_stage,
                        'last_completed_stage': current_stage
                    }
                )
            else:
                # Pipeline complete
                await self.repository.update_pipeline_status(
                    pipeline_id,
                    'completed',
                    {
                        'completed_at': datetime.utcnow().isoformat(),
                        'last_completed_stage': current_stage
                    }
                )

        except Exception as e:
            logger.error(f"Status update error: {str(e)}")

    def _get_next_stage(
            self,
            current_stage: str,
            stage_sequence: List[str]
    ) -> Optional[str]:
        """Get next stage in sequence"""
        try:
            current_idx = stage_sequence.index(current_stage)
            if current_idx < len(stage_sequence) - 1:
                return stage_sequence[current_idx + 1]
            return None
        except ValueError:
            return None

    def _validate_pipeline_config(self, config: Dict[str, Any]) -> bool:
        """Validate pipeline configuration"""
        required_fields = ['name', 'stage_sequence']
        return all(field in config for field in required_fields)