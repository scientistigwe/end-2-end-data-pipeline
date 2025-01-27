# backend/source_handlers/database/db_service.py

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
from .db_handler import DatabaseHandler
from .db_validator import DatabaseSourceValidator, DatabaseValidationConfig

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for handling database data operations at API layer"""

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager,
            cpm: ControlPointManager,
            config: Optional[DatabaseValidationConfig] = None
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.cpm = cpm
        self.config = config or DatabaseValidationConfig()

        # Initialize components
        self.handler = DatabaseHandler(
            staging_manager,
            message_broker,
            timeout=self.config.REQUEST_TIMEOUT
        )
        self.validator = DatabaseSourceValidator(config=self.config)

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="database_service",
            component_type=ComponentType.SERVICE,
            department="source",
            role="service"
        )

    async def source_data(
            self,
            source_type: str,
            host: str,
            database: str,
            query: str,
            operation: str = 'read',
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Source data from database"""
        try:
            # Create metadata for tracking
            metadata = {
                'user_id': user_id,
                'source_type': 'database',
                'db_type': source_type,
                'host': host,
                'database': database,
                'operation': operation
            }

            # Initial validation
            validation_result = await self.validator.validate_source({
                'source_type': source_type,
                'host': host,
                'database': database,
                'operation': operation,
                'auth': auth
            })

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Process through handler
            result = await self.handler.handle_database_request(
                source_type=source_type,
                host=host,
                database=database,
                query=query,
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
                    'source_type': 'database',
                    'staged_id': result['staged_id'],
                    'user_id': user_id,
                    'db_info': result['db_info']
                }
            )

            return {
                'status': 'success',
                'staged_id': result['staged_id'],
                'control_point_id': control_point.id,
                'tracking_url': f'/api/sources/database/{result["staged_id"]}/status'
            }

        except Exception as e:
            logger.error(f"Database data sourcing error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def get_source_status(
            self,
            staged_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get database data processing status"""
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
                'db_info': staged_data['metadata'].get('db_info'),
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
        """List database sources for a user"""
        try:
            # Get staged sources for user
            user_sources = await self.staging_manager.list_data(
                filters={'metadata.user_id': user_id, 'metadata.source_type': 'database'}
            )

            return {
                'status': 'success',
                'sources': [
                    {
                        'staged_id': f['id'],
                        'source_type': f['metadata'].get('db_type'),
                        'host': f['metadata'].get('host'),
                        'database': f['metadata'].get('database'),
                        'operation': f['metadata'].get('operation'),
                        'status': f['status'],
                        'fetched_at': f['created_at'],
                        'db_info': f['metadata'].get('db_info')
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
        """Validate database credentials"""
        try:
            # Validate credentials
            validation_result = await self.validator.validate_source({
                'source_type': credentials.get('source_type'),
                'host': credentials.get('host'),
                'database': credentials.get('database'),
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
        """Cancel an active database operation"""
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
            logger.info("DatabaseService resources cleaned up")
        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}", exc_info=True)