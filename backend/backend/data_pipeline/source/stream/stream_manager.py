# stream_manager.py
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import threading
import queue

from backend.core.registry.component_registry import ComponentRegistry
from backend.core.messaging.types import ProcessingMessage, MessageType, ModuleIdentifier
from .stream_validator import StreamValidator
from .stream_fetcher import StreamFetcher

logger = logging.getLogger(__name__)

class StreamManager:
    """Enhanced stream management system with messaging integration"""

    def __init__(self, message_broker):
        """Initialize StreamManager with component registration"""
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.validator = StreamValidator()

        # Initialize with consistent UUID
        component_uuid = self.registry.get_component_uuid("StreamManager")
        self.module_id = ModuleIdentifier("StreamManager", "process_stream", component_uuid)

        # Track active streams and operations
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.stream_threads: Dict[str, threading.Thread] = {}
        self.message_queues: Dict[str, queue.Queue] = {}

        # Register and subscribe
        self._initialize_messaging()
        logger.info(f"StreamManager initialized with ID: {self.module_id.get_tag()}")

    def _initialize_messaging(self) -> None:
        """Set up message broker registration and subscriptions"""
        try:
            self.message_broker.register_module(self.module_id)
            
            orchestrator_id = ModuleIdentifier(
                "DataOrchestrator",
                "manage_pipeline",
                self.registry.get_component_uuid("DataOrchestrator")
            )

            self.message_broker.subscribe_to_module(
                orchestrator_id.get_tag(),
                self._handle_orchestrator_response
            )
            logger.info("StreamManager messaging initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing messaging: {str(e)}")
            raise

    def initialize_stream(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize stream connection"""
        try:
            stream_id = str(uuid.uuid4())
            
            # Validate stream configuration
            config_valid, config_msg = self.validator.validate_stream_config(config)
            if not config_valid:
                raise ValueError(config_msg)

            # Create and validate connection based on stream type
            stream_fetcher = StreamFetcher(config)
            if config['stream_type'] == 'kafka':
                valid, msg = self.validator.validate_kafka_connection(config)
            else:  # rabbitmq
                valid, msg = self.validator.validate_rabbitmq_connection(config)

            if not valid:
                raise ValueError(msg)

            # Initialize message queue and consumer thread
            self.message_queues[stream_id] = queue.Queue()
            self.active_streams[stream_id] = {
                'fetcher': stream_fetcher,
                'config': config,
                'status': 'initialized',
                'created_at': datetime.now().isoformat()
            }

            return {
                'status': 'success',
                'stream_id': stream_id,
                'message': 'Stream connection initialized'
            }

        except Exception as e:
            logger.error(f"Stream initialization error: {str(e)}")
            raise

    def start_stream_processing(self, stream_id: str) -> Dict[str, Any]:
        """Start stream processing"""
        try:
            if stream_id not in self.active_streams:
                raise ValueError("Invalid stream ID")

            stream_info = self.active_streams[stream_id]
            stream_info['status'] = 'starting'

            def stream_worker():
                try:
                    stream_info['fetcher'].initialize_consumer()
                    stream_info['status'] = 'processing'
                    
                    def message_handler(message_data: Dict[str, Any]):
                        try:
                            processed_data = self._process_stream_data(
                                stream_id, message_data
                            )
                            self._send_to_orchestrator(stream_id, processed_data)
                        except Exception as e:
                            logger.error(f"Message handling error: {str(e)}")

                    stream_info['fetcher'].consume_stream(message_handler)
                except Exception as e:
                    logger.error(f"Stream processing error: {str(e)}")
                    stream_info['status'] = 'error'
                    stream_info['error'] = str(e)

            # Start processing thread
            processing_thread = threading.Thread(
                target=stream_worker,
                daemon=True
            )
            self.stream_threads[stream_id] = processing_thread
            processing_thread.start()

            return {
                'status': 'success',
                'message': 'Stream processing started'
            }

        except Exception as e:
            logger.error(f"Stream start error: {str(e)}")
            raise

    def _process_stream_data(self, stream_id: str, message_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process stream message data"""
        try:
            stream_info = self.active_streams[stream_id]
            
            return {
                "status": "success",
                "source_type": stream_info['config']['stream_type'],
                "data": message_data['data'],
                "metadata": {
                    **message_data['metadata'],
                    "stream_id": stream_id,
                    "processed_at": datetime.now().isoformat()
                }
            }
        except Exception as e:
            raise ValueError(str(e))

    def _send_to_orchestrator(self, stream_id: str, processed_data: Dict[str, Any]) -> None:
        """Send processed data to orchestrator"""
        try:
            orchestrator_id = ModuleIdentifier(
                "DataOrchestrator",
                "manage_pipeline",
                self.registry.get_component_uuid("DataOrchestrator")
            )

            message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=orchestrator_id,
                message_type=MessageType.ACTION,
                content={
                    'stream_id': stream_id,
                    'action': 'process_stream_data',
                    'data': processed_data['data'],
                    'metadata': processed_data['metadata'],
                    'source_type': processed_data['source_type']
                }
            )

            self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error sending to orchestrator: {str(e)}")
            raise

    def _handle_orchestrator_response(self, message: ProcessingMessage) -> None:
        """Handle responses from orchestrator"""
        try:
            stream_id = message.content.get('stream_id')
            if not stream_id or stream_id not in self.active_streams:
                logger.warning(f"Received response for unknown stream ID: {stream_id}")
                return

            stream_info = self.active_streams[stream_id]

            if message.message_type == MessageType.ERROR:
                logger.error(f"Error in stream {stream_id}")
                self._handle_orchestrator_error(stream_id, message.content.get('error'))

        except Exception as e:
            logger.error(f"Error handling orchestrator response: {str(e)}")

    def get_stream_status(self, stream_id: str) -> Dict[str, Any]:
        """Get current stream status"""
        try:
            if stream_id not in self.active_streams:
                raise ValueError("Invalid stream ID")

            stream_info = self.active_streams[stream_id]
            return {
                'status': stream_info['status'],
                'stream_type': stream_info['config']['stream_type'],
                'created_at': stream_info['created_at'],
                'error': stream_info.get('error')
            }
        except Exception as e:
            logger.error(f"Status retrieval error: {str(e)}")
            raise

    def stop_stream(self, stream_id: str) -> None:
        """Stop stream processing and cleanup"""
        try:
            if stream_id in self.active_streams:
                stream_info = self.active_streams[stream_id]
                stream_info['status'] = 'stopping'
                
                # Close stream fetcher
                stream_info['fetcher'].close()
                
                # Wait for thread to finish
                if stream_id in self.stream_threads:
                    self.stream_threads[stream_id].join(timeout=5.0)
                    del self.stream_threads[stream_id]

                # Cleanup
                del self.active_streams[stream_id]
                if stream_id in self.message_queues:
                    del self.message_queues[stream_id]

                logger.info(f"Stopped stream: {stream_id}")

        except Exception as e:
            logger.error(f"Stream stop error: {str(e)}")
            raise

