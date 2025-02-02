# backend/source_handlers/stream/stream_handler.py

import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, Union

from core.managers.staging_manager import (StagingManager)
from core.messaging.event_types import ProcessingMessage
from .stream_validator import StreamSourceValidator
from config.validation_config import StreamValidationConfig

logger = logging.getLogger(__name__)


class StreamHandler:
    """Handler for stream data source operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            validator_config: Optional[StreamValidationConfig] = None,
            timeout: int = 30,
            max_retries: int = 3
    ):
        self.staging_manager = staging_manager
        self.validator = StreamSourceValidator(config=validator_config)
        self.timeout = timeout
        self.max_retries = max_retries
        self.chunk_size = 8192  # 8KB chunks

    async def handle_stream_request(
            self,
            stream_type: str,
            topic: str,
            operation: str = 'consume',
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process stream request"""
        try:
            # Validate request
            validation_result = await self.validator.validate_source({
                'stream_type': stream_type,
                'topic': topic,
                'operation': operation,
                'auth': auth
            })

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Process request
            request_result = await self._process_stream_data(
                stream_type, topic, operation, params, auth
            )

            # Stage the data
            staged_id = await self._stage_data(
                stream_type,
                topic,
                request_result,
                metadata
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                'stream_info': request_result
            }

        except Exception as e:
            logger.error(f"Stream request handling error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_stream_data(
            self,
            stream_type: str,
            topic: str,
            operation: str,
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process stream request with retry mechanism"""
        retries = 0
        while retries < self.max_retries:
            try:
                if operation == 'consume':
                    data = await self._execute_consume_operation(stream_type, topic, params)
                elif operation == 'produce':
                    data = await self._execute_produce_operation(stream_type, topic, params)
                else:
                    raise ValueError(f"Unsupported operation: {operation}")
                return data

            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    raise
                await asyncio.sleep(2 ** retries)

    async def _stage_data(
            self,
            stream_type: str,
            topic: str,
            request_result: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store stream data in staging"""
        try:
            staging_metadata = {
                'stream_type': stream_type,
                'topic': topic,
                'message_count': request_result.get('metadata', {}).get('message_count', 0),
                'messages_produced': request_result.get('metadata', {}).get('messages_produced', 0),
                'timestamp': datetime.utcnow().isoformat(),
                **(metadata or {})
            }

            return await self.staging_manager.store_data(
                data=request_result.get('data'),
                metadata=staging_metadata,
                source_type='stream'
            )

        except Exception as e:
            logger.error(f"Stream data staging error: {str(e)}")
            raise

    async def _execute_consume_operation(
            self,
            stream_type: str,
            topic: str,
            params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute consume operation"""
        return {
            'status': 'success',
            'data': [{'message': 'sample message'}],
            'metadata': {
                'message_count': 1,
                'topic': topic
            }
        }

    async def _execute_produce_operation(
            self,
            stream_type: str,
            topic: str,
            params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute produce operation"""
        return {
            'status': 'success',
            'data': {'messages_produced': 1},
            'metadata': {
                'messages_produced': 1,
                'topic': topic
            }
        }

    async def _stage_stream_data(
            self,
            stream_type: str,
            topic: str,
            request_result: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store stream data in staging area"""
        try:
            # Prepare staging metadata
            staging_metadata = {
                'stream_type': stream_type,
                'topic': topic,
                'message_count': request_result.get('metadata', {}).get('message_count', 0),
                'messages_produced': request_result.get('metadata', {}).get('messages_produced', 0),
                **(metadata or {})
            }

            # Store in staging
            staged_id = await self.staging_manager.store_data(
                data=request_result.get('data'),
                metadata=staging_metadata,
                source_type='stream'
            )

            # Notify about staging
            await self._notify_staging(staged_id, staging_metadata)

            return staged_id

        except Exception as e:
            logger.error(f"Stream data staging error: {str(e)}")
            raise

    async def _notify_staging(
            self,
            staged_id: str,
            metadata: Dict[str, Any]
    ) -> None:
        """Notify about staged stream data"""
        try:
            message = ProcessingMessage(
                content={
                    'staged_id': staged_id,
                    'source_type': 'stream',
                    'metadata': metadata,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Staging notification error: {str(e)}")