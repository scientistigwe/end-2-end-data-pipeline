# backend/source_handlers/stream/stream_service.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4

from core.messaging.broker import MessageBroker
from core.staging.staging_manager import StagingManager
from core.control.cpm import ControlPointManager
from core.messaging.event_types import (
    MessageType, ProcessingStage, ModuleIdentifier, ComponentType
)
from .stream_handler import StreamHandler
from .stream_validator import StreamSourceValidator, StreamValidationConfig

logger = logging.getLogger(__name__)


class StreamService:
    """Service for handling stream data operations at API layer"""

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager,
            cpm: ControlPointManager,
            config: Optional[StreamValidationConfig] = None
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.cpm = cpm
        self.config = config or StreamValidationConfig()

        # Initialize components
        self.handler = StreamHandler(
            staging_manager,
            message_broker,
            timeout=self.config.REQUEST_TIMEOUT
        )
        self.validator = StreamSourceValidator(config=self.config)

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="stream_service",
            component_type=ComponentType.SERVICE,
            department="source",
            role="service"
        )

    async def source_data(
            self,
            stream_type: str,
            topic: str,
            operation: str = 'consume',
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Source data from stream"""
        try:
            # Create metadata for tracking
            metadata = {
                'user_id': user_id,
                'source_type': 'stream',
                'stream_type': stream_type,
                'topic': topic,
                'operation': operation
            }

            # Initial validation
            validation_result = await self.validator.validate_source({
                'stream_type': stream_type,
                'topic': topic,
                'operation': operation,
                'auth': auth
            })

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Process through handler
            result = await self.handler.handle_stream_request(
                stream_type=stream_type,
                topic=topic,
                operation=operation,
                params=params,
                auth=auth,
                metadata=metadata
            )

            if result['status'] != 'success':
                return result

            # Create control point
            control_point = await self.cpm.create_control_point(
                stage=ProcessingStage.RECEPTION,
                metadata={
                    'source_type': 'stream',
                    'staged_id': result['staged_id'],
                    'user_id': user_id,
                    'stream_info': result['stream_info']
                }
            )

            return {
                'status': 'success',
                'staged_id': result['staged_id'],
                'control_point_id': control_point.id,
                'tracking_url': f'/api/sources/stream/{result["staged_id"]}/status'
            }

        except Exception as e:
            logger.error(f"Stream data sourcing error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def get_source_status(
            self,
            staged_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get stream data processing status"""
        try:
            # Get staging status
            staged_data = await self.staging_manager.get_data(staged_id)
            if not staged_data:
                return {'status': 'not_found'}

            # Check authorization
            if staged_data['metadata'].get('user_id') != user_id:
                return {'status': 'unauthorized'}

            # Get control point status
            control_status = await self.cpm.get_status(
                staged_data['metadata'].get('control_point_id')
            )

            return {
                'staged_id': staged_id,
                'status': staged_data['status'],
                'control_status': control_status,
                'stream_info': staged_data['metadata'].get('stream_info'),
                'last_updated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Status retrieval error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def list_user_sources(
            self,
            user_id: str
    ) -> Dict[str, Any]:
        """List stream sources for a user"""
        try:
            # Get staged sources for user
            user_sources = await self.staging_manager.list_data(
                filters={'metadata.user_id': user_id, 'metadata.source_type': 'stream'}
            )

            return {
                'status': 'success',
                'sources': [
                    {
                        'staged_id': f['id'],
                        'stream_type': f['metadata'].get('stream_type'),
                        'topic': f['metadata'].get('topic'),
                        'operation': f['metadata'].get('operation'),
                        'status': f['status'],
                        'fetched_at': f['created_at'],
                        'stream_info': f['metadata'].get('stream_info')
                    }
                    for f in user_sources
                ]
            }

        except Exception as e:
            logger.error(f"Source listing error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def validate_credentials(
            self,
            credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate stream credentials"""
        try:
            # Validate credentials
            validation_result = await self.validator.validate_source({
                'stream_type': credentials.get('stream_type'),
                'topic': credentials.get('topic'),
                'auth': credentials
            })

            return {
                'status': 'success' if validation_result['passed'] else 'error',
                'validation_details': validation_result
            }

        except Exception as e:
            logger.error(f"Credential validation error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def cancel_operation(self, staged_id: str) -> Dict[str, Any]:
        """Cancel an active stream operation"""
        try:
            # Retrieve staged data
            staged_data = await self.staging_manager.get_data(staged_id)
            if not staged_data:
                return {
                    'status': 'error',
                    'message': f'Operation {staged_id} not found'
                }

            # Update status to cancelled
            await self.staging_manager.update_data_status(
                staged_id,
                status='cancelled'
            )

            return {
                'status': 'success',
                'message': f'Operation {staged_id} cancelled'
            }

        except Exception as e:
            logger.error(f"Operation cancellation error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def cleanup(self) -> None:
        """Clean up service resources"""
        try:
            logger.info("StreamService resources cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}", exc_info=True)