<<<<<<< HEAD
# backend/core/processors/decision_processor.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
    ProcessingStage,
    DecisionState,
    DecisionContext
)

# Direct module imports for processing work
from ..modules.decision.generators import (
    OptionGeneratorModule,
    ImpactAssessmentModule,
    RecommendationModule
)
from ..modules.decision.validators import (
    ConstraintValidatorModule,
    RuleValidatorModule,
    ComplianceValidatorModule
)
from ..modules.decision.evaluators import (
    RiskEvaluatorModule,
    CostBenefitModule,
    FeasibilityModule
=======
# data_pipeline/decisions/processor/decision_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    DecisionContext,
    MessageMetadata
)
from backend.core.staging.staging_manager import StagingManager

from ..types.decision_types import (
    DecisionSource,
    DecisionState,
    DecisionPhase,
    DecisionStatus,
    DecisionRequest,
    ComponentDecision,
    ComponentUpdate,
    DecisionValidation,
    DecisionImpact
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
)

logger = logging.getLogger(__name__)


class DecisionProcessor:
    """
<<<<<<< HEAD
    Decision Processor coordinates between modules and messaging system.
    Handles direct module interaction while maintaining message-based coordination.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.module_identifier = ModuleIdentifier(
            component_name="decision_processor",
            component_type=ComponentType.DECISION_PROCESSOR,
            department="decision",
            role="processor"
        )

        # Initialize processing modules
        self._initialize_modules()

        # Track active processing
        self.active_processes: Dict[str, DecisionContext] = {}

        self._setup_message_handlers()

    def _initialize_modules(self) -> None:
        """Initialize processing modules"""
        # Option generation modules
        self.option_generator = OptionGeneratorModule()
        self.impact_assessor = ImpactAssessmentModule()
        self.recommender = RecommendationModule()

        # Validation modules
        self.constraint_validator = ConstraintValidatorModule()
        self.rule_validator = RuleValidatorModule()
        self.compliance_validator = ComplianceValidatorModule()

        # Evaluation modules
        self.risk_evaluator = RiskEvaluatorModule()
        self.cost_benefit_analyzer = CostBenefitModule()
        self.feasibility_analyzer = FeasibilityModule()

    def _setup_message_handlers(self) -> None:
        """Setup message handlers"""
        handlers = {
            MessageType.DECISION_PROCESS_START: self._handle_process_start,
            MessageType.DECISION_VALIDATE_REQUEST: self._handle_validation_request,
            MessageType.DECISION_IMPACT_ASSESS_REQUEST: self._handle_impact_request,
            MessageType.DECISION_OPTIONS_GENERATE_REQUEST: self._handle_options_request,
            MessageType.DECISION_EVALUATE_REQUEST: self._handle_evaluation_request,
            MessageType.DECISION_PROCESS_CANCEL: self._handle_process_cancel
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle start of decision processing"""
        pipeline_id = message.content["pipeline_id"]
        try:
            # Create process context
            context = DecisionContext(
                pipeline_id=pipeline_id,
                correlation_id=message.metadata.correlation_id,
                state=DecisionState.INITIALIZING
            )
            self.active_processes[pipeline_id] = context

            # Begin with options generation
            await self._begin_options_generation(
                pipeline_id,
                message.content.get("parameters", {})
            )

        except Exception as e:
            logger.error(f"Process start failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _begin_options_generation(
            self,
            pipeline_id: str,
            parameters: Dict[str, Any]
    ) -> None:
        """Begin options generation phase"""
        try:
            context = self.active_processes[pipeline_id]
            context.state = DecisionState.OPTION_GENERATION

            # Generate options using module
            options = await self.option_generator.generate_options(
                parameters=parameters,
                constraints=parameters.get("constraints", {})
            )

            # Prioritize options
            prioritized_options = await self.recommender.prioritize_options(
                options=options,
                criteria=parameters.get("prioritization_criteria", {})
            )

            # Initial feasibility check
            feasible_options = await self.feasibility_analyzer.analyze_options(
                options=prioritized_options,
                constraints=parameters.get("feasibility_constraints", {})
            )

            # Store results
            context.available_options = feasible_options
            context.metadata["generation_params"] = parameters

            # Request validation
            await self._begin_validation(pipeline_id, feasible_options)

        except Exception as e:
            logger.error(f"Options generation failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _begin_validation(
            self,
            pipeline_id: str,
            options: list
    ) -> None:
        """Begin validation phase"""
        try:
            context = self.active_processes[pipeline_id]
            context.state = DecisionState.VALIDATION

            # Validate against constraints
            constraint_results = await self.constraint_validator.validate_options(
                options=options,
                constraints=context.metadata.get("generation_params", {}).get("constraints", {})
            )

            # Validate against business rules
            rule_results = await self.rule_validator.validate_options(
                options=options,
                rules=context.metadata.get("generation_params", {}).get("rules", {})
            )

            # Validate compliance
            compliance_results = await self.compliance_validator.validate_options(
                options=options,
                requirements=context.metadata.get("generation_params", {}).get("compliance", {})
            )

            # Combine validation results
            validation_passed = all([
                constraint_results["valid"],
                rule_results["valid"],
                compliance_results["valid"]
            ])

            if validation_passed:
                await self._begin_impact_assessment(pipeline_id, options)
            else:
                # Collect validation issues
                issues = []
                if not constraint_results["valid"]:
                    issues.extend(constraint_results["issues"])
                if not rule_results["valid"]:
                    issues.extend(rule_results["issues"])
                if not compliance_results["valid"]:
                    issues.extend(compliance_results["issues"])

                await self._publish_validation_failure(pipeline_id, issues)

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _begin_impact_assessment(
            self,
            pipeline_id: str,
            options: list
    ) -> None:
        """Begin impact assessment phase"""
        try:
            context = self.active_processes[pipeline_id]
            context.state = DecisionState.IMPACT_ANALYSIS

            # Assess various impacts
            impact_results = await self.impact_assessor.assess_impacts(
                options=options,
                parameters=context.metadata.get("generation_params", {})
            )

            # Evaluate risks
            risk_results = await self.risk_evaluator.evaluate_risks(
                options=options,
                impacts=impact_results
            )

            # Analyze cost-benefit
            cost_benefit_results = await self.cost_benefit_analyzer.analyze_options(
                options=options,
                impacts=impact_results,
                parameters=context.metadata.get("generation_params", {})
            )

            # Store assessment results
            context.impacts = {
                "impact_assessment": impact_results,
                "risk_assessment": risk_results,
                "cost_benefit_analysis": cost_benefit_results
            }

            # Complete processing
            await self._complete_processing(pipeline_id)

        except Exception as e:
            logger.error(f"Impact assessment failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _complete_processing(self, pipeline_id: str) -> None:
        """Complete decision processing"""
        try:
            context = self.active_processes[pipeline_id]

            # Final results package
            results = {
                "options": context.available_options,
                "impacts": context.impacts,
                "metadata": {
                    "processing_time": (datetime.now() - context.created_at).total_seconds(),
                    "validation_status": "passed",
                    "parameters": context.metadata.get("generation_params", {})
                }
            }

            # Publish completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.DECISION_PROCESS_COMPLETE,
                    content={
                        "pipeline_id": pipeline_id,
                        "results": results,
                        "completion_time": datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="decision_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Completion processing failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _publish_validation_failure(
            self,
            pipeline_id: str,
            issues: list
    ) -> None:
        """Publish validation failure"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.DECISION_VALIDATE_COMPLETE,
                content={
                    "pipeline_id": pipeline_id,
                    "is_valid": False,
                    "issues": issues,
                    "timestamp": datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="decision_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _publish_error(self, pipeline_id: str, error: str) -> None:
        """Publish processing error"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.DECISION_PROCESS_ERROR,
                content={
                    "pipeline_id": pipeline_id,
                    "error": error,
                    "timestamp": datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="decision_handler"
                ),
                source_identifier=self.module_identifier
            )
        )

        await self._cleanup_process(pipeline_id)

    async def _cleanup_process(self, pipeline_id: str) -> None:
        """Clean up process resources"""
        if pipeline_id in self.active_processes:
            del self.active_processes[pipeline_id]

    async def cleanup(self) -> None:
        """Clean up processor resources"""
        try:
            # Clean up all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self._cleanup_process(pipeline_id)

            # Unsubscribe from broker
            await self.message_broker.unsubscribe_all(self.module_identifier)

        except Exception as e:
            logger.error(f"Processor cleanup failed: {str(e)}")
