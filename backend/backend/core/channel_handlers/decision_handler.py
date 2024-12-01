# backend/core/channel_handlers/decision_handler.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.channel_handlers.base_handler import BaseHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage

# Import the decision module manager
from backend.data_pipeline.decision.decision_module_manager import DecisionModuleManager

logger = logging.getLogger(__name__)


class DecisionPhase(Enum):
    """Phases in decision process"""
    RECOMMENDATION = "recommendation"
    USER_DECISION = "user_decision"
    DECISION_PROCESSING = "decision_processing"


@dataclass
class DecisionContext:
    """Context for decision processing"""
    pipeline_id: str
    phase: DecisionPhase
    pipeline_stage: str  # The stage requiring decision (extraction/quality/insight etc)
    recommendations: Optional[List[Dict[str, Any]]] = None
    decision_options: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"


class DecisionHandler(BaseHandler):
    """
    Handles communication between orchestrator and decision module manager
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "decision_handler")

        # Initialize decision module manager
        self.decision_manager = DecisionModuleManager(message_broker)

        # Track active decision processes
        self.active_decisions: Dict[str, DecisionContext] = {}

        # Register handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers"""
        self.register_callback(
            MessageType.DECISION_REQUIRED,
            self._handle_decision_request
        )
        self.register_callback(
            MessageType.RECOMMENDATION_READY,
            self._handle_recommendation_ready
        )
        self.register_callback(
            MessageType.USER_DECISION_MADE,
            self._handle_user_decision
        )
        self.register_callback(
            MessageType.DECISION_ERROR,
            self._handle_decision_error
        )

    def initiate_decision_process(self, pipeline_id: str, pipeline_stage: str,
                                  context_data: Dict[str, Any]) -> None:
        """Entry point for decision process"""
        try:
            # Create decision context
            decision_context = DecisionContext(
                pipeline_id=pipeline_id,
                phase=DecisionPhase.RECOMMENDATION,
                pipeline_stage=pipeline_stage,
                metadata=context_data
            )

            self.active_decisions[pipeline_id] = decision_context

            # Start recommendation generation
            self.decision_manager.generate_recommendations(
                pipeline_id,
                pipeline_stage,
                context_data
            )

        except Exception as e:
            self.logger.error(f"Failed to initiate decision process: {str(e)}")
            self._handle_process_error(pipeline_id, str(e))

    def _handle_decision_request(self, message: ProcessingMessage) -> None:
        """Handle new decision request"""
        pipeline_id = message.content['pipeline_id']
        pipeline_stage = message.content['stage']
        context = message.content.get('context', {})

        self.initiate_decision_process(
            pipeline_id,
            pipeline_stage,
            context
        )

    def _handle_recommendation_ready(self, message: ProcessingMessage) -> None:
        """Handle completed recommendations"""
        pipeline_id = message.content['pipeline_id']
        recommendations = message.content.get('recommendations', [])
        decision_options = message.content.get('decision_options', [])

        context = self.active_decisions.get(pipeline_id)
        if context:
            # Update context
            context.recommendations = recommendations
            context.decision_options = decision_options
            context.phase = DecisionPhase.USER_DECISION

            # Forward to orchestrator for user interaction
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.REQUEST_USER_DECISION,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': context.pipeline_stage,
                    'recommendations': recommendations,
                    'decision_options': decision_options,
                    'metadata': context.metadata
                }
            )

    def _handle_user_decision(self, message: ProcessingMessage) -> None:
        """Handle user's decision"""
        pipeline_id = message.content['pipeline_id']
        decision = message.content.get('decision')

        context = self.active_decisions.get(pipeline_id)
        if context:
            context.phase = DecisionPhase.DECISION_PROCESSING

            # Process user decision
            self.decision_manager.process_user_decision(
                pipeline_id,
                context.pipeline_stage,
                decision,
                {
                    'recommendations': context.recommendations,
                    'original_options': context.decision_options,
                    'metadata': context.metadata
                }
            )

    def _handle_decision_error(self, message: ProcessingMessage) -> None:
        """Handle decision processing errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content.get('error')

        self._handle_process_error(pipeline_id, error)

    def _handle_process_error(self, pipeline_id: str, error: str) -> None:
        """Handle process errors"""
        context = self.active_decisions.get(pipeline_id)
        if context:
            # Notify orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.DECISION_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': context.pipeline_stage,
                    'phase': context.phase.value,
                    'error': error
                }
            )

            # Cleanup
            self._cleanup_decision_process(pipeline_id)

    def handle_decision_timeout(self, pipeline_id: str) -> None:
        """Handle decision timeout"""
        context = self.active_decisions.get(pipeline_id)
        if context:
            # Get default decision if available
            default_decision = self.decision_manager.get_default_decision(
                pipeline_id,
                context.pipeline_stage
            )

            if default_decision:
                # Apply default decision
                self._handle_user_decision(ProcessingMessage(
                    content={
                        'pipeline_id': pipeline_id,
                        'decision': default_decision
                    }
                ))
            else:
                # Handle as error if no default available
                self._handle_process_error(
                    pipeline_id,
                    "Decision timeout with no default action"
                )

    def get_decision_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current decision process status"""
        context = self.active_decisions.get(pipeline_id)
        if not context:
            return None

        return {
            'pipeline_id': pipeline_id,
            'stage': context.pipeline_stage,
            'phase': context.phase.value,
            'status': context.status,
            'has_recommendations': bool(context.recommendations),
            'has_options': bool(context.decision_options),
            'created_at': context.created_at.isoformat()
        }

    def _cleanup_decision_process(self, pipeline_id: str) -> None:
        """Clean up decision process resources"""
        if pipeline_id in self.active_decisions:
            del self.active_decisions[pipeline_id]

    def __del__(self):
        """Cleanup handler resources"""
        self.active_decisions.clear()
        super().__del__()
