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
)

logger = logging.getLogger(__name__)


class DecisionProcessor:
    """
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