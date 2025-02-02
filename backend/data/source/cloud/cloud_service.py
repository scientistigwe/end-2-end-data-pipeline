# backend/source_handlers/cloud/s3_service.py

import logging
from typing import Dict, Any, Optional, List, Union
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


# backend/source_handlers/cloud/s3_service.py

class S3Service:
    """Service for handling S3 data operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            cpm: ControlPointManager,
            config: Optional[Union[Dict[str, Any], S3ValidationConfig]] = None
    ):
        self.staging_manager = staging_manager
        self.cpm = cpm

        # Handle config initialization
        if isinstance(config, dict):
            self.config = S3ValidationConfig()
            for key, value in config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
        else:
            self.config = config or S3ValidationConfig()

        # Initialize components
        self.handler = CloudHandler(
            staging_manager=staging_manager,
            validator_config=self.config,
            timeout=getattr(self.config, 'REQUEST_TIMEOUT', 30)
        )
        self.validator = S3Validator(config=self.config)

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
            metadata = {
                'user_id': user_id,
                'source_type': 's3',
                'bucket': bucket,
                'key': key,
                'operation': operation,
                'timestamp': datetime.utcnow().isoformat()
            }

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

            result = await self.handler.handle_cloud_request(
                provider='aws',
                endpoint=bucket,
                path=key,
                operation=operation,
                params=params,
                auth=auth,
                metadata=metadata
            )

            if result['status'] != 'success':
                return result

            control_point = await self.cpm.create_control_point(
                stage=ProcessingStage.RECEPTION,
                metadata={
                    'source_type': 's3',
                    'staged_id': result['staged_id'],
                    'user_id': user_id,
                    's3_info': result['cloud_info']
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

    async def get_status(
            self,
            staged_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get S3 data processing status"""
        try:
            staged_data = await self.staging_manager.get_data(staged_id)
            if not staged_data:
                return {'status': 'not_found'}

            if staged_data['metadata'].get('user_id') != user_id:
                return {'status': 'unauthorized'}

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

    async def list_sources(
            self,
            user_id: str
    ) -> Dict[str, Any]:
        """List S3 sources for a user"""
        try:
            user_sources = await self.staging_manager.list_data(
                filters={
                    'metadata.user_id': user_id,
                    'metadata.source_type': 's3'
                }
            )

            return {
                'status': 'success',
                'sources': [
                    {
                        'staged_id': source['id'],
                        'bucket': source['metadata'].get('bucket'),
                        'key': source['metadata'].get('key'),
                        'operation': source['metadata'].get('operation'),
                        'status': source['status'],
                        'fetched_at': source['created_at'],
                        's3_info': source['metadata'].get('s3_info')
                    }
                    for source in user_sources
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

