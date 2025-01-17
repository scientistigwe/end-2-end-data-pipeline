# backend/source_handlers/stream/stream_handler.py

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, Union

from backend.core.messaging.broker import MessageBroker
from backend.core.staging.staging_manager import StagingManager
from backend.core.messaging.types import (
    MessageType, ProcessingMessage, ModuleIdentifier, ComponentType,
    ProcessingStage, ProcessingStatus
)
from .stream_validator import StreamSourceValidator, StreamValidationConfig
from .stream_connector import StreamConnector
from .stream_config import StreamSourceConfig

logger = logging.getLogger(__name__)


class StreamHandler:
    """Core handler for stream data source operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            message_broker: MessageBroker,
            validator_config: Optional[StreamValidationConfig] = None,
            timeout: int = 30,
            max_retries: int = 3
    ):
        self.staging_manager = staging_manager
        self.message_broker = message_broker
        self.timeout = timeout
        self.max_retries = max_retries
        self.validator = StreamSourceValidator(config=validator_config)

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="stream_handler",
            component_type=ComponentType.HANDLER,
            department="source",
            role="handler"
        )

        # Chunk size for processing
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
        """
        Process incoming stream request

        Args:
            stream_type: Type of stream (Kafka, RabbitMQ, etc.)
            topic: Stream topic or channel
            operation: Type of operation (consume, produce, etc.)
            params: Additional parameters
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary containing staging information
        """
        try:
            # Validate source configuration
            source_data = {
                'stream_type': stream_type,
                'topic': topic,
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
            if operation == 'consume':
                return await self._process_consume_request(
                    stream_type, topic, params, auth, metadata
                )
            elif operation == 'produce':
                return await self._process_produce_request(
                    stream_type, topic, params, auth, metadata
                )
            else:
                raise ValueError(f"Unsupported operation: {operation}")

        except Exception as e:
            logger.error(f"Stream request handling error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_consume_request(
            self,
            stream_type: str,
            topic: str,
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process stream consumption request

        Args:
            stream_type: Type of stream
            topic: Stream topic
            params: Additional parameters
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary with consumed messages
        """
        try:
            # Create stream configuration
            stream_config = StreamSourceConfig(
                stream_type=stream_type,
                topic=topic,
                credentials=auth
            )

            # Create stream connector
            connector = StreamConnector(stream_config)

            # Consume messages
            request_result = await self._consume_messages(
                connector, topic, params
            )

            # Stage the received data
            staged_id = await self._stage_stream_data(
                stream_type, topic, request_result, metadata
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                'stream_info': request_result
            }

        except Exception as e:
            logger.error(f"Stream consume request processing error: {str(e)}")
            raise

    async def _process_produce_request(
            self,
            stream_type: str,
            topic: str,
            params: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process stream production request

        Args:
            stream_type: Type of stream
            topic: Stream topic
            params: Additional parameters
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary with production results
        """
        try:
            # Create stream configuration
            stream_config = StreamSourceConfig(
                stream_type=stream_type,
                topic=topic,
                credentials=auth
            )

            # Create stream connector
            connector = StreamConnector(stream_config)

            # Produce messages
            request_result = await self._produce_messages(
                connector, topic, params
            )

            # Stage the production metadata
            staged_id = await self._stage_stream_data(
                stream_type, topic, request_result, metadata
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                'stream_info': request_result
            }

        except Exception as e:
            logger.error(f"Stream produce request processing error: {str(e)}")
            raise

    async def _consume_messages(
            self,
            connector: StreamConnector,
            topic: str,
            params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Consume messages from stream

        Args:
            connector: Stream connector
            topic: Stream topic
            params: Consumption parameters

        Returns:
            Dictionary with consumed messages
        """
        try:
            # Connect to stream
            await connector.connect()

            # Consume messages
            messages = await connector.consume_messages(
                topic,
                params or {}
            )

            # Process results
            return {
                'data': messages,
                'metadata': {
                    'message_count': len(messages),
                    'topics': [topic]
                }
            }

        except Exception as e:
            logger.error(f"Message consumption error: {str(e)}")
            raise
        finally:
            # Ensure connection is closed
            await connector.close()

    async def _produce_messages(
            self,
            connector: StreamConnector,
            topic: str,
            params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Produce messages to stream

        Args:
            connector: Stream connector
            topic: Stream topic
            params: Production parameters

        Returns:
            Dictionary with production results
        """
        try:
            # Connect to stream
            await connector.connect()

            # Produce messages
            result = await connector.produce_messages(
                topic,
                params or {}
            )

            # Process results
            return {
                'data': result,
                'metadata': {
                    'messages_produced': result.get('messages_produced', 0),
                    'topic': topic
                }
            }

        except Exception as e:
            logger.error(f"Message production error: {str(e)}")
            raise
        finally:
            # Ensure connection is closed
            await connector.close()

    async def _stage_stream_data(
            self,
            stream_type: str,
            topic: str,
            request_result: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store stream data in staging area

        Args:
            stream_type: Type of stream
            topic: Stream topic
            request_result: Processed stream data
            metadata: Additional metadata

        Returns:
            Staged data identifier
        """
        try:
            # Prepare staging metadata
            staging_metadata = {
                'stream_type': stream_type,
                'topic': topic,
                'message_count': request_result.get('metadata', {}).get('message_count', 0),
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
        """
        Notify about staged stream data

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
                    'source_type': 'stream',
                    'metadata': metadata,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Staging notification error: {str(e)}")