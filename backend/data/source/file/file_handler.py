# backend/data/source/file/file_handler.py

import uuid
import logging
from typing import Dict, Any, Optional, BinaryIO, List
from datetime import datetime
from pathlib import Path
import aiofiles
import hashlib

from core.managers.staging_manager import StagingManager
from core.messaging.event_types import ComponentType
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

                # Generate stage key and ensure essential metadata
                stage_key = f"file_{datetime.now().timestamp()}"
                pipeline_id = metadata.get('pipeline_id') if metadata else str(uuid.uuid4())

                # Build complete metadata
                complete_metadata = {
                    'stage_key': stage_key,
                    'pipeline_id': pipeline_id,
                    'resource_type': 'file',
                    'name': filename,
                    'format': content_type,
                    'original_filename': filename,
                    'content_type': content_type,

                    # Add defaults for required fields
                    'component_type': 'ANALYTICS',
                    'model_type': 'DEFAULT',  # Default value for required model_type field
                    'status': 'PENDING',

                    # Including any provided metadata
                    **(metadata or {})
                }

                # Store in staging with required fields
                staged_id = await self.stage_file(
                    temp_path,
                    filename,
                    file_info,
                    complete_metadata
                )

                return {
                    'status': 'success',
                    'staged_id': staged_id,
                    'file_info': file_info,
                    'stage_key': stage_key,
                    'pipeline_id': pipeline_id
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
            metadata: Dict[str, Any]
    ) -> str:
        """Store file in staging area"""
        try:
            # Read file content
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()

            # Generate or use existing stage key
            stage_key = metadata.get('stage_key') or f"file_{datetime.now().timestamp()}_{uuid.uuid4().hex}"
            pipeline_id = metadata.get('pipeline_id') or str(uuid.uuid4())

            # Ensure metadata contains stage_key
            metadata['stage_key'] = stage_key

            # Create staging metadata with all required fields
            staging_metadata = {
                'stage_key': stage_key,
                'pipeline_id': pipeline_id,
                'component_type': 'ANALYTICS',  # Use correct enum value
                'model_type': 'DEFAULT',  # Required field for staged_analytics_outputs
                'status': 'PENDING',
                'storage_path': str(file_path),
                'data_size': len(content),
                'meta_data': {
                    'original_filename': filename,
                    'file_info': file_info,
                    **{k: v for k, v in metadata.items() if
                       k not in ['stage_key', 'pipeline_id', 'component_type', 'model_type', 'status']}
                },
                'is_temporary': True,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
            }

            # Ensure any other required fields are set
            if 'source_id' not in staging_metadata:
                staging_metadata['source_id'] = None  # Set to None if not provided

            # Log the metadata we're passing to the staging manager
            logger.info(f"Staging file with metadata: {staging_metadata}")

            # Store in staging manager
            result = await self.staging_manager.store_data(
                data=content,
                metadata=staging_metadata,
                source_type='file'
            )

            return result['staged_id']

        except Exception as e:
            logger.error(f"File staging error: {str(e)}", exc_info=True)
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

    async def _process_file(
            self,
            file: BinaryIO,
            temp_path: Path
    ) -> Dict[str, Any]:
        """
        Process file and calculate metadata

        Args:
            file: File-like object to process
            temp_path: Path to save temporary file

        Returns:
            Dict containing file information including size, hash, etc.
        """
        try:
            size = 0
            sha256_hash = hashlib.sha256()

            # Write file in chunks while calculating hash and size
            async with aiofiles.open(temp_path, 'wb') as out_file:
                while True:
                    chunk = file.read(self.chunk_size)
                    if not chunk:
                        break

                    # Update hash
                    sha256_hash.update(chunk)

                    # Write chunk
                    await out_file.write(chunk)

                    # Update size
                    size += len(chunk)

            # Get file stats
            stats = temp_path.stat()

            return {
                'size': size,
                'checksum': sha256_hash.hexdigest(),
                'created_at': datetime.fromtimestamp(stats.st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stats.st_mtime).isoformat(),
                'mime_type': self._get_mime_type(temp_path),
                'extension': temp_path.suffix.lower()[1:] if temp_path.suffix else None
            }

        except Exception as e:
            logger.error(f"File processing error: {str(e)}", exc_info=True)
            raise

    def _get_mime_type(self, file_path: Path) -> str:
        """Get MIME type from file path"""
        import mimetypes
        mime_type, _ = mimetypes.guess_type(str(file_path))
        return mime_type or 'application/octet-stream'