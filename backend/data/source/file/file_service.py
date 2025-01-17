# backend/data/source/file/file_service.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from werkzeug.datastructures import FileStorage

from backend.core.messaging.broker import MessageBroker
from backend.core.staging.staging_manager import StagingManager
from backend.core.control.cpm import ControlPointManager
from backend.core.messaging.types import (
    MessageType, ProcessingStage, ModuleIdentifier, ComponentType
)
from .file_handler import FileHandler
from .file_validator import FileValidator

logger = logging.getLogger(__name__)


class FileService:
    """Service for handling file operations at API layer"""

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager,
            cpm: ControlPointManager
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.cpm = cpm

        # Initialize components
        self.handler = FileHandler(staging_manager, message_broker)
        self.validator = FileValidator()

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="file_service",
            component_type=ComponentType.SERVICE,
            department="source",
            role="service"
        )

    async def handle_upload(
            self,
            file: FileStorage,
            user_id: str,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle file upload request"""
        try:
            # Initial validation
            validation_result = await self.validator.validate_file_source(
                file.filename,
                {
                    'content_type': file.content_type,
                    'user_id': user_id,
                    **(metadata or {})
                }
            )

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Process through handler
            result = await self.handler.handle_file(
                file.stream,
                file.filename,
                file.content_type,
                {
                    'user_id': user_id,
                    **(metadata or {})
                }
            )

            if result['status'] != 'success':
                return result

            # Create control point
            control_point = await self.cpm.create_control_point(
                stage=ProcessingStage.RECEPTION,
                metadata={
                    'source_type': 'file',
                    'staged_id': result['staged_id'],
                    'user_id': user_id,
                    'file_info': result['file_info']
                }
            )

            return {
                'status': 'success',
                'staged_id': result['staged_id'],
                'control_point_id': control_point.id,
                'tracking_url': f'/api/files/{result["staged_id"]}/status'
            }

        except Exception as e:
            logger.error(f"Upload handling error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def get_file_status(
            self,
            staged_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get file processing status"""
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
                'file_info': staged_data['metadata'].get('file_info'),
                'last_updated': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Status retrieval error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def list_user_files(
            self,
            user_id: str
    ) -> Dict[str, Any]:
        """List files for a user"""
        try:
            # Get staged files for user
            user_files = await self.staging_manager.list_data(
                filters={'metadata.user_id': user_id}
            )

            return {
                'status': 'success',
                'files': [
                    {
                        'staged_id': f['id'],
                        'filename': f['metadata'].get('filename'),
                        'status': f['status'],
                        'uploaded_at': f['created_at'],
                        'file_info': f['metadata'].get('file_info')
                    }
                    for f in user_files
                ]
            }

        except Exception as e:
            logger.error(f"File listing error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }