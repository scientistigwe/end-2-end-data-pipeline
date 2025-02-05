import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    PipelineContext,
    PipelineState,
    ComponentType,
    ModuleIdentifier,
    MetricType
)

logger = logging.getLogger(__name__)


class PipelineService:
    """
    Service layer for pipeline orchestration.
    Coordinates business logic between components through handler layer.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="pipeline_service",
            component_type=ComponentType.PIPELINE_SERVICE,
            department="pipeline",
            role="service"
        )

        # Active pipelines
        self.active_contexts: Dict[str, PipelineContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup message handling for service layer"""
        handlers = {
            # Pipeline Management
            MessageType.PIPELINE_CREATE_REQUEST: self._handle_pipeline_create,
            MessageType.PIPELINE_START_REQUEST: self._handle_pipeline_start,
            MessageType.PIPELINE_PAUSE_REQUEST: self._handle_pipeline_pause,
            MessageType.PIPELINE_RESUME_REQUEST: self._handle_pipeline_resume,
            MessageType.PIPELINE_CANCEL_REQUEST: self._handle_pipeline_cancel,

            # Stage Management
            MessageType.PIPELINE_STAGE_START_REQUEST: self._handle_stage_start,
            MessageType.PIPELINE_STAGE_COMPLETE: self._handle_stage_complete,
            MessageType.PIPELINE_STAGE_ERROR: self._handle_stage_error,

            # Component Coordination
            MessageType.QUALITY_PROCESS_COMPLETE: self._handle_quality_complete,
            MessageType.INSIGHT_GENERATE_COMPLETE: self._handle_insight_complete,
            MessageType.ANALYTICS_PROCESS_COMPLETE: self._handle_analytics_complete,
            MessageType.DECISION_PROCESS_COMPLETE: self._handle_decision_complete,
            MessageType.RECOMMENDATION_PROCESS_COMPLETE: self._handle_recommendation_complete,
            MessageType.REPORT_PROCESS_COMPLETE: self._handle_report_complete,

            # Monitoring & Health
            MessageType.MONITORING_METRICS_UPDATE: self._handle_monitoring_update,
            MessageType.MONITORING_ALERT_GENERATE: self._handle_monitoring_alert,

            # Resource Management
            MessageType.RESOURCE_ACCESS_GRANT: self._handle_resource_granted,
            MessageType.RESOURCE_ACCESS_DENY: self._handle_resource_denied
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                f"pipeline.{message_type.value}",
                handler
            )

    async def _handle_pipeline_create(self, message: ProcessingMessage) -> None:
        """Handle pipeline creation request"""
        try:
            pipeline_id = str(uuid.uuid4())
            config = message.content.get('config', {})

            # Create pipeline context
            context = PipelineContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                state=PipelineState.INITIALIZING,
                stage_sequence=self._get_stage_sequence(config),
                stage_dependencies=self._get_stage_dependencies()
            )

            self.active_contexts[pipeline_id] = context

            # Notify creation complete
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_CREATE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'created'
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component=message.source_identifier.component_name
                    ),
                    source_identifier=self.module_identifier,
                    target_identifier=message.source_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to create pipeline: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_pipeline_start(self, message: ProcessingMessage) -> None:
        """Handle pipeline start request"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            context.state = PipelineState.RUNNING

            # Start monitoring
            await self._start_monitoring(pipeline_id, context.stage_configs)

            # Initialize first stage
            await self._initialize_first_stage(pipeline_id, context.stage_configs)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_START_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'started'
                    },
                    metadata=message.metadata,
                    source_identifier=self.module_identifier,
                    target_identifier=message.source_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to start pipeline: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_pipeline_pause(self, message: ProcessingMessage) -> None:
        """Handle pipeline pause request"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            context.state = PipelineState.PAUSED
            context.pause_reason = message.content.get('reason')

            # Notify all components
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_PAUSE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'paused',
                        'reason': context.pause_reason
                    },
                    metadata=message.metadata,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to pause pipeline: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_pipeline_resume(self, message: ProcessingMessage) -> None:
        """Handle pipeline resume request"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            if context.state != PipelineState.PAUSED:
                raise ValueError(f"Pipeline {pipeline_id} is not paused")

            context.state = PipelineState.RUNNING
            context.pause_reason = None

            # Resume from current stage
            await self._resume_pipeline(pipeline_id)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_RESUME_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'resumed'
                    },
                    metadata=message.metadata,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to resume pipeline: {str(e)}")
            await self._handle_error(message, str(e))

    async def _resume_pipeline(self, pipeline_id: str) -> None:
        """Resume pipeline from current stage"""
        context = self.active_contexts.get(pipeline_id)
        if not context or not context.current_stage:
            return

        # Re-initiate current stage
        await self._initiate_stage(
            pipeline_id,
            context.current_stage.stage_type,
            context.current_stage.results
        )

    async def _handle_stage_start(self, message: ProcessingMessage) -> None:
        """Handle stage start request"""
        try:
            pipeline_id = message.content['pipeline_id']
            stage = ProcessingStage(message.content['stage'])

            context = self.active_contexts.get(pipeline_id)
            if not context:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            # Update context
            context.update_stage(stage)

            # Initiate stage processing
            await self._initiate_stage(pipeline_id, stage, {})

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STAGE_STATUS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': stage.value,
                        'status': 'started'
                    },
                    metadata=message.metadata,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to start stage: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_pipeline_cancel(self, message: ProcessingMessage) -> None:
        """Handle pipeline cancellation request"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = self.active_contexts.get(pipeline_id)

            if not context:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            # Update state
            context.state = PipelineState.CANCELLED

            # Stop monitoring
            await self._stop_monitoring(pipeline_id)

            # Cleanup resources
            await self._cleanup_pipeline(pipeline_id)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_CANCEL_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'cancelled'
                    },
                    metadata=message.metadata,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to cancel pipeline: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_monitoring_update(self, message: ProcessingMessage) -> None:
        """Handle monitoring metric updates"""
        try:
            pipeline_id = message.content['pipeline_id']
            metrics = message.content['metrics']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update metrics in context
            context.update_metrics(metrics)

            # Check resource thresholds
            if self._check_resource_constraints(metrics):
                await self._handle_resource_constraint(pipeline_id, metrics)

            # Forward update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_METRICS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=message.metadata,
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle monitoring update: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_monitoring_alert(self, message: ProcessingMessage) -> None:
        """Handle monitoring alerts"""
        try:
            pipeline_id = message.content['pipeline_id']
            alert = message.content['alert']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Process alert based on severity
            if alert['severity'] == 'critical':
                await self._handle_critical_alert(pipeline_id, alert)
            else:
                # Forward alert
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.PIPELINE_ERROR_NOTIFY,
                        content={
                            'pipeline_id': pipeline_id,
                            'alert': alert,
                            'timestamp': datetime.now().isoformat()
                        },
                        metadata=message.metadata,
                        source_identifier=self.module_identifier
                    )
                )

        except Exception as e:
            logger.error(f"Failed to handle monitoring alert: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_critical_alert(self, pipeline_id: str, alert: Dict[str, Any]) -> None:
        """Handle critical monitoring alerts"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Pause pipeline
        context.state = PipelineState.PAUSED
        context.pause_reason = f"Critical alert: {alert['message']}"

        # Notify about pause
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_PAUSE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': 'paused',
                    'reason': context.pause_reason
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name
                ),
                source_identifier=self.module_identifier
            )
        )

    def _check_resource_constraints(self, metrics: Dict[str, Any]) -> bool:
        """Check if resource constraints are violated"""
        # Define thresholds
        thresholds = {
            'cpu_usage': 90.0,  # 90% CPU usage
            'memory_usage': 85.0,  # 85% memory usage
            'disk_usage': 90.0  # 90% disk usage
        }

        for metric, threshold in thresholds.items():
            if metrics.get(metric, 0) > threshold:
                return True

        return False

    async def _handle_resource_granted(self, message: ProcessingMessage) -> None:
        """Handle resource access grant"""
        try:
            pipeline_id = message.content['pipeline_id']
            resource_type = message.content['resource_type']
            resource_id = message.content['resource_id']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update resource allocation
            if 'allocated_resources' not in context.resource_allocation:
                context.resource_allocation['allocated_resources'] = {}

            context.resource_allocation['allocated_resources'][resource_type] = resource_id

            # Continue pipeline if waiting for this resource
            if context.state == PipelineState.AWAITING_DECISION:
                await self._resume_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle resource grant: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_resource_denied(self, message: ProcessingMessage) -> None:
        """Handle resource access denial"""
        try:
            pipeline_id = message.content['pipeline_id']
            resource_type = message.content['resource_type']
            reason = message.content.get('reason', 'Unknown reason')

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Log resource denial
            context.add_error(
                context.current_stage.stage_type.value if context.current_stage else 'unknown',
                f"Resource access denied: {resource_type}",
                {'reason': reason}
            )

            # Determine if pipeline can continue
            if self._is_resource_critical(resource_type):
                await self._handle_critical_resource_denial(pipeline_id, resource_type, reason)
            else:
                await self._attempt_resource_alternative(pipeline_id, resource_type)

        except Exception as e:
            logger.error(f"Failed to handle resource denial: {str(e)}")
            await self._handle_error(message, str(e))

    def _is_resource_critical(self, resource_type: str) -> bool:
        """Determine if resource is critical for pipeline operation"""
        critical_resources = {'database', 'storage', 'compute'}
        return resource_type in critical_resources

    async def _handle_critical_resource_denial(self, pipeline_id: str, resource_type: str, reason: str) -> None:
        """Handle denial of critical resource"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Pause pipeline
        context.state = PipelineState.PAUSED
        context.pause_reason = f"Critical resource denied: {resource_type} - {reason}"

        # Notify about critical resource denial
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_ERROR_NOTIFY,
                content={
                    'pipeline_id': pipeline_id,
                    'error_type': 'critical_resource_denied',
                    'resource_type': resource_type,
                    'reason': reason,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _attempt_resource_alternative(self, pipeline_id: str, resource_type: str) -> None:
        """Attempt to find alternative resource"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Request alternative resource
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.RESOURCE_ACCESS_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'resource_type': resource_type,
                    'is_alternative': True,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """Handle quality check completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            results = message.content['results']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update quality metrics
            context.update_metrics({
                'quality_metrics': results.get('metrics', {}),
                'quality_score': results.get('overall_score', 0)
            })

            # Determine next stage based on quality results
            if results.get('passed', False):
                await self._proceed_to_next_stage(pipeline_id, results)
            else:
                await self._handle_quality_failure(pipeline_id, results)

        except Exception as e:
            logger.error(f"Failed to handle quality completion: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_quality_failure(self, pipeline_id: str, results: Dict[str, Any]) -> None:
        """Handle quality check failure"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Create user decision point
        context.state = PipelineState.AWAITING_DECISION
        context.pending_decision = {
            'type': 'quality_failure',
            'issues': results.get('issues', []),
            'options': ['retry', 'skip', 'abort']
        }

        # Notify about required decision
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_ERROR_NOTIFY,
                content={
                    'pipeline_id': pipeline_id,
                    'error_type': 'quality_failure',
                    'details': results,
                    'requires_decision': True,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name
                ),
                source_identifier=self.module_identifier
            )
        )

    def _validate_insight_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate insight generation results"""
        validation = {'passed': True, 'checks': []}

        insights = results.get('insights', [])

        # Check insights format
        if not isinstance(insights, list):
            validation['passed'] = False
            validation['checks'].append({
                'check': 'insights_format',
                'passed': False,
                'message': "Insights must be a list"
            })
            return validation

        # Validate each insight
        for idx, insight in enumerate(insights):
            if not isinstance(insight, dict):
                validation['passed'] = False
                validation['checks'].append({
                    'check': f'insight_{idx}_format',
                    'passed': False,
                    'message': f"Insight {idx} must be a dictionary"
                })
                continue

            # Check required fields
            required_fields = ['type', 'description', 'confidence']
            missing_fields = [field for field in required_fields if field not in insight]
            if missing_fields:
                validation['passed'] = False
                validation['checks'].append({
                    'check': f'insight_{idx}_required_fields',
                    'passed': False,
                    'message': f"Insight {idx} missing required fields: {missing_fields}"
                })

            # Validate confidence score
            confidence = insight.get('confidence', 0)
            if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                validation['passed'] = False
                validation['checks'].append({
                    'check': f'insight_{idx}_confidence',
                    'passed': False,
                    'message': f"Insight {idx} has invalid confidence score: {confidence}"
                })

        return validation

    def _validate_analytics_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate analytics results"""
        validation = {'passed': True, 'checks': []}

        # Check for required sections
        required_sections = ['analysis_results', 'metrics', 'model_performance']
        missing_sections = [section for section in required_sections if section not in results]
        if missing_sections:
            validation['passed'] = False
            validation['checks'].append({
                'check': 'required_sections',
                'passed': False,
                'message': f"Missing required sections: {missing_sections}"
            })

        # Validate metrics
        metrics = results.get('metrics', {})
        if not isinstance(metrics, dict):
            validation['passed'] = False
            validation['checks'].append({
                'check': 'metrics_format',
                'passed': False,
                'message': "Metrics must be a dictionary"
            })
        else:
            # Check for required metrics
            required_metrics = ['accuracy', 'performance', 'processing_time']
            missing_metrics = [metric for metric in required_metrics if metric not in metrics]
            if missing_metrics:
                validation['passed'] = False
                validation['checks'].append({
                    'check': 'required_metrics',
                    'passed': False,
                    'message': f"Missing required metrics: {missing_metrics}"
                })

        return validation

    async def _handle_dependency_failure(self, pipeline_id: str, target_stage: ProcessingStage) -> None:
        """Handle stage dependency failure"""
        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Get missing dependencies
            stage_deps = context.stage_dependencies.get(target_stage.value, [])
            completed_stages = {stage.value for stage in context.completed_stages}
            missing_deps = [dep for dep in stage_deps if dep not in completed_stages]

            error_details = {
                'type': 'dependency_failure',
                'target_stage': target_stage.value,
                'missing_dependencies': missing_deps,
                'completed_stages': list(completed_stages)
            }

            # Update context
            context.add_error(target_stage.value, "Stage dependencies not met", error_details)
            context.state = PipelineState.PAUSED

            # Notify about dependency failure
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_ERROR_NOTIFY,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error_details,
                        'requires_decision': True,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Create decision point for handling dependency failure
            context.pending_decision = {
                'type': 'dependency_failure',
                'target_stage': target_stage.value,
                'missing_dependencies': missing_deps,
                'options': ['wait_and_retry', 'skip_dependencies', 'abort']
            }

        except Exception as e:
            logger.error(f"Error handling dependency failure: {str(e)}")

    async def _handle_validation_failure(self, pipeline_id: str, validation_result: Dict[str, Any]) -> None:
        """Handle post-stage validation failure"""
        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            error_details = {
                'type': 'validation_failure',
                'stage': context.current_stage.stage_type.value if context.current_stage else None,
                'validation_details': validation_result,
                'timestamp': datetime.now().isoformat()
            }

            # Add to context error history
            context.add_error(
                context.current_stage.stage_type.value if context.current_stage else 'unknown',
                "Post-stage validation failed",
                error_details
            )

            # Create decision point
            context.state = PipelineState.AWAITING_DECISION
            context.pending_decision = {
                'type': 'validation_failure',
                'validation_result': validation_result,
                'options': ['retry', 'ignore', 'abort']
            }

            # Notify about validation failure
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_ERROR_NOTIFY,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error_details,
                        'requires_decision': True
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Record validation attempt
            context.metrics[f'validation_attempts_{context.current_stage.stage_type.value}'] = \
                context.metrics.get(f'validation_attempts_{context.current_stage.stage_type.value}', 0) + 1

        except Exception as e:
            logger.error(f"Error handling validation failure: {str(e)}")

    async def _retry_stage_execution(self, pipeline_id: str, stage: ProcessingStage) -> None:
        """Retry stage execution with exponential backoff"""
        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Get retry count and update
            retry_key = f"{stage.value}_retries"
            retry_count = context.retry_counts.get(retry_key, 0) + 1
            context.retry_counts[retry_key] = retry_count

            # Calculate backoff delay (max 30 seconds)
            delay = min(2 ** retry_count, 30)

            # Wait for backoff period
            await asyncio.sleep(delay)

            # Attempt stage re-execution
            await self._initiate_stage(
                pipeline_id,
                stage,
                {
                    'is_retry': True,
                    'retry_count': retry_count,
                    'previous_errors': context.error_history
                }
            )

            logger.info(f"Pipeline {pipeline_id}: Retrying stage {stage.value} (attempt {retry_count})")

        except Exception as e:
            logger.error(f"Error retrying stage execution: {str(e)}")
            await self._handle_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                f"Stage retry error: {str(e)}"
            )

    def _calculate_stage_progress(self, context: PipelineContext, completed_stage: ProcessingStage) -> float:
        """Calculate pipeline progress after stage completion"""
        try:
            # Get stage weights (can be customized based on stage complexity)
            stage_weights = {
                ProcessingStage.QUALITY_CHECK: 0.15,
                ProcessingStage.INSIGHT_GENERATION: 0.20,
                ProcessingStage.ADVANCED_ANALYTICS: 0.25,
                ProcessingStage.DECISION_MAKING: 0.15,
                ProcessingStage.RECOMMENDATION: 0.15,
                ProcessingStage.REPORT_GENERATION: 0.10
            }

            # Calculate progress based on completed stages
            total_progress = 0.0
            completed_stages = {stage.stage_type for stage in context.completed_stages}
            completed_stages.add(completed_stage)  # Add current completion

            for stage in completed_stages:
                total_progress += stage_weights.get(stage, 0)

            return min(total_progress * 100, 100.0)

        except Exception as e:
            logger.error(f"Error calculating stage progress: {str(e)}")
            return 0.0
            import logging

    async def _handle_insight_complete(self, message: ProcessingMessage) -> None:
        """Handle insight generation completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            insights = message.content['insights']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update insight metrics
            context.update_metrics({
                'total_insights': len(insights),
                'insight_categories': self._categorize_insights(insights)
            })

            # Proceed to next stage
            await self._proceed_to_next_stage(pipeline_id, {'insights': insights})

        except Exception as e:
            logger.error(f"Failed to handle insight completion: {str(e)}")
            await self._handle_error(message, str(e))

    def _categorize_insights(self, insights: List[Dict[str, Any]]) -> Dict[str, int]:
        """Categorize insights by type"""
        categories = {}
        for insight in insights:
            category = insight.get('category', 'uncategorized')
            categories[category] = categories.get(category, 0) + 1
        return categories

    async def _handle_analytics_complete(self, message: ProcessingMessage) -> None:
        """Handle analytics completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            analytics_results = message.content['results']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update analytics metrics
            context.update_metrics({
                'analytics_metrics': analytics_results.get('metrics', {}),
                'model_performance': analytics_results.get('model_metrics', {})
            })

            # Proceed to next stage
            await self._proceed_to_next_stage(pipeline_id, analytics_results)

        except Exception as e:
            logger.error(f"Failed to handle analytics completion: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_decision_complete(self, message: ProcessingMessage) -> None:
        """Handle decision process completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            decision = message.content['decision']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Apply decision
            if decision.get('requires_confirmation', False):
                await self._request_decision_confirmation(pipeline_id, decision)
            else:
                await self._apply_decision(pipeline_id, decision)

        except Exception as e:
            logger.error(f"Failed to handle decision completion: {str(e)}")
            await self._handle_error(message, str(e))

    async def _request_decision_confirmation(self, pipeline_id: str, decision: Dict[str, Any]) -> None:
        """Request confirmation for decision"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        context.state = PipelineState.AWAITING_DECISION
        context.pending_decision = {
            'type': 'decision_confirmation',
            'decision': decision,
            'options': ['confirm', 'reject']
        }

        # Notify about required confirmation
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': 'awaiting_decision',
                    'decision_type': 'confirmation',
                    'decision_details': decision,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _apply_decision(self, pipeline_id: str, decision: Dict[str, Any]) -> None:
        """Apply confirmed decision"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Update decision metrics
        context.update_metrics({
            'decisions_made': context.metrics.get('decisions_made', 0) + 1,
            'decision_type': decision.get('type'),
            'decision_confidence': decision.get('confidence', 0)
        })

        # Proceed to next stage
        await self._proceed_to_next_stage(pipeline_id, {'decision': decision})

    async def _proceed_to_next_stage(self, pipeline_id: str, current_results: Dict[str, Any]) -> None:
        """Determine and initiate next pipeline stage"""
        context = self.active_contexts.get(pipeline_id)
        if not context or not context.current_stage:
            return

        current_stage = context.current_stage.stage_type
        next_stage = self._get_next_stage(context, current_stage)

        if next_stage:
            # Mark current stage as complete
            context.complete_stage(current_stage.value)

            # Initiate next stage
            await self._initiate_stage(pipeline_id, next_stage, current_results)
        else:
            # Pipeline complete
            await self._complete_pipeline(pipeline_id)

    def _get_next_stage(self, context: PipelineContext, current_stage: ProcessingStage) -> Optional[ProcessingStage]:
        """Get next stage in pipeline sequence"""
        try:
            current_index = context.stage_sequence.index(current_stage)
            if current_index < len(context.stage_sequence) - 1:
                return context.stage_sequence[current_index + 1]
        except ValueError:
            logger.error(f"Current stage {current_stage} not found in sequence")
        return None

    async def _handle_recommendation_complete(self, message: ProcessingMessage) -> None:
        """Handle recommendation generation completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            recommendations = message.content['recommendations']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update recommendation metrics
            context.update_metrics({
                'total_recommendations': len(recommendations),
                'recommendation_confidence': self._calculate_recommendation_confidence(recommendations)
            })

            # Proceed to next stage
            await self._proceed_to_next_stage(pipeline_id, {'recommendations': recommendations})

        except Exception as e:
            logger.error(f"Failed to handle recommendation completion: {str(e)}")
            await self._handle_error(message, str(e))

    def _calculate_recommendation_confidence(self, recommendations: List[Dict[str, Any]]) -> float:
        """Calculate average confidence of recommendations"""
        if not recommendations:
            return 0.0

        confidence_sum = sum(rec.get('confidence', 0) for rec in recommendations)
        return confidence_sum / len(recommendations)

    async def _handle_report_complete(self, message: ProcessingMessage) -> None:
        """Handle report generation completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            report = message.content['report']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update report metrics
            context.update_metrics({
                'report_sections': len(report.get('sections', [])),
                'report_insights': len(report.get('insights', [])),
                'report_generated_at': datetime.now().isoformat()
            })

            # Proceed to next stage or complete pipeline
            if context.current_stage.stage_type == ProcessingStage.REPORT_GENERATION:
                await self._complete_pipeline(pipeline_id)
            else:
                await self._proceed_to_next_stage(pipeline_id, {'report': report})

        except Exception as e:
            logger.error(f"Failed to handle report completion: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_stage_error(self, message: ProcessingMessage) -> None:
        """Handle stage processing error"""
        try:
            pipeline_id = message.content['pipeline_id']
            stage = message.content['stage']
            error = message.content['error']

            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Record error
            context.add_error(stage, error, message.content.get('details', {}))

            # Update retry count
            retry_count = context.retry_counts.get(stage, 0) + 1
            context.retry_counts[stage] = retry_count

            # Attempt retry or handle failure
            if retry_count <= context.stage_configs.get('max_retries', 3):
                await self._retry_stage(pipeline_id, stage)
            else:
                await self._handle_stage_failure(pipeline_id, stage, error)

        except Exception as e:
            logger.error(f"Failed to handle stage error: {str(e)}")
            await self._handle_error(message, str(e))

    async def _retry_stage(self, pipeline_id: str, stage: str) -> None:
        """Retry failed stage"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Add delay based on retry count
        retry_count = context.retry_counts.get(stage, 0)
        await asyncio.sleep(min(2 ** retry_count, 30))  # Exponential backoff, max 30 seconds

        await self._initiate_stage(pipeline_id, ProcessingStage(stage), {
            'is_retry': True,
            'retry_count': retry_count
        })

    async def _handle_stage_failure(self, pipeline_id: str, stage: str, error: str) -> None:
        """Handle permanent stage failure"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Create decision point for failure
        context.state = PipelineState.AWAITING_DECISION
        context.pending_decision = {
            'type': 'stage_failure',
            'stage': stage,
            'error': error,
            'options': ['skip', 'abort', 'custom_resolution']
        }

        # Notify about failure
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': stage,
                    'error': error,
                    'requires_decision': True,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_resource_constraint(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """Handle resource constraint violations"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return

        # Identify constrained resources
        constrained_resources = []
        for resource, usage in metrics.items():
            if resource.endswith('_usage') and usage > 90:  # 90% threshold
                constrained_resources.append(resource)

        if constrained_resources:
            # Pause pipeline if resources are critically constrained
            context.state = PipelineState.PAUSED
            context.pause_reason = f"Resource constraints: {', '.join(constrained_resources)}"

            # Notify about resource constraints
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_PAUSE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'paused',
                        'reason': context.pause_reason,
                        'constrained_resources': constrained_resources,
                        'metrics': metrics
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    ),
                    source_identifier=self.module_identifier
                )
            )

    async def _complete_pipeline(self, pipeline_id: str) -> None:
        """Handle pipeline completion"""
        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            # Update state
            context.state = PipelineState.COMPLETED
            context.completed_at = datetime.now()

            # Calculate final metrics
            final_metrics = {
                'total_duration': (context.completed_at - context.created_at).total_seconds(),
                'stages_completed': len(context.completed_stages),
                'total_errors': len(context.error_history),
                'completion_status': 'success'
            }

            # Update context metrics
            context.update_metrics(final_metrics)

            # Stop monitoring
            await self._stop_monitoring(pipeline_id)

            # Generate completion report
            completion_report = {
                'pipeline_id': pipeline_id,
                'status': 'completed',
                'metrics': context.metrics,
                'stage_results': {stage.value: stage.results for stage in context.completed_stages},
                'duration': final_metrics['total_duration'],
                'completed_at': context.completed_at.isoformat()
            }

            # Notify completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STATUS_UPDATE,
                    content=completion_report,
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            await self._cleanup_pipeline(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to complete pipeline: {str(e)}")
            await self._handle_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _cleanup_pipeline(self, pipeline_id: str) -> None:
        """Clean up pipeline resources"""
        try:
            context = self.active_contexts.pop(pipeline_id, None)
            if not context:
                return

            # Release resources
            if context.resource_allocation:
                for resource_type, resource_id in context.resource_allocation.get('allocated_resources', {}).items():
                    await self.message_broker.publish(
                        ProcessingMessage(
                            message_type=MessageType.RESOURCE_RELEASE_REQUEST,
                            content={
                                'pipeline_id': pipeline_id,
                                'resource_type': resource_type,
                                'resource_id': resource_id
                            },
                            metadata=MessageMetadata(
                                correlation_id=context.correlation_id,
                                source_component=self.module_identifier.component_name
                            ),
                            source_identifier=self.module_identifier
                        )
                    )

            # Cleanup notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_CLEANUP_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'cleaned',
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Error during pipeline cleanup: {str(e)}")

    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive pipeline status"""
        context = self.active_contexts.get(pipeline_id)
        if not context:
            return None

        return {
            'pipeline_id': pipeline_id,
            'state': context.state.value,
            'current_stage': context.current_stage.stage_type.value if context.current_stage else None,
            'progress': context.progress,
            'metrics': context.metrics,
            'error_count': len(context.error_history),
            'started_at': context.created_at.isoformat(),
            'updated_at': context.updated_at.isoformat(),
            'completed_at': context.completed_at.isoformat() if context.completed_at else None,
            'duration': (datetime.now() - context.created_at).total_seconds(),
            'stages_completed': [stage.value for stage in context.completed_stages],
            'pending_decision': context.pending_decision,
            'resource_allocation': context.resource_allocation
        }

    async def _handle_stage_complete(self, message: ProcessingMessage) -> None:
        """
        Handle stage completion and determine next stage.

        Args:
            message (ProcessingMessage): Message containing stage completion details
                Expected content:
                - pipeline_id: str
                - stage: str (the completed stage)
                - results: Dict[str, Any] (stage results)
                - metrics: Optional[Dict[str, Any]] (stage metrics)
        """
        try:
            pipeline_id = message.content['pipeline_id']
            completed_stage = ProcessingStage(message.content['stage'])
            stage_results = message.content.get('results', {})
            stage_metrics = message.content.get('metrics', {})

            context = self.active_contexts.get(pipeline_id)
            if not context:
                logger.error(f"No active context found for pipeline {pipeline_id}")
                return

            # Validate stage completion
            if not self._validate_stage_completion(context, completed_stage, stage_results):
                await self._handle_invalid_stage_completion(pipeline_id, completed_stage)
                return

            # Update context with stage completion
            context.complete_stage(completed_stage.value)

            # Update metrics
            if stage_metrics:
                context.update_metrics({
                    f'stage_{completed_stage.value}_metrics': stage_metrics,
                    f'stage_{completed_stage.value}_duration': stage_metrics.get('duration', 0)
                })

            # Calculate and update overall progress
            self._update_pipeline_progress(context, completed_stage)

            # Check if any post-stage validations are needed
            validation_result = await self._perform_post_stage_validation(pipeline_id, completed_stage, stage_results)
            if not validation_result.get('passed', True):
                await self._handle_validation_failure(pipeline_id, validation_result)
                return

            # Determine and initiate next stage
            next_stage = self._get_next_stage(context, completed_stage)
            if next_stage:
                stage_config = context.stage_configs.get(next_stage.value, {})

                # Check if we can proceed to next stage
                if context.can_proceed_to_stage(next_stage):
                    logger.info(f"Pipeline {pipeline_id}: Proceeding to stage {next_stage.value}")
                    await self._initiate_stage(pipeline_id, next_stage, stage_results)
                else:
                    logger.warning(
                        f"Pipeline {pipeline_id}: Cannot proceed to {next_stage.value}, dependencies not met")
                    await self._handle_dependency_failure(pipeline_id, next_stage)
            else:
                # This was the final stage
                logger.info(f"Pipeline {pipeline_id}: All stages completed")
                await self._complete_pipeline(pipeline_id)

            # Notify about stage completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STAGE_COMPLETE_NOTIFY,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': completed_stage.value,
                        'next_stage': next_stage.value if next_stage else None,
                        'progress': context.progress,
                        'metrics': stage_metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        domain_type="pipeline",
                        processing_stage=completed_stage
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Error handling stage completion: {str(e)}")
            await self._handle_error(message, f"Stage completion error: {str(e)}")

    def _validate_stage_completion(self, context: PipelineContext, completed_stage: ProcessingStage,
                                   results: Dict[str, Any]) -> bool:
        """
        Validate stage completion integrity.

        Args:
            context (PipelineContext): Current pipeline context
            completed_stage (ProcessingStage): Stage that completed
            results (Dict[str, Any]): Stage results

        Returns:
            bool: Whether the stage completion is valid
        """
        try:
            # Check if stage is in pipeline sequence
            if completed_stage not in context.stage_sequence:
                logger.error(f"Completed stage {completed_stage} not in pipeline sequence")
                return False

            # Check if stage was actually the current stage
            if context.current_stage and context.current_stage.stage_type != completed_stage:
                logger.error(
                    f"Completed stage {completed_stage} doesn't match current stage {context.current_stage.stage_type}")
                return False

            # Check for required results based on stage type
            required_results = self._get_required_results(completed_stage)
            missing_results = [key for key in required_results if key not in results]
            if missing_results:
                logger.error(f"Missing required results for stage {completed_stage}: {missing_results}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating stage completion: {str(e)}")
            return False

    def _get_required_results(self, stage: ProcessingStage) -> List[str]:
        """Get required result keys for a stage"""
        stage_requirements = {
            ProcessingStage.QUALITY_CHECK: ['quality_score', 'issues'],
            ProcessingStage.INSIGHT_GENERATION: ['insights'],
            ProcessingStage.ADVANCED_ANALYTICS: ['analysis_results'],
            ProcessingStage.DECISION_MAKING: ['decisions'],
            ProcessingStage.RECOMMENDATION: ['recommendations'],
            ProcessingStage.REPORT_GENERATION: ['report']
        }
        return stage_requirements.get(stage, [])

    def _update_pipeline_progress(self, context: PipelineContext, completed_stage: ProcessingStage) -> None:
        """
        Update pipeline progress after stage completion.

        Args:
            context (PipelineContext): Current pipeline context
            completed_stage (ProcessingStage): Stage that completed
        """
        try:
            # Calculate stage weight (can be customized based on stage complexity)
            total_stages = len(context.stage_sequence)
            stage_weight = 1.0 / total_stages

            # Calculate completed stages progress
            completed_count = len(context.stages_completed) + 1  # +1 for current completion
            base_progress = (completed_count / total_stages) * 100

            # Update progress in context
            context.progress['overall'] = min(base_progress, 100.0)
            context.progress[completed_stage.value] = 100.0

            # Update stage-specific progress metric
            context.update_metrics({
                'progress': context.progress['overall'],
                f'stage_{completed_stage.value}_completed': datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error updating pipeline progress: {str(e)}")

    async def _handle_invalid_stage_completion(self, pipeline_id: str, stage: ProcessingStage) -> None:
        """Handle invalid stage completion"""
        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return

            error_details = {
                'type': 'invalid_stage_completion',
                'stage': stage.value,
                'current_stage': context.current_stage.stage_type.value if context.current_stage else None,
                'pipeline_state': context.state.value
            }

            # Add error to context
            context.add_error(stage.value, "Invalid stage completion", error_details)

            # Notify about error
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_ERROR_NOTIFY,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error_details,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Error handling invalid stage completion: {str(e)}")

    async def _perform_post_stage_validation(
            self,
            pipeline_id: str,
            completed_stage: ProcessingStage,
            results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform additional validations after stage completion.

        Returns:
            Dict[str, Any]: Validation results with at least {'passed': bool}
        """
        validation_result = {'passed': True, 'checks': []}

        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                return {'passed': False, 'error': 'No context found'}

            # Perform stage-specific validations
            if completed_stage == ProcessingStage.QUALITY_CHECK:
                validation_result = self._validate_quality_results(results)
            elif completed_stage == ProcessingStage.INSIGHT_GENERATION:
                validation_result = self._validate_insight_results(results)
            elif completed_stage == ProcessingStage.ADVANCED_ANALYTICS:
                validation_result = self._validate_analytics_results(results)

        except Exception as e:
            logger.error(f"Error in post-stage validation: {str(e)}")
            validation_result = {'passed': False, 'error': str(e)}

        return validation_result

    def _validate_quality_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Validate quality check results"""
        validation = {'passed': True, 'checks': []}

        # Check quality score
        quality_score = results.get('quality_score', 0)
        if quality_score < 0 or quality_score > 100:
            validation['passed'] = False
            validation['checks'].append({
                'check': 'quality_score_range',
                'passed': False,
                'message': f"Quality score {quality_score} out of valid range [0-100]"
            })

        # Validate issues structure
        issues = results.get('issues', [])
        if not isinstance(issues, list):
            validation['passed'] = False
            validation['checks'].append({
                'check': 'issues_format',
                'passed': False,
                'message': "Issues must be a list"
            })

        return validation

    def _get_stage_sequence(self, config: Dict[str, Any]) -> List[ProcessingStage]:
        """Get configured stage sequence"""
        default_sequence = [
            ProcessingStage.QUALITY_CHECK,
            ProcessingStage.INSIGHT_GENERATION,
            ProcessingStage.ADVANCED_ANALYTICS,
            ProcessingStage.DECISION_MAKING,
            ProcessingStage.RECOMMENDATION,
            ProcessingStage.REPORT_GENERATION
        ]

        if 'stage_sequence' not in config:
            return default_sequence

        # Validate and convert configured sequence
        try:
            return [ProcessingStage(stage) for stage in config['stage_sequence']]
        except ValueError as e:
            logger.error(f"Invalid stage in configuration: {e}")
            return default_sequence

    def _get_stage_dependencies(self) -> Dict[str, List[str]]:
        """Get stage dependencies mapping"""
        return {
            ProcessingStage.INSIGHT_GENERATION.value: [ProcessingStage.QUALITY_CHECK.value],
            ProcessingStage.ADVANCED_ANALYTICS.value: [ProcessingStage.QUALITY_CHECK.value],
            ProcessingStage.DECISION_MAKING.value: [
                ProcessingStage.INSIGHT_GENERATION.value,
                ProcessingStage.ADVANCED_ANALYTICS.value
            ],
            ProcessingStage.RECOMMENDATION.value: [ProcessingStage.DECISION_MAKING.value],
            ProcessingStage.REPORT_GENERATION.value: [ProcessingStage.RECOMMENDATION.value]
        }

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            # Stop all active pipelines
            for pipeline_id in list(self.active_contexts.keys()):
                context = self.active_contexts[pipeline_id]

                # Stop monitoring
                await self._stop_monitoring(pipeline_id)

                # Mark as cancelled
                context.state = PipelineState.CANCELLED
                context.completed_at = datetime.now()

                # Cleanup resources
                await self._cleanup_pipeline(pipeline_id)

            logger.info("Pipeline service cleanup completed successfully")

        except Exception as e:
            logger.error(f"Service cleanup failed: {str(e)}")
            raise
