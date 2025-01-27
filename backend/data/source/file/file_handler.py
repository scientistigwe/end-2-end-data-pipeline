# backend/data/source/file/file_handler.py

import asyncio
import logging
from typing import Dict, Any, Optional, BinaryIO
from datetime import datetime
from pathlib import Path
import aiofiles
import hashlib

from core.messaging.broker import MessageBroker
from core.managers.staging_manager import StagingManager
from core.messaging.event_types import (
    MessageType, ProcessingMessage, ModuleIdentifier, ComponentType
)
from .file_validator import FileValidator

logger = logging.getLogger(__name__)


class FileHandler:
    """Core handler for file processing operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            message_broker: MessageBroker
    ):
        self.staging_manager = staging_manager
        self.message_broker = message_broker
        self.validator = FileValidator()

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="file_handler",
            component_type=ComponentType.HANDLER,
            department="source",
            role="handler"
        )

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
            # Generate unique temp path
            temp_path = self.temp_dir / f"temp_{datetime.now().timestamp()}_{filename}"

            try:
                # Process file
                file_info = await self._process_file(file, temp_path)

                # Validate file
                validation_result = await self.validator.validate_file_source(
                    temp_path,
                    {
                        'filename': filename,
                        'content_type': content_type,
                        **file_info
                    }
                )

                if not validation_result['passed']:
                    return {
                        'status': 'error',
                        'errors': validation_result['issues']
                    }

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

    async def _process_file(
            self,
            file: BinaryIO,
            temp_path: Path
    ) -> Dict[str, Any]:
        """Process and analyze file"""
        hasher = hashlib.sha256()
        size = 0

        try:
            # Write file in chunks
            async with aiofiles.open(temp_path, 'wb') as f:
                while chunk := await file.read(self.chunk_size):
                    hasher.update(chunk)
                    size += len(chunk)
                    await f.write(chunk)

            return {
                'size_bytes': size,
                'checksum': hasher.hexdigest(),
                'temp_path': str(temp_path)
            }

        except Exception as e:
            logger.error(f"File processing error: {str(e)}")
            raise

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
            staged_id = await self.staging_manager.store_data(
                data=content,
                metadata=staging_metadata,
                source_type='file'
            )

            # Notify about staging
            await self._notify_staging(staged_id, staging_metadata)

            return staged_id

        except Exception as e:
            logger.error(f"File staging error: {str(e)}")
            raise

    async def _notify_staging(
            self,
            staged_id: str,
            metadata: Dict[str, Any]
    ) -> None:
        """Notify about staged file"""
        try:
            message = ProcessingMessage(
                source_identifier=self.module_identifier,
                message_type=MessageType.DATA_STORAGE,
                content={
                    'staged_id': staged_id,
                    'source_type': 'file',
                    'metadata': metadata,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Staging notification error: {str(e)}")