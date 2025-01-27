# backend/data/source/file/file_service.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from werkzeug.datastructures import FileStorage

from core.control.cpm import ControlPointManager
from core.managers.staging_manager import StagingManager
from .file_handler import FileHandler
from .file_validator import FileValidator, FileValidationConfig

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