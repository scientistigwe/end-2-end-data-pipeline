# backend/source_handlers/cloud/s3_service.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4

from core.messaging.broker import MessageBroker
from core.managers.staging_manager import StagingManager
from core.control.cpm import ControlPointManager
from core.messaging.event_types import (
    MessageType, ProcessingStage, ModuleIdentifier, ComponentType
)
from .cloud_handler import CloudHandler
from .cloud_validator import S3Validator, S3ValidationConfig

logger = logging.getLogger(__name__)


class S3Service:
    """Service for handling S3 data operations at API layer"""

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager,
            cpm: ControlPointManager,
            config: Optional[S3ValidationConfig] = None
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.cpm = cpm
        self.config = config or S3ValidationConfig()

        # Initialize components
        self.handler = CloudHandler(
            staging_manager,
            message_broker,
            timeout=self.config.REQUEST_TIMEOUT
        )
        self.validator = S3Validator(config=self.config)

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="s3_service",
            component_type=ComponentType.SERVICE,
            department="source",
            role="service"
        )

    async def source_data(
            self,
            bucket: str,
            key: Optional[str] = None,
            operation: str = 'get',
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Source data from S3"""
        try:
            # Create metadata for tracking
            metadata = {
                'user_id': user_id,
                'source_type': 's3',
                'bucket': bucket,
                'key': key,
                'operation': operation
            }

            # Initial validation
            validation_result = await self.validator.validate_source({
                'bucket': bucket,
                'key': key,
                'operation': operation,
                'auth': auth
            })

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Process through handler
            result = await self.handler.handle_s3_request(
                bucket=bucket,
                key=key,
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
                    'source_type': 's3',
                    'staged_id': result['staged_id'],
                    'user_id': user_id,
                    's3_info': result['s3_info']
                }
            )

            return {
                'status': 'success',
                'staged_id': result['staged_id'],
                'control_point_id': control_point.id,
                'tracking_url': f'/api/sources/s3/{result["staged_id"]}/status'
            }

        except Exception as e:
            logger.error(f"S3 data sourcing error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def get_source_status(
            self,
            staged_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get S3 data processing status"""
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
                's3_info': staged_data['metadata'].get('s3_info'),
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
        """List S3 sources for a user"""
        try:
            # Get staged sources for user
            user_sources = await self.staging_manager.list_data(
                filters={'metadata.user_id': user_id, 'metadata.source_type': 's3'}
            )

            return {
                'status': 'success',
                'sources': [
                    {
                        'staged_id': f['id'],
                        'bucket': f['metadata'].get('bucket'),
                        'key': f['metadata'].get('key'),
                        'operation': f['metadata'].get('operation'),
                        'status': f['status'],
                        'fetched_at': f['created_at'],
                        's3_info': f['metadata'].get('s3_info')
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
        """Validate S3 credentials"""
        try:
            # Validate credentials
            validation_result = await self.validator.validate_source({
                'endpoint': credentials.get('endpoint'),
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