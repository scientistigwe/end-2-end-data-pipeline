# backend/core/managers/pipeline_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    PipelineContext,
    PipelineState,
    ComponentType,
    ModuleIdentifier
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)

class PipelineManager(BaseManager):
    """
    Pipeline Manager that coordinates all system components.
    Central orchestrator for the entire data processing workflow.
    """

    def __init__(
        self,
        message_broker: MessageBroker,
        component_name: str,
        domain_type: str
    ):
        # Initialize base manager
        super().__init__(
            message_broker=message_broker,
            component_name=component_name,
            domain_type=domain_type
        )

        # Pipeline-specific state
        self.active_pipelines: Dict[str, PipelineContext] = {}

    async def _setup_domain_handlers(self) -> None:
        """Setup pipeline-specific message handlers"""
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

            # Pipeline Control
            MessageType.PIPELINE_PAUSE_REQUEST: self._handle_pause_request,
            MessageType.PIPELINE_RESUME_REQUEST: self._handle_resume_request,
            MessageType.PIPELINE_CANCEL_REQUEST: self._handle_cancel_request,
            MessageType.PIPELINE_STATUS_REQUEST: self._handle_status_request,

            # Resource Management
            MessageType.RESOURCE_ACCESS_REQUEST: self._handle_resource_request,
            MessageType.RESOURCE_RELEASE_COMPLETE: self._handle_resource_release,

            # Monitoring
            MessageType.MONITORING_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.MONITORING_ALERT_NOTIFY: self._handle_monitoring_alert,
            MessageType.MONITORING_HEALTH_STATUS: self._handle_health_status
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

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
    async def cleanup(self) -> None:
        """Cleanup pipeline manager resources"""
        try:
            # Do base cleanup first
            await super().cleanup()

            # Cleanup active pipelines
            for pipeline_id in list(self.active_pipelines.keys()):
                await self._cleanup_pipeline(pipeline_id)

        except Exception as e:
            self.logger.error(f"Pipeline cleanup failed: {e}")
            raise

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

    def _setup_message_handlers(self) -> None:
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
            self.message_broker.subscribe(
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

    async def _handle_component_error(self, message: ProcessingMessage) -> None:
        """
        Handle generic component errors

        Args:
            message (ProcessingMessage): Component error message
        """
        try:
            pipeline_id = message.content['pipeline_id']
            error_details = message.content.get('error', 'Unknown error')
            component = message.content.get('component', 'Unknown component')
            context = self.active_pipelines.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update pipeline context
            context.update_stage(context.current_stage, ProcessingStatus.FAILED)
            context.error = {
                'component': component,
                'details': error_details
            }

            # Publish error notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'component': component,
                        'error': error_details,
                        'stage': context.current_stage.value
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
            logger.error(f"Component error handling failed: {str(e)}")

    async def _handle_error(self, pipeline_id: str, error: str) -> None:
        """
        Generic error handling method

        Args:
            pipeline_id (str): Pipeline identifier
            error (str): Error message
        """
        try:
            context = self.active_pipelines.get(pipeline_id)
            if not context:
                logger.warning(f"No context found for pipeline {pipeline_id}")
                return

            # Update pipeline context
            context.update_stage(context.current_stage, ProcessingStatus.FAILED)
            context.error = error

            # Publish error notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'stage': context.current_stage.value
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
            logger.error(f"Error handling failed: {str(e)}")

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
