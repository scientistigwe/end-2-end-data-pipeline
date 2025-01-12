from __future__ import annotations

import logging
import asyncio
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
from backend.core.orchestration.base_manager import BaseManager
from backend.core.monitoring.process import ProcessMonitor
from backend.core.utils.process_manager import ProcessManager, with_process_handling
from .db_validator import DBValidator
from .db_fetcher import DBFetcher
from .db_config import Config

logger = logging.getLogger(__name__)


@dataclass
class DBContext:
    """Context for database operations"""
    request_id: str
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)


class DBManager(BaseManager):
    """Enhanced database manager with control point integration"""

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            config: Optional[Config] = None
    ):
        """Initialize DBManager with required components"""
        super().__init__(
            message_broker=message_broker,
            component_name="DBManager"
        )

        self.control_point_manager = control_point_manager
        self.config = config or Config()
        self.validator = DBValidator(config=self.config)

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="database",
            source_id=str(uuid4())
        )

        # Initialize process handler
        self.process_handler = ProcessManager(config=self.config)

        # State tracking
        self.active_connections: Dict[str, DBFetcher] = {}
        self.active_operations: Dict[str, DBContext] = {}

        # Initialize handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Set up message handlers"""
        handlers = {
            MessageType.DB_REQUEST: self._handle_db_request,
            MessageType.CONTROL_POINT_DECISION: self._handle_control_decision,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.ERROR: self._handle_error,
            MessageType.QUALITY_COMPLETE: self._handle_quality_complete
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                component=self.module_id,
                pattern=f"{message_type.value}.#",
                callback=handler
            )

    @with_process_handling
    async def process_db_request(
            self,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process database request with control points"""
        try:
            # Create operation context
            context = DBContext(
                request_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING,
                metadata=request_data.get('metadata', {})
            )

            self.active_operations[context.request_id] = context

            # Process based on action
            action = request_data.get('action')
            if action == 'connect':
                return await self._handle_connect_request(context, request_data)
            elif action == 'execute_query':
                return await self._handle_query_request(context, request_data)
            elif action == 'get_schema':
                return await self._handle_schema_request(context, request_data)
            else:
                raise ValueError(f"Unknown action: {action}")

        except Exception as e:
            logger.error(f"Database request error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _handle_connect_request(
            self,
            context: DBContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle database connection request with control points"""
        try:
            stages = [
                (ProcessingStage.INITIAL_VALIDATION, self._validate_connection_params),
                (ProcessingStage.CONNECTION_CHECK, self._check_connection),
                (ProcessingStage.ACCESS_CHECK, self._verify_access),
                (ProcessingStage.SETUP, self._setup_connection)
            ]

            stage_results = {}

            for stage, processor in stages:
                context.stage = stage
                await self._update_status(context, f"Starting {stage.value}")

                # Process stage
                result = await processor(context, request_data)

                # Create control point
                decision = await self._create_control_point(
                    context=context,
                    stage=stage,
                    data=result,
                    options=['proceed', 'reject']
                )

                if decision['decision'] == 'reject':
                    await self._handle_rejection(context, decision.get('details', {}))
                    raise ValueError(f"Connection rejected at stage {stage.value}")

                stage_results[stage.value] = result

                # Update processing history
                context.processing_history.append({
                    'stage': stage.value,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'completed',
                    'details': {
                        k: v for k, v in result.items()
                        if k not in ['credentials']
                    }
                })

            return stage_results

        except Exception as e:
            await self._handle_error(context, str(e))
            raise

    async def _validate_connection_params(
            self,
            context: DBContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate connection parameters"""
        return await self.validator.validate_connection_params(request_data)

    async def _check_connection(
            self,
            context: DBContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check database connection"""
        try:
            # Create fetcher
            fetcher = DBFetcher(request_data)
            connection_check = await fetcher.check_connection()

            if connection_check['status'] == 'connected':
                return {
                    'connection_status': 'success',
                    'diagnostics': connection_check.get('diagnostics', {}),
                    'capabilities': connection_check.get('capabilities', {})
                }
            else:
                raise ValueError(connection_check.get('error', 'Connection failed'))

        except Exception as e:
            logger.error(f"Connection check error: {str(e)}")
            raise

    async def _verify_access(
            self,
            context: DBContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify database access permissions"""
        try:
            # Create fetcher if not exists
            fetcher = DBFetcher(request_data)

            # Check permissions
            access_check = await self.validator.verify_access_permissions(
                fetcher.engine,
                request_data.get('database'),
                request_data.get('schema')
            )

            if not access_check['has_access']:
                raise ValueError(access_check['message'])

            return {
                'access_status': 'success',
                'permissions': access_check['permissions'],
                'restrictions': access_check.get('restrictions', [])
            }

        except Exception as e:
            logger.error(f"Access verification error: {str(e)}")
            raise

    async def _setup_connection(
            self,
            context: DBContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set up database connection"""
        try:
            # Create fetcher
            fetcher = DBFetcher(request_data)

            # Generate connection ID
            connection_id = str(uuid4())

            # Store connection
            self.active_connections[connection_id] = fetcher

            return {
                'connection_id': connection_id,
                'connection_info': {
                    'database_type': request_data.get('type'),
                    'database': request_data.get('database'),
                    'schema': request_data.get('schema'),
                    'created_at': datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Connection setup error: {str(e)}")
            raise

    async def _handle_query_request(
            self,
            context: DBContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle query execution with control points"""
        try:
            stages = [
                (ProcessingStage.INITIAL_VALIDATION, self._validate_query),
                (ProcessingStage.ACCESS_CHECK, self._check_query_access),
                (ProcessingStage.DATA_EXTRACTION, self._execute_query),
                (ProcessingStage.DATA_VALIDATION, self._validate_query_data),
                (ProcessingStage.PROCESSING, self._process_query_data)
            ]

            stage_results = {}

            for stage, processor in stages:
                context.stage = stage
                await self._update_status(context, f"Starting {stage.value}")

                # Process stage
                result = await processor(context, request_data)

                # Create control point
                decision = await self._create_control_point(
                    context=context,
                    stage=stage,
                    data=result,
                    options=['proceed', 'modify', 'reject']
                )

                if decision['decision'] == 'reject':
                    await self._handle_rejection(context, decision.get('details', {}))
                    raise ValueError(f"Query rejected at stage {stage.value}")

                elif decision['decision'] == 'modify':
                    request_data = await self._apply_modifications(
                        request_data,
                        decision.get('modifications', {})
                    )

                stage_results[stage.value] = result

                # Update processing history
                context.processing_history.append({
                    'stage': stage.value,
                    'timestamp': datetime.now().isoformat(),
                    'status': 'completed',
                    'details': {
                        k: v for k, v in result.items()
                        if k not in ['data']  # Exclude large data from history
                    }
                })

            return stage_results

        except Exception as e:
            await self._handle_error(context, str(e))
            raise

    async def _validate_query(
            self,
            context: DBContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate query syntax and security"""
        return await self.validator.validate_query_comprehensive(
            request_data.get('query'),
            request_data.get('params', {})
        )

    async def _check_query_access(
            self,
            context: DBContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check access permissions for query"""
        try:
            connection_id = request_data.get('connection_id')
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]
            access_check = await self.validator.verify_query_access(
                fetcher.engine,
                request_data.get('query'),
                request_data.get('params', {})
            )

            if not access_check['has_access']:
                raise ValueError(access_check['message'])

            return {
                'access_status': 'success',
                'permissions': access_check['permissions'],
                'objects_accessed': access_check['objects_accessed']
            }

        except Exception as e:
            logger.error(f"Query access check error: {str(e)}")
            raise

    async def _execute_query(
            self,
            context: DBContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute database query"""
        try:
            connection_id = request_data.get('connection_id')
            fetcher = self.active_connections[connection_id]

            # Record start metrics
            await self.process_monitor.record_metric(
                'query_execution_start',
                1,
                connection_id=connection_id,
                query_type=self._get_query_type(request_data.get('query'))
            )

            start_time = datetime.now()
            result = await fetcher.fetch_data_async(
                request_data.get('query'),
                request_data.get('params', {})
            )
            duration = (datetime.now() - start_time).total_seconds()

            # Record completion metrics
            await self.process_monitor.record_operation_metric(
                'query_execution',
                success=True,
                duration=duration,
                rows_processed=result.get('row_count', 0)
            )

            return {
                'data': result.get('data'),
                'metadata': {
                    'row_count': result.get('row_count'),
                    'columns': result.get('columns'),
                    'execution_time': duration
                }
            }

        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise

    async def _validate_query_data(
            self,
            context: DBContext,
            result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate query results"""
        return await self.validator.validate_query_data(
            result_data.get('data'),
            context.metadata
        )

    async def _process_query_data(
            self,
            context: DBContext,
            result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process query results with data analysis"""
        try:
            data = result_data.get('data')
            metadata = result_data.get('metadata', {})

            # Analyze data characteristics
            analysis = {
                'total_rows': metadata.get('row_count', 0),
                'columns': metadata.get('columns', []),
                'null_analysis': self._analyze_null_values(data),
                'type_distribution': self._analyze_type_distribution(data),
                'value_distribution': self._analyze_value_distribution(data)
            }

            # Generate insights
            insights = self._generate_data_insights(analysis)

            # Record metrics
            await self.process_monitor.record_operation_metric(
                'data_processing',
                success=True,
                row_count=analysis['total_rows'],
                column_count=len(analysis['columns'])
            )

            return {
                'processed_data': data,
                'analysis': analysis,
                'insights': insights,
                'processing_stats': {
                    'timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Data processing error: {str(e)}")
            raise

    async def _create_control_point(
            self,
            context: DBContext,
            stage: ProcessingStage,
            data: Dict[str, Any],
            options: List[str]
    ) -> Dict[str, Any]:
        """Create control point and wait for decision"""
        try:
            control_point_id = await self.control_point_manager.create_control_point(
                pipeline_id=context.pipeline_id,
                stage=stage,
                data={
                    'request_id': context.request_id,
                    'stage_data': data,
                    'metadata': context.metadata
                },
                options=options
            )

            context.control_points.append(control_point_id)
            context.status = ProcessingStatus.AWAITING_DECISION

            await self._update_status(
                context,
                f"Awaiting decision at {stage.value}"
            )

            return await self.control_point_manager.wait_for_decision(
                control_point_id,
                timeout=self.config.QUERY_TIMEOUT
            )

        except Exception as e:
            logger.error(f"Control point creation error: {str(e)}")
            raise

    async def _update_status(
            self,
            context: DBContext,
            message: str
    ) -> None:
        """Update processing status"""
        try:
            status_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("pipeline_manager"),
                message_type=MessageType.STATUS_UPDATE,
                content={
                    'pipeline_id': context.pipeline_id,
                    'request_id': context.request_id,
                    'status': context.status.value,
                    'stage': context.stage.value if context.stage else None,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(status_message)

            # Record metrics
            await self.process_monitor.record_status_update(
                status=context.status.value,
                stage=context.stage.value if context.stage else None,
                request_id=context.request_id
            )

        except Exception as e:
            logger.error(f"Status update error: {str(e)}")

    def _analyze_null_values(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze null values in dataset"""
        try:
            null_counts = data.isnull().sum()
            null_percentages = (null_counts / len(data) * 100).round(2)

            return {
                'null_counts': null_counts.to_dict(),
                'null_percentages': null_percentages.to_dict(),
                'total_null_cells': int(null_counts.sum()),
                'completeness_score': float(
                    (1 - null_counts.sum() / (len(data) * len(data.columns))) * 100
                )
            }

        except Exception as e:
            logger.error(f"Null analysis error: {str(e)}")
            return {}

    def _analyze_type_distribution(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze data type distribution"""
        try:
            type_counts = data.dtypes.value_counts().to_dict()
            column_types = data.dtypes.to_dict()

            return {
                'type_summary': {
                    str(k): int(v) for k, v in type_counts.items()
                },
                'column_types': {
                    k: str(v) for k, v in column_types.items()
                }
            }

        except Exception as e:
            logger.error(f"Type analysis error: {str(e)}")
            return {}

    def _analyze_value_distribution(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze value distribution for each column"""
        try:
            distributions = {}

            for column in data.columns:
                if data[column].dtype in ['int64', 'float64']:
                    # Numeric column analysis
                    stats = data[column].describe()
                    distributions[column] = {
                        'type': 'numeric',
                        'min': float(stats['min']),
                        'max': float(stats['max']),
                        'mean': float(stats['mean']),
                        'std': float(stats['std'])
                    }
                elif data[column].dtype == 'object':
                    # Categorical column analysis
                    value_counts = data[column].value_counts()
                    unique_ratio = len(value_counts) / len(data)
                    distributions[column] = {
                        'type': 'categorical',
                        'unique_values': len(value_counts),
                        'unique_ratio': float(unique_ratio),
                        'top_values': value_counts.head().to_dict()
                    }

            return distributions

        except Exception as e:
            logger.error(f"Distribution analysis error: {str(e)}")
            return {}

    def _generate_data_insights(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate insights from data analysis"""
        insights = []

        try:
            # Completeness insights
            completeness = analysis.get('null_analysis', {}).get('completeness_score', 0)
            if completeness < 80:
                insights.append({
                    'type': 'data_quality',
                    'category': 'completeness',
                    'message': f"Data completeness is low ({completeness:.1f}%)",
                    'suggestion': "Consider handling missing values"
                })

            # Type distribution insights
            type_dist = analysis.get('type_distribution', {}).get('type_summary', {})
            if len(type_dist) > 3:
                insights.append({
                    'type': 'data_structure',
                    'category': 'types',
                    'message': "Mixed data types detected",
                    'suggestion': "Consider standardizing data types"
                })

            # Value distribution insights
            value_dist = analysis.get('value_distribution', {})
            for column, dist in value_dist.items():
                if dist['type'] == 'categorical' and dist['unique_ratio'] > 0.9:
                    insights.append({
                        'type': 'data_structure',
                        'category': 'cardinality',
                        'message': f"High cardinality in column {column}",
                        'suggestion': "Review if this column should be categorical"
                    })

            return insights

        except Exception as e:
            logger.error(f"Insight generation error: {str(e)}")
            return []

    def _get_query_type(self, query: str) -> str:
        """Determine query type"""
        query = query.strip().upper()
        if query.startswith('SELECT'):
            return 'select'
        elif query.startswith('WITH'):
            return 'with'
        elif query.startswith('SHOW') or query.startswith('DESCRIBE'):
            return 'metadata'
        else:
            return 'unknown'

    async def list_connections(self) -> Dict[str, Any]:
        """List all active connections with detailed status"""
        try:
            connections = []
            for conn_id, fetcher in self.active_connections.items():
                # Get connection stats
                stats = await fetcher.get_connection_stats()
                connections.append({
                    'connection_id': conn_id,
                    'database_type': fetcher.config.get('type'),
                    'database': fetcher.config.get('database'),
                    'schema': fetcher.config.get('schema'),
                    'status': 'active',
                    'stats': stats,
                    'created_at': fetcher.created_at.isoformat()
                })

            return {
                'status': 'success',
                'count': len(connections),
                'connections': connections
            }

        except Exception as e:
            logger.error(f"List connections error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def close_connection(self, connection_id: str) -> Dict[str, Any]:
        """Close database connection with cleanup"""
        try:
            if connection_id not in self.active_connections:
                raise ValueError(f"Connection {connection_id} not found")

            fetcher = self.active_connections[connection_id]

            # Record final metrics
            stats = await fetcher.get_connection_stats()
            await self.process_monitor.record_metric(
                'connection_close',
                1,
                connection_id=connection_id,
                duration=stats.get('duration'),
                queries_executed=stats.get('queries_executed', 0)
            )

            # Close connection
            await fetcher.close()

            # Remove from active connections
            del self.active_connections[connection_id]

            return {
                'status': 'success',
                'message': f'Connection {connection_id} closed successfully',
                'statistics': stats
            }

        except Exception as e:
            logger.error(f"Connection closure error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        try:
            # Close all active connections
            for connection_id in list(self.active_connections.keys()):
                try:
                    await self.close_connection(connection_id)
                except Exception as e:
                    logger.error(
                        f"Error closing connection {connection_id}: {str(e)}"
                    )

            # Clean up processing contexts
            for request_id in list(self.active_operations.keys()):
                context = self.active_operations[request_id]
                # Clean up control points
                for control_point_id in context.control_points:
                    try:
                        await self.control_point_manager.cleanup_control_point(
                            control_point_id
                        )
                    except Exception as e:
                        logger.error(
                            f"Control point cleanup error: {str(e)}"
                        )

            self.active_operations.clear()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Manager cleanup error: {str(e)}", exc_info=True)