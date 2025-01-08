# backend/data_pipeline/decision/decision_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage

# Import decision modules (you'll need to create these)
from backend.data_pipeline.decision.recommendation_engine import (
    rule_based_recommendations,
    ml_based_recommendations,
    user_preference_based
)

from backend.data_pipeline.decision.decision_validator import (
    constraint_validation,
    impact_analysis,
    dependency_checker
)

logger = logging.getLogger(__name__)


class DecisionPhase(Enum):
    """Decision processing phases"""
    RECOMMENDATION = "recommendation"
    USER_DECISION = "user_decision"
    DECISION_PROCESSING = "decision_processing"


@dataclass
class DecisionContext:
    """Context for decision processing"""
    pipeline_id: str
    current_phase: DecisionPhase
    pipeline_stage: str
    metadata: Dict[str, Any]
    recommendations: Optional[List[Dict[str, Any]]] = None
    decision_options: Optional[List[Dict[str, Any]]] = None
    selected_decision: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class DecisionProcessor:
    """
    Manages interaction with decision processing modules
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.logger = logging.getLogger(__name__)

        # Track decision processes
        self.active_processes: Dict[str, DecisionContext] = {}

        # Initialize module interfaces
        self._initialize_module_interfaces()

    def _initialize_module_interfaces(self) -> None:
        """Initialize interfaces to all decision modules"""
        # Recommendation engines
        self.recommendation_engines = {
            'rule_based': {
                'generate': rule_based_recommendations.generate,
                'validate': rule_based_recommendations.validate
            },
            'ml_based': {
                'generate': ml_based_recommendations.generate,
                'validate': ml_based_recommendations.validate
            },
            'user_preference': {
                'generate': user_preference_based.generate,
                'validate': user_preference_based.validate
            }
        }

        # Decision validators
        self.validators = {
            'constraints': constraint_validation.validate,
            'impact': impact_analysis.analyze,
            'dependencies': dependency_checker.check
        }

    def generate_recommendations(self, pipeline_id: str, pipeline_stage: str,
                                 context_data: Dict[str, Any]) -> None:
        """Generate recommendations for decision making"""
        try:
            decision_context = DecisionContext(
                pipeline_id=pipeline_id,
                current_phase=DecisionPhase.RECOMMENDATION,
                pipeline_stage=pipeline_stage,
                metadata=context_data
            )

            self.active_processes[pipeline_id] = decision_context

            # Generate recommendations using all available engines
            recommendations = []
            decision_options = []

            for engine_type, engine in self.recommendation_engines.items():
                engine_recommendations = engine['generate'](context_data)
                if engine_recommendations:
                    recommendations.extend(engine_recommendations)

                    # Extract valid options from recommendations
                    valid_options = engine['validate'](engine_recommendations)
                    decision_options.extend(valid_options)

            # Update context
            decision_context.recommendations = recommendations
            decision_context.decision_options = decision_options
            decision_context.updated_at = datetime.now()

            # Notify recommendations ready
            self._notify_recommendations_ready(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {str(e)}")
            self._handle_decision_error(pipeline_id, "recommendation", str(e))

    def process_user_decision(self, pipeline_id: str, pipeline_stage: str,
                              decision: Dict[str, Any], context: Dict[str, Any]) -> None:
        """Process user's selected decision"""
        try:
            proc_context = self.active_processes.get(pipeline_id)
            if not proc_context:
                raise ValueError(f"No active decision process for pipeline {pipeline_id}")

            proc_context.selected_decision = decision
            proc_context.current_phase = DecisionPhase.DECISION_PROCESSING
            proc_context.updated_at = datetime.now()

            # Validate decision
            self._validate_decision(pipeline_id, decision, context)

        except Exception as e:
            self._handle_decision_error(pipeline_id, "processing", str(e))

    def _validate_decision(self, pipeline_id: str, decision: Dict[str, Any],
                           context: Dict[str, Any]) -> None:
        """Validate and process the selected decision"""
        try:
            # Run all validators
            validation_results = {}
            for validator_name, validator in self.validators.items():
                result = validator(decision, context)
                validation_results[validator_name] = result

            # Check for validation issues
            has_issues = any(
                result.get('has_issues', False)
                for result in validation_results.values()
            )

            if has_issues:
                raise ValueError(f"Decision validation failed: {validation_results}")

            # If valid, notify completion
            self._notify_completion(pipeline_id, validation_results)

        except Exception as e:
            self._handle_decision_error(pipeline_id, "validation", str(e))

    def get_default_decision(self, pipeline_id: str, pipeline_stage: str) -> Optional[Dict[str, Any]]:
        """Get default decision for timeout scenarios"""
        context = self.active_processes.get(pipeline_id)
        if not context or not context.decision_options:
            return None

        # Return first valid option as default
        for option in context.decision_options:
            if option.get('is_default'):
                return option

        return None

    def _notify_recommendations_ready(self, pipeline_id: str) -> None:
        """Notify that recommendations are ready"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        message = ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_READY,
            content={
                'pipeline_id': pipeline_id,
                'recommendations': context.recommendations,
                'decision_options': context.decision_options,
                'metadata': context.metadata
            }
        )

        self.message_broker.publish(message)

    def _notify_completion(self, pipeline_id: str, validation_results: Dict[str, Any]) -> None:
        """Notify completion of decision process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        message = ProcessingMessage(
            message_type=MessageType.DECISION_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'stage': context.pipeline_stage,
                'decision': context.selected_decision,
                'validation_results': validation_results,
                'metadata': context.metadata
            }
        )

        self.message_broker.publish(message)
        self._cleanup_process(pipeline_id)

    def _handle_decision_error(self, pipeline_id: str, phase: str, error: str) -> None:
        """Handle errors in decision processing"""
        message = ProcessingMessage(
            message_type=MessageType.DECISION_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'phase': phase,
                'error': error
            }
        )

        self.message_broker.publish(message)
        self._cleanup_process(pipeline_id)

    def _cleanup_process(self, pipeline_id: str) -> None:
        """Clean up process resources"""
        if pipeline_id in self.active_processes:
            del self.active_processes[pipeline_id]

    def get_process_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of decision process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return None

        return {
            'pipeline_id': pipeline_id,
            'stage': context.pipeline_stage,
            'phase': context.current_phase.value,
            'has_recommendations': bool(context.recommendations),
            'has_options': bool(context.decision_options),
            'has_selected_decision': bool(context.selected_decision),
            'created_at': context.created_at.isoformat(),
            'updated_at': context.updated_at.isoformat()
        }

    def __del__(self):
        """Cleanup processor resources"""
        self.active_processes.clear()