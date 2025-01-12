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

from .s3_manager import S3Manager
from .s3_config import Config

logger = logging.getLogger(__name__)


@dataclass
class S3ProcessContext:
    """Context for S3 operations"""
    request_id: str
    pipeline_id: str
    stage: ProcessingStage
    status: ProcessingStatus
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    error: Optional[str] = None
    processing_history: List[Dict[str, Any]] = field(default_factory=list)
    control_points: List[str] = field(default_factory=list)


class S3Service:
    """Enhanced S3 service with comprehensive integration"""

    def __init__(
            self,
            message_broker: Optional[MessageBroker] = None,
            control_point_manager: Optional[ControlPointManager] = None,
            config: Optional[Config] = None,
            data_conductor: Optional[DataConductor] = None,
            staging_manager: Optional[StagingManager] = None,
            pipeline_manager: Optional[PipelineManager] = None,
            pipeline_repository: Optional[PipelineRepository] = None,
            s3_manager: Optional[S3Manager] = None
    ):
        """Initialize S3Service with required components"""
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

        # Initialize S3 Manager
        self.s3_manager = s3_manager or S3Manager(
            message_broker=self.message_broker,
            control_point_manager=self.control_point_manager,
            config=self.config
        )

        # Initialize monitoring and processing
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="s3_service",
            source_id=str(uuid4())
        )

        self.process_handler = ProcessHandler(config=self.config.PERFORMANCE)

        # Operation tracking
        self.active_processes: Dict[str, S3ProcessContext] = {}

        # Initialize handlers
        self._setup_message_handlers()

        logger.info("S3Service initialized")

    def _setup_message_handlers(self):
        """Set up message handlers"""
        handlers = {
            's3.connection.requested': self._handle_connection_event,
            's3.object.processing.start': self._handle_object_processing,
            's3.object.processing.complete': self._handle_processing_complete,
            's3.control.decision': self._handle_control_decision,
            's3.error': self._handle_error
        }

        for pattern, handler in handlers.items():
            self.message_broker.subscribe(
                component=ModuleIdentifier(
                    component_name='s3_service',
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
        """Handle S3 connection request with control points"""
        try:
            # Create process context
            context = S3ProcessContext(
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
            context: S3ProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process connection through stages with control points"""
        stages = [
            (ProcessingStage.INITIAL_VALIDATION, self._validate_connection),
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

    async def _validate_connection(
            self,
            context: S3ProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate connection request"""
        return await self.s3_manager.validate_connection(request_data)

    async def _check_connection(
            self,
            context: S3ProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check S3 connection"""
        return await self.s3_manager.check_connection(request_data)

    async def _verify_access(
            self,
            context: S3ProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Verify S3 access permissions"""
        return await self.s3_manager.verify_access(request_data)

    async def _setup_connection(
            self,
            context: S3ProcessContext,
            request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Set up S3 connection"""
        connection_id = str(uuid4())

        # Store connection in staging
        staging_id = await self.staging_manager.store_data(
            pipeline_id=context.pipeline_id,
            data=request_data.get('connection_data', {}),
            metadata={
                'connection_id': connection_id,
                'source_type': 's3',
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
            initial_nodes=['s3_connection']
        )

        return {
            'connection_id': connection_id,
            'staging_id': staging_id,
            'route_execution_id': route_execution_id
        }

    async def _create_control_point(
            self,
            context: S3ProcessContext,
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
                timeout=self.config.PERFORMANCE.CONNECTION_TIMEOUT
            )

        except Exception as e:
            logger.error(f"Control point creation error: {str(e)}", exc_info=True)
            raise

    async def _update_status(
            self,
            context: S3ProcessContext,
            message: str
    ) -> None:
        """Update processing status"""
        try:
            status_message = ProcessingMessage(
                source_identifier=ModuleIdentifier(
                    component_name='s3_service',
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
            logger.error(f"Status update error: {str(e)}", exc_info=True)

    async def process_object_request(
            self,
            connection_id: str,
            object_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process S3 object operation with control points"""
        try:
            # Create process context
            context = S3ProcessContext(
                request_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING,
                metadata={
                    'connection_id': connection_id,
                    'object_key': object_data.get('key'),
                    'operation_type': object_data.get('operation', 'get')
                }
            )

            self.active_processes[context.request_id] = context

            try:
                result = await self._process_object_stages(
                    context,
                    object_data
                )

                # Record metrics
                await self.process_monitor.record_operation_metric(
                    'object_operation',
                    success=True,
                    duration=(datetime.now() - context.created_at).total_seconds(),
                    operation=object_data.get('operation'),
                    object_size=result.get('size', 0)
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
            logger.error(f"Object operation error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_object_stages(
            self,
            context: S3ProcessContext,
            object_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process object through stages with control points"""
        stages = [
            (ProcessingStage.INITIAL_VALIDATION, self._validate_object_request),
            (ProcessingStage.ACCESS_CHECK, self._check_object_access),
            (ProcessingStage.DATA_EXTRACTION, self._fetch_object),
            (ProcessingStage.DATA_VALIDATION, self._validate_object_data),
            (ProcessingStage.PROCESSING, self._process_object_data)
        ]

        stage_results = {}

        for stage, processor in stages:
            context.stage = stage
            await self._update_status(context, f"Starting {stage.value}")

            # Process stage
            result = await processor(context, object_data)

            # Create control point
            decision = await self._create_control_point(
                context=context,
                stage=stage,
                data=result,
                options=['proceed', 'modify', 'reject']
            )

            if decision['decision'] == 'reject':
                await self._handle_rejection(context, decision.get('details', {}))
                raise ValueError(f"Processing rejected at stage {stage.value}")

            elif decision['decision'] == 'modify':
                object_data = await self._apply_modifications(
                    object_data,
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

    async def _validate_object_request(
            self,
            context: S3ProcessContext,
            object_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate object request"""
        return await self.s3_manager.validate_object_request(object_data)

    async def _check_object_access(
            self,
            context: S3ProcessContext,
            object_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check object accessibility"""
        return await self.s3_manager.verify_object_access(
            object_data.get('bucket'),
            object_data.get('key')
        )

    async def _fetch_object(
            self,
            context: S3ProcessContext,
            object_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch object from S3"""
        return await self.s3_manager.fetch_object(object_data)

    async def _validate_object_data(
            self,
            context: S3ProcessContext,
            object_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate fetched object data"""
        return await self.s3_manager.validate_object_data(
            object_data.get('data'),
            context.metadata
        )

    async def _process_object_data(
            self,
            context: S3ProcessContext,
            object_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process object data"""
        processed_data = await self.s3_manager.process_object_data(object_data)

        # Store in staging
        staging_id = await self.staging_manager.store_data(
            pipeline_id=context.pipeline_id,
            data=processed_data.get('data'),
            metadata={
                'source_type': 's3',
                'object_key': object_data.get('key'),
                'processing_stats': processed_data.get('stats')
            }
        )

        return {
            'processed_data': processed_data,
            'staging_id': staging_id
        }

    async def list_objects(
            self,
            connection_id: str,
            prefix: str = '',
            max_items: Optional[int] = None
    ) -> Dict[str, Any]:
        """List S3 objects with control points"""
        try:
            # Create process context
            context = S3ProcessContext(
                request_id=str(uuid4()),
                pipeline_id=str(uuid4()),
                stage=ProcessingStage.INITIAL_VALIDATION,
                status=ProcessingStatus.PENDING,
                metadata={
                    'connection_id': connection_id,
                    'prefix': prefix,
                    'max_items': max_items
                }
            )

            self.active_processes[context.request_id] = context

            try:
                result = await self._process_list_stages(context)
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
            logger.error(f"Object listing error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_list_stages(
            self,
            context: S3ProcessContext
    ) -> Dict[str, Any]:
        """Process list operation through stages"""
        stages = [
            (ProcessingStage.INITIAL_VALIDATION, self._validate_list_request),
            (ProcessingStage.ACCESS_CHECK, self._check_list_access),
            (ProcessingStage.DATA_EXTRACTION, self._list_objects),
            (ProcessingStage.PROCESSING, self._process_object_list)
        ]

        stage_results = {}

        for stage, processor in stages:
            context.stage = stage
            await self._update_status(context, f"Starting {stage.value}")

            result = await processor(context)
            stage_results[stage.value] = result

            # Update processing history
            context.processing_history.append({
                'stage': stage.value,
                'timestamp': datetime.now().isoformat(),
                'status': 'completed',
                'details': {
                    k: v for k, v in result.items()
                    if k not in ['objects']  # Exclude large lists from history
                }
            })

        return stage_results

    async def _handle_cancellation(self, context: S3ProcessContext) -> None:
        """Handle operation cancellation"""
        try:
            context.status = ProcessingStatus.CANCELLED
            await self._update_status(context, "Operation cancelled")
            await self._cleanup_process(context.request_id)
        except Exception as e:
            logger.error(f"Cancellation handling error: {str(e)}", exc_info=True)

    async def _handle_error(
            self,
            context: S3ProcessContext,
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
            logger.error(f"Error handling error: {str(e)}", exc_info=True)

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
            await self.s3_manager.cleanup()

        except Exception as e:
            logger.error(f"Service cleanup error: {str(e)}", exc_info=True)