# backend/source_handlers/database/db_service.py

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from utils.exceptions import ResourceNotFoundError, ValidationError

from core.managers.staging_manager import StagingManager
from core.control.cpm import ControlPointManager
from core.messaging.broker import MessageBroker
from core.messaging.event_types import ProcessingStage, MessageType, ProcessingMessage
from .db_handler import DatabaseHandler
from .db_validator import DatabaseSourceValidator
from config.validation_config import DatabaseValidationConfig

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for handling database data operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            cpm: ControlPointManager,
            config: Optional[DatabaseValidationConfig] = None
    ):
        """
        Initialize database service with required dependencies

        Args:
            staging_manager: Manager for staging operations
            cpm: Control point manager for workflow control
            message_broker: Message broker for async communication
            config: Optional validation configuration
        """
        self.staging_manager = staging_manager
        self.cpm = cpm
        self.config = config or DatabaseValidationConfig()

        # Initialize components
        self.handler = DatabaseHandler(
            staging_manager=staging_manager
        )
        self.validator = DatabaseSourceValidator(config=self.config)

        # Track active operations
        self.active_operations: Dict[str, Dict[str, Any]] = {}

    async def _notify_operation_status(
            self,
            operation_id: str,
            status: str,
            details: Dict[str, Any]
    ):
        """Send operation status notification"""
        try:
            message = ProcessingMessage(
                message_type=MessageType.DATABASE_OPERATION_STATUS,
                content={
                    'operation_id': operation_id,
                    'status': status,
                    'details': details,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            await self.message_broker.publish(message)
        except Exception as e:
            logger.error(f"Failed to send status notification: {str(e)}")

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
        operation_id = None
        try:
            # Generate unique operation ID
            operation_id = f"db_op_{datetime.utcnow().timestamp()}"

            # Create metadata for tracking
            metadata = {
                'operation_id': operation_id,
                'user_id': user_id,
                'source_type': 'database',
                'db_type': source_type,
                'host': host,
                'database': database,
                'operation': operation
            }

            # Track operation
            self.active_operations[operation_id] = {
                'start_time': datetime.utcnow(),
                'status': 'initializing',
                'metadata': metadata
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
                await self._notify_operation_status(
                    operation_id,
                    'validation_failed',
                    {'errors': validation_result['issues']}
                )
                return {
                    'status': 'error',
                    'operation_id': operation_id,
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
                await self._notify_operation_status(
                    operation_id,
                    'handler_failed',
                    result
                )
                return {
                    **result,
                    'operation_id': operation_id
                }

            # Create control point
            control_point = await self.cpm.create_control_point(
                stage=ProcessingStage.RECEPTION,
                metadata={
                    'source_type': 'database',
                    'staged_id': result['staged_id'],
                    'operation_id': operation_id,
                    'user_id': user_id,
                    'db_info': result['db_info']
                }
            )

            # Update operation status
            self.active_operations[operation_id]['status'] = 'success'
            self.active_operations[operation_id]['complete_time'] = datetime.utcnow()

            await self._notify_operation_status(
                operation_id,
                'success',
                {
                    'staged_id': result['staged_id'],
                    'control_point_id': control_point.id
                }
            )

            return {
                'status': 'success',
                'operation_id': operation_id,
                'staged_id': result['staged_id'],
                'control_point_id': control_point.id,
                'tracking_url': f'/api/sources/database/{result["staged_id"]}/status'
            }

        except Exception as e:
            error_details = {
                'error': str(e),
                'operation_id': operation_id
            }
            logger.error(f"Database data sourcing error: {str(e)}", exc_info=True)

            if operation_id:
                await self._notify_operation_status(
                    operation_id,
                    'error',
                    error_details
                )

            return {
                'status': 'error',
                **error_details
            }
        finally:
            if operation_id in self.active_operations:
                if self.active_operations[operation_id]['status'] == 'initializing':
                    self.active_operations[operation_id]['status'] = 'error'
                self.active_operations[operation_id]['end_time'] = datetime.utcnow()

    async def get_source_status(
            self,
            staged_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get database data processing status"""
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
                'db_info': staged_data['metadata'].get('db_info'),
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
    ) -> Dict[str, Union[str, List[Dict[str, Any]]]]:
        """
        List database sources for a user

        Args:
            user_id (str): ID of the user whose sources to list

        Returns:
            Dict containing:
                - status (str): Operation status ('success' or 'error')
                - sources (List[Dict]): List of source information
                - error (str, optional): Error message if status is 'error'

        Raises:
            ResourceNotFoundError: If no sources are found
            ValidationError: If user_id is invalid
        """
        try:
            if not user_id:
                raise ValidationError("User ID is required")

            # Add timing for performance monitoring
            start_time = datetime.utcnow()

            user_sources = await self.staging_manager.list_data(
                filters={
                    'metadata.user_id': user_id,
                    'metadata.source_type': 'database'
                }
            )

            # Log performance metrics
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.debug(f"Listed {len(user_sources)} sources in {duration:.2f}s")

            if not user_sources:
                return {
                    'status': 'success',
                    'sources': []
                }

            return {
                'status': 'success',
                'sources': [
                    self._format_source_data(source)
                    for source in user_sources
                ]
            }

        except ValidationError as e:
            logger.warning(f"Validation error in list_sources: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Unexpected error in list_sources: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': "Internal server error"
            }

    def _format_source_data(self, source: Dict) -> Dict[str, Any]:
        """Helper method to format source data consistently"""
        return {
            'staged_id': source['id'],
            'source_type': source['metadata'].get('db_type'),
            'host': source['metadata'].get('host'),
            'database': source['metadata'].get('database'),
            'operation': source['metadata'].get('operation'),
            'status': source['status'],
            'fetched_at': source['created_at'],
            'db_info': source['metadata'].get('db_info')
        }