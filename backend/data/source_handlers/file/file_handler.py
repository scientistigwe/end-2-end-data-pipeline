# backend/source_handlers/file/file_handler.py

import asyncio
import logging
from typing import Dict, Any, Optional, BinaryIO, List, Tuple
from datetime import datetime
import hashlib
import magic
import aiofiles
from pathlib import Path

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage
from backend.core.staging.staging_manager import StagingManager
from backend.core.monitoring.process import ProcessMonitor
from .file_validator import FileValidator

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles file data source operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            message_broker: MessageBroker,
            upload_dir: str = "uploads",
            chunk_size: int = 8192  # 8KB chunks
    ):
        self.staging_manager = staging_manager
        self.message_broker = message_broker
        self.upload_dir = Path(upload_dir)
        self.chunk_size = chunk_size
        self.validator = FileValidator()
        self.process_monitor = ProcessMonitor()

        # Create upload directory
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def handle_file(
            self,
            file: BinaryIO,
            filename: str,
            content_type: Optional[str] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle incoming file

        Args:
            file: File-like object
            filename: Original filename
            content_type: MIME type if known
            metadata: Additional metadata

        Returns:
            Dictionary containing staging information
        """
        try:
            # Start monitoring
            start_time = datetime.now()

            # Create temporary file
            temp_path = self.upload_dir / f"temp_{datetime.now().timestamp()}_{filename}"

            # Read and validate file
            file_info = await self._process_file(file, temp_path)

            # Validate file
            validation_result = await self.validator.validate_file(
                temp_path,
                filename,
                file_info['content_type']
            )

            if not validation_result['passed']:
                # Clean up temp file
                temp_path.unlink()
                return {
                    'status': 'error',
                    'error': 'File validation failed',
                    'details': validation_result
                }

            # Create staging area
            staged_id = await self.staging_manager.create_staging_area(
                source_type='file',
                source_identifier=filename,
                metadata={
                    **file_info,
                    **(metadata or {}),
                    'validation_result': validation_result
                }
            )

            # Store file in staging
            async with aiofiles.open(temp_path, 'rb') as f:
                file_data = await f.read()
                await self.staging_manager.store_staged_data(
                    staged_id,
                    file_data,
                    metadata={
                        'file_size': len(file_data),
                        'checksum': file_info['checksum']
                    }
                )

            # Clean up temp file
            temp_path.unlink()

            # Record metrics
            duration = (datetime.now() - start_time).total_seconds()
            await self.process_monitor.record_operation_metric(
                'file_processing',
                success=True,
                duration=duration,
                file_size=file_info['size']
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                'file_info': file_info
            }

        except Exception as e:
            logger.error(f"Error handling file: {str(e)}")
            # Clean up temp file if exists
            if 'temp_path' in locals() and temp_path.exists():
                temp_path.unlink()

            # Record error
            await self.process_monitor.record_error(
                'file_processing_error',
                error=str(e),
                filename=filename
            )

            raise

    async def _process_file(
            self,
            file: BinaryIO,
            temp_path: Path
    ) -> Dict[str, Any]:
        """
        Process and analyze file

        Args:
            file: File-like object
            temp_path: Temporary file path

        Returns:
            Dictionary containing file information
        """
        hasher = hashlib.sha256()
        size = 0

        try:
            # Write file in chunks
            async with aiofiles.open(temp_path, 'wb') as f:
                while chunk := file.read(self.chunk_size):
                    hasher.update(chunk)
                    size += len(chunk)
                    await f.write(chunk)

            # Detect content type
            content_type = magic.from_file(str(temp_path), mime=True)

            return {
                'size': size,
                'checksum': hasher.hexdigest(),
                'content_type': content_type
            }

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise

    async def get_file_info(
            self,
            staged_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get information about staged file"""
        try:
            staged_data = await self.staging_manager.get_staged_data(staged_id)
            if not staged_data:
                return None

            # Decrypt sensitive metadata if present
            metadata = staged_data['metadata']
            if 'encrypted_metadata' in metadata:
                metadata['secure_info'] = self.encryption.decrypt(
                    metadata['encrypted_metadata']
                )

            return {
                'filename': staged_data['source_identifier'],
                'size': staged_data['metadata'].get('file_size'),
                'content_type': staged_data['metadata'].get('content_type'),
                'checksum': staged_data['metadata'].get('checksum'),
                'upload_date': staged_data['created_at'],
                'metadata': metadata
            }

        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            raise

    async def encrypt_and_stage_file(
            self,
            file_path: Path,
            staged_id: str
    ) -> bool:
        """Encrypt and store file in staging area"""
        try:
            # Read file content
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()

            # Encrypt content
            encrypted_content = self.encryption.encrypt(content)

            # Store encrypted content
            await self.staging_manager.store_staged_data(
                staged_id,
                encrypted_content,
                metadata={
                    'encrypted': True,
                    'encryption_method': 'AES-256'
                }
            )

            return True

        except Exception as e:
            logger.error(f"Error encrypting and staging file: {str(e)}")
            raise

    async def process_file_batch(
            self,
            files: List[Tuple[BinaryIO, str]],
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process multiple files in batch"""
        results = {
            'successful': [],
            'failed': []
        }

        for file, filename in files:
            try:
                result = await self.handle_file(
                    file=file,
                    filename=filename,
                    metadata=metadata
                )

                if result['status'] == 'success':
                    results['successful'].append({
                        'filename': filename,
                        'staged_id': result['staged_id']
                    })
                else:
                    results['failed'].append({
                        'filename': filename,
                        'error': result.get('error', 'Unknown error')
                    })

            except Exception as e:
                results['failed'].append({
                    'filename': filename,
                    'error': str(e)
                })

        # Record batch metrics
        await self.process_monitor.record_metric(
            'batch_processing',
            1,
            successful_count=len(results['successful']),
            failed_count=len(results['failed'])
        )

        return results

    async def cleanup(self):
        """Clean up resources"""
        try:
            # Clear upload directory
            for file in self.upload_dir.glob('temp_*'):
                try:
                    file.unlink()
                except Exception as e:
                    logger.error(f"Error deleting temporary file {file}: {str(e)}")

        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise