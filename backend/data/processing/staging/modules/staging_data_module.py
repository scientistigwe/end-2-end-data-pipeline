# backend/core/modules/staging_data_module.py

import logging
import aiofiles
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime

from db.models.staging.base_staging_model import BaseStagedOutput
from utils.encryption import encrypt_data, decrypt_data
from utils.validators import validate_storage_path

logger = logging.getLogger(__name__)


class StagingDataModule:
    """
    Staging Data Module: Handles direct data storage and retrieval operations

    Responsibilities:
    - Direct file system operations
    - Data encryption/decryption
    - Storage path management
    - Storage cleanup
    """

    def __init__(self, base_storage_path: Union[str, Path]):
        self.base_storage_path = Path(base_storage_path)
        self.staged_data_path = self.base_storage_path / "staged_data"
        self.temp_data_path = self.base_storage_path / "temp"

        # Ensure storage directories exist
        self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Initialize storage directories"""
        self.staged_data_path.mkdir(parents=True, exist_ok=True)
        self.temp_data_path.mkdir(parents=True, exist_ok=True)

    async def store_data(
            self,
            stage_id: str,
            data: Any,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Store data securely in staging area"""
        try:
            # Create stage directory
            stage_path = self.staged_data_path / stage_id
            stage_path.mkdir(parents=True, exist_ok=True)

            # Prepare data for storage
            storage_data = {
                'content': data,
                'metadata': metadata or {},
                'stored_at': datetime.utcnow().isoformat()
            }

            # Encrypt data
            encrypted_data = encrypt_data(json.dumps(storage_data))

            # Store encrypted data
            data_path = stage_path / "data.enc"
            async with aiofiles.open(data_path, 'wb') as f:
                await f.write(encrypted_data)

            # Store metadata separately for quick access
            meta_path = stage_path / "metadata.json"
            async with aiofiles.open(meta_path, 'w') as f:
                await f.write(json.dumps({
                    'stage_id': stage_id,
                    'stored_at': storage_data['stored_at'],
                    **(metadata or {})
                }))

            return data_path

        except Exception as e:
            logger.error(f"Data storage failed for stage {stage_id}: {str(e)}")
            raise

    async def retrieve_data(
            self,
            stage_id: str,
            decrypt: bool = True
    ) -> Any:
        """Retrieve staged data"""
        try:
            # Validate stage exists
            stage_path = self.staged_data_path / stage_id
            if not stage_path.exists():
                raise FileNotFoundError(f"Stage {stage_id} not found")

            # Read encrypted data
            data_path = stage_path / "data.enc"
            async with aiofiles.open(data_path, 'rb') as f:
                encrypted_data = await f.read()

            if decrypt:
                # Decrypt and parse data
                decrypted_data = decrypt_data(encrypted_data)
                storage_data = json.loads(decrypted_data)
                return storage_data['content']

            return encrypted_data

        except Exception as e:
            logger.error(f"Data retrieval failed for stage {stage_id}: {str(e)}")
            raise

    async def delete_data(self, stage_id: str) -> None:
        """Delete staged data"""
        try:
            stage_path = self.staged_data_path / stage_id
            if stage_path.exists():
                for file_path in stage_path.glob('*'):
                    file_path.unlink(missing_ok=True)
                stage_path.rmdir()

        except Exception as e:
            logger.error(f"Data deletion failed for stage {stage_id}: {str(e)}")
            raise

    async def update_metadata(
            self,
            stage_id: str,
            metadata: Dict[str, Any]
    ) -> None:
        """Update metadata for staged data"""
        try:
            stage_path = self.staged_data_path / stage_id
            meta_path = stage_path / "metadata.json"

            if not meta_path.exists():
                raise FileNotFoundError(f"Metadata for stage {stage_id} not found")

            # Read existing metadata
            async with aiofiles.open(meta_path, 'r') as f:
                content = await f.read()
                existing_metadata = json.loads(content)

            # Update metadata
            updated_metadata = {**existing_metadata, **metadata}

            # Write updated metadata
            async with aiofiles.open(meta_path, 'w') as f:
                await f.write(json.dumps(updated_metadata))

        except Exception as e:
            logger.error(f"Metadata update failed for stage {stage_id}: {str(e)}")
            raise

    async def cleanup_expired(self, max_age_hours: int = 24) -> None:
        """Clean up expired staged data"""
        try:
            current_time = datetime.utcnow()

            for stage_path in self.staged_data_path.glob('*'):
                if not stage_path.is_dir():
                    continue

                meta_path = stage_path / "metadata.json"
                if not meta_path.exists():
                    continue

                # Check metadata for age
                async with aiofiles.open(meta_path, 'r') as f:
                    content = await f.read()
                    metadata = json.loads(content)

                stored_at = datetime.fromisoformat(metadata['stored_at'])
                age_hours = (current_time - stored_at).total_seconds() / 3600

                if age_hours > max_age_hours:
                    await self.delete_data(metadata['stage_id'])

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise

    async def get_storage_info(self, stage_id: str) -> Dict[str, Any]:
        """Get storage information for staged data"""
        try:
            stage_path = self.staged_data_path / stage_id
            if not stage_path.exists():
                raise FileNotFoundError(f"Stage {stage_id} not found")

            data_path = stage_path / "data.enc"
            meta_path = stage_path / "metadata.json"

            stats = {
                'stage_id': stage_id,
                'exists': True,
                'size': data_path.stat().st_size if data_path.exists() else 0,
                'metadata_exists': meta_path.exists(),
                'created_at': datetime.fromtimestamp(stage_path.stat().st_ctime).isoformat(),
                'modified_at': datetime.fromtimestamp(stage_path.stat().st_mtime).isoformat()
            }

            if meta_path.exists():
                async with aiofiles.open(meta_path, 'r') as f:
                    content = await f.read()
                    stats['metadata'] = json.loads(content)

            return stats

        except Exception as e:
            logger.error(f"Failed to get storage info for stage {stage_id}: {str(e)}")
            raise