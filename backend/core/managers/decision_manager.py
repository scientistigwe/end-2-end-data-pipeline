import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    DecisionContext,
    DecisionState,
    MessageMetadata,
    ManagerState
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class DecisionManager(BaseManager):
    """
    Decision Manager coordinates decision workflow through message-based communication.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str = "decision_manager",
            domain_type: str = "decision"
    ):
        # Call base class initialization first
        super().__init__(
            message_broker=message_broker,
            component_name=component_name,
            domain_type=domain_type
        )

        # Active processes and contexts
        self.active_processes: Dict[str, DecisionContext] = {}

        # Decision thresholds and configuration
        self.decision_thresholds = {
            "confidence_threshold": 0.8,
            "impact_threshold": 0.7,
            "max_processing_time": 3600  # 1 hour
        }

    async def start(self) -> None:
        """Initialize and start the manager"""
        try:
            # Initialize base components
            await super().start()

            # Setup decision-specific message handlers
            await self._setup_domain_handlers()

            # Start decision-specific monitoring
            self._start_background_task(
                self._monitor_decision_quality(),
                "decision_quality_monitor"
            )

            self.logger.info(f"Decision manager started successfully: {self.context.component_name}")

        except Exception as e:
            self.logger.error(f"Failed to start decision manager: {str(e)}")
            self.state = ManagerState.ERROR
            raise

    async def _setup_domain_handlers(self) -> None:
        """Setup decision-specific message handlers"""
        handlers = {
            # Core Process Flow
            MessageType.DECISION_PROCESS_START: self._handle_process_start,
            MessageType.DECISION_PROCESS_PROGRESS: self._handle_process_progress,
            MessageType.DECISION_PROCESS_COMPLETE: self._handle_process_complete,
            MessageType.DECISION_PROCESS_FAILED: self._handle_process_failed,

            # Context Analysis
            MessageType.DECISION_CONTEXT_ANALYZE_REQUEST: self._handle_context_analysis,
            MessageType.DECISION_CONTEXT_ANALYZE_PROGRESS: self._handle_context_progress,
            MessageType.DECISION_CONTEXT_ANALYZE_COMPLETE: self._handle_context_complete,
            MessageType.DECISION_CONTEXT_ANALYZE_FAILED: self._handle_context_failed,

            # Option Management
            MessageType.DECISION_OPTIONS_GENERATE_REQUEST: self._handle_options_generate,
            MessageType.DECISION_OPTIONS_GENERATE_PROGRESS: self._handle_options_progress,
            MessageType.DECISION_OPTIONS_UPDATE: self._handle_options_update,
            MessageType.DECISION_OPTIONS_PRIORITIZE: self._handle_options_prioritize,

            # Validation Flow
            MessageType.DECISION_VALIDATE_REQUEST: self._handle_validate_request,
            MessageType.DECISION_VALIDATE_PROGRESS: self._handle_validate_progress,
            MessageType.DECISION_VALIDATE_COMPLETE: self._handle_validate_complete,
            MessageType.DECISION_VALIDATE_REJECT: self._handle_validate_reject,
            MessageType.DECISION_VALIDATE_RETRY: self._handle_validate_retry,

            # Impact Assessment
            MessageType.DECISION_IMPACT_ASSESS_REQUEST: self._handle_impact_assess_request,
            MessageType.DECISION_IMPACT_ASSESS_PROGRESS: self._handle_impact_progress,
            MessageType.DECISION_IMPACT_ASSESS_COMPLETE: self._handle_impact_complete,
            MessageType.DECISION_IMPACT_SIMULATE: self._handle_impact_simulate,

            # Component Communication
            MessageType.DECISION_COMPONENT_REQUEST: self._handle_component_request,
            MessageType.DECISION_COMPONENT_RESPONSE: self._handle_component_response,
            MessageType.DECISION_COMPONENT_TIMEOUT: self._handle_component_timeout,
            MessageType.DECISION_COMPONENT_UPDATE: self._handle_component_update,
            MessageType.DECISION_COMPONENT_NOTIFY: self._handle_component_notify,

            # Resource Management
            MessageType.DECISION_RESOURCE_REQUEST: self._handle_resource_request,
            MessageType.DECISION_RESOURCE_ALLOCATE: self._handle_resource_allocate,
            MessageType.DECISION_RESOURCE_RELEASE: self._handle_resource_release,
            MessageType.DECISION_RESOURCE_EXCEEDED: self._handle_resource_exceeded,

            # Feedback and Updates
            MessageType.DECISION_FEEDBACK_PROCESS: self._handle_feedback_process,
            MessageType.DECISION_POLICY_VALIDATE: self._handle_policy_validate,
            MessageType.DECISION_STATUS_UPDATE: self._handle_status_update
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

    async def _handle_process_complete(self, message: ProcessingMessage) -> None:
        """Handle successful completion of the decision process"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Get final decision details
            final_decision = message.content.get('decision', {})
            completion_time = message.content.get('completion_time')

            # Update context state
            context.state = DecisionState.COMPLETED
            context.completed_at = datetime.now()
            context.final_decision = final_decision

            # Record completion metrics
            completion_metrics = {
                'total_processing_time': (context.completed_at - context.created_at).total_seconds(),
                'options_evaluated': len(context.available_options),
                'final_confidence_score': self._calculate_confidence_score(context),
                'validation_success': bool(context.validation_results.get('success')),
                'impact_assessment_completed': bool(context.impact_assessment)
            }

            # Notify about completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'final_decision': final_decision,
                        'completion_metrics': completion_metrics,
                        'completion_time': completion_time or context.completed_at.isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="control_point_manager",
                        domain_type="decision"
                    )
                )
            )

            # Release resources
            for resource_type in context.resource_usage:
                await self._release_resources(pipeline_id, resource_type)

            # Archive process data if needed
            await self._archive_process_data(pipeline_id, completion_metrics)

            # Cleanup process
            await self._cleanup_process(pipeline_id)

            logger.info(f"Decision process completed successfully for pipeline: {pipeline_id}")

        except Exception as e:
            logger.error(f"Process completion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_process_failed(self, message: ProcessingMessage) -> None:
        """Handle failure of the decision process"""
        pipeline_id = message.content.get('pipeline_id')
        error = message.content.get('error', 'Unknown error occurred')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = DecisionState.FAILED
            context.error = error
            context.failed_at = datetime.now()

            # Collect failure details
            failure_details = {
                'error_message': error,
                'failed_stage': context.state.value,
                'failure_time': context.failed_at.isoformat(),
                'processing_duration': (context.failed_at - context.created_at).total_seconds(),
                'component_states': context.component_states,
                'last_successful_stage': context.last_successful_stage,
                'validation_status': context.validation_results.get('status'),
                'retry_count': context.retry_count
            }

            # Check for specific failure conditions
            if 'timeout' in error.lower():
                failure_details['timeout_components'] = context.timeout_components

            if 'resource' in error.lower():
                failure_details['resource_state'] = context.resource_usage

            # Notify about failure
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'failure_details': failure_details,
                        'recovery_possible': self._is_recovery_possible(context)
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="control_point_manager",
                        domain_type="decision"
                    )
                )
            )

            # Attempt recovery if possible
            if self._is_recovery_possible(context):
                await self._attempt_process_recovery(pipeline_id)
            else:
                # Release all resources
                for resource_type in context.resource_usage:
                    await self._release_resources(pipeline_id, resource_type)

                # Log failure
                await self._log_process_failure(pipeline_id, failure_details)

                # Cleanup process
                await self._cleanup_process(pipeline_id)

            logger.error(f"Decision process failed for pipeline: {pipeline_id}, Error: {error}")

        except Exception as e:
            logger.error(f"Process failure handling failed: {str(e)}")
            # Ensure cleanup still happens
            await self._cleanup_process(pipeline_id)

    async def _archive_process_data(
            self,
            pipeline_id: str,
            completion_metrics: Dict[str, Any]
    ) -> None:
        """Archive process data for completed decisions"""
        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            archive_data = {
                'pipeline_id': pipeline_id,
                'correlation_id': context.correlation_id,
                'process_metrics': completion_metrics,
                'final_decision': context.final_decision,
                'processing_history': context.processing_history,
                'validation_results': context.validation_results,
                'impact_assessment': context.impact_assessment,
                'resource_usage': context.resource_usage,
                'completed_at': context.completed_at.isoformat(),
                'created_at': context.created_at.isoformat()
            }

            # Archive data (implementation would depend on storage backend)
            logger.info(f"Archived process data for pipeline: {pipeline_id}")

        except Exception as e:
            logger.error(f"Process data archival failed: {str(e)}")

    def _is_recovery_possible(self, context: DecisionContext) -> bool:
        """Determine if process recovery is possible"""
        try:
            # Check retry count
            if context.retry_count >= context.config.get('max_retries', 3):
                return False

            # Check error type
            if context.error and any(
                    fatal_error in context.error.lower()
                    for fatal_error in ['critical', 'fatal', 'unrecoverable']
            ):
                return False

            # Check resource state
            if any(
                    usage > 0.95 for usage in context.resource_usage.values()
            ):
                return False

            # Check if in a recoverable state
            recoverable_states = {
                DecisionState.CONTEXT_ANALYSIS,
                DecisionState.OPTION_GENERATION,
                DecisionState.VALIDATION,
                DecisionState.IMPACT_ANALYSIS
            }
            return context.state in recoverable_states

        except Exception as e:
            logger.error(f"Recovery possibility check failed: {str(e)}")
            return False

    async def _attempt_process_recovery(self, pipeline_id: str) -> None:
        """Attempt to recover failed process"""
        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Increment retry count
            context.retry_count += 1

            # Reset error state
            context.error = None
            context.failed_at = None

            # Determine recovery point
            recovery_stage = self._determine_recovery_stage(context)

            # Reset stage-specific data
            await self._reset_stage_data(context, recovery_stage)

            # Restart from recovery point
            await self._initiate_stage(pipeline_id, recovery_stage)

            logger.info(f"Initiated recovery for pipeline {pipeline_id} at stage {recovery_stage}")

        except Exception as e:
            logger.error(f"Process recovery attempt failed: {str(e)}")
            await self._handle_process_failed(ProcessingMessage(
                message_type=MessageType.DECISION_PROCESS_FAILED,
                content={
                    'pipeline_id': pipeline_id,
                    'error': f"Recovery failed: {str(e)}"
                }
            ))

    async def _log_process_failure(
            self,
            pipeline_id: str,
            failure_details: Dict[str, Any]
    ) -> None:
        """Log process failure details"""
        try:
            # Log to system logger
            logger.error(
                f"Decision process failure - Pipeline: {pipeline_id}, "
                f"Details: {failure_details}"
            )

            # Could implement additional logging to external systems here

        except Exception as e:
            logger.error(f"Failure logging failed: {str(e)}")

    def _determine_recovery_stage(self, context: DecisionContext) -> DecisionState:
        """Determine appropriate stage for recovery"""
        # Default to last successful stage if available
        if context.last_successful_stage:
            return context.last_successful_stage

        # Otherwise, determine based on current state
        recovery_points = {
            DecisionState.IMPACT_ANALYSIS: DecisionState.VALIDATION,
            DecisionState.VALIDATION: DecisionState.OPTION_GENERATION,
            DecisionState.OPTION_GENERATION: DecisionState.CONTEXT_ANALYSIS,
            DecisionState.CONTEXT_ANALYSIS: DecisionState.INITIALIZING
        }

        return recovery_points.get(context.state, DecisionState.INITIALIZING)

    async def _reset_stage_data(
            self,
            context: DecisionContext,
            recovery_stage: DecisionState
    ) -> None:
        """Reset stage-specific data for recovery"""
        # Reset data based on recovery stage
        if recovery_stage <= DecisionState.CONTEXT_ANALYSIS:
            context.context_analysis_results = {}

        if recovery_stage <= DecisionState.OPTION_GENERATION:
            context.available_options = []

        if recovery_stage <= DecisionState.VALIDATION:
            context.validation_results = {}

        if recovery_stage <= DecisionState.IMPACT_ANALYSIS:
            context.impact_assessment = {}

    async def _handle_validate_request(self, message: ProcessingMessage) -> None:
        """Handle request to validate decision options"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = DecisionState.VALIDATION
            context.updated_at = datetime.now()

            validation_config = message.content.get('validation_config', {})
            options = context.available_options

            # Request validation of options
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_VALIDATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'options': options,
                        'validation_config': validation_config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="validation_service",
                        domain_type="decision"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Validation request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validate_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of validation process"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            validation_results = message.content.get('validation_results', {})

            # Store validation results
            context.validation_results = validation_results
            context.updated_at = datetime.now()

            # Check validation outcome
            if self._check_validation_success(validation_results):
                # Proceed to impact analysis
                await self._start_impact_analysis(pipeline_id)
            else:
                # Handle validation failure
                await self._handle_validation_failure(
                    pipeline_id,
                    validation_results
                )

        except Exception as e:
            logger.error(f"Validation completion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

        def _check_validation_success(self, validation_results: Dict[str, Any]) -> bool:
            """Check if validation was successful"""
            try:
                # Check overall validation status
                if not validation_results.get('status') == 'success':
                    return False

                # Check validation metrics
                validation_score = validation_results.get('validation_score', 0.0)
                min_score = self.decision_thresholds.get('validation_threshold', 0.7)

                return validation_score >= min_score

            except Exception as e:
                logger.error(f"Validation success check failed: {str(e)}")
                return False

    async def _handle_validate_reject(self, message: ProcessingMessage) -> None:
        """Handle validation rejection"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            rejection_reason = message.content.get('reason', 'No reason provided')
            rejection_details = message.content.get('details', {})

            # Update context
            context.validation_results['rejected'] = True
            context.validation_results['rejection_reason'] = rejection_reason
            context.validation_results['rejection_details'] = rejection_details
            context.updated_at = datetime.now()

            # Check for retry possibility
            if context.retry_count < context.config.get('max_validation_retries', 3):
                await self._handle_validate_retry(pipeline_id)
            else:
                # If max retries exceeded, fail the process
                await self._handle_process_failed(
                    ProcessingMessage(
                        message_type=MessageType.DECISION_PROCESS_FAILED,
                        content={
                            'pipeline_id': pipeline_id,
                            'error': f"Validation rejected: {rejection_reason}",
                            'details': rejection_details
                        },
                        metadata=MessageMetadata(
                            correlation_id=context.correlation_id,
                            source_component=self.context.component_name,
                            target_component="control_point_manager",
                            domain_type="decision"
                        )
                    )
                )

        except Exception as e:
            logger.error(f"Validation rejection handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_impact_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of impact assessment"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            impact_results = message.content.get('impact_results', {})

            # Store impact assessment results
            context.impact_assessment = impact_results
            context.updated_at = datetime.now()

            # Validate impact results
            if self._validate_impact_results(impact_results):
                # Generate final decision based on impact assessment
                final_decision = self._generate_final_decision(context)

                # Update context with final decision
                context.final_decision = final_decision

                # Complete the decision process
                await self._complete_decision(pipeline_id)
            else:
                # Handle invalid impact results
                await self._handle_impact_validation_failed(pipeline_id, impact_results)

        except Exception as e:
            logger.error(f"Impact completion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

        def _validate_impact_results(self, impact_results: Dict[str, Any]) -> bool:
            """Validate impact assessment results"""
            try:
                # Check for required fields
                required_fields = {'impact_scores', 'confidence_scores', 'risk_assessment'}
                if not all(field in impact_results for field in required_fields):
                    return False

                # Check impact thresholds
                impact_threshold = self.decision_thresholds.get('impact_threshold', 0.7)
                if impact_results.get('overall_impact_score', 0.0) < impact_threshold:
                    return False

                # Check confidence scores
                min_confidence = self.decision_thresholds.get('minimum_confidence', 0.7)
                confidence_scores = impact_results.get('confidence_scores', {})
                if any(score < min_confidence for score in confidence_scores.values()):
                    return False

                return True

            except Exception as e:
                logger.error(f"Impact results validation failed: {str(e)}")
                return False

        async def _handle_impact_validation_failed(self, pipeline_id: str, impact_results: Dict[str, Any]) -> None:
            """Handle failure in impact validation"""
            try:
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.DECISION_PROCESS_FAILED,
                        content={
                            'pipeline_id': pipeline_id,
                            'error': "Impact validation failed",
                            'impact_results': impact_results,
                            'validation_details': {
                                'threshold': self.decision_thresholds.get('impact_threshold'),
                                'actual_score': impact_results.get('overall_impact_score')
                            }
                        },
                        metadata=MessageMetadata(
                            correlation_id=self.active_processes[pipeline_id].correlation_id,
                            source_component=self.context.component_name,
                            target_component="control_point_manager",
                            domain_type="decision"
                        )
                    )
                )
            except Exception as e:
                logger.error(f"Impact validation failure handling failed: {str(e)}")
                await self._handle_error(pipeline_id, str(e))

    async def _handle_non_critical_timeout(self, pipeline_id: str, component: str) -> None:
        """Handle non-critical component timeout"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Log timeout
            logger.warning(f"Non-critical timeout for component {component} in pipeline {pipeline_id}")

            # Retry component request
            await self._retry_component_request(pipeline_id, component)

        except Exception as e:
            logger.error(f"Non-critical timeout handling failed: {str(e)}")

    async def _check_component_states(self, pipeline_id: str) -> None:
        """Check states of all components"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Check if any components are in error state
            error_components = [
                comp for comp, state in context.component_states.items()
                if state.get('status') == 'error'
            ]

            if error_components:
                await self._handle_component_errors(pipeline_id, error_components)

        except Exception as e:
            logger.error(f"Component state check failed: {str(e)}")

    async def _process_component_request(
            self,
            component: str,
            request_type: str,
            params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process request to a specific component"""
        try:
            # Process based on request type
            processors = {
                'status': self._process_status_request,
                'data': self._process_data_request,
                'config': self._process_config_request
            }

            processor = processors.get(request_type)
            if processor:
                return await processor(component, params)

            raise ValueError(f"Unknown request type: {request_type}")

        except Exception as e:
            logger.error(f"Component request processing failed: {str(e)}")
            return {'error': str(e)}

    def _check_required_responses(self, context: DecisionContext) -> bool:
        """Check if all required component responses received"""
        required_components = {
            DecisionState.CONTEXT_ANALYSIS: {'context_analyzer'},
            DecisionState.OPTION_GENERATION: {'option_generator'},
            DecisionState.VALIDATION: {'validator'},
            DecisionState.IMPACT_ANALYSIS: {'impact_assessor'}
        }

        needed = required_components.get(context.state, set())
        received = set(context.component_responses.keys())

        return needed.issubset(received)

    async def _process_component_notification(
            self,
            pipeline_id: str,
            notification_type: str,
            notification_data: Dict[str, Any]
    ) -> None:
        """Process notification from component"""
        try:
            handlers = {
                'status_change': self._handle_status_notification,
                'resource_warning': self._handle_resource_notification,
                'error': self._handle_error_notification
            }

            handler = handlers.get(notification_type)
            if handler:
                await handler(pipeline_id, notification_data)

        except Exception as e:
            logger.error(f"Notification processing failed: {str(e)}")

    async def _process_status_update(self, pipeline_id: str, update_type: str) -> None:
        """Process specific status update"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Handle different types of status updates
            handlers = {
                'progress': self._handle_progress_update,
                'state_change': self._handle_state_change,
                'completion': self._handle_completion_update
            }

            handler = handlers.get(update_type)
            if handler:
                await handler(context)

        except Exception as e:
            logger.error(f"Status update processing failed: {str(e)}")

    async def _allocate_resources(self, pipeline_id: str, resource_type: str, amount: float) -> Dict[str, Any]:
        """Allocate resources for decision process"""
        try:
            # Use base resource check
            metrics = await self._collect_resource_metrics()
            if not await self._check_resource_limits(metrics):
                return {'success': False, 'reason': f"Resource limits exceeded"}

            # Decision-specific allocation logic
            allocation_result = await self._perform_resource_allocation(
                pipeline_id,
                resource_type,
                amount
            )
            return allocation_result
        except Exception as e:
            self.logger.error(f"Resource allocation failed: {str(e)}")
            return {'success': False, 'reason': str(e)}

    async def _release_resources(self, pipeline_id: str, resource_type: str) -> None:
        """Release allocated resources"""
        try:
            await self._perform_resource_release(pipeline_id, resource_type)
            logger.info(f"Released {resource_type} resources for pipeline {pipeline_id}")

        except Exception as e:
            logger.error(f"Resource release failed: {str(e)}")

    async def _handle_resource_allocation_failed(
            self,
            pipeline_id: str,
            resource_type: str,
            reason: str
    ) -> None:
        """Handle resource allocation failure"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Update context
            context.resource_allocation_failures.append({
                'resource_type': resource_type,
                'reason': reason,
                'timestamp': datetime.now().isoformat()
            })

            # Notify failure
            await self._notify_resource_failure(pipeline_id, resource_type, reason)

        except Exception as e:
            logger.error(f"Resource allocation failure handling failed: {str(e)}")

    async def _reduce_memory_usage(self, context: DecisionContext) -> None:
        """Implement memory usage reduction"""
        try:
            # Clear caches
            context.clear_caches()

            # Reduce stored data
            context.trim_history()

            # Request garbage collection
            import gc
            gc.collect()

        except Exception as e:
            logger.error(f"Memory reduction failed: {str(e)}")

    async def _reduce_cpu_usage(self, context: DecisionContext) -> None:
        """Implement CPU usage reduction"""
        try:
            # Reduce processing priority
            context.reduce_processing_priority()

            # Delay non-critical tasks
            context.defer_background_tasks()

        except Exception as e:
            logger.error(f"CPU reduction failed: {str(e)}")

    async def _reduce_storage_usage(self, context: DecisionContext) -> None:
        """Implement storage usage reduction"""
        try:
            # Clean up temporary files
            await context.cleanup_temp_files()

            # Compress stored data
            await context.compress_stored_data()

        except Exception as e:
            logger.error(f"Storage reduction failed: {str(e)}")

    def _validate_options(self, options: List[Dict[str, Any]]) -> bool:
        """Validate generated options"""
        try:
            if not options:
                return False

            required_fields = {'id', 'description', 'impact_factors'}
            return all(
                all(field in option for field in required_fields)
                for option in options
            )

        except Exception as e:
            logger.error(f"Options validation failed: {str(e)}")
            return False

    async def _handle_options_invalid(self, pipeline_id: str) -> None:
        """Handle invalid options case"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Notify about invalid options
            await self._notify_invalid_options(pipeline_id)

            # Retry option generation if possible
            if context.retry_count < context.config.get('max_retries', 3):
                context.retry_count += 1
                await self._handle_options_generate(pipeline_id)
            else:
                await self._handle_process_failed(ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': 'Failed to generate valid options'
                    }
                ))

        except Exception as e:
            logger.error(f"Invalid options handling failed: {str(e)}")

    def _prioritize_options(
            self,
            options: List[Dict[str, Any]],
            criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Prioritize options based on criteria"""
        try:
            weighted_scores = {}
            for option in options:
                score = sum(
                    criteria.get(factor, 1.0) * option.get(factor, 0.0)
                    for factor in criteria
                )
                weighted_scores[option['id']] = score

            return sorted(
                options,
                key=lambda x: weighted_scores.get(x['id'], 0),
                reverse=True
            )

        except Exception as e:
            logger.error(f"Options prioritization failed: {str(e)}")
            return options

    async def _handle_context_failed(self, message: ProcessingMessage) -> None:
        """Handle context analysis failure"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            error = message.content.get('error', 'Unknown error in context analysis')

            # Update context state
            context.state = DecisionState.FAILED
            context.error = error

            # Notify failure
            await self._notify_context_failure(pipeline_id, error)

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Context failure handling failed: {str(e)}")

    async def _simulate_impact(
            self,
            options: List[Dict[str, Any]],
            params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Simulate impact of options"""
        try:
            simulation_results = {}
            for option in options:
                result = await self._run_impact_simulation(option, params)
                simulation_results[option['id']] = result

            return simulation_results

        except Exception as e:
            logger.error(f"Impact simulation failed: {str(e)}")
            return {}

    async def _handle_validate_retry(self, pipeline_id: str) -> None:
        """Handle validation retry request"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Reset validation state
            context.validation_results = {}

            # Start validation again
            await self._start_validation(pipeline_id)

        except Exception as e:
            logger.error(f"Validation retry failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_policy_validate(self, message: ProcessingMessage) -> None:
        """Handle policy validation request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            policy = message.content.get('policy', {})
            validation_result = await self._validate_against_policy(
                context.available_options,
                policy
            )

            if validation_result['valid']:
                await self._proceed_to_next_stage(pipeline_id)
            else:
                await self._handle_policy_violation(
                    pipeline_id,
                    validation_result['violations']
                )

        except Exception as e:
            logger.error(f"Policy validation failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_resource_request(self, message: ProcessingMessage) -> None:
        """Handle resource request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            resource_type = message.content.get('resource_type')
            amount = message.content.get('amount')

            allocation_result = await self._allocate_resources(
                pipeline_id,
                resource_type,
                amount
            )

            if allocation_result['success']:
                await self._notify_resource_allocated(pipeline_id, resource_type, amount)
            else:
                await self._handle_resource_allocation_failed(
                    pipeline_id,
                    resource_type,
                    allocation_result['reason']
                )

        except Exception as e:
            logger.error(f"Resource request handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _start_validation(self, pipeline_id: str) -> None:
        """Start validation process for decisions"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_VALIDATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'options': context.available_options,
                        'config': context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="decision_service",
                        domain_type="decision"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Failed to start validation: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _start_impact_analysis(self, pipeline_id: str) -> None:
        """Start impact analysis for selected options"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_IMPACT_ASSESS_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'options': context.available_options,
                        'validation_results': context.validation_results
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="decision_service",
                        domain_type="decision"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Failed to start impact analysis: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _request_decision_adjustment(self, pipeline_id: str, feedback: Dict[str, Any]) -> None:
        """Request adjustment based on feedback"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_OPTIONS_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'feedback': feedback,
                        'current_options': context.available_options
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="decision_service",
                        domain_type="decision"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Failed to request decision adjustment: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _initiate_stage(self, pipeline_id: str, stage: DecisionState) -> None:
        """Initiate specific decision stage"""
        stage_handlers = {
            DecisionState.CONTEXT_ANALYSIS: self._handle_context_analysis,
            DecisionState.OPTION_GENERATION: self._handle_options_generate,
            DecisionState.VALIDATION: self._start_validation,
            DecisionState.IMPACT_ANALYSIS: self._start_impact_analysis
        }

        handler = stage_handlers.get(stage)
        if handler:
            try:
                await handler(pipeline_id)
            except Exception as e:
                logger.error(f"Failed to initiate stage {stage}: {str(e)}")
                await self._handle_error(pipeline_id, str(e))

    async def _handle_validation_failure(self, pipeline_id: str, validation_results: Dict[str, Any]) -> None:
        """Handle validation failure"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Store validation results
            context.validation_results = validation_results

            # Check if retry is possible
            if context.retry_count < context.config.get('max_retries', 3):
                context.retry_count += 1
                await self._handle_validate_retry(pipeline_id)
            else:
                # Mark as failed if max retries exceeded
                await self._handle_process_failed(ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': 'Validation failed after maximum retries'
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="control_point_manager",
                        domain_type="decision"
                    )
                ))
        except Exception as e:
            logger.error(f"Failed to handle validation failure: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validation_rejection(self, pipeline_id: str, rejection_reason: str) -> None:
        """Handle validation rejection"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Update context with rejection
            context.validation_results['rejected'] = True
            context.validation_results['rejection_reason'] = rejection_reason

            # Notify rejection
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_VALIDATE_REJECT,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': rejection_reason,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="control_point_manager",
                        domain_type="decision"
                    )
                )
            )

            # Clean up process
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Failed to handle validation rejection: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_context_analysis(self, message: ProcessingMessage) -> None:
        """Handle context analysis for decision"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = DecisionState.CONTEXT_ANALYSIS
            context.updated_at = datetime.now()

            # Start context analysis
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_CONTEXT_ANALYZE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'data': context.metadata.get('context_data', {}),
                        'config': context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="decision_service",
                        domain_type="decision"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Context analysis failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_context_progress(self, message: ProcessingMessage) -> None:
        """Handle context analysis progress updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update progress
            progress = message.content.get('progress', 0)
            context.progress['context_analysis'] = progress

            # Forward progress update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'stage': 'context_analysis',
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=message.metadata
                )
            )

        except Exception as e:
            logger.error(f"Failed to handle context progress: {str(e)}")

    async def _handle_context_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of context analysis"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Store context analysis results
            context.context_analysis_results = message.content.get('results', {})

            # Proceed to option generation
            await self._proceed_to_next_stage(pipeline_id)

        except Exception as e:
            logger.error(f"Context completion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_process_progress(self, message: ProcessingMessage) -> None:
        """Handle overall process progress"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update progress
            stage = message.content.get('stage', '')
            progress = message.content.get('progress', 0)

            context.progress[stage] = progress
            context.updated_at = datetime.now()

            # Calculate overall progress
            total_progress = sum(context.progress.values()) / len(context.progress)

            # Forward progress update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'overall_progress': total_progress,
                        'stage_progress': {
                            'stage': stage,
                            'progress': progress
                        },
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=message.metadata
                )
            )

        except Exception as e:
            logger.error(f"Progress update failed: {str(e)}")

    async def _handle_component_timeout(self, message: ProcessingMessage) -> None:
        """Handle component timeout"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Record timeout
            component = message.content.get('component')
            if component:
                context.timeout_components.append(component)

            # Check if timeout is critical
            if self._is_critical_timeout(component, context):
                await self._handle_critical_timeout(pipeline_id, component)
            else:
                await self._handle_non_critical_timeout(pipeline_id, component)

        except Exception as e:
            logger.error(f"Timeout handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _is_critical_timeout(self, component: str, context: DecisionContext) -> bool:
        """Determine if timeout is critical"""
        critical_components = {
            'validation_service',
            'impact_assessment_service',
            'context_analysis_service'
        }
        return component in critical_components

    async def _handle_critical_timeout(self, pipeline_id: str, component: str) -> None:
        """Handle critical component timeout"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Mark process as failed
            context.state = DecisionState.FAILED

            # Notify about critical timeout
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': f"Critical component timeout: {component}",
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="control_point_manager",
                        domain_type="decision"
                    )
                )
            )

            # Clean up
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Critical timeout handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_resource_exceeded(self, message: ProcessingMessage) -> None:
        """Handle resource exceeded notification"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Get resource details
            resource_type = message.content.get('resource_type')
            current_usage = message.content.get('current_usage')

            # Update resource tracking
            context.resource_usage[resource_type] = current_usage

            # Check if we need to take action
            if self._should_reduce_resource_usage(resource_type, current_usage):
                await self._reduce_resource_usage(pipeline_id, resource_type)

        except Exception as e:
            logger.error(f"Resource exceeded handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _should_reduce_resource_usage(self, resource_type: str, usage: float) -> bool:
        """Determine if resource usage should be reduced"""
        thresholds = {
            'memory': 0.9,  # 90%
            'cpu': 0.85,  # 85%
            'storage': 0.95  # 95%
        }
        return usage > thresholds.get(resource_type, 0.8)

    async def _reduce_resource_usage(self, pipeline_id: str, resource_type: str) -> None:
        """Implement resource usage reduction strategies"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Implement resource-specific reduction strategies
            strategies = {
                'memory': self._reduce_memory_usage,
                'cpu': self._reduce_cpu_usage,
                'storage': self._reduce_storage_usage
            }

            strategy = strategies.get(resource_type)
            if strategy:
                await strategy(context)

        except Exception as e:
            logger.error(f"Resource reduction failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_options_progress(self, message: ProcessingMessage) -> None:
        """Handle progress updates for option generation"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            progress = message.content.get('progress', 0)
            context.progress['option_generation'] = progress

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_OPTIONS_GENERATE_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=message.metadata
                )
            )

        except Exception as e:
            logger.error(f"Options progress handling failed: {str(e)}")

    async def _handle_options_update(self, message: ProcessingMessage) -> None:
        """Handle updates to available options"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            new_options = message.content.get('options', [])
            context.available_options = new_options
            context.updated_at = datetime.now()

            # Check if options meet minimum criteria
            if self._validate_options(new_options):
                await self._proceed_to_next_stage(pipeline_id)
            else:
                await self._handle_options_invalid(pipeline_id)

        except Exception as e:
            logger.error(f"Options update failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_options_prioritize(self, message: ProcessingMessage) -> None:
        """Handle option prioritization request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            prioritization_criteria = message.content.get('criteria', {})
            context.available_options = self._prioritize_options(
                context.available_options,
                prioritization_criteria
            )

            await self._proceed_to_next_stage(pipeline_id)

        except Exception as e:
            logger.error(f"Options prioritization failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validate_progress(self, message: ProcessingMessage) -> None:
        """Handle validation progress updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            progress = message.content.get('progress', 0)
            context.progress['validation'] = progress

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_VALIDATE_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=message.metadata
                )
            )

        except Exception as e:
            logger.error(f"Validation progress handling failed: {str(e)}")

    async def _handle_impact_progress(self, message: ProcessingMessage) -> None:
        """Handle impact assessment progress updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            progress = message.content.get('progress', 0)
            context.progress['impact_assessment'] = progress

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_IMPACT_ASSESS_PROGRESS,
                    content={
                        'pipeline_id': pipeline_id,
                        'progress': progress,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=message.metadata
                )
            )

        except Exception as e:
            logger.error(f"Impact progress handling failed: {str(e)}")

    async def _handle_impact_simulate(self, message: ProcessingMessage) -> None:
        """Handle impact simulation request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            simulation_params = message.content.get('simulation_params', {})
            simulation_results = await self._simulate_impact(
                context.available_options,
                simulation_params
            )

            context.impact_assessment['simulation_results'] = simulation_results
            await self._proceed_to_next_stage(pipeline_id)

        except Exception as e:
            logger.error(f"Impact simulation failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_component_request(self, message: ProcessingMessage) -> None:
        """Handle component-specific requests"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            component = message.content.get('component')
            request_type = message.content.get('request_type')

            response = await self._process_component_request(
                component,
                request_type,
                message.content.get('params', {})
            )

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_COMPONENT_RESPONSE,
                    content={
                        'pipeline_id': pipeline_id,
                        'component': component,
                        'response': response,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=message.metadata
                )
            )

        except Exception as e:
            logger.error(f"Component request handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_component_response(self, message: ProcessingMessage) -> None:
        """Handle responses from components"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            component = message.content.get('component')
            response = message.content.get('response', {})

            context.component_responses[component] = response

            # Check if we have all required responses
            if self._check_required_responses(context):
                await self._proceed_to_next_stage(pipeline_id)

        except Exception as e:
            logger.error(f"Component response handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_component_update(self, message: ProcessingMessage) -> None:
        """Handle component status updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            component = message.content.get('component')
            status = message.content.get('status', {})

            context.component_states[component] = status
            await self._check_component_states(pipeline_id)

        except Exception as e:
            logger.error(f"Component update handling failed: {str(e)}")

    async def _handle_component_notify(self, message: ProcessingMessage) -> None:
        """Handle component notifications"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            notification_type = message.content.get('notification_type')
            notification_data = message.content.get('data', {})

            await self._process_component_notification(
                pipeline_id,
                notification_type,
                notification_data
            )

        except Exception as e:
            logger.error(f"Component notification handling failed: {str(e)}")

    async def _handle_status_update(self, message: ProcessingMessage) -> None:
        """Handle decision status updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            new_status = message.content.get('status')
            update_type = message.content.get('update_type')

            if new_status:
                context.status = new_status
                context.updated_at = datetime.now()

                # Handle specific status updates
                await self._process_status_update(pipeline_id, update_type)

        except Exception as e:
            logger.error(f"Status update handling failed: {str(e)}")

    async def _handle_resource_allocate(self, message: ProcessingMessage) -> None:
        """Handle resource allocation requests"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            resource_type = message.content.get('resource_type')
            amount = message.content.get('amount')

            allocation_result = await self._allocate_resources(
                pipeline_id,
                resource_type,
                amount
            )

            if allocation_result.get('success'):
                context.resource_usage[resource_type] = amount
            else:
                await self._handle_resource_allocation_failed(
                    pipeline_id,
                    resource_type,
                    allocation_result.get('reason')
                )

        except Exception as e:
            logger.error(f"Resource allocation failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_resource_release(self, message: ProcessingMessage) -> None:
        """Handle resource release requests"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            resource_type = message.content.get('resource_type')

            await self._release_resources(pipeline_id, resource_type)
            context.resource_usage.pop(resource_type, None)

        except Exception as e:
            logger.error(f"Resource release failed: {str(e)}")

    async def request_decision(
            self,
            pipeline_id: str,
            options: Dict[str, Any],
            config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Initiate a new decision request"""
        try:
            correlation_id = str(uuid.uuid4())

            # Create decision context
            context = DecisionContext(
                pipeline_id=pipeline_id,
                correlation_id=correlation_id,
                options=options,
                state=DecisionState.INITIALIZING,
                config=config or {},
                created_at=datetime.now()
            )

            self.active_processes[pipeline_id] = context

            # Start decision process
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'options': options,
                        'config': context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=correlation_id,
                        source_component=self.component_name,
                        target_component="decision_service",
                        domain_type="decision",
                        processing_stage=ProcessingStage.DECISION_MAKING
                    )
                )
            )

            logger.info(f"Decision request initiated for pipeline: {pipeline_id}")
            return correlation_id

        except Exception as e:
            logger.error(f"Failed to initiate decision request: {str(e)}")
            raise

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle decision process start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})

            # Validate configuration
            if not self._validate_decision_config(config):
                raise ValueError("Invalid decision configuration")

            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Start context analysis
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_CONTEXT_ANALYZE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="decision_service",
                        domain_type="decision"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Process start failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _validate_decision_config(self, config: Dict[str, Any]) -> bool:
        """Validate decision configuration"""
        try:
            required_fields = ['decision_type', 'constraints', 'requirements']
            if not all(field in config for field in required_fields):
                return False

            # Validate constraints
            if not self._validate_constraints(config['constraints']):
                return False

            return True

        except Exception as e:
            logger.error(f"Configuration validation failed: {str(e)}")
            return False

    def _validate_constraints(self, constraints: Dict[str, Any]) -> bool:
        """Validate decision constraints"""
        try:
            required_constraint_fields = ['business_rules', 'thresholds']
            return all(field in constraints for field in required_constraint_fields)
        except Exception as e:
            logger.error(f"Constraints validation failed: {str(e)}")
            return False

    async def _handle_options_generate(self, message: ProcessingMessage) -> None:
        """Handle options generation request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = DecisionState.OPTION_GENERATION
            context.updated_at = datetime.now()

            # Generate options
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_OPTIONS_GENERATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="decision_service",
                        domain_type="decision"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Options generation failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_impact_assess_request(self, message: ProcessingMessage) -> None:
        """Handle impact assessment request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = DecisionState.IMPACT_ANALYSIS
            context.updated_at = datetime.now()

            # Request impact assessment
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_IMPACT_ASSESS_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'options': context.available_options,
                        'validation_results': context.validation_results
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="decision_service",
                        domain_type="decision"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Impact assessment request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_feedback_process(self, message: ProcessingMessage) -> None:
        """Handle decision feedback"""
        pipeline_id = message.content.get('pipeline_id')
        feedback = message.content.get('feedback', {})
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Process feedback
            if self._validate_feedback(feedback):
                await self._incorporate_feedback(pipeline_id, feedback)
            else:
                raise ValueError("Invalid feedback format")

        except Exception as e:
            logger.error(f"Feedback processing failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _validate_feedback(self, feedback: Dict[str, Any]) -> bool:
        """Validate feedback format"""
        required_fields = ['feedback_type', 'content', 'source']
        return all(field in feedback for field in required_fields)

    async def _incorporate_feedback(self, pipeline_id: str, feedback: Dict[str, Any]) -> None:
        """Incorporate feedback into decision process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Update context with feedback
            context.feedback = feedback
            context.updated_at = datetime.now()

            # Check if feedback requires decision adjustment
            if feedback.get('requires_adjustment', False):
                await self._request_decision_adjustment(pipeline_id, feedback)
            else:
                await self._proceed_to_next_stage(pipeline_id)

        except Exception as e:
            logger.error(f"Feedback incorporation failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _proceed_to_next_stage(self, pipeline_id: str) -> None:
        """Proceed to next decision stage"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            next_stage = self._determine_next_stage(context)
            if next_stage:
                context.state = next_stage
                await self._initiate_stage(pipeline_id, next_stage)
            else:
                await self._complete_decision(pipeline_id)

        except Exception as e:
            logger.error(f"Stage progression failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _determine_next_stage(self, context: DecisionContext) -> Optional[DecisionState]:
        """Determine next processing stage"""
        stage_sequence = {
            DecisionState.INITIALIZING: DecisionState.CONTEXT_ANALYSIS,
            DecisionState.CONTEXT_ANALYSIS: DecisionState.OPTION_GENERATION,
            DecisionState.OPTION_GENERATION: DecisionState.VALIDATION,
            DecisionState.VALIDATION: DecisionState.IMPACT_ANALYSIS,
            DecisionState.IMPACT_ANALYSIS: None
        }
        return stage_sequence.get(context.state)

    async def _complete_decision(self, pipeline_id: str) -> None:
        """Complete decision process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Generate final decision
            final_decision = self._generate_final_decision(context)

            # Update context
            context.state = DecisionState.COMPLETED
            context.completed_at = datetime.now()

            # Notify completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'decision': final_decision,
                        'completion_time': context.completed_at.isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.component_name,
                        target_component="control_point_manager",
                        domain_type="decision"
                    )
                )
            )

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Decision completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _generate_final_decision(self, context: DecisionContext) -> Dict[str, Any]:
        """Generate final decision based on all available information"""
        try:
            return {
                'selected_option': self._select_best_option(context),
                'impact_analysis': context.impact_assessment,
                'validation_status': context.validation_results,
                'confidence_score': self._calculate_confidence_score(context),
                'rationale': self._generate_decision_rationale(context),
                'metadata': {
                    'processing_time': (context.completed_at - context.created_at).total_seconds(),
                    'feedback_incorporated': bool(context.feedback),
                    'decision_path': self._get_decision_path(context)
                }
            }
        except Exception as e:
            logger.error(f"Final decision generation failed: {str(e)}")
            raise

    def _select_best_option(self, context: DecisionContext) -> Dict[str, Any]:
        """Select the best option based on analysis"""
        try:
            weighted_scores = {}
            for option in context.available_options:
                weighted_scores[option['id']] = self._calculate_option_score(option, context)

            # Sort options by score
            sorted_options = sorted(
                context.available_options,
                key=lambda x: weighted_scores.get(x['id'], 0),
                reverse=True
            )

            return sorted_options[0] if sorted_options else {}

        except Exception as e:
            logger.error(f"Option selection failed: {str(e)}")
            return {}

    def _calculate_option_score(self, option: Dict[str, Any], context: DecisionContext) -> float:
        """Calculate weighted score for an option"""
        try:
            weights = {
                'impact': 0.4,
                'feasibility': 0.3,
                'risk': 0.2,
                'cost': 0.1
            }

            scores = {
                'impact': self._get_impact_score(option, context),
                'feasibility': self._get_feasibility_score(option, context),
                'risk': self._get_risk_score(option, context),
                'cost': self._get_cost_score(option, context)
            }

            return sum(weights[k] * scores[k] for k in weights)

        except Exception as e:
            logger.error(f"Score calculation failed: {str(e)}")
            return 0.0

    def _get_impact_score(self, option: Dict[str, Any], context: DecisionContext) -> float:
        """Calculate impact score"""
        try:
            impact_assessment = context.impact_assessment.get(option['id'], {})
            return min(
                impact_assessment.get('positive_impact', 0) /
                max(impact_assessment.get('negative_impact', 1), 1),
                1.0
            )
        except Exception:
            return 0.0

    def _get_feasibility_score(self, option: Dict[str, Any], context: DecisionContext) -> float:
        """Calculate feasibility score"""
        try:
            validation_results = context.validation_results.get(option['id'], {})
            return validation_results.get('feasibility_score', 0.0)
        except Exception:
            return 0.0

    def _get_risk_score(self, option: Dict[str, Any], context: DecisionContext) -> float:
        """Calculate risk score (inverse - higher is better)"""
        try:
            impact_assessment = context.impact_assessment.get(option['id'], {})
            risk_level = impact_assessment.get('risk_level', 1.0)
            return max(1.0 - risk_level, 0.0)
        except Exception:
            return 0.0

    def _get_cost_score(self, option: Dict[str, Any], context: DecisionContext) -> float:
        """Calculate cost score (inverse - higher is better)"""
        try:
            impact_assessment = context.impact_assessment.get(option['id'], {})
            cost_level = impact_assessment.get('cost_level', 1.0)
            return max(1.0 - cost_level, 0.0)
        except Exception:
            return 0.0

    def _calculate_confidence_score(self, context: DecisionContext) -> float:
        """Calculate overall confidence score for the decision"""
        try:
            factors = {
                'validation_confidence': self._get_validation_confidence(context),
                'impact_confidence': self._get_impact_confidence(context),
                'data_quality': self._get_data_quality_score(context)
            }

            weights = {
                'validation_confidence': 0.4,
                'impact_confidence': 0.4,
                'data_quality': 0.2
            }

            return sum(weights[k] * factors[k] for k in weights)

        except Exception as e:
            logger.error(f"Confidence calculation failed: {str(e)}")
            return 0.0

    def _get_validation_confidence(self, context: DecisionContext) -> float:
        """Get confidence score from validation results"""
        try:
            validation_metrics = [
                result.get('confidence', 0.0)
                for result in context.validation_results.values()
            ]
            return sum(validation_metrics) / len(validation_metrics) if validation_metrics else 0.0
        except Exception:
            return 0.0

    def _get_impact_confidence(self, context: DecisionContext) -> float:
        """Get confidence score from impact assessment"""
        try:
            impact_metrics = [
                assessment.get('confidence', 0.0)
                for assessment in context.impact_assessment.values()
            ]
            return sum(impact_metrics) / len(impact_metrics) if impact_metrics else 0.0
        except Exception:
            return 0.0

    def _get_data_quality_score(self, context: DecisionContext) -> float:
        """Calculate data quality score"""
        try:
            quality_metrics = context.data_quality_metrics
            required_metrics = ['completeness', 'accuracy', 'consistency']

            if not all(metric in quality_metrics for metric in required_metrics):
                return 0.0

            return sum(quality_metrics[metric] for metric in required_metrics) / len(required_metrics)
        except Exception:
            return 0.0

    def _generate_decision_rationale(self, context: DecisionContext) -> str:
        """Generate explanation for the decision"""
        try:
            selected_option = self._select_best_option(context)
            if not selected_option:
                return "No valid option found"

            impact_assessment = context.impact_assessment.get(selected_option['id'], {})
            validation_results = context.validation_results.get(selected_option['id'], {})

            return (
                f"Option selected based on: "
                f"Impact Score: {self._get_impact_score(selected_option, context):.2f}, "
                f"Feasibility: {self._get_feasibility_score(selected_option, context):.2f}, "
                f"Risk Level: {impact_assessment.get('risk_level', 'Unknown')}, "
                f"Confidence: {validation_results.get('confidence', 0.0):.2f}"
            )

        except Exception as e:
            logger.error(f"Rationale generation failed: {str(e)}")
            return "Unable to generate decision rationale"

    def _get_decision_path(self, context: DecisionContext) -> List[str]:
        """Get the sequence of states that led to the decision"""
        try:
            return [
                state.value for state in [
                    DecisionState.INITIALIZING,
                    DecisionState.CONTEXT_ANALYSIS,
                    DecisionState.OPTION_GENERATION,
                    DecisionState.VALIDATION,
                    DecisionState.IMPACT_ANALYSIS,
                    DecisionState.COMPLETED
                ] if state.value in context.processing_history
            ]
        except Exception:
            return []

    async def _start_background_tasks(self) -> None:
        """Start background monitoring tasks"""
        asyncio.create_task(self._monitor_process_timeouts())
        asyncio.create_task(self._monitor_decision_quality())

    async def _monitor_decision_quality(self) -> None:
        """Monitor quality metrics of active decisions"""
        while not self._shutting_down:
            try:
                for pipeline_id, context in self.active_processes.items():
                    confidence_score = self._calculate_confidence_score(context)

                    if confidence_score < self.decision_thresholds['confidence_threshold']:
                        await self._handle_low_confidence(pipeline_id, confidence_score)

                await asyncio.sleep(300)  # Check every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Decision quality monitoring failed: {str(e)}")
                if not self._shutting_down:
                    await asyncio.sleep(60)

    async def _handle_low_confidence(self, pipeline_id: str, confidence_score: float) -> None:
        """Handle low confidence decisions"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_QUALITY_ALERT,
                    content={
                        'pipeline_id': pipeline_id,
                        'confidence_score': confidence_score,
                        'threshold': self.decision_thresholds['confidence_threshold'],
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component="control_point_manager",
                        domain_type="decision"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Low confidence handling failed: {str(e)}")
