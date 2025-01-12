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
from backend.core.orchestration.data_conductor import DataConductor
from backend.core.orchestration.staging_manager import StagingManager
from backend.core.orchestration.pipeline_manager import PipelineManager
from backend.core.control.control_point_manager import ControlPointManager
from backend.core.monitoring.process import ProcessMonitor
from backend.core.utils.process_manager import ProcessManager
from backend.database.repository.pipeline_repository import PipelineRepository

from .db_manager import DBManager
from .db_config import Config

logger = logging.getLogger(__name__)


@dataclass
class DBProcessContext:
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


class DBService:
    """Enhanced database service with comprehensive integration"""
    source_type = 'database'

    def __init__(
            self,
            message_broker: Optional[MessageBroker] = None,
            control_point_manager: Optional[ControlPointManager] = None,
            config: Optional[Config] = None,
            data_conductor: Optional[DataConductor] = None,
            staging_manager: Optional[StagingManager] = None,
            pipeline_manager: Optional[PipelineManager] = None,
            pipeline_repository: Optional[PipelineRepository] = None,
            db_manager: Optional[DBManager] = None
    ):
        """Initialize DBService with required components"""
        # Core components
        self.message_broker = message_broker or MessageBroker()
        self.control_point_manager = control_point_manager or ControlPointManager(
            message_broker=self.message_broker
        )
        self.config = config or Config()

        # Initialize managers
        self.data_conductor = data_conductor or DataConductor(self.message_broker)
        self.staging_manager = staging_manager or StagingManager(
            message_broker=self.message_broker,
            control_point_manager=self.control_point_manager
        )

        # Initialize repository if not provided
        if pipeline_repository is None:
            from backend.database.repository.pipeline_repository import PipelineRepository
            from backend.flask_api.app.middleware.auth_middleware import get_db_session
            pipeline_repository = PipelineRepository(get_db_session())

        self.pipeline_manager = pipeline_manager or PipelineManager(
            message_broker=self.message_broker,
            repository=pipeline_repository
        )

        # Initialize DB Manager
        self.db_manager = db_manager or DBManager(
            message_broker=self.message_broker,
            control_point_manager=self.control_point_manager,
            config=self.config
        )

        # Initialize monitoring and processing
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="db_service",
            source_id=str(uuid4())
        )

        self.process_handler = ProcessManager(config=self.config.QUERY)

        # Operation tracking
        self.active_processes: Dict[str, DBProcessContext] = {}

        # Initialize handlers
        self._setup_message_handlers()

        logger.info("DBService initialized")

    def _setup_message_handlers(self):
        """Set up message handlers"""
        handlers = {
            'db.connection.requested': self._handle_connection_event,
            'db.query.requested': self._handle_query_event,
            'db.query.complete': self._handle_query_complete,
            'db.control.decision': self._handle_control_decision,
            'db.error': self._handle_error
        }

        for pattern, handler in handlers.items():
            self.message_broker.subscribe(
                component=ModuleIdentifier(
                    component_name='db_service',
                    component_type=ComponentType.SERVICE,
                    method_name=handler.__name__
                ),
                pattern=pattern,
                callback=handler
            )

    async def process_connection_request(
            self,
            data: Dict[str, Any],
            user_id: str
    ) -> Dict[str, Any]:
        """Handle database connection request with control points"""
        try:
            # Create process context
            context = DBProcessContext(
                request_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING,
                metadata={
                    'user_id': user_id,
                    'request_type': 'connection',
                    **data.get('metadata', {})
                }
            )

            self.active_processes[context.request_id] = context

            try:
                result = await self._process_connection_stages(context, data)
                return {
                    'status': 'success',
                    'request_id': context.request_id,
                    'pipeline_id': context.pipeline_id,
                    'data': result
                }

            except asyncio.CancelledError:
                await self._handle_cancellation(context)
                raise
            except Exception as e:
                await self._handle_error(context, str(e))
                raise

        except Exception as e:
            logger.error(f"Connection request error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_connection_stages(
            self,
            context: DBProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process connection through stages with control points"""
        stages = [
            (ProcessingStage.INITIAL_VALIDATION, self._validate_connection_request),
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
                    if k not in ['credentials']  # Exclude sensitive data
                }
            })

        return stage_results

    async def process_query_request(
            self,
            connection_id: str,
            query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle database query request with control points"""
        try:
            # Create process context
            context = DBProcessContext(
                request_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING,
                metadata={
                    'connection_id': connection_id,
                    'query_type': self._get_query_type(query_data.get('query', '')),
                    'request_type': 'query'
                }
            )

            self.active_processes[context.request_id] = context

            try:
                result = await self._process_query_stages(context, query_data)

                # Record query metrics
                await self.process_monitor.record_metric(
                    'query_processed',
                    1,
                    query_type=context.metadata['query_type'],
                    rows=result.get('row_count', 0)
                )

                return {
                    'status': 'success',
                    'request_id': context.request_id,
                    'pipeline_id': context.pipeline_id,
                    'data': result
                }

            except asyncio.CancelledError:
                await self._handle_cancellation(context)
                raise
            except Exception as e:
                await self._handle_error(context, str(e))
                raise

        except Exception as e:
            logger.error(f"Query request error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_query_stages(
            self,
            context: DBProcessContext,
            query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process query through stages with control points"""
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
            result = await processor(context, query_data)

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
                query_data = await self._apply_modifications(
                    query_data,
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

    async def _create_control_point(
            self,
            context: DBProcessContext,
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
                timeout=self.config.QUERY.QUERY_TIMEOUT
            )

        except Exception as e:
            logger.error(f"Control point creation error: {str(e)}")
            raise

    async def _validate_connection_request(
            self,
            context: DBProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate connection request"""
        return await self.db_manager.validate_connection(request_data)

    async def _check_connection(
            self,
            context: DBProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check database connection"""
        return await self.db_manager.check_connection(request_data)

    async def _verify_access(
            self,
            context: DBProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify database access permissions"""
        return await self.db_manager.verify_access(request_data)

    async def _setup_connection(
            self,
            context: DBProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set up database connection"""
        connection_id = str(uuid4())

        # Store connection in staging
        staging_id = await self.staging_manager.store_data(
            pipeline_id=context.pipeline_id,
            data=request_data.get('connection_data', {}),
            metadata={
                'connection_id': connection_id,
                'source_type': 'database',
                'connection_details': {
                    k: v for k, v in request_data.items()
                    if k not in ['credentials']
                }
            }
        )

        # Initialize route
        route_execution_id = await self.data_conductor.start_route_execution(
            pipeline_id=context.pipeline_id,
            route_type='sequential',
            initial_nodes=['db_connection']
        )

        return {
            'connection_id': connection_id,
            'staging_id': staging_id,
            'route_execution_id': route_execution_id
        }

    async def _validate_query(
            self,
            context: DBProcessContext,
            query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate query request"""
        return await self.db_manager.validate_query(
            query_data.get('query'),
            query_data.get('params', {})
        )

    async def _check_query_access(
            self,
            context: DBProcessContext,
            query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check access permissions for query"""
        return await self.db_manager.check_query_access(
            query_data.get('connection_id'),
            query_data.get('query')
        )

    async def _execute_query(
            self,
            context: DBProcessContext,
            query_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute database query"""
        return await self.db_manager.execute_query(query_data)

    async def _validate_query_data(
            self,
            context: DBProcessContext,
            result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate query results"""
        return await self.db_manager.validate_query_data(
            result_data.get('data'),
            context.metadata
        )

    async def _process_query_data(
            self,
            context: DBProcessContext,
            result_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process query results"""
        processed_data = await self.db_manager.process_query_data(result_data)

        # Store in staging
        staging_id = await self.staging_manager.store_data(
            pipeline_id=context.pipeline_id,
            data=processed_data.get('data'),
            metadata={
                'source_type': 'database',
                'query_info': {
                    'type': context.metadata['query_type'],
                    'row_count': processed_data.get('row_count'),
                    'execution_time': processed_data.get('execution_time')
                }
            }
        )

        return {
            'processed_data': processed_data,
            'staging_id': staging_id
        }

    async def _update_status(
            self,
            context: DBProcessContext,
            message: str
    ) -> None:
        """Update processing status"""
        try:
            status_message = ProcessingMessage(
                source_identifier=ModuleIdentifier(
                    component_name='db_service',
                    component_type=ComponentType.SERVICE,
                    method_name='update_status'
                ),
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

    async def _handle_cancellation(self, context: DBProcessContext) -> None:
        """Handle operation cancellation"""
        try:
            context.status = ProcessingStatus.CANCELLED
            await self._update_status(context, "Operation cancelled")
            await self._cleanup_process(context.request_id)
        except Exception as e:
            logger.error(f"Cancellation handling error: {str(e)}")

    async def _handle_error(
            self,
            context: DBProcessContext,
            error: str
    ) -> None:
        """Handle operation error"""
        try:
            context.status = ProcessingStatus.ERROR
            context.error = error

            # Record error metrics
            await self.process_monitor.record_error(
                'operation_error',
                error=error,
                request_id=context.request_id,
                stage=context.stage.value if context.stage else None
            )

            await self._update_status(context, f"Error: {error}")
        except Exception as e:
            logger.error(f"Error handling error: {str(e)}")

    async def _handle_rejection(
            self,
            context: DBProcessContext,
            details: Dict[str, Any]
    ) -> None:
        """Handle operation rejection"""
        try:
            context.status = ProcessingStatus.REJECTED
            context.error = details.get('reason', 'Operation rejected')

            # Record rejection metrics
            await self.process_monitor.record_metric(
                'operation_rejected',
                1,
                reason=context.error,
                stage=context.stage.value if context.stage else None
            )

            await self._update_status(context, f"Rejected: {context.error}")
        except Exception as e:
            logger.error(f"Rejection handling error: {str(e)}")

    def _get_query_type(self, query: str) -> str:
        """Determine query type"""
        query = query.strip().upper()
        if query.startswith('SELECT'):
            if 'GROUP BY' in query:
                return 'aggregate'
            elif 'JOIN' in query:
                return 'join'
            else:
                return 'select'
        elif query.startswith('WITH'):
            return 'cte'
        elif query.startswith('SHOW') or query.startswith('DESCRIBE'):
            return 'metadata'
        else:
            return 'unknown'

    async def _cleanup_process(self, request_id: str) -> None:
        """Clean up process resources"""
        try:
            context = self.active_processes.get(request_id)
            if not context:
                return

            # Clean up control points
            for control_point_id in context.control_points:
                try:
                    await self.control_point_manager.cleanup_control_point(
                        control_point_id
                    )
                except Exception as e:
                    logger.error(
                        f"Control point cleanup error: {str(e)}",
                        exc_info=True
                    )

            # Remove from active processes
            del self.active_processes[request_id]

        except Exception as e:
            logger.error(f"Process cleanup error: {str(e)}", exc_info=True)

    async def cleanup(self) -> None:
        """Clean up service resources"""
        try:
            # Clean up all active processes
            for request_id in list(self.active_processes.keys()):
                await self._cleanup_process(request_id)

            # Clean up managers
            await self.db_manager.cleanup()

        except Exception as e:
            logger.error(f"Service cleanup error: {str(e)}", exc_info=True)

    async def handle_orchestrator_feedback(
            self,
            feedback: Dict[str, Any]
    ) -> None:
        """Handle feedback from orchestration components"""
        try:
            feedback_type = feedback.get('type')
            pipeline_id = feedback.get('pipeline_id')

            if not pipeline_id:
                logger.warning("Received feedback without pipeline_id")
                return

            if feedback_type == 'connection_complete':
                # Update route execution
                route_execution_id = await self.data_conductor.update_route_execution(
                    feedback.get('route_execution_id'),
                    completed_node='db_connection',
                    context=feedback
                )
                logger.info(f"Updated route execution for pipeline {pipeline_id}")

            elif feedback_type == 'query_complete':
                # Update route execution
                route_execution_id = await self.data_conductor.update_route_execution(
                    feedback.get('route_execution_id'),
                    completed_node='db_query',
                    context=feedback
                )
                logger.info(f"Completed query for pipeline {pipeline_id}")

            elif feedback_type == 'error':
                logger.error(
                    f"Received error feedback for pipeline {pipeline_id}: {feedback.get('error')}"
                )

            # Record feedback metrics
            await self.process_monitor.record_metric(
                'orchestrator_feedback',
                1,
                feedback_type=feedback_type,
                pipeline_id=pipeline_id
            )

        except Exception as e:
            logger.error(f"Error handling orchestrator feedback: {str(e)}")

    async def get_process_status(
            self,
            request_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current status of a process"""
        try:
            context = self.active_processes.get(request_id)
            if not context:
                return None

            return {
                'request_id': request_id,
                'pipeline_id': context.pipeline_id,
                'status': context.status.value,
                'stage': context.stage.value if context.stage else None,
                'created_at': context.created_at.isoformat(),
                'error': context.error,
                'processing_history': context.processing_history
            }

        except Exception as e:
            logger.error(f"Status retrieval error: {str(e)}")
            return None

    async def list_active_processes(self) -> List[Dict[str, Any]]:
        """List all active processes"""
        try:
            return [
                await self.get_process_status(request_id)
                for request_id in self.active_processes
            ]

        except Exception as e:
            logger.error(f"Process listing error: {str(e)}")
            return []

    async def cancel_process(
            self,
            request_id: str
    ) -> Dict[str, Any]:
        """Cancel an active process"""
        try:
            context = self.active_processes.get(request_id)
            if not context:
                return {
                    'status': 'error',
                    'message': f'Process {request_id} not found'
                }

            await self._handle_cancellation(context)

            return {
                'status': 'success',
                'message': f'Process {request_id} cancelled'
            }

        except Exception as e:
            logger.error(f"Process cancellation error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }