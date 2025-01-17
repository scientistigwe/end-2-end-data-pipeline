from __future__ import annotations

import logging
import asyncio
import pandas as pd
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from uuid import uuid4

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    ComponentType,
    MessageType,
    ProcessingMessage,
    ModuleIdentifier,
    ProcessingStage,
    ProcessingStatus
)
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from backend.core.utils.process_manager import ProcessManager
from backend.core.orchestration.base_manager import BaseManager

from .db_validator import DatabaseSourceValidator
from .db_config import DatabaseSourceConfig
from .db_fetcher import DBFetcher

logger = logging.getLogger(__name__)


@dataclass
class DBContext:
    """Context for db operations"""
    request_id: str
    pipeline_id: str
    connection_id: Optional[str] = None
    stage: Optional[ProcessingStage] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)


class DBManager(BaseManager):
    """Enhanced db manager with CPM integration"""

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            config: Optional[DatabaseSourceConfig] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize DBManager with required components"""
        super().__init__(
            message_broker=message_broker,
            component_name="DBManager"
        )

        self.control_point_manager = control_point_manager
        self.config = config or DatabaseSourceConfig()
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.validator = DatabaseSourceValidator()

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="database_manager",
            source_id=str(uuid4())
        )

        # State tracking
        self.active_connections: Dict[str, DBFetcher] = {}
        self.active_contexts: Dict[str, DBContext] = {}

        # Register handlers with CPM
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Register handlers with Control Point Manager"""
        handlers = {
            'db.connect.request': self._handle_connect_request,
            'db.query.request': self._handle_query_request,
            'db.validate.request': self._handle_validate_request,
            'db.process.data': self._handle_process_data
        }

        self.control_point_manager.register_handler(
            source_type='db_manager',
            handlers=handlers
        )

    async def _handle_connect_request(self, control_point: ControlPoint) -> None:
        """Handle db connection request through CPM"""
        try:
            request_data = control_point.data
            context = DBContext(
                request_id=str(uuid4()),
                pipeline_id=control_point.pipeline_id,
                metadata=request_data
            )
            self.active_contexts[context.request_id] = context

            # Validate connection config
            validation_results = self.validator.validate_source_configuration(
                request_data
            )
            validation_errors = [
                result for result in validation_results
                if not result.passed
            ]

            if validation_errors:
                error_messages = [
                    f"{result.check_type}: {result.message}"
                    for result in validation_errors
                ]
                await self.control_point_manager.submit_decision(
                    control_point.id,
                    'reject',
                    {'reason': '; '.join(error_messages)}
                )
                return

            # Create fetcher and test connection
            fetcher = DBFetcher(request_data)
            connection_check = await fetcher.check_connection()

            if connection_check['status'] != 'connected':
                await self.control_point_manager.submit_decision(
                    control_point.id,
                    'reject',
                    {'reason': connection_check.get('error', 'Connection failed')}
                )
                return

            # Store connection
            connection_id = str(uuid4())
            self.active_connections[connection_id] = fetcher
            context.connection_id = connection_id

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {
                    'connection_id': connection_id,
                    'connection_details': {
                        'database_type': request_data.get('type'),
                        'db': request_data.get('db'),
                        'host': request_data.get('host')
                    }
                }
            )

        except Exception as e:
            logger.error(f"Connection request error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    async def _handle_query_request(self, control_point: ControlPoint) -> None:
        """Handle db query request through CPM"""
        try:
            request_data = control_point.data
            connection_id = request_data.get('connection_id')

            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]
            context = DBContext(
                request_id=str(uuid4()),
                pipeline_id=control_point.pipeline_id,
                connection_id=connection_id,
                metadata=request_data
            )
            self.active_contexts[context.request_id] = context

            # Validate and execute query
            validation_results = await self.validator.validate_query_comprehensive(
                request_data.get('query'),
                request_data.get('params', {})
            )

            if not validation_results['passed']:
                await self.control_point_manager.submit_decision(
                    control_point.id,
                    'reject',
                    {'reason': validation_results['summary']}
                )
                return

            # Fetch data
            result = await fetcher.fetch_data_async(
                request_data.get('query'),
                request_data.get('params', {})
            )

            # Create data processing control point
            process_point = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=ProcessingStage.PROCESSING,
                data={
                    'request_id': context.request_id,
                    'query_result': result,
                    'metadata': context.metadata
                },
                options=['process']
            )

            await self.control_point_manager.submit_decision(
                control_point.id,
                'proceed',
                {
                    'process_point_id': process_point.id,
                    'data_preview': result.get('preview')
                }
            )

        except Exception as e:
            logger.error(f"Query request error: {str(e)}", exc_info=True)
            await self.control_point_manager.submit_decision(
                control_point.id,
                'reject',
                {'reason': str(e)}
            )

    def _setup_message_handlers(self) -> None:
        """Set up message handlers for db operations"""
        handlers = {
            MessageType.DB_CONNECT: self._handle_connection_request,
            MessageType.DB_QUERY: self._handle_query_request,
            MessageType.DB_SCHEMA: self._handle_schema_request
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                component=self.module_id,
                pattern=f"{message_type.value}.#",
                callback=handler
            )

    async def _handle_connection_request(
            self, 
            message: ProcessingMessage
    ) -> None:
        """Handle db connection request"""
        try:
            # Create context
            context = DBContext(
                request_id=str(uuid4()),
                pipeline_id=message.metadata.pipeline_id or str(uuid4()),
                metadata=message.content
            )
            self.active_contexts[context.request_id] = context

            # Validate connection parameters
            validation_results = self.validator.validate_source_configuration(
                message.content
            )
            validation_errors = [
                result for result in validation_results 
                if not result.passed
            ]

            if validation_errors:
                error_messages = [
                    f"{result.check_type}: {result.message}" 
                    for result in validation_errors
                ]
                raise ValueError(f"Connection validation failed: {'; '.join(error_messages)}")

            # Attempt to create db fetcher
            fetcher = DBFetcher(message.content)
            
            # Verify connection
            connection_check = await fetcher.check_connection()
            
            if connection_check['status'] != 'connected':
                raise ValueError(connection_check.get('error', 'Connection failed'))

            # Generate connection ID
            connection_id = str(uuid4())
            
            # Store connection
            self.active_connections[connection_id] = fetcher
            context.connection_id = connection_id

            # Prepare response
            response = message.create_response(
                message_type=MessageType.DB_SUCCESS,
                content={
                    'connection_id': connection_id,
                    'connection_details': {
                        'database_type': message.content.get('type'),
                        'db': message.content.get('db'),
                        'host': message.content.get('host')
                    },
                    'diagnostics': connection_check.get('diagnostics', {})
                }
            )

            # Publish response
            await self.message_broker.publish(response)

            # Record metrics
            await self.process_monitor.record_metric(
                'connection_established',
                1,
                database_type=message.content.get('type')
            )

        except Exception as e:
            # Handle and log errors
            logger.error(f"Connection request error: {str(e)}", exc_info=True)
            
            # Prepare error response
            error_response = message.create_response(
                message_type=MessageType.DB_ERROR,
                content={
                    'error': str(e),
                    'request_id': context.request_id
                }
            )

            # Publish error
            await self.message_broker.publish(error_response)

            # Record error metrics
            await self.process_monitor.record_metric(
                'connection_error',
                1,
                error_message=str(e)
            )

    async def _handle_query_request(
            self, 
            message: ProcessingMessage
    ) -> None:
        """Handle db query request"""
        try:
            # Validate connection ID
            connection_id = message.content.get('connection_id')
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            # Create context
            context = DBContext(
                request_id=str(uuid4()),
                pipeline_id=message.metadata.pipeline_id or str(uuid4()),
                connection_id=connection_id,
                metadata=message.content
            )
            self.active_contexts[context.request_id] = context

            # Get fetcher
            fetcher = self.active_connections[connection_id]

            # Execute query
            query = message.content.get('query')
            query_params = message.content.get('params', {})
            
            # Validate query 
            validation_results = await self.validator.validate_query_comprehensive(
                query, query_params
            )
            
            # Fetch data
            start_time = datetime.now()
            result = await fetcher.fetch_data_async(query, query_params)
            duration = (datetime.now() - start_time).total_seconds()

            # Convert to DataFrame
            df = pd.DataFrame(
                result.get('data', []), 
                columns=result.get('columns', [])
            )

            # Prepare response
            response = message.create_response(
                message_type=MessageType.DB_SUCCESS,
                content={
                    'data': df,
                    'metadata': {
                        'row_count': len(df),
                        'columns': list(df.columns),
                        'execution_time': duration,
                        'query': query
                    }
                }
            )

            # Publish response
            await self.message_broker.publish(response)

            # Record metrics
            await self.process_monitor.record_metric(
                'query_executed',
                1,
                row_count=len(df),
                execution_time=duration
            )

        except Exception as e:
            # Handle and log errors
            logger.error(f"Query request error: {str(e)}", exc_info=True)
            
            # Prepare error response
            error_response = message.create_response(
                message_type=MessageType.DB_ERROR,
                content={
                    'error': str(e),
                    'request_id': context.request_id
                }
            )

            # Publish error
            await self.message_broker.publish(error_response)

            # Record error metrics
            await self.process_monitor.record_metric(
                'query_error',
                1,
                error_message=str(e)
            )

    async def _handle_schema_request(
            self, 
            message: ProcessingMessage
    ) -> None:
        """Handle db schema request"""
        try:
            # Validate connection ID
            connection_id = message.content.get('connection_id')
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            # Create context
            context = DBContext(
                request_id=str(uuid4()),
                pipeline_id=message.metadata.pipeline_id or str(uuid4()),
                connection_id=connection_id,
                metadata=message.content
            )
            self.active_contexts[context.request_id] = context

            # Get fetcher
            fetcher = self.active_connections[connection_id]

            # Get schema information
            schema_info = await fetcher.get_schema_info(
                message.content.get('schema'),
                message.content.get('table')
            )

            # Prepare response
            response = message.create_response(
                message_type=MessageType.DB_SUCCESS,
                content={
                    'schema_info': schema_info
                }
            )

            # Publish response
            await self.message_broker.publish(response)

            # Record metrics
            await self.process_monitor.record_metric(
                'schema_retrieved',
                1,
                schema=message.content.get('schema')
            )

        except Exception as e:
            # Handle and log errors
            logger.error(f"Schema request error: {str(e)}", exc_info=True)
            
            # Prepare error response
            error_response = message.create_response(
                message_type=MessageType.DB_ERROR,
                content={
                    'error': str(e),
                    'request_id': context.request_id
                }
            )

            # Publish error
            await self.message_broker.publish(error_response)

            # Record error metrics
            await self.process_monitor.record_metric(
                'schema_error',
                1,
                error_message=str(e)
            )

    async def close_connection(self, connection_id: str) -> Dict[str, Any]:
        """Close a specific db connection"""
        try:
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]
            await fetcher.close()

            # Remove from active connections
            del self.active_connections[connection_id]

            # Remove associated contexts
            contexts_to_remove = [
                request_id for request_id, context 
                in self.active_contexts.items() 
                if context.connection_id == connection_id
            ]
            for request_id in contexts_to_remove:
                del self.active_contexts[request_id]

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

    async def list_connections(self) -> Dict[str, Any]:
        """List all active db connections"""
        try:
            connections = []
            for conn_id, fetcher in self.active_connections.items():
                connections.append({
                    'connection_id': conn_id,
                    'database_type': fetcher.config.get('type'),
                    'db': fetcher.config.get('db'),
                    'host': fetcher.config.get('host')
                })

            return {
                'status': 'success',
                'connections': connections,
                'count': len(connections)
            }

        except Exception as e:
            logger.error(f"Connection listing error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }

    async def cleanup(self) -> None:
        """Clean up all resources"""
        try:
            # Close all active connections
            for connection_id in list(self.active_connections.keys()):
                try:
                    await self.close_connection(connection_id)
                except Exception as cleanup_error:
                    logger.error(f"Error closing connection {connection_id}: {cleanup_error}")

            # Clear contexts
            self.active_contexts.clear()

            logger.info("DBManager resources cleaned up")

        except Exception as e:
            logger.error(f"Cleanup error: {str(e)}", exc_info=True)