# backend/core/managers/analytics_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import asyncio

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    MessageMetadata,
    AnalyticsContext,
    AnalyticsState,
    ModuleIdentifier,
    ComponentType,
    ManagerState
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class AnalyticsManager(BaseManager):
    """
    Analytics Manager responsible for coordinating analytics workflow.
    Maintains process state and coordinates between components via message broker.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker=message_broker)

        self.module_identifier = ModuleIdentifier(
            component_name="analytics_manager",
            component_type=ComponentType.ANALYTICS_MANAGER,
            department="analytics",
            role="manager"
        )

        # State tracking
        self.active_processes: Dict[str, AnalyticsContext] = {}
        self.process_timeouts: Dict[str, datetime] = {}
        self.state = ManagerState.INITIALIZING

        # Initialize manager
        self._initialize_manager()

    def _initialize_manager(self) -> None:
        """Initialize manager components"""
        self._setup_message_handlers()
        self._start_background_tasks()
        self.state = ManagerState.ACTIVE

    def _setup_message_handlers(self) -> None:
        """Setup all message handlers"""
        handlers = {
            # Process Lifecycle
            MessageType.ANALYTICS_PROCESS_REQUEST: self._handle_process_request,
            MessageType.ANALYTICS_PROCESS_COMPLETE: self._handle_process_complete,
            MessageType.ANALYTICS_PROCESS_ERROR: self._handle_process_error,

            # Stage Management
            MessageType.ANALYTICS_STAGE_COMPLETE: self._handle_stage_complete,
            MessageType.ANALYTICS_STAGE_FAILED: self._handle_stage_failed,
            MessageType.ANALYTICS_STAGE_START: self._handle_stage_start,

            # Status Updates
            MessageType.ANALYTICS_STATUS_UPDATE: self._handle_status_update,
            MessageType.ANALYTICS_STATUS_REQUEST: self._handle_status_request,

            # Control Messages
            MessageType.ANALYTICS_PAUSE_REQUEST: self._handle_pause_request,
            MessageType.ANALYTICS_RESUME_REQUEST: self._handle_resume_request,
            MessageType.ANALYTICS_CANCEL_REQUEST: self._handle_cancel_request,

            # Resource Management
            MessageType.ANALYTICS_RESOURCE_REQUEST: self._handle_resource_request,
            MessageType.ANALYTICS_RESOURCE_RELEASE: self._handle_resource_release,

            # Model Management
            MessageType.ANALYTICS_MODEL_VERSION_CONTROL: self._handle_version_control,
            MessageType.ANALYTICS_MODEL_REGISTRY_UPDATE: self._handle_registry_update,
            MessageType.ANALYTICS_MODEL_LINEAGE_TRACK: self._handle_lineage_tracking,

            # System Messages
            MessageType.ANALYTICS_CONFIG_UPDATE: self._handle_config_update,
            MessageType.ANALYTICS_HEALTH_CHECK: self._handle_health_check,

            # Service Response Messages
            MessageType.ANALYTICS_SERVICE_COMPLETE: self._handle_service_complete,
            MessageType.ANALYTICS_SERVICE_ERROR: self._handle_service_error,
            MessageType.ANALYTICS_SERVICE_STATUS: self._handle_service_status,

            # Status and Control Response Messages
            MessageType.ANALYTICS_PROCESS_STATUS: self._handle_process_status,
            MessageType.ANALYTICS_STAGE_STATUS: self._handle_stage_status,
            MessageType.ANALYTICS_RESOURCE_STATUS: self._handle_resource_status,

            # Control Point Messages
            MessageType.CONTROL_POINT_DECISION: self._handle_control_point_decision,
            MessageType.CONTROL_POINT_UPDATE: self._handle_control_point_update,

            # Resource Messages
            MessageType.RESOURCE_ALLOCATED: self._handle_resource_allocated,
            MessageType.RESOURCE_RELEASED: self._handle_resource_released
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_service_complete(self, message: ProcessingMessage) -> None:
        """Handle completion message from service"""
        pipeline_id = message.content["pipeline_id"]
        results = message.content.get("results", {})

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        # Update context with results
        context.status = ProcessingStatus.COMPLETED
        context.results = results
        context.completed_at = datetime.now()

        # Notify CPM of completion
        await self._notify_completion(pipeline_id, results)

    async def _handle_service_error(self, message: ProcessingMessage) -> None:
        """Handle error message from service"""
        pipeline_id = message.content["pipeline_id"]
        error = message.content.get("error")

        # Handle error and notify CPM
        await self._handle_process_error(pipeline_id, error)

    async def _handle_service_status(self, message: ProcessingMessage) -> None:
        """Handle status update from service"""
        pipeline_id = message.content["pipeline_id"]
        status = message.content.get("status")
        progress = message.content.get("progress")

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        # Update tracking
        context.status = status
        context.progress = progress
        context.updated_at = datetime.now()

        # Forward status to CPM
        await self._notify_status_update(pipeline_id, status, progress)

    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_process_timeouts())
        asyncio.create_task(self._monitor_resource_usage())
        asyncio.create_task(self._monitor_system_health())

    async def _handle_process_request(self, message: ProcessingMessage) -> None:
        """Handle new analytics process request"""
        try:
            pipeline_id = message.content["pipeline_id"]

            # Create process context
            context = AnalyticsContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                state=AnalyticsState.INITIALIZING,
                status=ProcessingStatus.PENDING,
                created_at=datetime.now(),
                model_config=message.content.get("model_config", {}),
                data_config=message.content.get("data_config", {})
            )

            self.active_processes[pipeline_id] = context
            self.process_timeouts[pipeline_id] = datetime.now()

            # Forward to service layer
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_SERVICE_START,
                    content={
                        "pipeline_id": pipeline_id,
                        "context": context.to_dict(),
                        "config": message.content.get("config", {})
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="analytics_service",
                        domain_type="analytics",
                        processing_stage=ProcessingStage.ADVANCED_ANALYTICS
                    ),
                    source_identifier=self.module_identifier
                )
            )

            await self._update_process_status(
                pipeline_id,
                AnalyticsState.INITIALIZING,
                "Analytics process initiated"
            )

        except Exception as e:
            logger.error(f"Failed to handle process request: {str(e)}")
            await self._handle_process_error(pipeline_id, str(e))

    async def _handle_stage_complete(self, message: ProcessingMessage) -> None:
        """Handle stage completion"""
        pipeline_id = message.content["pipeline_id"]
        stage = message.content["stage"]
        results = message.content.get("results", {})

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        # Update context
        context.update_state(AnalyticsState[stage])
        context.stage_results[stage] = results
        context.updated_at = datetime.now()

        # Determine next stage
        next_stage = self._determine_next_stage(context)
        if next_stage:
            await self._initiate_stage(pipeline_id, next_stage)
        else:
            await self._complete_process(pipeline_id)

    async def _handle_stage_failed(self, message: ProcessingMessage) -> None:
        """Handle stage failure"""
        pipeline_id = message.content["pipeline_id"]
        error = message.content.get("error", "Unknown error")

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        # Attempt recovery if possible
        if await self._attempt_stage_recovery(pipeline_id, error):
            return

        # If recovery not possible, fail the process
        await self._handle_process_error(pipeline_id, error)

    async def _attempt_stage_recovery(self, pipeline_id: str, error: str) -> bool:
        """Attempt to recover failed stage"""
        context = self.active_processes.get(pipeline_id)
        if not context or context.retry_count >= 3:
            return False

        context.retry_count += 1
        recovery_strategy = self._determine_recovery_strategy(context, error)

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.ANALYTICS_STAGE_RETRY,
                content={
                    "pipeline_id": pipeline_id,
                    "stage": context.state.value,
                    "retry_count": context.retry_count,
                    "recovery_strategy": recovery_strategy
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="analytics_service"
                ),
                source_identifier=self.module_identifier
            )
        )
        return True

    def _determine_recovery_strategy(
            self,
            context: AnalyticsContext,
            error: str
    ) -> Dict[str, Any]:
        """Determine appropriate recovery strategy"""
        strategies = {
            AnalyticsState.DATA_PREPARATION: {
                "action": "retry",
                "batch_size": "reduced"
            },
            AnalyticsState.MODEL_TRAINING: {
                "action": "simplify",
                "complexity": "reduced"
            },
            AnalyticsState.MODEL_EVALUATION: {
                "action": "redistribute",
                "resources": "scaled"
            }
        }
        return strategies.get(
            context.state,
            {"action": "retry", "backoff": "exponential"}
        )

    async def _update_process_status(
            self,
            pipeline_id: str,
            state: AnalyticsState,
            message: str
    ) -> None:
        """Update process status and notify"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.state = state
        context.updated_at = datetime.now()

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.ANALYTICS_STATUS_UPDATE,
                content={
                    "pipeline_id": pipeline_id,
                    "state": state.value,
                    "message": message,
                    "timestamp": context.updated_at.isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _complete_process(self, pipeline_id: str) -> None:
        """Handle process completion"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.status = ProcessingStatus.COMPLETED
        context.completed_at = datetime.now()

        # Notify completion
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.ANALYTICS_PROCESS_COMPLETE,
                content={
                    "pipeline_id": pipeline_id,
                    "results": context.stage_results,
                    "metrics": context.performance_metrics,
                    "completion_time": context.completed_at.isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

        # Cleanup
        await self._cleanup_process(pipeline_id)

    async def _cleanup_process(self, pipeline_id: str) -> None:
        """Clean up process resources"""
        if pipeline_id in self.active_processes:
            del self.active_processes[pipeline_id]
        if pipeline_id in self.process_timeouts:
            del self.process_timeouts[pipeline_id]

    async def _monitor_process_timeouts(self) -> None:
        """Monitor processes for timeouts"""
        while self.state == ManagerState.ACTIVE:
            try:
                current_time = datetime.now()
                for pipeline_id, start_time in self.process_timeouts.items():
                    if (current_time - start_time).total_seconds() > 3600:  # 1 hour timeout
                        await self._handle_process_timeout(pipeline_id)
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Process monitoring error: {str(e)}")

    async def _handle_process_timeout(self, pipeline_id: str) -> None:
        """Handle process timeout"""
        await self._handle_process_error(
            pipeline_id,
            "Process exceeded maximum execution time"
        )

    async def _notify_completion(self, pipeline_id: str, results: Dict[str, Any]) -> None:
            """
            Notify Control Point Manager about process completion

            Args:
                pipeline_id (str): Unique identifier for the processing pipeline
                results (Dict[str, Any]): Processed results
            """
            try:
                context = self.active_processes.get(pipeline_id)
                if not context:
                    logger.warning(f"No context found for pipeline {pipeline_id}")
                    return

                message = ProcessingMessage(
                    message_type=MessageType.ANALYTICS_PROCESS_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'results': results,
                        'timestamp': datetime.now().isoformat(),
                        'performance_metrics': context.performance_metrics
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=ModuleIdentifier(
                        component_name="control_point_manager",
                        component_type=ComponentType.ORCHESTRATOR,
                        department="control",
                        role="manager"
                    ),
                    metadata=MessageMetadata(
                        source_component="analytics_manager",
                        target_component="control_point_manager",
                        domain_type="analytics",
                        processing_stage=ProcessingStage.ADVANCED_ANALYTICS,
                        correlation_id=pipeline_id
                    )
                )
                await self.message_broker.publish(message)
                logger.info(f"Completion notification sent for pipeline {pipeline_id}")
            except Exception as e:
                logger.error(f"Failed to notify completion: {str(e)}")

    async def _handle_process_error(self, pipeline_id: str, error: str) -> None:
            """
            Handle and propagate process errors

            Args:
                pipeline_id (str): Unique identifier for the processing pipeline
                error (str): Error description
            """
            try:
                context = self.active_processes.get(pipeline_id)
                if not context:
                    logger.warning(f"No context found for pipeline {pipeline_id}")
                    return

                # Update context
                context.status = ProcessingStatus.FAILED
                context.error = error
                context.completed_at = datetime.now()

                # Publish error message
                message = ProcessingMessage(
                    message_type=MessageType.FLOW_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'component': 'analytics_manager',
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=ModuleIdentifier(
                        component_name="control_point_manager",
                        component_type=ComponentType.ORCHESTRATOR,
                        department="control",
                        role="manager"
                    ),
                    metadata=MessageMetadata(
                        source_component="analytics_manager",
                        target_component="control_point_manager",
                        domain_type="error",
                        processing_stage=ProcessingStage.ERROR_HANDLING,
                        correlation_id=pipeline_id
                    )
                )
                await self.message_broker.publish(message)

                # Attempt recovery or cleanup
                await self._cleanup_process(pipeline_id)
                logger.error(f"Process error handled for pipeline {pipeline_id}: {error}")
            except Exception as e:
                logger.critical(f"Error handling process error: {str(e)}")

    async def _notify_status_update(
            self,
            pipeline_id: str,
            status: ProcessingStatus,
            progress: Optional[float] = None
    ) -> None:
            """
            Forward status updates to Control Point Manager

            Args:
                pipeline_id (str): Unique identifier for the processing pipeline
                status (ProcessingStatus): Current processing status
                progress (Optional[float]): Processing progress percentage
            """
            try:
                context = self.active_processes.get(pipeline_id)
                if not context:
                    logger.warning(f"No context found for pipeline {pipeline_id}")
                    return

                message = ProcessingMessage(
                    message_type=MessageType.PROCESSING_STATUS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': status.value,
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=ModuleIdentifier(
                        component_name="control_point_manager",
                        component_type=ComponentType.ORCHESTRATOR,
                        department="control",
                        role="manager"
                    ),
                    metadata=MessageMetadata(
                        source_component="analytics_manager",
                        target_component="control_point_manager",
                        domain_type="analytics",
                        processing_stage=ProcessingStage.ADVANCED_ANALYTICS,
                        correlation_id=pipeline_id
                    )
                )
                await self.message_broker.publish(message)
                logger.info(f"Status update sent for pipeline {pipeline_id}: {status}")
            except Exception as e:
                logger.error(f"Failed to send status update: {str(e)}")

    async def _monitor_resource_usage(self) -> None:
            """
            Monitor system resource utilization
            Periodically checks and reports resource consumption
            """
            while self.state == ManagerState.ACTIVE:
                try:
                    # Example resource tracking (you'd replace with actual resource monitoring)
                    import psutil

                    # CPU and Memory usage
                    cpu_usage = psutil.cpu_percent()
                    memory_usage = psutil.virtual_memory().percent

                    # If resources are critically high, publish a warning
                    if cpu_usage > 90 or memory_usage > 90:
                        await self.message_broker.publish(
                            ProcessingMessage(
                                message_type=MessageType.SYSTEM_RESOURCE_ALERT,
                                content={
                                    'cpu_usage': cpu_usage,
                                    'memory_usage': memory_usage,
                                    'timestamp': datetime.now().isoformat()
                                },
                                source_identifier=self.module_identifier
                            )
                        )
                        logger.warning(f"High resource usage detected. CPU: {cpu_usage}%, Memory: {memory_usage}%")

                    # Wait before next check
                    await asyncio.sleep(300)  # Check every 5 minutes
                except Exception as e:
                    logger.error(f"Resource monitoring error: {str(e)}")
                    await asyncio.sleep(60)  # Wait a minute before retrying

    async def _monitor_system_health(self) -> None:
            """
            Perform periodic system health checks
            Validates critical system components and services
            """
            while self.state == ManagerState.ACTIVE:
                try:
                    # Perform health checks on critical components
                    health_checks = {
                        'message_broker': await self._check_message_broker_health(),
                        'database_connection': await self._check_database_connection(),
                        'active_processes': len(self.active_processes)
                    }

                    # Publish health status
                    await self.message_broker.publish(
                        ProcessingMessage(
                            message_type=MessageType.SYSTEM_HEALTH_STATUS,
                            content={
                                'health_checks': health_checks,
                                'timestamp': datetime.now().isoformat()
                            },
                            source_identifier=self.module_identifier
                        )
                    )

                    # Log any potential issues
                    for component, status in health_checks.items():
                        if not status:
                            logger.warning(f"Health check failed for {component}")

                    # Wait before next health check
                    await asyncio.sleep(600)  # Check every 10 minutes
                except Exception as e:
                    logger.error(f"System health monitoring error: {str(e)}")
                    await asyncio.sleep(120)  # Wait two minutes before retrying

    async def _check_message_broker_health(self) -> bool:
            """Check message broker connectivity"""
            try:
                # Implement a ping or connectivity check
                return await self.message_broker.health_check()
            except Exception:
                return False

    async def _check_database_connection(self) -> bool:
            """Check database connection"""
            try:
                # Implement database connection check
                # This would depend on your specific database setup
                return True  # Placeholder
            except Exception:
                return False

    def _determine_next_stage(self, context: AnalyticsContext) -> Optional[AnalyticsState]:
            """
            Determine the next processing stage based on current context

            Args:
                context (AnalyticsContext): Current processing context

            Returns:
                Optional[AnalyticsState]: Next stage or None if process is complete
            """
            stage_sequence = [
                AnalyticsState.DATA_PREPARATION,
                AnalyticsState.FEATURE_ENGINEERING,
                AnalyticsState.MODEL_TRAINING,
                AnalyticsState.MODEL_EVALUATION,
                AnalyticsState.RESULT_VALIDATION
            ]

            try:
                current_index = stage_sequence.index(context.state)
                next_index = current_index + 1

                return stage_sequence[next_index] if next_index < len(stage_sequence) else None
            except ValueError:
                logger.warning(f"Invalid current stage: {context.state}")
                return None

    async def _initiate_stage(self, pipeline_id: str, stage: AnalyticsState) -> None:
            """
            Initiate the next processing stage

            Args:
                pipeline_id (str): Unique identifier for the processing pipeline
                stage (AnalyticsState): Next stage to initiate
            """
            try:
                context = self.active_processes.get(pipeline_id)
                if not context:
                    logger.warning(f"No context found for pipeline {pipeline_id}")
                    return

                message = ProcessingMessage(
                    message_type=MessageType.ANALYTICS_STAGE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': stage.value,
                        'config': context.model_config,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=ModuleIdentifier(
                        component_name="analytics_service",
                        component_type=ComponentType.ANALYTICS_SERVICE,
                        department="analytics",
                        role="service"
                    ),
                    metadata=MessageMetadata(
                        source_component="analytics_manager",
                        target_component="analytics_service",
                        domain_type="analytics",
                        processing_stage=stage,
                        correlation_id=pipeline_id
                    )
                )
                await self.message_broker.publish(message)
                logger.info(f"Initiated stage {stage} for pipeline {pipeline_id}")
            except Exception as e:
                logger.error(f"Failed to initiate stage {stage}: {str(e)}")
                await self._handle_process_error(pipeline_id, f"Stage initiation error: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        self.state = ManagerState.SHUTDOWN

        # Clean up all active processes
        for pipeline_id in list(self.active_processes.keys()):
            await self._cleanup_process(pipeline_id)

        # Unsubscribe from all messages
        await self.message_broker.unsubscribe_all(self.module_identifier)