=======
    Processes and coordinates decisions across pipeline components.
    Handles decision validation, impact assessment, and state management.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.logger = logging.getLogger(__name__)

        # Active states
        self.active_states: Dict[str, DecisionState] = {}

    async def handle_component_request(
            self,
            pipeline_id: str,
            source: DecisionSource,
            request_data: Dict[str, Any],
            context: DecisionContext
    ) -> DecisionRequest:
        """Process decision request from component"""
        try:
            # Create decision request
            request = DecisionRequest(
                request_id=str(uuid.uuid4()),
                pipeline_id=pipeline_id,
                source=source,
                options=self._prepare_options(request_data.get('options', []), source),
                context=context.__dict__,
                priority=request_data.get('priority', 'medium'),
                requires_confirmation=request_data.get('requires_confirmation', True),
                metadata=request_data.get('metadata', {})
            )

            # Initialize or update state
            state = await self._get_or_create_state(pipeline_id)
            state.current_requests.append(request)
            state.status = DecisionStatus.AWAITING_INPUT
            state.phase = DecisionPhase.ANALYSIS
            self.active_states[pipeline_id] = state

            # Store in staging
            await self._store_request(pipeline_id, request)

            # Notify components about request
            await self._notify_components_of_request(request)

            return request

        except Exception as e:
            logger.error(f"Failed to handle component request: {str(e)}")
            raise

    async def process_decision(
            self,
            pipeline_id: str,
            decision: ComponentDecision
    ) -> Dict[str, Any]:
        """Process submitted decision"""
        try:
            state = self.active_states.get(pipeline_id)
            if not state:
                raise ValueError(f"No active state for pipeline: {pipeline_id}")

            # Validate decision
            validation = await self._validate_decision(decision, state)
            if not validation.passed:
                return {
                    'status': 'invalid',
                    'validation': validation.__dict__,
                    'errors': validation.issues
                }

            # Assess impact
            impact = await self._assess_decision_impact(decision, state)

            # Update state
            state.pending_decisions.append(decision)
            state.status = DecisionStatus.VALIDATING
            state.phase = DecisionPhase.VALIDATION

            # Store updated state
            await self._store_state(state)

            # Notify affected components
            await self._notify_affected_components(decision, impact)

            return {
                'status': 'valid',
                'decision': decision.__dict__,
                'validation': validation.__dict__,
                'impact': impact.__dict__
            }

        except Exception as e:
            logger.error(f"Failed to process decision: {str(e)}")
            raise

    async def handle_component_update(
            self,
            update: ComponentUpdate
    ) -> None:
        """Handle component update about decision impact"""
        try:
            state = self.active_states.get(update.pipeline_id)
            if not state:
                return

            # Find relevant decision
            decision = next(
                (d for d in state.pending_decisions
                 if d.decision_id == update.decision_id),
                None
            )

            if decision:
                # Update impact details
                decision.impacts[update.component] = update.impact_details

                # Check if all components updated
                if self._check_all_components_updated(decision, state):
                    # Move to completed
                    state.completed_decisions.append(decision)
                    state.pending_decisions.remove(decision)
                    state.status = DecisionStatus.COMPLETED

                # Store updated state
                await self._store_state(state)

                # If action required, notify
                if update.requires_action:
                    await self._notify_action_required(update)

        except Exception as e:
            logger.error(f"Failed to handle component update: {str(e)}")
            raise

    async def _validate_decision(
            self,
            decision: ComponentDecision,
            state: DecisionState
    ) -> DecisionValidation:
        """Validate decision against current state"""
        issues = []
        component_validations = {}

        # Validate request exists
        request = next(
            (r for r in state.current_requests
             if r.request_id == decision.request_id),
            None
        )
        if not request:
            issues.append("No matching request found")
            return DecisionValidation(
                decision_id=decision.decision_id,
                validation_type="request_validation",
                passed=False,
                issues=issues,
                component_validations={},
                metadata={'state': state.status.value}
            )

        # Validate option
        if not self._validate_option(decision.selected_option, request.options):
            issues.append("Invalid option selected")

        # Validate against each affected component
        for component, impact in decision.impacts.items():
            component_validations[component] = self._validate_component_impact(
                component,
                impact,
                request.context
            )

        return DecisionValidation(
            decision_id=decision.decision_id,
            validation_type="full_validation",
            passed=len(issues) == 0 and all(component_validations.values()),
            issues=issues,
            component_validations=component_validations,
            metadata={
                'state': state.status.value,
                'request_id': request.request_id
            }
        )

    async def _assess_decision_impact(
            self,
            decision: ComponentDecision,
            state: DecisionState
    ) -> DecisionImpact:
        """Assess impact of decision on components"""
        affected_components = {}
        cascading_effects = []
        requires_updates = []

        # Assess primary impacts
        for component, impact in decision.impacts.items():
            component_impact = await self._assess_component_impact(
                component,
                impact,
                decision
            )
            affected_components[component] = component_impact

            # Check for cascading effects
            if component_impact.get('cascading'):
                cascading_effects.extend(component_impact['cascading_effects'])
                requires_updates.append(component)

        return DecisionImpact(
            decision_id=decision.decision_id,
            affected_components=affected_components,
            cascading_effects=cascading_effects,
            requires_updates=requires_updates,
            metadata={
                'source': decision.source.value,
                'timestamp': datetime.now().isoformat()
            }
        )

    def _validate_option(
            self,
            selected_option: Dict[str, Any],
            available_options: List[Dict[str, Any]]
    ) -> bool:
        """Validate selected option against available options"""
        return any(
            opt['id'] == selected_option.get('id')
            for opt in available_options
        )

    def _validate_component_impact(
            self,
            component: str,
            impact: Dict[str, Any],
            context: Dict[str, Any]
    ) -> bool:
        """Validate impact on specific component"""
        # Implement component-specific validation
        return True

    async def _assess_component_impact(
            self,
            component: str,
            impact: Dict[str, Any],
            decision: ComponentDecision
    ) -> Dict[str, Any]:
        """Assess impact on specific component"""
        return {
            'level': impact.get('level', 'medium'),
            'type': impact.get('type', 'direct'),
            'requires_action': impact.get('requires_action', False),
            'cascading': impact.get('cascading', False),
            'cascading_effects': impact.get('cascading_effects', [])
        }

    async def _notify_components_of_request(
            self,
            request: DecisionRequest
    ) -> None:
        """Notify relevant components about decision request"""
        message = ProcessingMessage(
            message_type=MessageType.DECISION_REQUEST,
            content={
                'pipeline_id': request.pipeline_id,
                'request_id': request.request_id,
                'source': request.source.value,
                'options': request.options,
                'requires_confirmation': request.requires_confirmation
            },
            metadata=MessageMetadata(
                source_component="decision_processor",
                target_component="all",
                domain_type="decision"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_affected_components(
            self,
            decision: ComponentDecision,
            impact: DecisionImpact
    ) -> None:
        """Notify affected components about decision"""
        for component in impact.affected_components:
            message = ProcessingMessage(
                message_type=MessageType.DECISION_IMPACT,
                content={
                    'pipeline_id': decision.pipeline_id,
                    'decision_id': decision.decision_id,
                    'impact': impact.affected_components[component],
                    'requires_update': component in impact.requires_updates
                },
                metadata=MessageMetadata(
                    source_component="decision_processor",
                    target_component=component,
                    domain_type="decision"
                )
            )
            await self.message_broker.publish(message)

    async def _notify_action_required(
            self,
            update: ComponentUpdate
    ) -> None:
        """Notify about required action"""
        message = ProcessingMessage(
            message_type=MessageType.DECISION_UPDATE,
            content={
                'pipeline_id': update.pipeline_id,
                'decision_id': update.decision_id,
                'component': update.component,
                'requires_action': True,
                'impact_details': update.impact_details
            },
            metadata=MessageMetadata(
                source_component="decision_processor",
                target_component="decision_manager",
                domain_type="decision"
            )
        )
        await self.message_broker.publish(message)

    async def _get_or_create_state(
            self,
            pipeline_id: str
    ) -> DecisionState:
        """Get existing state or create new one"""
        state = self.active_states.get(pipeline_id)
        if not state:
            state = DecisionState(
                pipeline_id=pipeline_id,
                current_requests=[],
                pending_decisions=[],
                completed_decisions=[],
                status=DecisionStatus.INITIALIZING,
                phase=DecisionPhase.INITIALIZATION
            )
        return state

    async def _store_state(self, state: DecisionState) -> None:
        """Store decision state"""
        await self.staging_manager.store_staged_data(
            state.pipeline_id,
            {
                'type': 'decision_state',
                'data': state.__dict__,
                'updated_at': datetime.now().isoformat()
            }
        )

    async def _store_request(
            self,
            pipeline_id: str,
            request: DecisionRequest
    ) -> None:
        """Store decision request"""
        await self.staging_manager.store_staged_data(
            pipeline_id,
            {
                'type': 'decision_request',
                'data': request.__dict__,
                'created_at': datetime.now().isoformat()
            }
        )

    def _check_all_components_updated(
            self,
            decision: ComponentDecision,
            state: DecisionState
    ) -> bool:
        """Check if all affected components have provided updates"""
        return all(
            component in decision.impacts
            for component in decision.impacts.keys()
        )
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
