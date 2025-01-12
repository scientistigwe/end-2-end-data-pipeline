import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

from backend.core.messaging.types import ComponentType
from backend.core.registry.component_registry import ComponentRegistry
from backend.core.messaging.types import ProcessingMessage, MessageType, ModuleIdentifier
from .stream_validator import StreamValidator
from .stream_fetcher import StreamFetcher
from .stream_config import Config

logger = logging.getLogger(__name__)

class StreamManager:
    """Core processing and orchestration for stream operations"""

    def __init__(self, message_broker):
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.validator = StreamValidator()
        
        # Component registration
        component_uuid = self.registry.get_component_uuid("StreamManager")
        self.module_id = ModuleIdentifier(
            component_name="StreamManager",
            component_type=ComponentType.MODULE,
            method_name="process_stream",
            instance_id=component_uuid
        )

        # State tracking
        self.active_connections: Dict[str, StreamFetcher] = {}
        self.pending_requests: Dict[str, Dict[str, Any]] = {}

        self._initialize_messaging()
        logger.info(f"StreamManager initialized with ID: {self.module_id.get_tag()}")

    def _initialize_messaging(self) -> None:
        """Initialize messaging with orchestrator"""
        try:
            self.message_broker.register_component(self.module_id)
            orchestrator_id = self._get_orchestrator_id()

            patterns = [
                f"{orchestrator_id.get_tag()}.{MessageType.SOURCE_SUCCESS.value}",
                f"{orchestrator_id.get_tag()}.{MessageType.SOURCE_ERROR.value}"
            ]

            for pattern in patterns:
                self.message_broker.subscribe(
                    component=self.module_id,
                    pattern=pattern,
                    callback=self._handle_orchestrator_response
                )
            
            logger.info("Messaging initialized")
        except Exception as e:
            logger.error(f"Messaging initialization error: {str(e)}")
            raise

    def process_stream_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming stream requests"""
        try:
            request_id = str(uuid.uuid4())
            action = request_data.get('action')

            # Track request
            self.pending_requests[request_id] = {
                'action': action,
                'status': 'received',
                'created_at': datetime.now().isoformat()
            }

            logger.info(f"Processing {action} request (ID: {request_id})")

            if action == 'connect':
                return self._handle_connect_request(request_id, request_data.get('data', {}))
            elif action == 'consumer':
                return self._handle_consumer_request(
                    request_id,
                    request_data.get('connection_id'),
                    request_data.get('consumer_data', {})
                )
            elif action == 'topic':
                return self._handle_topic_request(
                    request_id,
                    request_data.get('connection_id'),
                    request_data.get('topic_data', {})
                )
            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Request processing error: {str(e)}")
            if request_id:
                self._handle_request_error(request_id, str(e))
            raise

    def _handle_connect_request(self, request_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle connection request"""
        try:
            # Validate configuration
            is_valid, message = self.validator.validate_stream_config(data)
            if not is_valid:
                raise ValueError(message)

            # Create fetcher
            connection_id = str(uuid.uuid4())
            stream_fetcher = StreamFetcher(Config.get_fetcher_config(data))
            
            # Test connection
            test_result = stream_fetcher.test_connection()
            if not test_result.get('connected'):
                raise ValueError(f"Connection test failed: {test_result.get('message')}")

            # Store connection
            self.active_connections[connection_id] = stream_fetcher
            
            # Update request status
            self.pending_requests[request_id].update({
                'connection_id': connection_id,
                'status': 'connected'
            })

            # Notify orchestrator
            self._send_to_orchestrator(
                request_id,
                'connect',
                {
                    'connection_id': connection_id,
                    'config': data,
                    'test_result': test_result
                }
            )

            return {
                'status': 'success',
                'request_id': request_id,
                'connection_id': connection_id
            }

        except Exception as e:
            self._handle_request_error(request_id, str(e))
            raise

    def _handle_consumer_request(
        self, 
        request_id: str, 
        connection_id: str, 
        consumer_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle consumer operations"""
        try:
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]
            operation = consumer_data.get('operation')

            if operation == 'start':
                result = fetcher.start_consumer(consumer_data)
            elif operation == 'stop':
                result = fetcher.stop_consumer(consumer_data.get('consumer_id'))
            else:
                raise ValueError(f"Unknown consumer operation: {operation}")

            self._send_to_orchestrator(
                request_id,
                'consumer',
                {
                    'connection_id': connection_id,
                    'operation': operation,
                    'result': result
                }
            )

            return {
                'status': 'success',
                'request_id': request_id,
                'data': result
            }

        except Exception as e:
            self._handle_request_error(request_id, str(e))
            raise

    def _handle_topic_request(
        self, 
        request_id: str, 
        connection_id: str, 
        topic_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle topic operations"""
        try:
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]
            operation = topic_data.get('operation')

            if operation == 'create':
                result = fetcher.create_topic(topic_data)
            elif operation == 'delete':
                result = fetcher.delete_topic(topic_data.get('topic_name'))
            else:
                raise ValueError(f"Unknown topic operation: {operation}")

            self._send_to_orchestrator(
                request_id,
                'topic',
                {
                    'connection_id': connection_id,
                    'operation': operation,
                    'result': result
                }
            )

            return {
                'status': 'success',
                'request_id': request_id,
                'data': result
            }

        except Exception as e:
            self._handle_request_error(request_id, str(e))
            raise

    def get_metrics(self, connection_id: str) -> Dict[str, Any]:
        """Get metrics for a connection"""
        try:
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]
            return {
                'status': 'success',
                'data': fetcher.get_metrics()
            }

        except Exception as e:
            logger.error(f"Metrics error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def list_connections(self) -> Dict[str, Any]:
        """List all active connections"""
        try:
            connections = [
                {
                    'connection_id': conn_id,
                    'status': 'active',
                    'consumers': fetcher.list_consumers(),
                    'topics': fetcher.list_topics()
                }
                for conn_id, fetcher in self.active_connections.items()
            ]

            return {
                'status': 'success',
                'data': connections
            }

        except Exception as e:
            logger.error(f"List connections error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    def close_connection(self, connection_id: str) -> Dict[str, Any]:
            """Close a connection"""
            try:
                if connection_id not in self.active_connections:
                    raise ValueError(f"Connection {connection_id} not found")

                # Close fetcher
                fetcher = self.active_connections[connection_id]
                fetcher.close()

                # Remove from active connections
                del self.active_connections[connection_id]

                return {
                    'status': 'success',
                    'message': f'Connection {connection_id} closed successfully'
                }

            except Exception as e:
                logger.error(f"Connection closure error: {str(e)}")
                return {
                    'status': 'error',
                    'message': str(e)
                }

    def _send_to_orchestrator(self, request_id: str, action: str, data: Dict[str, Any]) -> None:
        """Send data to orchestrator"""
        try:
            message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=self._get_orchestrator_id(),
                message_type=MessageType.SOURCE_SUCCESS,
                content={
                    'request_id': request_id,
                    'source_type': 'stream',
                    'action': action,
                    'data': data,
                    'timestamp': datetime.now().isoformat()
                }
            )

            self.message_broker.publish(message)
            logger.info(f"Sent {action} request {request_id} to orchestrator")

        except Exception as e:
            logger.error(f"Error sending to orchestrator: {str(e)}")
            raise

    def _handle_orchestrator_response(self, message: ProcessingMessage) -> None:
        """Handle responses from orchestrator"""
        try:
            content = message.content
            request_id = content.get('request_id')
            
            if not request_id in self.pending_requests:
                logger.warning(f"Response for unknown request: {request_id}")
                return

            request = self.pending_requests[request_id]
            
            if message.message_type == MessageType.SOURCE_SUCCESS:
                request['status'] = 'completed'
                request['result'] = content.get('result')
                logger.info(f"Request {request_id} completed")
            
            elif message.message_type == MessageType.SOURCE_ERROR:
                self._handle_request_error(request_id, content.get('error'))

            # Update metrics if available
            if metrics := content.get('metrics'):
                connection_id = request.get('connection_id')
                if connection_id in self.active_connections:
                    self.active_connections[connection_id].update_metrics(metrics)

        except Exception as e:
            logger.error(f"Error handling orchestrator response: {str(e)}")

    def _handle_request_error(self, request_id: str, error: str) -> None:
        """Handle request errors"""
        try:
            if request_id in self.pending_requests:
                self.pending_requests[request_id].update({
                    'status': 'error',
                    'error': error,
                    'error_at': datetime.now().isoformat()
                })
                logger.error(f"Request {request_id} failed: {error}")

                # Cleanup if needed
                if error_type := self.pending_requests[request_id].get('action'):
                    if error_type == 'connect':
                        connection_id = self.pending_requests[request_id].get('connection_id')
                        if connection_id in self.active_connections:
                            self.active_connections[connection_id].close()
                            del self.active_connections[connection_id]

        except Exception as e:
            logger.error(f"Error handling request error: {str(e)}")

    def _get_orchestrator_id(self) -> ModuleIdentifier:
        """Get orchestrator identifier"""
        return ModuleIdentifier(
            component_name="DataOrchestrator",
            component_type=ComponentType.ORCHESTRATOR,
            method_name="manage_pipeline",
            instance_id=self.registry.get_component_uuid("DataOrchestrator")
        )