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
    Responsible for orchestrating the decision process while maintaining workflow state.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str = "decision_manager",
            domain_type: str = "decision"
    ):
        super().__init__(
            message_broker=message_broker,
            component_name=component_name,
            domain_type=domain_type
        )

        # Active processes and contexts
        self.active_processes: Dict[str, DecisionContext] = {}
        self.process_timeouts: Dict[str, datetime] = {}

        # Decision thresholds and configuration
        self.decision_thresholds = {
            "confidence_threshold": 0.8,
            "impact_threshold": 0.7,
            "max_processing_time": 3600  # 1 hour
        }

        # State initialization
        self.state = ManagerState.INITIALIZING
        self._initialize_manager()

    def _initialize_manager(self) -> None:
        """Initialize decision manager components"""
        self._setup_message_handlers()
        self._start_background_tasks()
        self.state = ManagerState.ACTIVE

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
        while self.state == ManagerState.ACTIVE:
            try:
                for pipeline_id, context in self.active_processes.items():
                    confidence_score = self._calculate_confidence_score(context)

                    if confidence_score < self.decision_thresholds['confidence_threshold']:
                        await self._handle_low_confidence(pipeline_id, confidence_score)

                await asyncio.sleep(300)  # Check every 5 minutes

            except Exception as e:
                logger.error(f"Decision quality monitoring failed: {str(e)}")
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

    async def cleanup(self) -> None:
        """Cleanup decision manager resources"""
        try:
            self.state = ManagerState.SHUTDOWN

            # Clean up all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self._cleanup_process(pipeline_id)

            # Clear all data
            self.active_processes.clear()
            self.process_timeouts.clear()

            # Cleanup base manager resources
            await super().cleanup()

        except Exception as e:
            logger.error(f"Decision manager cleanup failed: {str(e)}")
            raise