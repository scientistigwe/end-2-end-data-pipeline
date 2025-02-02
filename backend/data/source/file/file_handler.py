# backend/data/source/file/file_handler.py

import logging
from typing import Dict, Any, Optional, BinaryIO, List
from datetime import datetime
from pathlib import Path
import aiofiles
import hashlib

from core.managers.staging_manager import StagingManager
from .file_validator import FileValidator

logger = logging.getLogger(__name__)

class FileHandler:
    """Handler for file processing operations"""

    def __init__(self, staging_manager: StagingManager):
        self.staging_manager = staging_manager
        self.validator = FileValidator()
        self.chunk_size = 8192  # 8KB chunks
        self.temp_dir = Path("temp")
        self.temp_dir.mkdir(exist_ok=True)

    async def handle_file(
            self,
            file: BinaryIO,
            filename: str,
            content_type: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process incoming file"""
        try:
            # Generate temp path
            temp_path = self.temp_dir / f"temp_{datetime.now().timestamp()}_{filename}"

            try:
                # Process file
                file_info = await self._process_file(file, temp_path)

                # Store in staging
                staged_id = await self.stage_file(
                    temp_path,
                    filename,
                    file_info,
                    metadata
                )

                return {
                    'status': 'success',
                    'staged_id': staged_id,
                    'file_info': file_info
                }

            finally:
                # Cleanup temp file
                if temp_path.exists():
                    temp_path.unlink()

        except Exception as e:
            logger.error(f"File handling error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def stage_file(
            self,
            file_path: Path,
            filename: str,
            file_info: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store file in staging area"""
        try:
            # Read file content
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()

            # Create staging metadata
            staging_metadata = {
                'filename': filename,
                'file_info': file_info,
                **(metadata or {})
            }

            # Store in staging
            return await self.staging_manager.store_data(
                data=content,
                metadata=staging_metadata,
                source_type='file'
            )

        except Exception as e:
            logger.error(f"File staging error: {str(e)}")
            raise

    def list_files(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List files in staging area for a user

        Args:
            user_id: ID of the user

        Returns:
            List of file metadata
        """
        try:
            # Query staging area for user's files
            staged_files = self.staging_manager.get_staged_files(
                filter_params={
                    'user_id': user_id,
                    'source_type': 'file'
                }
            )

            return [
                {
                    'staged_id': file['id'],
                    'filename': file['metadata'].get('original_filename', ''),
                    'status': file['status'],
                    'created_at': file['created_at'],
                    'metadata': file['metadata'],
                    'size': file['metadata'].get('size', 0),
                    'mime_type': file['metadata'].get('mime_type', ''),
                    'processing_status': file['processing_status']
                }
                for file in staged_files
            ]
        except Exception as e:
            logger.error(f"Error listing staged files: {str(e)}")
            return []