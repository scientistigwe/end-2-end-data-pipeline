import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
from enum import Enum
from pathlib import Path
import json
from dataclasses import dataclass, field

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    PipelineContext,
    PipelineState,
    MessageMetadata,
    ManagerState
)
from .base.base_manager import BaseManager
from ..config.settings import Settings
from ..utils.metrics import MetricsCollector

logger = logging.getLogger(__name__)


class PipelineState(str, Enum):
    """Pipeline state enumeration"""
    INITIALIZED = "initialized"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RECOVERING = "recovering"

@dataclass
class PipelineStage:
    """Pipeline stage information"""
    name: str
    status: ProcessingStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class PipelineContext:
    """Pipeline execution context"""
    pipeline_id: str
    state: PipelineState
    stages: Dict[str, PipelineStage] = field(default_factory=dict)
    current_stage: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)


class PipelineManager(BaseManager):
    """Pipeline Manager coordinates pipeline workflow through message-based communication.
    Responsible for orchestrating the pipeline process while maintaining workflow state."""

    def __init__(
        self,
        message_broker: MessageBroker,
        settings: Settings,
        metrics_collector: MetricsCollector,
        component_name: str = "pipeline_manager",
        domain_type: str = "pipeline"
    ):
        # Call base class initialization first
        super().__init__(
            message_broker=message_broker,
            component_name=component_name,
            domain_type=domain_type
        )
        
        self.settings = settings
        self.metrics_collector = metrics_collector
        
        # Resource limits
        self.max_concurrent_pipelines = settings.get("pipeline.max_concurrent_pipelines", 10)
        self.max_retries_per_stage = settings.get("pipeline.max_retries_per_stage", 3)
        self.stage_timeout = settings.get("pipeline.stage_timeout", 3600)  # 1 hour
        
        # Initialize message handlers
        self._setup_message_handlers()
        
        # Start monitoring tasks
        self._start_monitoring_tasks()

    async def _initialize_manager(self) -> None:
        """Initialize pipeline manager components"""
        try:
            # Initialize base components - this will also start background tasks
            await super()._initialize_manager()

            # Setup pipeline-specific message handlers
            await self._setup_domain_handlers()

            # Update state
            self.state = ManagerState.ACTIVE
            logger.info(f"Pipeline manager initialized successfully: {self.context.component_name}")

        except Exception as e:
            logger.error(f"Failed to initialize pipeline manager: {str(e)}")
            self.state = ManagerState.ERROR
            raise

    async def _setup_domain_handlers(self) -> None:
        """Setup pipeline-specific message handlers"""
        handlers = {
            # Core Process Flow
            MessageType.PIPELINE_PROCESS_START: self._handle_process_start,
            MessageType.PIPELINE_PROCESS_PROGRESS: self._handle_process_progress,
            MessageType.PIPELINE_PROCESS_COMPLETE: self._handle_process_complete,
            MessageType.PIPELINE_PROCESS_FAILED: self._handle_process_failed,

            # Stage Management
            MessageType.PIPELINE_STAGE_START: self._handle_stage_start,
            MessageType.PIPELINE_STAGE_PROGRESS: self._handle_stage_progress,
            MessageType.PIPELINE_STAGE_COMPLETE: self._handle_stage_complete,
            MessageType.PIPELINE_STAGE_FAILED: self._handle_stage_failed,
            MessageType.PIPELINE_STAGE_ROLLBACK: self._handle_stage_rollback,

            # Data Flow Management
            MessageType.PIPELINE_DATA_VALIDATE: self._handle_data_validate,
            MessageType.PIPELINE_DATA_TRANSFORM: self._handle_data_transform,
            MessageType.PIPELINE_DATA_LOAD: self._handle_data_load,
            MessageType.PIPELINE_DATA_ERROR: self._handle_data_error,

            # Performance & Resource Management
            MessageType.PIPELINE_PERFORMANCE_CHECK: self._handle_performance_check,
            MessageType.PIPELINE_RESOURCE_REQUEST: self._handle_resource_request,
            MessageType.PIPELINE_RESOURCE_RELEASE: self._handle_resource_release,
            MessageType.PIPELINE_RESOURCE_ERROR: self._handle_resource_error,

            # Error & Recovery
            MessageType.PIPELINE_ERROR_DETECTED: self._handle_error_detected,
            MessageType.PIPELINE_ERROR_RESOLVED: self._handle_error_resolved,
            MessageType.PIPELINE_RECOVERY_START: self._handle_recovery_start,
            MessageType.PIPELINE_RECOVERY_COMPLETE: self._handle_recovery_complete,

            # Monitoring & Status
            MessageType.PIPELINE_STATUS_CHECK: self._handle_status_check,
            MessageType.PIPELINE_STATUS_UPDATE: self._handle_status_update,
            MessageType.PIPELINE_METRICS_UPDATE: self._handle_metrics_update,

            # Configuration & Maintenance
            MessageType.PIPELINE_CONFIG_UPDATE: self._handle_config_update,
            MessageType.PIPELINE_MAINTENANCE_START: self._handle_maintenance_start,
            MessageType.PIPELINE_MAINTENANCE_COMPLETE: self._handle_maintenance_complete
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle pipeline process start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})

            # Validate configuration
            if not self._validate_pipeline_config(config):
                raise ValueError("Invalid pipeline configuration")

            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Initialize pipeline stages
            await self._initialize_pipeline_stages(pipeline_id, config)

            # Start first stage
            await self._start_next_stage(pipeline_id)

        except Exception as e:
            logger.error(f"Process start failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_process_progress(self, message: ProcessingMessage) -> None:
        """Handle pipeline progress updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            progress = message.content.get('progress', 0)
            stage = message.content.get('stage')

            # Update progress for specific stage
            if stage:
                context.stage_progress[stage] = progress

            # Calculate overall progress
            total_progress = sum(context.stage_progress.values()) / len(context.stage_progress)

            # Update context
            context.current_progress = total_progress
            context.updated_at = datetime.now()

            # Notify progress
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_PROCESS_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'total_progress': total_progress,
                        'stage_progress': context.stage_progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="control_point_manager",
                        domain_type="pipeline"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Progress update failed: {str(e)}")

    async def _handle_process_complete(self, message: ProcessingMessage) -> None:
        """Handle pipeline process completion"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = PipelineState.COMPLETED
            context.completed_at = datetime.now()

            # Generate completion report
            completion_report = self._generate_completion_report(context)

            # Notify completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_PROCESS_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'completion_report': completion_report,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="control_point_manager",
                        domain_type="pipeline"
                    )
                )
            )

            # Cleanup resources
            await self._cleanup_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Process completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_process_failed(self, message: ProcessingMessage) -> None:
        """Handle pipeline process failure"""
        pipeline_id = message.content.get('pipeline_id')
        error = message.content.get('error', 'Unknown error')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = PipelineState.FAILED
            context.error = error
            context.failure_timestamp = datetime.now()

            # Generate failure report
            failure_report = self._generate_failure_report(context)

            # Notify failure
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'failure_report': failure_report,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="control_point_manager",
                        domain_type="pipeline"
                    )
                )
            )

            # Attempt recovery if possible
            if self._can_recover(context):
                await self._handle_recovery_start(message)
            else:
                await self._cleanup_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Process failure handling failed: {str(e)}")

    async def _handle_stage_start(self, message: ProcessingMessage) -> None:
        """Handle pipeline stage start"""
        pipeline_id = message.content.get('pipeline_id')
        stage = message.content.get('stage')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Validate stage transition
            if not self._validate_stage_transition(context, stage):
                raise ValueError(f"Invalid stage transition to {stage}")

            # Update context
            context.current_stage = stage
            context.stage_start_time = datetime.now()
            context.stage_progress = {stage: 0}

            # Initialize stage resources
            await self._initialize_stage_resources(pipeline_id, stage)

            # Notify stage start
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STAGE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': stage,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="control_point_manager",
                        domain_type="pipeline"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Stage start failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_stage_progress(self, message: ProcessingMessage) -> None:
        """Handle pipeline stage progress"""
        pipeline_id = message.content.get('pipeline_id')
        stage = message.content.get('stage')
        progress = message.content.get('progress', 0)
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update stage progress
            context.stage_progress[stage] = progress
            context.updated_at = datetime.now()

            # Check for stage timeout
            if self._check_stage_timeout(context):
                await self._handle_stage_timeout(pipeline_id, stage)
                return

            # Notify progress
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STAGE_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': stage,
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="control_point_manager",
                        domain_type="pipeline"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Stage progress update failed: {str(e)}")

    async def _handle_stage_complete(self, message: ProcessingMessage) -> None:
        """Handle pipeline stage completion"""
        pipeline_id = message.content.get('pipeline_id')
        stage = message.content.get('stage')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Validate stage completion
            stage_results = message.content.get('results', {})
            if not self._validate_stage_results(stage_results):
                raise ValueError(f"Invalid results for stage {stage}")

            # Update context
            context.stage_results[stage] = stage_results
            context.completed_stages.append(stage)
            context.stage_completion_time = datetime.now()

            # Check if all stages are complete
            if self._all_stages_complete(context):
                await self._handle_process_complete(message)
            else:
                # Start next stage
                await self._start_next_stage(pipeline_id)

        except Exception as e:
            logger.error(f"Stage completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_stage_failed(self, message: ProcessingMessage) -> None:
        """Handle pipeline stage failure"""
        pipeline_id = message.content.get('pipeline_id')
        stage = message.content.get('stage')
        error = message.content.get('error', 'Unknown error')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context
            context.stage_errors[stage] = error
            context.failed_stages.append(stage)

            # Check if stage can be retried
            if self._can_retry_stage(context, stage):
                await self._retry_stage(pipeline_id, stage)
            else:
                # Attempt stage rollback
                await self._handle_stage_rollback(message)

        except Exception as e:
            logger.error(f"Stage failure handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_data_receive(self, message: ProcessingMessage) -> None:
        """Handle initial data reception"""
        try:
            pipeline_id = message.content['pipeline_id']
            data_source = message.content['source']

            # Create pipeline context
            pipeline_context = PipelineContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECEPTION,
                status=ProcessingStatus.PENDING,
                correlation_id=str(uuid.uuid4())
            )
            self.active_pipelines[pipeline_id] = pipeline_context

            # Use base manager's message broker
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_SERVICE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'data_source': data_source
                    },
                    metadata=MessageMetadata(
                        correlation_id=pipeline_context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle data reception: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_metrics_update(self, message: ProcessingMessage) -> None:
        """Handle monitoring metrics updates"""
        try:
            pipeline_id = message.content['pipeline_id']
            metrics = message.content['metrics']
            pipeline_context = self.active_pipelines.get(pipeline_id)

            if not pipeline_context:
                return

            # Update pipeline metrics and use base manager's metrics tracking
            pipeline_context.update_metrics(metrics)
            self._update_metrics(processing_time=metrics.get('processing_time', 0.0))

            if self._check_critical_metrics(metrics):
                await self._handle_critical_metrics(pipeline_id, metrics)

        except Exception as e:
            self.logger.error(f"Metrics update failed: {str(e)}")
            await self._handle_error(message, e)

    # Override base manager cleanup to handle pipeline resources
    def _check_critical_metrics(self, metrics: Dict[str, Any]) -> bool:
        """Check metrics for critical conditions"""
        thresholds = {
            'cpu_usage': 90,
            'memory_usage': 90,
            'error_rate': 0.1,
            'latency': 5000  # ms
        }

        return any(
            metrics.get(metric, 0) > threshold
            for metric, threshold in thresholds.items()
        )

    async def _setup_message_handlers(self) -> None:
        """Setup comprehensive message handling"""
        handlers = {
            # Control Point Messages
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.CONTROL_POINT_UPDATED: self._handle_control_point_updated,
            MessageType.CONTROL_POINT_DECISION: self._handle_control_point_decision,

            # Initial Data Reception
            MessageType.DATA_RECEIVE_REQUEST: self._handle_data_receive,
            MessageType.DATA_VALIDATE_COMPLETE: self._handle_data_validation,
            MessageType.DATA_VALIDATE_REJECT: self._handle_data_rejection,

            # Quality Flow
            MessageType.QUALITY_CHECK_COMPLETE: self._handle_quality_complete,
            MessageType.QUALITY_ISSUE_DETECTED: self._handle_quality_issue,
            MessageType.QUALITY_VALIDATE_COMPLETE: self._handle_quality_validation,
            MessageType.QUALITY_ERROR: self._handle_component_error,

            # Insight Flow
            MessageType.INSIGHT_GENERATE_COMPLETE: self._handle_insight_complete,
            MessageType.INSIGHT_REVIEW_REQUIRED: self._handle_insight_review,
            MessageType.INSIGHT_VALIDATE_COMPLETE: self._handle_insight_validation,
            MessageType.INSIGHT_ERROR: self._handle_component_error,

            # Analytics Flow
            MessageType.ANALYTICS_PROCESS_COMPLETE: self._handle_analytics_complete,
            MessageType.ANALYTICS_MODEL_EVALUATE_COMPLETE: self._handle_model_evaluation,
            MessageType.ANALYTICS_PERFORMANCE_EVALUATE: self._handle_performance_evaluation,
            MessageType.ANALYTICS_ERROR: self._handle_component_error,

            # Decision Flow
            MessageType.DECISION_PROCESS_COMPLETE: self._handle_decision_complete,
            MessageType.DECISION_OPTIONS_READY: self._handle_decision_options,
            MessageType.DECISION_VALIDATE_COMPLETE: self._handle_decision_validation,
            MessageType.DECISION_IMPACT_ASSESS_COMPLETE: self._handle_impact_assessment,
            MessageType.DECISION_ERROR: self._handle_component_error,

            # Recommendation Flow
            MessageType.RECOMMENDATION_GENERATE_COMPLETE: self._handle_recommendation_complete,
            MessageType.RECOMMENDATION_VALIDATE_COMPLETE: self._handle_recommendation_validation,
            MessageType.RECOMMENDATION_ERROR: self._handle_component_error,

            # Monitoring Flow
            MessageType.MONITORING_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.MONITORING_ALERT_NOTIFY: self._handle_monitoring_alert,
            MessageType.MONITORING_HEALTH_STATUS: self._handle_health_status,
            MessageType.MONITORING_ERROR: self._handle_component_error,

            # Report Flow
            MessageType.REPORT_GENERATE_COMPLETE: self._handle_report_complete,
            MessageType.REPORT_VALIDATE_COMPLETE: self._handle_report_validation,
            MessageType.REPORT_ERROR: self._handle_component_error,

            # Pipeline Control 
            MessageType.PIPELINE_PAUSE_REQUEST: self._handle_pause_request,
            MessageType.PIPELINE_RESUME_REQUEST: self._handle_resume_request,
            MessageType.PIPELINE_CANCEL_REQUEST: self._handle_cancel_request,
            MessageType.PIPELINE_STATUS_REQUEST: self._handle_status_request,

            # Resource Management
            MessageType.RESOURCE_ACCESS_REQUEST: self._handle_resource_request,
            MessageType.RESOURCE_RELEASE_COMPLETE: self._handle_resource_release
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                f"{message_type.value}",
                handler
            )

    async def _handle_monitoring_alert(self, message: ProcessingMessage) -> None:
        """Handle monitoring alerts"""
        pipeline_id = message.content['pipeline_id']
        alert = message.content['alert']
        context = self.active_pipelines.get(pipeline_id)

        if not context:
            return

        # Add alert to context
        context.add_alert(alert)

        # Handle critical alerts
        if alert['severity'] in ['critical', 'high']:
            await self._handle_critical_alert(pipeline_id, alert)

    async def _handle_report_complete(self, message: ProcessingMessage) -> None:
        """Handle report generation completion"""
        pipeline_id = message.content['pipeline_id']
        report = message.content['report']
        context = self.active_pipelines.get(pipeline_id)

        if not context:
            return

        # Update context with report
        context.add_report(report)
        context.complete_stage(ProcessingStage.REPORT_GENERATION)

        # Forward to service
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.REPORT_GENERATION.value,
                    'report': report
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="pipeline_service"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_critical_metrics(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """Handle critical metrics situation"""
        context = self.active_pipelines.get(pipeline_id)
        if not context:
            return

        # Pause pipeline if necessary
        if metrics.get('resource_usage', 0) > 90:  # Example threshold
            await self._pause_pipeline(pipeline_id, "Critical resource usage detected")

        # Notify service about critical situation
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_CRITICAL_SITUATION,
                content={
                    'pipeline_id': pipeline_id,
                    'metrics': metrics,
                    'situation': 'critical_resource_usage'
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="pipeline_service"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_data_validation(self, message: ProcessingMessage) -> None:
        """
        Handle successful data validation

        Args:
            message (ProcessingMessage): Data validation completion message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            validation_results = message.content.get('validation_results', {})
            context = self.active_pipelines.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update pipeline context
            context.update_stage(ProcessingStage.DATA_VALIDATION, ProcessingStatus.COMPLETED)
            context.validation_results = validation_results

            # Proceed to next stage
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STAGE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': ProcessingStage.DATA_VALIDATION.value,
                        'validation_results': validation_results
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Data validation handling failed: {str(e)}")
            await self._handle_error(pipeline_id, f"Data validation error: {str(e)}")

    async def _handle_data_rejection(self, message: ProcessingMessage) -> None:
        """
        Handle data validation rejection

        Args:
            message (ProcessingMessage): Data rejection message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            rejection_reasons = message.content.get('reasons', [])
            context = self.active_pipelines.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update pipeline context
            context.update_stage(ProcessingStage.DATA_VALIDATION, ProcessingStatus.REJECTED)
            context.rejection_reasons = rejection_reasons

            # Publish rejection notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STAGE_REJECTED,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': ProcessingStage.DATA_VALIDATION.value,
                        'reasons': rejection_reasons
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup pipeline
            await self._cleanup_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Data rejection handling failed: {str(e)}")
            await self._handle_error(pipeline_id, f"Data rejection error: {str(e)}")

    async def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """
        Handle quality check completion

        Args:
            message (ProcessingMessage): Quality check completion message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            quality_results = message.content.get('quality_results', {})
            context = self.active_pipelines.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update pipeline context
            context.update_stage(ProcessingStage.QUALITY_CHECK, ProcessingStatus.COMPLETED)
            context.quality_results = quality_results

            # Proceed to next stage
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STAGE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': ProcessingStage.QUALITY_CHECK.value,
                        'quality_results': quality_results
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Quality check handling failed: {str(e)}")
            await self._handle_error(pipeline_id, f"Quality check error: {str(e)}")

    async def _handle_quality_issue(self, message: ProcessingMessage) -> None:
        """
        Handle quality issues detected

        Args:
            message (ProcessingMessage): Quality issue message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            issues = message.content.get('issues', [])
            context = self.active_pipelines.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update pipeline context
            context.update_stage(ProcessingStage.QUALITY_CHECK, ProcessingStatus.REQUIRES_REVIEW)
            context.quality_issues = issues

            # Publish quality issue notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_QUALITY_REVIEW_REQUIRED,
                    content={
                        'pipeline_id': pipeline_id,
                        'issues': issues
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Quality issue handling failed: {str(e)}")
            await self._handle_error(pipeline_id, f"Quality issue error: {str(e)}")

    async def _handle_pause_request(self, message: ProcessingMessage) -> None:
        """
        Handle pipeline pause request

        Args:
            message (ProcessingMessage): Pause request message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            reason = message.content.get('reason', 'Unspecified')
            context = self.active_pipelines.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update pipeline context
            context.update_stage(context.current_stage, ProcessingStatus.PAUSED)

            # Publish pause notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_PAUSED,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': reason,
                        'current_stage': context.current_stage.value
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Pipeline pause request handling failed: {str(e)}")

    async def _handle_resume_request(self, message: ProcessingMessage) -> None:
        """
        Handle pipeline resume request

        Args:
            message (ProcessingMessage): Resume request message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_pipelines.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update pipeline context
            context.update_stage(context.current_stage, ProcessingStatus.RUNNING)

            # Publish resume notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_RESUMED,
                    content={
                        'pipeline_id': pipeline_id,
                        'current_stage': context.current_stage.value
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Pipeline resume request handling failed: {str(e)}")

    async def _handle_cancel_request(self, message: ProcessingMessage) -> None:
        """
        Handle pipeline cancellation request

        Args:
            message (ProcessingMessage): Cancel request message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            reason = message.content.get('reason', 'Unspecified')
            context = self.active_pipelines.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update pipeline context
            context.update_stage(context.current_stage, ProcessingStatus.CANCELLED)

            # Publish cancellation notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_CANCELLED,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': reason,
                        'current_stage': context.current_stage.value
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup pipeline
            await self._cleanup_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Pipeline cancellation request handling failed: {str(e)}")

    async def _handle_status_request(self, message: ProcessingMessage) -> None:
        """
        Handle pipeline status request

        Args:
            message (ProcessingMessage): Status request message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_pipelines.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Publish status
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STATUS,
                    content={
                        'pipeline_id': pipeline_id,
                        'current_stage': context.current_stage.value,
                        'status': context.status.value,
                        'metrics': context.metrics,
                        'alerts': context.alerts
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Pipeline status request handling failed: {str(e)}")

    async def _cleanup_pipeline(self, pipeline_id: str) -> None:
        """Cleanup pipeline resources"""
        try:
            if pipeline_id in self.active_pipelines:
                # Get context before removal
                pipeline_context = self.active_pipelines[pipeline_id]

                # Remove from active pipelines
                del self.active_pipelines[pipeline_id]

                # Use base manager's message broker
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.PIPELINE_CLEANUP,
                        content={
                            'pipeline_id': pipeline_id
                        },
                        metadata=MessageMetadata(
                            correlation_id=pipeline_context.correlation_id,
                            source_component=self.context.component_name,
                            target_component="pipeline_service"
                        ),
                        source_identifier=self.module_identifier
                    )
                )

        except Exception as e:
            self.logger.error(f"Pipeline cleanup failed: {str(e)}")
            raise

    def _start_monitoring_tasks(self) -> None:
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_pipeline_health())
        asyncio.create_task(self._monitor_stage_timeouts())
        asyncio.create_task(self._update_pipeline_metrics())

    async def _monitor_pipeline_health(self) -> None:
        """Monitor health of active pipelines"""
        while True:
            try:
                for pipeline_id, context in self.active_pipelines.items():
                    if context.state == PipelineState.RUNNING:
                        await self._check_pipeline_health(pipeline_id)
                await asyncio.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Pipeline health monitoring error: {str(e)}")

    async def _monitor_stage_timeouts(self) -> None:
        """Monitor stage timeouts"""
        while True:
            try:
                for pipeline_id, context in self.active_pipelines.items():
                    if context.state == PipelineState.RUNNING and context.current_stage:
                        stage = context.stages[context.current_stage]
                        if stage.start_time and (datetime.now() - stage.start_time).total_seconds() > self.stage_timeout:
                            await self._handle_stage_timeout(pipeline_id, context.current_stage)
                await asyncio.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self.logger.error(f"Stage timeout monitoring error: {str(e)}")

    async def _update_pipeline_metrics(self) -> None:
        """Update pipeline metrics"""
        while True:
            try:
                for pipeline_id, context in self.active_pipelines.items():
                    await self._collect_pipeline_metrics(pipeline_id)
                await asyncio.sleep(15)  # Update every 15 seconds
            except Exception as e:
                self.logger.error(f"Pipeline metrics update error: {str(e)}")

    async def _check_pipeline_health(self, pipeline_id: str) -> None:
        """Check health of a specific pipeline"""
        try:
            context = self.active_pipelines[pipeline_id]
            health_status = {
                'pipeline_id': pipeline_id,
                'state': context.state,
                'current_stage': context.current_stage,
                'stages': {
                    name: {
                        'status': stage.status,
                        'retry_count': stage.retry_count,
                        'error': stage.error
                    }
                    for name, stage in context.stages.items()
                },
                'timestamp': datetime.now().isoformat()
            }
            
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_HEALTH_CHECK,
                    content=health_status,
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_manager",
                        domain_type="pipeline"
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Pipeline health check failed for {pipeline_id}: {str(e)}")

    async def _handle_stage_timeout(self, pipeline_id: str, stage_name: str) -> None:
        """Handle stage timeout"""
        try:
            context = self.active_pipelines[pipeline_id]
            stage = context.stages[stage_name]
            
            if stage.retry_count < stage.max_retries:
                # Retry the stage
                stage.retry_count += 1
                stage.start_time = datetime.now()
                stage.status = ProcessingStatus.RUNNING
                stage.error = None
                
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.PIPELINE_RETRY,
                        content={
                            'pipeline_id': pipeline_id,
                            'stage_name': stage_name,
                            'retry_count': stage.retry_count
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="pipeline_handler",
                            domain_type="pipeline"
                        )
                    )
                )
            else:
                # Mark stage as failed
                stage.status = ProcessingStatus.FAILED
                stage.error = f"Stage timeout after {stage.retry_count} retries"
                context.state = PipelineState.FAILED
                
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.PIPELINE_STAGE_ERROR,
                        content={
                            'pipeline_id': pipeline_id,
                            'stage_name': stage_name,
                            'error': stage.error
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="pipeline_handler",
                            domain_type="pipeline"
                        )
                    )
                )
        except Exception as e:
            self.logger.error(f"Stage timeout handling failed for {pipeline_id}: {str(e)}")

    async def _collect_pipeline_metrics(self, pipeline_id: str) -> None:
        """Collect metrics for a specific pipeline"""
        try:
            context = self.active_pipelines[pipeline_id]
            metrics = {
                'pipeline_id': pipeline_id,
                'state': context.state,
                'current_stage': context.current_stage,
                'stages': {
                    name: {
                        'status': stage.status,
                        'start_time': stage.start_time.isoformat() if stage.start_time else None,
                        'end_time': stage.end_time.isoformat() if stage.end_time else None,
                        'retry_count': stage.retry_count,
                        'metrics': stage.metrics
                    }
                    for name, stage in context.stages.items()
                },
                'start_time': context.start_time.isoformat() if context.start_time else None,
                'end_time': context.end_time.isoformat() if context.end_time else None,
                'timestamp': datetime.now().isoformat()
            }
            
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_METRICS_UPDATE,
                    content=metrics,
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="monitoring_manager",
                        domain_type="pipeline"
                    )
                )
            )
        except Exception as e:
            self.logger.error(f"Pipeline metrics collection failed for {pipeline_id}: {str(e)}")

    async def _handle_service_start(self, message: ProcessingMessage) -> None:
        """Handle pipeline service start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            stages = message.content.get('stages', [])
            
            # Check resource limits
            if len(self.active_pipelines) >= self.max_concurrent_pipelines:
                await self._send_error_response(
                    message,
                    "Maximum concurrent pipelines limit reached",
                    MessageType.PIPELINE_SERVICE_ERROR
                )
                return
            
            # Create pipeline context
            context = PipelineContext(
                pipeline_id=pipeline_id,
                state=PipelineState.INITIALIZED,
                stages={
                    stage['name']: PipelineStage(
                        name=stage['name'],
                        status=ProcessingStatus.PENDING,
                        max_retries=stage.get('max_retries', self.max_retries_per_stage)
                    )
                    for stage in stages
                },
                metadata=message.content.get('metadata', {})
            )
            
            self.active_pipelines[pipeline_id] = context
            
            # Send success response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'status': 'initialized',
                    'stages': [stage['name'] for stage in stages]
                },
                MessageType.PIPELINE_SERVICE_START
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline service start failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_SERVICE_ERROR
            )

    async def _handle_handler_start(self, message: ProcessingMessage) -> None:
        """Handle pipeline handler start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_pipelines.get(pipeline_id)
            
            if not context:
                await self._send_error_response(
                    message,
                    f"Pipeline {pipeline_id} not found",
                    MessageType.PIPELINE_HANDLER_ERROR
                )
                return
            
            # Start first stage
            first_stage = next(iter(context.stages.values()))
            first_stage.start_time = datetime.now()
            first_stage.status = ProcessingStatus.RUNNING
            context.current_stage = first_stage.name
            context.state = PipelineState.RUNNING
            
            # Send success response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'current_stage': first_stage.name,
                    'status': 'started'
                },
                MessageType.PIPELINE_HANDLER_START
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline handler start failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_HANDLER_ERROR
            )

    async def _handle_stage_complete(self, message: ProcessingMessage) -> None:
        """Handle stage completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            stage_name = message.content.get('stage_name')
            context = self.active_pipelines.get(pipeline_id)
            
            if not context or stage_name not in context.stages:
                await self._send_error_response(
                    message,
                    f"Stage {stage_name} not found in pipeline {pipeline_id}",
                    MessageType.PIPELINE_STAGE_ERROR
                )
                return
            
            # Update stage status
            stage = context.stages[stage_name]
            stage.status = ProcessingStatus.COMPLETED
            stage.end_time = datetime.now()
            stage.metrics.update(message.content.get('metrics', {}))
            
            # Check if pipeline is complete
            if all(s.status == ProcessingStatus.COMPLETED for s in context.stages.values()):
                context.state = PipelineState.COMPLETED
                context.end_time = datetime.now()
                
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.PIPELINE_HANDLER_COMPLETE,
                        content={
                            'pipeline_id': pipeline_id,
                            'status': 'completed'
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="pipeline_handler",
                            domain_type="pipeline"
                        )
                    )
                )
            else:
                # Start next stage
                next_stage = self._get_next_stage(context, stage_name)
                if next_stage:
                    next_stage.start_time = datetime.now()
                    next_stage.status = ProcessingStatus.RUNNING
                    context.current_stage = next_stage.name
                    
                    await self.message_broker.publish(
                        ProcessingMessage(
                            message_type=MessageType.PIPELINE_STAGE_START,
                            content={
                                'pipeline_id': pipeline_id,
                                'stage_name': next_stage.name
                            },
                            metadata=MessageMetadata(
                                source_component=self.component_name,
                                target_component="pipeline_handler",
                                domain_type="pipeline"
                            )
                        )
                    )
            
            # Send success response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'stage_name': stage_name,
                    'status': 'completed',
                    'next_stage': next_stage.name if next_stage else None
                },
                MessageType.PIPELINE_STAGE_COMPLETE
            )
            
        except Exception as e:
            self.logger.error(f"Stage completion handling failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_STAGE_ERROR
            )

    def _get_next_stage(self, context: PipelineContext, current_stage: str) -> Optional[PipelineStage]:
        """Get the next stage in the pipeline"""
        stages = list(context.stages.values())
        current_index = next(i for i, s in enumerate(stages) if s.name == current_stage)
        return stages[current_index + 1] if current_index < len(stages) - 1 else None

    async def _send_success_response(
        self,
        message: ProcessingMessage,
        content: Dict[str, Any],
        response_type: MessageType
    ) -> None:
        """Send success response"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=response_type,
                content=content,
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component=message.metadata.source_component,
                    domain_type="pipeline"
                )
            )
        )

    async def _send_error_response(
        self,
        message: ProcessingMessage,
        error: str,
        response_type: MessageType
    ) -> None:
        """Send error response"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=response_type,
                content={'error': error},
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component=message.metadata.source_component,
                    domain_type="pipeline"
                )
            )
        )

    async def _handle_stage_error(self, message: ProcessingMessage) -> None:
        """Handle stage error with retry logic"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            stage_name = message.content.get('stage_name')
            error = message.content.get('error')
            context = self.active_pipelines.get(pipeline_id)
            
            if not context or stage_name not in context.stages:
                await self._send_error_response(
                    message,
                    f"Stage {stage_name} not found in pipeline {pipeline_id}",
                    MessageType.PIPELINE_STAGE_ERROR
                )
                return
            
            # Update stage status
            stage = context.stages[stage_name]
            stage.status = ProcessingStatus.FAILED
            stage.error = error
            
            # Check retry logic
            if stage.retry_count < stage.max_retries:
                # Retry the stage
                stage.retry_count += 1
                stage.start_time = datetime.now()
                stage.status = ProcessingStatus.RUNNING
                stage.error = None
                
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.PIPELINE_RETRY,
                        content={
                            'pipeline_id': pipeline_id,
                            'stage_name': stage_name,
                            'retry_count': stage.retry_count
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="pipeline_handler",
                            domain_type="pipeline"
                        )
                    )
                )
            else:
                # Mark pipeline as failed
                context.state = PipelineState.FAILED
                context.error = f"Stage {stage_name} failed after {stage.retry_count} retries: {error}"
                
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.PIPELINE_HANDLER_ERROR,
                        content={
                            'pipeline_id': pipeline_id,
                            'stage_name': stage_name,
                            'error': context.error
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="pipeline_handler",
                            domain_type="pipeline"
                        )
                    )
                )
            
            # Send response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'stage_name': stage_name,
                    'status': 'error',
                    'retry_count': stage.retry_count,
                    'error': error
                },
                MessageType.PIPELINE_STAGE_ERROR
            )
            
        except Exception as e:
            self.logger.error(f"Stage error handling failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_STAGE_ERROR
            )

    async def _handle_pipeline_pause(self, message: ProcessingMessage) -> None:
        """Handle pipeline pause request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_pipelines.get(pipeline_id)
            
            if not context:
                await self._send_error_response(
                    message,
                    f"Pipeline {pipeline_id} not found",
                    MessageType.PIPELINE_HANDLER_ERROR
                )
                return
            
            if context.state != PipelineState.RUNNING:
                await self._send_error_response(
                    message,
                    f"Pipeline {pipeline_id} is not running",
                    MessageType.PIPELINE_HANDLER_ERROR
                )
                return
            
            # Update pipeline state
            context.state = PipelineState.PAUSED
            
            # Send success response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'status': 'paused',
                    'current_stage': context.current_stage
                },
                MessageType.PIPELINE_PAUSE
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline pause failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_HANDLER_ERROR
            )

    async def _handle_pipeline_resume(self, message: ProcessingMessage) -> None:
        """Handle pipeline resume request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_pipelines.get(pipeline_id)
            
            if not context:
                await self._send_error_response(
                    message,
                    f"Pipeline {pipeline_id} not found",
                    MessageType.PIPELINE_HANDLER_ERROR
                )
                return
            
            if context.state != PipelineState.PAUSED:
                await self._send_error_response(
                    message,
                    f"Pipeline {pipeline_id} is not paused",
                    MessageType.PIPELINE_HANDLER_ERROR
                )
                return
            
            # Update pipeline state
            context.state = PipelineState.RUNNING
            
            # Resume current stage
            if context.current_stage:
                stage = context.stages[context.current_stage]
                stage.start_time = datetime.now()
                stage.status = ProcessingStatus.RUNNING
                
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.PIPELINE_STAGE_START,
                        content={
                            'pipeline_id': pipeline_id,
                            'stage_name': context.current_stage
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component="pipeline_handler",
                            domain_type="pipeline"
                        )
                    )
                )
            
            # Send success response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'status': 'resumed',
                    'current_stage': context.current_stage
                },
                MessageType.PIPELINE_RESUME
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline resume failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_HANDLER_ERROR
            )

    async def _handle_pipeline_cancel(self, message: ProcessingMessage) -> None:
        """Handle pipeline cancellation request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_pipelines.get(pipeline_id)
            
            if not context:
                await self._send_error_response(
                    message,
                    f"Pipeline {pipeline_id} not found",
                    MessageType.PIPELINE_HANDLER_ERROR
                )
                return
            
            # Update pipeline state
            context.state = PipelineState.CANCELLED
            context.end_time = datetime.now()
            
            # Cancel current stage
            if context.current_stage:
                stage = context.stages[context.current_stage]
                stage.status = ProcessingStatus.CANCELLED
                stage.end_time = datetime.now()
            
            # Send success response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'status': 'cancelled',
                    'current_stage': context.current_stage
                },
                MessageType.PIPELINE_CANCEL
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline cancellation failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_HANDLER_ERROR
            )

    async def _handle_recovery_start(self, message: ProcessingMessage) -> None:
        """Handle pipeline recovery start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_pipelines.get(pipeline_id)
            
            if not context:
                await self._send_error_response(
                    message,
                    f"Pipeline {pipeline_id} not found",
                    MessageType.PIPELINE_HANDLER_ERROR
                )
                return
            
            # Update pipeline state
            context.state = PipelineState.RECOVERING
            
            # Get checkpoint data
            checkpoint_data = message.content.get('checkpoint_data', {})
            context.checkpoint_data = checkpoint_data
            
            # Start recovery process
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_RESTORE,
                    content={
                        'pipeline_id': pipeline_id,
                        'checkpoint_data': checkpoint_data
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="pipeline_handler",
                        domain_type="pipeline"
                    )
                )
            )
            
            # Send success response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'status': 'recovering',
                    'checkpoint_data': checkpoint_data
                },
                MessageType.PIPELINE_RECOVERY_START
            )
            
        except Exception as e:
            self.logger.error(f"Pipeline recovery start failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_RECOVERY_ERROR
            )

    async def _handle_data_ready(self, message: ProcessingMessage) -> None:
        """Handle data ready notification"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            stage_name = message.content.get('stage_name')
            data_reference = message.content.get('data_reference')
            context = self.active_pipelines.get(pipeline_id)
            
            if not context or stage_name not in context.stages:
                await self._send_error_response(
                    message,
                    f"Stage {stage_name} not found in pipeline {pipeline_id}",
                    MessageType.PIPELINE_DATA_ERROR
                )
                return
            
            # Update stage metrics
            stage = context.stages[stage_name]
            stage.metrics.update({
                'data_reference': data_reference,
                'data_ready_time': datetime.now().isoformat()
            })
            
            # Send success response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'stage_name': stage_name,
                    'data_reference': data_reference,
                    'status': 'ready'
                },
                MessageType.PIPELINE_DATA_READY
            )
            
        except Exception as e:
            self.logger.error(f"Data ready handling failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_DATA_ERROR
            )

    async def _handle_data_processed(self, message: ProcessingMessage) -> None:
        """Handle data processed notification"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            stage_name = message.content.get('stage_name')
            result_reference = message.content.get('result_reference')
            metrics = message.content.get('metrics', {})
            context = self.active_pipelines.get(pipeline_id)
            
            if not context or stage_name not in context.stages:
                await self._send_error_response(
                    message,
                    f"Stage {stage_name} not found in pipeline {pipeline_id}",
                    MessageType.PIPELINE_DATA_ERROR
                )
                return
            
            # Update stage metrics
            stage = context.stages[stage_name]
            stage.metrics.update({
                'result_reference': result_reference,
                'processing_complete_time': datetime.now().isoformat(),
                **metrics
            })
            
            # Send success response
            await self._send_success_response(
                message,
                {
                    'pipeline_id': pipeline_id,
                    'stage_name': stage_name,
                    'result_reference': result_reference,
                    'metrics': metrics,
                    'status': 'processed'
                },
                MessageType.PIPELINE_DATA_PROCESSED
            )
            
        except Exception as e:
            self.logger.error(f"Data processed handling failed: {str(e)}")
            await self._send_error_response(
                message,
                str(e),
                MessageType.PIPELINE_DATA_ERROR
            )
