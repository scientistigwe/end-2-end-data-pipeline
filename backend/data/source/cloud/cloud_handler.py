# backend/source_handlers/s3/s3_manager.py

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.core.messaging.broker import MessageBroker
from backend.core.staging.staging_manager import StagingManager
from backend.core.messaging.types import (
    MessageType, ProcessingMessage, ModuleIdentifier, ComponentType,
    ProcessingStage, ProcessingStatus
)
from backend.core.control.control_point_manager import ControlPointManager
from .s3_validator import S3Validator, S3ValidationConfig
from .s3_fetcher import S3Fetcher
from .s3_config import Config

logger = logging.getLogger(__name__)


class S3Handler:
    """Core handler for S3 data source operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            message_broker: MessageBroker,
            validator_config: Optional[S3ValidationConfig] = None,
            timeout: int = 30,
            max_retries: int = 3
    ):
        self.staging_manager = staging_manager
        self.message_broker = message_broker
        self.timeout = timeout
        self.max_retries = max_retries
        self.validator = S3Validator(config=validator_config)

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="s3_handler",
            component_type=ComponentType.HANDLER,
            department="source",
            role="handler"
        )

        # Chunk size for processing
        self.chunk_size = 8192  # 8KB chunks

    async def handle_s3_request(
            self,
            endpoint: str,
            bucket: str,
            key: Optional[str] = None,
            operation: str = 'get',
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process incoming S3 request

        Args:
            endpoint: S3 endpoint URL
            bucket: S3 bucket name
            key: Object key (optional)
            operation: Operation type (get, list, etc.)
            params: Additional parameters
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary containing staging information
        """
        try:
            # Validate source configuration
            source_data = {
                'endpoint': endpoint,
                'bucket': bucket,
                'key': key,
                'operation': operation,
                'auth': auth
            }
            validation_result = await self.validator.validate_source(source_data)

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Process based on operation
            if operation == 'get':
                return await self._process_object_request(
                    endpoint, bucket, key, params, auth, metadata
                )
            elif operation == 'list':
                return await self._process_list_request(
                    endpoint, bucket, params, auth, metadata
                )
            else:
                raise ValueError(f"Unsupported operation: {operation}")

        except Exception as e:
            logger.error(f"S3 request handling error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_object_request(
            self,
            endpoint: str,
            bucket: str,
            key: str,
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process object retrieval request

        Args:
            endpoint: S3 endpoint URL
            bucket: S3 bucket name
            key: Object key
            params: Additional parameters
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary with staging information
        """
        try:
            # Create S3 fetcher
            fetcher = S3Fetcher({
                'endpoint': endpoint,
                'bucket': bucket,
                'credentials': auth
            })

            # Fetch object
            request_result = await self._fetch_object(
                fetcher, bucket, key, params
            )

            # Stage the received data
            staged_id = await self._stage_s3_data(
                bucket, key, request_result, metadata
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                's3_info': request_result
            }

        except Exception as e:
            logger.error(f"Object request processing error: {str(e)}")
            raise

    async def _process_list_request(
            self,
            endpoint: str,
            bucket: str,
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process object listing request

        Args:
            endpoint: S3 endpoint URL
            bucket: S3 bucket name
            params: Additional parameters
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary with object listing
        """
        try:
            # Create S3 fetcher
            fetcher = S3Fetcher({
                'endpoint': endpoint,
                'bucket': bucket,
                'credentials': auth
            })

            # List objects
            list_result = await self._list_objects(
                fetcher, bucket, params
            )

            # Stage the object list
            staged_id = await self._stage_s3_data(
                bucket, 'object_list', list_result, metadata
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                's3_info': list_result
            }

        except Exception as e:
            logger.error(f"Object list processing error: {str(e)}")
            raise

    async def _fetch_object(
            self,
            fetcher: S3Fetcher,
            bucket: str,
            key: str,
            params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Fetch object from S3

        Args:
            fetcher: S3Fetcher instance
            bucket: S3 bucket name
            key: Object key
            params: Additional parameters

        Returns:
            Dictionary with object data
        """
        try:
            # Fetch object
            result = await fetcher.fetch_object_async(bucket, key, **(params or {}))

            return {
                'data': result.get('data'),
                'metadata': {
                    'content_type': result.get('content_type'),
                    'size_bytes': len(result.get('data', b'')),
                    'temp_path': result.get('temp_path')
                }
            }

        except Exception as e:
            logger.error(f"Object fetch error: {str(e)}")
            raise

    async def _list_objects(
            self,
            fetcher: S3Fetcher,
            bucket: str,
            params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        List objects in S3 bucket

        Args:
            fetcher: S3Fetcher instance
            bucket: S3 bucket name
            params: Additional parameters

        Returns:
            Dictionary with object listing
        """
        try:
            # List objects
            result = await fetcher.list_objects_async(
                bucket, **(params or {})
            )

            return {
                'objects': result.get('objects', []),
                'continuation_token': result.get('continuation_token'),
                'is_truncated': result.get('is_truncated', False)
            }

        except Exception as e:
            logger.error(f"Object listing error: {str(e)}")
            raise

    async def _stage_s3_data(
            self,
            bucket: str,
            key: str,
            request_result: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store S3 data in staging area

        Args:
            bucket: S3 bucket name
            key: Object key
            request_result: Processed request result
            metadata: Additional metadata

        Returns:
            Staged data identifier
        """
        try:
            # Prepare staging metadata
            staging_metadata = {
                'bucket': bucket,
                'key': key,
                'content_type': request_result.get('metadata', {}).get('content_type'),
                'size_bytes': request_result.get('metadata', {}).get('size_bytes'),
                **(metadata or {})
            }

            # Store in staging
            staged_id = await self.staging_manager.store_data(
                data=request_result.get('data'),
                metadata=staging_metadata,
                source_type='s3'
            )

            # Notify about staging
            await self._notify_staging(staged_id, staging_metadata)

            return staged_id

        except Exception as e:
            logger.error(f"S3 data staging error: {str(e)}")
            raise

    async def _notify_staging(
            self,
            staged_id: str,
            metadata: Dict[str, Any]
    ) -> None:
        """
        Notify about staged S3 data

        Args:
            staged_id: Identifier of staged data
            metadata: Staging metadata
        """
        try:
            message = ProcessingMessage(
                source_identifier=self.module_identifier,
                message_type=MessageType.DATA_STORAGE,
                content={
                    'staged_id': staged_id,
                    'source_type': 's3',
                    'metadata': metadata,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Staging notification error: {str(e)}")