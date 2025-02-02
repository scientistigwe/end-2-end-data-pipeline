# backend/data/source/file/file_service.py

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from werkzeug.datastructures import FileStorage

from core.control.cpm import ControlPointManager
from core.managers.staging_manager import StagingManager
from .file_handler import FileHandler
from .file_validator import FileValidator
from config.validation_config import FileValidationConfig

logger = logging.getLogger(__name__)

class FileService:
    """Service for handling file operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            cpm: ControlPointManager,
            config: Optional[FileValidationConfig] = None
    ):
        self.staging_manager = staging_manager
        self.cpm = cpm
        self.config = config or FileValidationConfig()
        
        # Initialize components
        self.handler = FileHandler(staging_manager)
        self.validator = FileValidator()

    def process_file_upload(
            self,
            file: FileStorage,
            metadata: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Process file upload (synchronous wrapper around async handle_upload)"""
        import json
        import asyncio

        try:
            metadata_dict = json.loads(metadata) if isinstance(metadata, str) else metadata

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.handle_upload(file, user_id, metadata_dict)
            )
            loop.close()

            # Format response to match schema
            return {
                'status': result.get('status', 'error'),
                'staged_id': result.get('staged_id', ''),
                'control_point_id': result.get('control_point_id', ''),
                'tracking_url': result.get('tracking_url', ''),
                'upload_status': 'completed' if result.get('status') == 'success' else 'failed',
                'error': result.get('error'),
                'message': result.get('message')
            }

        except Exception as e:
            logger.error(f"File upload processing error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'message': "File upload failed",
                'staged_id': '',
                'control_point_id': '',
                'tracking_url': '',
                'upload_status': 'failed'
            }

    async def handle_upload(
            self,
            file: FileStorage,
            user_id: str,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Handle file upload"""
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
                metadata
            )

            if result['status'] != 'success':
                return result

            # Notify CPM with metadata
            control_point = await self.cpm.create_control_point(
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

    def list_sources(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List file sources for a user

        Args:
            user_id: ID of the user

        Returns:
            List of file sources
        """
        try:
            # Get files from staging area using the new method
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            staged_files = loop.run_until_complete(
                self.staging_manager.list_files(user_id)
            )
            loop.close()

            return staged_files

        except Exception as e:
            logger.error(f"Error listing file sources: {str(e)}")
            # Return empty list on error rather than raise
            return []