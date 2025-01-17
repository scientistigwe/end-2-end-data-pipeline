# backend/source_handlers/api/api_service.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4

from backend.core.messaging.broker import MessageBroker
from backend.core.staging.staging_manager import StagingManager
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.messaging.types import (
    MessageType, ProcessingStage, ModuleIdentifier, ComponentType
)
from .api_handler import APIHandler
from .api_validator import APIValidator
from .api_config import Config

logger = logging.getLogger(__name__)


class APIService:
    """Service for handling API data operations at API layer"""

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager,
            cpm: ControlPointManager,
            config: Optional[Config] = None
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.cpm = cpm
        self.config = config or Config()

        # Initialize components
        self.handler = APIHandler(
            staging_manager,
            message_broker,
            timeout=self.config.REQUEST_TIMEOUT
        )
        self.validator = APIValidator(config=self.config)

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="api_service",
            component_type=ComponentType.SERVICE,
            department="source",
            role="service"
        )

    async def fetch_data(
            self,
            endpoint: str,
            method: str = 'GET',
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, Any]] = None,
            body: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch data from an API endpoint"""
        try:
            # Create metadata for tracking
            metadata = {
                'user_id': user_id,
                'source_type': 'api',
                'endpoint': endpoint,
                'method': method
            }

            # Initial validation
            validation_result = await self.validator.validate_api_source({
                'endpoint': endpoint,
                'method': method,
                'headers': headers,
                'auth': auth
            })

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Process through handler
            result = await self.handler.handle_api_request(
                endpoint=endpoint,
                method=method,
                params=params,
                headers=headers,
                body=body,
                auth=auth,
                metadata=metadata
            )

            if result['status'] != 'success':
                return result

            # Create control point
            control_point = await self.cpm.create_control_point(
                stage=ProcessingStage.RECEPTION,
                metadata={
                    'source_type': 'api',
                    'staged_id': result['staged_id'],
                    'user_id': user_id,
                    'api_info': result['api_info']
                }
            )

            return {
                'status': 'success',
                'staged_id': result['staged_id'],
                'control_point_id': control_point.id,
                'tracking_url': f'/api/sources/api/{result["staged_id"]}/status'
            }

        except Exception as e:
            logger.error(f"API data fetch error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def get_source_status(
            self,
            staged_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get API data processing status"""
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
                'api_info': staged_data['metadata'].get('api_info'),
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
        """List API sources for a user"""
        try:
            # Get staged sources for user
            user_sources = await self.staging_manager.list_data(
                filters={'metadata.user_id': user_id, 'metadata.source_type': 'api'}
            )

            return {
                'status': 'success',
                'sources': [
                    {
                        'staged_id': f['id'],
                        'endpoint': f['metadata'].get('endpoint'),
                        'method': f['metadata'].get('method'),
                        'status': f['status'],
                        'fetched_at': f['created_at'],
                        'api_info': f['metadata'].get('api_info')
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
        """Validate API credentials"""
        try:
            # Validate credentials
            validation_result = await self.validator.validate_api_source({
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