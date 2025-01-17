from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4
import uuid
from dataclasses import dataclass, field

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    ComponentType,
    MessageType,
    ProcessingMessage,
    ModuleIdentifier,
    ProcessingStage,
    ProcessingStatus
)
from backend.core.control.control_point_manager import ControlPointManager, ControlPoint
from backend.core.orchestration.base_manager import BaseManager
from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from backend.core.utils.process_manager import (
    ProcessManager,
    with_process_handling,
    ProcessContext
)

from .stream_validator import StreamValidator
from .stream_fetcher import StreamFetcher
from .stream_config import Config

logger = logging.getLogger(__name__)

@dataclass
class StreamContext:
    """Context for stream operations"""
    request_id: str
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)

class StreamManager:
    """Enhanced stream manager with CPM integration"""

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            metrics_collector: Optional[MetricsCollector] = None,
            config: Optional[Config] = None
    ):
        """Initialize StreamManager with required components"""
        super().__init__(
            message_broker=message_broker,
            component_name="StreamManager"
        )

        # Core components
        self.control_point_manager = control_point_manager
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.config = config or Config()
        self.validator = StreamValidator(config=self.config)

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="stream_manager",
            source_id=str(uuid4())
        )

        # State tracking
        self.active_connections: Dict[str, StreamFetcher] = {}
        self.active_processes: Dict[str, Dict[str, Any]] = {}

        # Register handlers with CPM
        self._setup_handlers()

    @with_process_handling
    async def process_stream_request(
            self,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process stream request with control points

        Args:
            request_data: Stream request configuration

        Returns:
            Dictionary containing processing results
        """
        try:
            # Create request context
            context = StreamContext(
                request_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                status=ProcessingStatus.PENDING,
                metadata=request_data.get('metadata', {})
            )

            self.active_processes[context.request_id] = context

            # Create validation control point
            validation_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.INITIAL_VALIDATION,
                data={
                    'request_data': request_data,
                    'metadata': context.metadata
                },
                options=['proceed', 'reject']
            )

            # Wait for validation decision
            decision = await self.control_point_manager.wait_for_decision(
                validation_point.id,
                timeout=self.config.VALIDATION_TIMEOUT
            )

            if decision.decision == 'proceed':
                return await self._process_request(context, request_data)
            else:
                context.status = ProcessingStatus.REJECTED
                context.error = decision.details.get('reason', 'Request rejected')
                return {
                    'status': 'rejected',
                    'reason': context.error
                }

        except Exception as e:
            logger.error(f"Stream request processing error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_request(self, context: StreamContext, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process the validated request"""
        try:
            # Create processing control point
            process_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.PROCESSING,
                data={
                    'request_id': context.request_id,
                    'request_data': request_data,
                    'metadata': context.metadata
                },
                options=['process']
            )

            return {
                'status': 'processing',
                'request_id': context.request_id,
                'pipeline_id': context.pipeline_id
            }

        except Exception as e:
            logger.error(f"Request processing error: {str(e)}", exc_info=True)
            raise

    def _setup_handlers(self) -> None:
        """Register handlers with Control Point Manager"""
        handlers = {
            'stream.connect.request': self._handle_connect_request,
            'stream.consumer.request': self._handle_consumer_request,
            'stream.topic.request': self._handle_topic_request,
            'stream.validate.request': self._handle_validate_request,
            'stream.data.request': self._handle_data_request
        }

        self.control_point_manager.register_handler(
            source_type='stream_manager',
            handlers=handlers
        )

    async def _handle_connect_request(self, control_point: ControlPoint) -> None:
        """Handle stream connection request through CPM"""
        try:
            # Create fetcher with validated configuration
            connection_id = str(uuid4())
            stream_fetcher = StreamFetcher(Config.get_fetcher_config(control_point.data))

            # Test connection
            test_result = await stream_fetcher.test_connection()
            if not test_result.get('connected'):
                await self.control_point_manager.submit_decision(
                    control_point.id,
                    'reject',
                    {'reason': f"Connection test failed: {test_result.get('message')}"}
                )
                return

            # Store connection
            self.active_connections[connection_id] = stream_fetcher

            # Update process status
            if control_point.pipeline_id in self.active_processes:
                self.active_processes[control_point.pipeline_id].update({
                    'connection_id': connection_id,
                    'status': ProcessingStatus.RUNNING.value
                })

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {
                    'connection_id': connection_id,
                    'test_result': test_result
                }
            )

        except Exception as e:
            logger.error(f"Connection request error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_consumer_request(self, control_point: ControlPoint) -> None:
        """Handle consumer operations through CPM"""
        try:
            consumer_data = control_point.data
            connection_id = consumer_data.get('connection_id')

            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]
            operation = consumer_data.get('operation')

            if operation == 'start':
                result = await fetcher.start_consumer(consumer_data)
            elif operation == 'stop':
                result = await fetcher.stop_consumer(consumer_data.get('consumer_id'))
            else:
                raise ValueError(f"Unknown consumer operation: {operation}")

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {
                    'connection_id': connection_id,
                    'operation': operation,
                    'result': result
                }
            )

        except Exception as e:
            logger.error(f"Consumer operation error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_topic_request(self, control_point: ControlPoint) -> None:
        """Handle topic operations through CPM"""
        try:
            topic_data = control_point.data
            connection_id = topic_data.get('connection_id')

            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]
            operation = topic_data.get('operation')

            if operation == 'create':
                result = await fetcher.create_topic(topic_data)
            elif operation == 'delete':
                result = await fetcher.delete_topic(topic_data.get('topic_name'))
            else:
                raise ValueError(f"Unknown topic operation: {operation}")

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {
                    'connection_id': connection_id,
                    'operation': operation,
                    'result': result
                }
            )

        except Exception as e:
            logger.error(f"Topic operation error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_validate_request(self, control_point: ControlPoint) -> None:
        """Handle validation request through CPM"""
        try:
            request_data = control_point.data

            # Validate request
            validation_result = await self.validator.validate_request_comprehensive(request_data)

            if not validation_result['passed']:
                await self.control_point_manager.submit_decision(
                    control_point.id,
                    'reject',
                    {'reason': validation_result['summary']}
                )
                return

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {'validation_result': validation_result}
            )

        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_data_request(self, control_point: ControlPoint) -> None:
        """Handle data request through CPM"""
        try:
            request_data = control_point.data
            connection_id = request_data.get('connection_id')

            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]

            # Fetch data
            result = await fetcher.fetch_data(request_data)

            # Create validation control point
            validation_point = await self.control_point_manager.create_control_point(
                pipeline_id=control_point.pipeline_id,
                stage=ProcessingStage.DATA_VALIDATION,
                data={
                    'data': result,
                    'metadata': request_data.get('metadata', {})
                },
                options=['validate']
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {'validation_point_id': validation_point.id}
            )

        except Exception as e:
            logger.error(f"Data request error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def cleanup(self) -> None:
        """Clean up manager resources through CPM"""
        try:
            # Close all active connections
            for connection_id in list(self.active_connections.keys()):
                try:
                    fetcher = self.active_connections[connection_id]
                    await fetcher.close()
                except Exception as cleanup_error:
                    logger.error(f"Error closing connection {connection_id}: {cleanup_error}")

            # Clear tracking
            self.active_connections.clear()
            self.active_processes.clear()

            logger.info("StreamManager resources cleaned up")

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}", exc_info=True)


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
        """Process incoming stream requests with control point management"""
        try:
            request_id = str(uuid.uuid4())
            action = request_data.get('action')

            # Track request
            self.active_processes[request_id] = {
                'request_id': request_id,
                'action': action,
                'status': ProcessingStatus.PENDING.value,
                'stage': ProcessingStage.INITIAL_VALIDATION.value,
                'created_at': datetime.now().isoformat()
            }

            logger.info(f"Processing {action} request (ID: {request_id})")

            # Validate request
            validation_result = self._validate_request(request_data)

            # Create control point
            control_point_id = self._create_control_point(
                request_id, 
                ProcessingStage.INITIAL_VALIDATION, 
                validation_result
            )

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
            self._handle_request_error(request_id, str(e))
            return {
                'status': 'error',
                'error': str(e)
            }

    def _validate_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate incoming stream request"""
        action = request_data.get('action')
        data = request_data.get('data', {})

        if action == 'connect':
            # Validate stream configuration
            is_valid, message = self.validator.validate_stream_config(data)
            if not is_valid:
                raise ValueError(message)

            return {
                'status': 'valid',
                'details': data
            }
        
        # Add more specific validations for other actions
        return {
            'status': 'valid',
            'details': request_data
        }

    def _create_control_point(
        self, 
        request_id: str, 
        stage: ProcessingStage, 
        data: Dict[str, Any]
    ) -> str:
        """Create a control point for the request"""
        try:
            control_point_id = self.control_point_manager.create_control_point(
                pipeline_id=request_id,  # Using request_id as pipeline_id
                stage=stage,
                data={
                    'request_id': request_id,
                    'stage_data': data,
                    'source_type': 'stream'
                },
                options=['proceed', 'modify', 'reject']
            )

            # Update process status
            if request_id in self.active_processes:
                self.active_processes[request_id].update({
                    'status': ProcessingStatus.AWAITING_DECISION.value,
                    'control_point_id': control_point_id
                })

            return control_point_id

        except Exception as e:
            logger.error(f"Control point creation error: {str(e)}")
            raise

    def _handle_request_error(self, request_id: str, error: str) -> None:
        """Handle request errors with comprehensive tracking"""
        try:
            if request_id in self.active_processes:
                # Update process status
                self.active_processes[request_id].update({
                    'status': ProcessingStatus.FAILED.value,
                    'error': error,
                    'error_at': datetime.now().isoformat()
                })

                # Log the error
                logger.error(f"Request {request_id} failed: {error}")

                # Cleanup if needed
                action = self.active_processes[request_id].get('action')
                if action == 'connect':
                    connection_id = self.active_processes[request_id].get('connection_id')
                    if connection_id and connection_id in self.active_connections:
                        self.active_connections[connection_id].close()
                        del self.active_connections[connection_id]

                # Notify control point manager
                control_point_id = self.active_processes[request_id].get('control_point_id')
                if control_point_id:
                    try:
                        self.control_point_manager.process_decision(
                            control_point_id, 
                            'reject', 
                            {'reason': error}
                        )
                    except Exception as cp_error:
                        logger.error(f"Control point error handling failed: {cp_error}")

        except Exception as e:
            logger.error(f"Error handling request error: {str(e)}")
    
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

    def _get_orchestrator_id(self) -> ModuleIdentifier:
        """Get orchestrator identifier"""
        return ModuleIdentifier(
            component_name="DataOrchestrator",
            component_type=ComponentType.ORCHESTRATOR,
            method_name="manage_pipeline",
            instance_id=self.registry.get_component_uuid("DataOrchestrator")
        )