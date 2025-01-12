from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import uuid
import pandas as pd

from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.data_conductor import DataConductor
from backend.core.orchestration.staging_manager import StagingManager
from backend.core.orchestration.pipeline_manager import PipelineManager
from backend.database.repository.pipeline_repository import PipelineRepository
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.messaging.types import (
    ModuleIdentifier,
    ComponentType
)
from .stream_manager import StreamManager

logger = logging.getLogger(__name__)


class StreamService:
    """Comprehensive service for Stream operations with end-to-end pipeline integration"""
    source_type = 'stream'

    def __init__(
            self,
            message_broker: Optional[MessageBroker] = None,
            data_conductor: Optional[DataConductor] = None,
            staging_manager: Optional[StagingManager] = None,
            pipeline_manager: Optional[PipelineManager] = None,
            pipeline_repository: Optional[PipelineRepository] = None,
            control_point_manager: Optional[ControlPointManager] = None,
            stream_manager: Optional[StreamManager] = None
    ):
        """
        Initialize StreamService with configurable components

        Args:
            message_broker (Optional[MessageBroker]): Messaging broker
            data_conductor (Optional[DataConductor]): Route determination service
            staging_manager (Optional[StagingManager]): Data staging manager
            pipeline_manager (Optional[PipelineManager]): Pipeline management service
            control_point_manager (Optional[ControlPointManager]): Control point management service
            stream_manager (Optional[StreamManager]): Stream connection manager
        """
        # Create PipelineRepository if not provided
        if pipeline_repository is None:
            from backend.database.repository.pipeline_repository import PipelineRepository
            from backend.flask_api.app.middleware.auth_middleware import get_db_session
            pipeline_repository = PipelineRepository(get_db_session())

        # Create ControlPointManager if not provided
        if control_point_manager is None:
            control_point_manager = ControlPointManager(message_broker)

        # Initialize messaging and orchestration components
        self.message_broker = message_broker or MessageBroker()
        self.data_conductor = data_conductor or DataConductor(self.message_broker)
        self.staging_manager = staging_manager or StagingManager(
            message_broker=self.message_broker,
            control_point_manager=control_point_manager
        )
        self.pipeline_manager = pipeline_manager or PipelineManager(
            message_broker=self.message_broker,
            repository=pipeline_repository
        )

        # Initialize Stream Manager
        self.stream_manager = stream_manager or StreamManager(self.message_broker)

        # Set up message subscriptions
        self._setup_subscriptions()

        logger.info("StreamService initialized")

    def _setup_subscriptions(self):
        """Set up message broker subscriptions for Stream processing events"""
        # Create module identifiers for each subscription
        connection_handler = ModuleIdentifier(
            component_name='stream_service',
            component_type=ComponentType.HANDLER,
            method_name='handle_connection',
            instance_id=str(uuid.uuid4())
        )

        consumer_processing_handler = ModuleIdentifier(
            component_name='stream_service',
            component_type=ComponentType.HANDLER,
            method_name='process_consumer',
            instance_id=str(uuid.uuid4())
        )

        topic_processing_handler = ModuleIdentifier(
            component_name='stream_service',
            component_type=ComponentType.HANDLER,
            method_name='process_topic',
            instance_id=str(uuid.uuid4())
        )

        # Subscribe to Stream events with callback methods
        self.message_broker.subscribe(
            component=connection_handler,
            pattern='stream.connection.requested.#',
            callback=self._handle_connection_event
        )

        self.message_broker.subscribe(
            component=consumer_processing_handler,
            pattern='stream.consumer.processing.#',
            callback=self._start_consumer_processing
        )

        self.message_broker.subscribe(
            component=topic_processing_handler,
            pattern='stream.topic.processing.#',
            callback=self._start_topic_processing
        )

    def _handle_connection_event(self, connection_data: Dict[str, Any]):
        """
        Internal handler for Stream connection events

        Args:
            connection_data (Dict[str, Any]): Connection event data
        """
        try:
            logger.info(f"Processing Stream connection event: {connection_data.get('connection_id')}")

            # Validate connection data
            if not connection_data or 'connection_details' not in connection_data:
                raise ValueError("Invalid connection data")

            # Publish connection processing start event
            self.message_broker.publish('stream_connection_start', connection_data)

        except Exception as e:
            logger.error(f"Stream connection event handler error: {str(e)}", exc_info=True)
            # Publish error event
            self.message_broker.publish('stream_connection_error', {
                'error': str(e),
                'connection_data': connection_data
            })

    def _start_consumer_processing(self, consumer_data: Dict[str, Any]):
        """
        Initiate Stream consumer processing

        Args:
            consumer_data (Dict[str, Any]): Consumer data to process
        """
        try:
            # Process consumer
            result = self.process_consumer_request(
                consumer_data.get('connection_id'),
                consumer_data.get('consumer_data')
            )

            # Publish consumer processing complete event
            self.message_broker.publish('stream_consumer_processing_complete', result)

        except Exception as e:
            logger.error(f"Stream consumer processing error: {str(e)}", exc_info=True)
            # Publish error event
            self.message_broker.publish('stream_consumer_processing_error', {
                'error': str(e),
                'consumer_data': consumer_data
            })

    def _start_topic_processing(self, topic_data: Dict[str, Any]):
        """
        Initiate Stream topic processing

        Args:
            topic_data (Dict[str, Any]): Topic data to process
        """
        try:
            # Process topic
            result = self.process_topic_request(
                topic_data.get('connection_id'),
                topic_data.get('topic_data')
            )

            # Publish topic processing complete event
            self.message_broker.publish('stream_topic_processing_complete', result)

        except Exception as e:
            logger.error(f"Stream topic processing error: {str(e)}", exc_info=True)
            # Publish error event
            self.message_broker.publish('stream_topic_processing_error', {
                'error': str(e),
                'topic_data': topic_data
            })

    def process_connection_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle stream connection request

        Args:
            data (Dict[str, Any]): Connection configuration data

        Returns:
            Dict[str, Any]: Connection processing result
        """
        try:
            # Generate unique identifiers
            connection_id = str(uuid.uuid4())
            pipeline_id = self._create_pipeline_entry(data)

            # Process connection request
            result = self.stream_manager.process_stream_request({
                'action': 'connect',
                'data': {**data, 'connection_id': connection_id}
            })

            if result.get('status') != 'success':
                return {
                    'status': 'error',
                    'message': result.get('message', 'Connection failed')
                }

            # Store connection metadata in staging
            staging_id = self.staging_manager.store_data(
                pipeline_id=pipeline_id,
                data=result.get('data', {}),
                metadata={
                    'connection_id': connection_id,
                    'source_type': 'stream',
                    'connection_details': data
                }
            )

            # Determine initial route
            initial_route = self.data_conductor.get_initial_route(
                pipeline_id,
                context={'connection_data': result.get('data', {})}
            )

            # Track route execution
            route_execution_id = self.data_conductor.start_route_execution(
                pipeline_id,
                route_type='sequential',
                initial_nodes=initial_route
            )

            return {
                'status': 'success',
                'connection_id': connection_id,
                'pipeline_id': pipeline_id,
                'staging_id': staging_id,
                'route_execution_id': route_execution_id,
                'message': 'Stream connection established'
            }

        except Exception as e:
            logger.error(f"Stream connection error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }

    def process_consumer_request(self, connection_id: str, consumer_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle consumer operations request

        Args:
            connection_id (str): Stream connection identifier
            consumer_data (Dict[str, Any]): Consumer operation details

        Returns:
            Dict[str, Any]: Consumer processing result
        """
        try:
            # Generate pipeline ID
            pipeline_id = self._create_pipeline_entry(consumer_data)

            # Process consumer request
            result = self.stream_manager.process_stream_request({
                'action': 'consumer',
                'connection_id': connection_id,
                'consumer_data': consumer_data
            })

            if result.get('status') != 'success':
                return {
                    'status': 'error',
                    'message': result.get('message', 'Consumer processing failed')
                }

            # Convert result to DataFrame for consistency
            df = pd.DataFrame(
                result.get('data', []) if isinstance(result.get('data'), list) else [result.get('data', {})])

            # Store consumer result in staging
            staging_id = self.staging_manager.store_data(
                pipeline_id=pipeline_id,
                data=df,
                metadata={
                    'connection_id': connection_id,
                    'source_type': 'stream_consumer',
                    'consumer_details': consumer_data
                }
            )

            # Determine next nodes in route
            route_execution_id = self.data_conductor.start_route_execution(
                pipeline_id,
                route_type='sequential',
                initial_nodes=['stream_consumer']
            )

            # Use data conductor to get next nodes
            context = {
                'connection_id': connection_id,
                'consumer_data': consumer_data,
                'result': result.get('data', [])
            }
            next_nodes = self.data_conductor.get_next_nodes(
                pipeline_id,
                current_node='stream_consumer',
                context=context
            )

            return {
                'status': 'success',
                'pipeline_id': pipeline_id,
                'staging_id': staging_id,
                'route_execution_id': route_execution_id,
                'next_nodes': next_nodes,
                'data': result.get('data', [])
            }

        except Exception as e:
            logger.error(f"Stream consumer processing error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }

    def process_topic_request(self, connection_id: str, topic_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle topic operations request

        Args:
            connection_id (str): Stream connection identifier
            topic_data (Dict[str, Any]): Topic operation details

        Returns:
            Dict[str, Any]: Topic processing result
        """
        try:
            # Generate pipeline ID
            pipeline_id = self._create_pipeline_entry(topic_data)

            # Process topic request
            result = self.stream_manager.process_stream_request({
                'action': 'topic',
                'connection_id': connection_id,
                'topic_data': topic_data
            })

            if result.get('status') != 'success':
                return {
                    'status': 'error',
                    'message': result.get('message', 'Topic processing failed')
                }

            # Convert result to DataFrame for consistency
            df = pd.DataFrame(
                result.get('data', []) if isinstance(result.get('data'), list) else [result.get('data', {})])

            # Store topic result in staging
            staging_id = self.staging_manager.store_data(
                pipeline_id=pipeline_id,
                data=df,
                metadata={
                    'connection_id': connection_id,
                    'source_type': 'stream_topic',
                    'topic_details': topic_data
                }
            )

            # Determine next nodes in route
            route_execution_id = self.data_conductor.start_route_execution(
                pipeline_id,
                route_type='sequential',
                initial_nodes=['stream_topic']
            )

            # Use data conductor to get next nodes
            context = {
                'connection_id': connection_id,
                'topic_data': topic_data,
                'result': result.get('data', [])
            }
            next_nodes = self.data_conductor.get_next_nodes(
                pipeline_id,
                current_node='stream_topic',
                context=context
            )

            return {
                'status': 'success',
                'pipeline_id': pipeline_id,
                'staging_id': staging_id,
                'route_execution_id': route_execution_id,
                'next_nodes': next_nodes,
                'data': result.get('data', [])
            }

        except Exception as e:
            logger.error(f"Stream topic processing error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }

    def _create_pipeline_entry(self, data: Dict[str, Any]) -> str:
        """
        Create pipeline entry for tracking stream operations

        Args:
            data (Dict[str, Any]): Operation metadata

        Returns:
            str: Pipeline identifier
        """
        pipeline_config = {
            'source_type': self.source_type,
            'metadata': data,
            'start_time': datetime.now().isoformat()
        }

        return self.pipeline_manager.start_pipeline(pipeline_config)

    def get_metrics(self, connection_id: str) -> Dict[str, Any]:
        """
        Get stream metrics

        Args:
            connection_id (str): Stream connection identifier

        Returns:
            Dict[str, Any]: Stream metrics or error response
        """
        try:
            # Generate pipeline ID for metrics retrieval
            pipeline_id = self._create_pipeline_entry({
                'connection_id': connection_id,
                'action': 'get_metrics'
            })

            # Retrieve metrics from stream manager
            result = self.stream_manager.get_metrics(connection_id)

            # Check for unsuccessful result
            if result.get('status') != 'success':
                return {
                    'status': 'error',
                    'message': result.get('message', 'Metrics retrieval failed')
                }

            # Store metrics in staging
            staging_id = self.staging_manager.store_data(
                pipeline_id=pipeline_id,
                data=result.get('data', {}),
                metadata={
                    'connection_id': connection_id,
                    'source_type': 'stream_metrics'
                }
            )

            # Determine route execution
            route_execution_id = self.data_conductor.start_route_execution(
                pipeline_id,
                route_type='sequential',
                initial_nodes=['stream_metrics']
            )

            return {
                'status': 'success',
                'pipeline_id': pipeline_id,
                'staging_id': staging_id,
                'route_execution_id': route_execution_id,
                'data': result.get('data', {})
            }

        except Exception as e:
            logger.error(f"Metrics retrieval error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e)
            }

    def list_connections(self) -> Dict[str, Any]:
        """
        List all stream connections

        Returns:
            Dict[str, Any]: List of stream connections
        """
        try:
            result = self.stream_manager.list_connections()
            return self._format_response(result)
        except Exception as e:
            logger.error(f"List connections error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }


    def close_connection(self, connection_id: str) -> Dict[str, Any]:
        """
        Close stream connection

        Args:
            connection_id (str): Connection identifier to close

        Returns:
            Dict[str, Any]: Connection closure result
        """
        try:
            # Close connection
            result = self.stream_manager.close_connection(connection_id)

            # Remove any staged data for this connection
            staged_data = self.staging_manager.get_pipeline_data(connection_id)
            for item in staged_data:
                self.staging_manager.delete_data(item['staging_id'])

            return self._format_response(result)
        except Exception as e:
            logger.error(f"Connection closure error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }


    def _format_response(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format manager response for routes

        Args:
            result (Dict[str, Any]): Raw response from manager

        Returns:
            Dict[str, Any]: Formatted response
        """
        if result.get('status') == 'error':
            return {
                'status': 'error',
                'message': result.get('message', 'Unknown error')
            }

        return {
            'status': 'success',
            'data': result.get('data', {}),
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'request_id': result.get('request_id'),
                **result.get('metadata', {})
            }
        }


    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve source information

        Args:
            source_id (str): Source identifier

        Returns:
            Optional[Dict[str, Any]]: Source details or None
        """
        try:
            connections = self.list_connections()
            if connections['status'] == 'success':
                for conn in connections.get('data', []):
                    if conn.get('id') == source_id:
                        return conn
            return None
        except Exception as e:
            logger.error(f"Error retrieving source: {str(e)}")
            return None


    def handle_orchestrator_feedback(self, feedback: Dict[str, Any]) -> None:
        """
        Handle feedback from orchestration components

        Args:
            feedback (Dict[str, Any]): Orchestrator feedback
        """
        try:
            feedback_type = feedback.get('type')
            pipeline_id = feedback.get('pipeline_id')

            if not pipeline_id:
                logger.warning("Received feedback without pipeline_id")
                return

            if feedback_type == 'consumer_status':
                # Update route execution
                route_execution_id = self.data_conductor.update_route_execution(
                    feedback.get('route_execution_id'),
                    completed_node='stream_consumer',
                    context=feedback
                )
                consumer_id = feedback.get('consumer_id')
                logger.info(f"Updated route execution for pipeline {pipeline_id}, consumer {consumer_id}")

            elif feedback_type == 'topic_update':
                topic = feedback.get('topic')
                logger.info(f"Received topic update for {topic}")

            elif feedback_type == 'error':
                logger.error(f"Received error feedback for pipeline {pipeline_id}: {feedback.get('error')}")

        except Exception as e:
            logger.error(f"Error handling orchestrator feedback: {str(e)}")