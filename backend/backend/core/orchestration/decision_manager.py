# backend/core/managers/decision_manager.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.base.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus

# Channel Handler
from backend.core.channel_handlers.decision_handler import DecisionChannelHandler

logger = logging.getLogger(__name__)


class PipelinePhase(Enum):
    """Core pipeline phases"""
    EXTRACTION = "extraction"
    PROCESSING = "processing"
    QUALITY_ANALYSIS = "quality_analysis"
    INSIGHT_ANALYSIS = "insight_analysis"
    FINAL_REPORT = "final_report"


@dataclass
class DecisionState:
    """Tracks state of decision process"""
    pipeline_id: str
    phase: PipelinePhase
    context: Dict[str, Any]
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class DecisionManager(BaseManager):
    """
    Orchestrates the decision-recommendation process throughout pipeline phases
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "DecisionManager")
        self.decision_handler = DecisionChannelHandler(message_broker)
        self.active_decisions: Dict[str, DecisionState] = {}

    def initiate_decision_process(self, message: ProcessingMessage) -> None:
        """Entry point for decision process"""
        try:
            pipeline_id = message.content['pipeline_id']
            phase = PipelinePhase(message.content['phase'])

            # Create decision state
            decision_state = DecisionState(
                pipeline_id=pipeline_id,
                phase=phase,
                context=message.content.get('context', {})
            )

            self.active_decisions[pipeline_id] = decision_state

            # Route to decision handler for recommendation generation
            self.decision_handler.start_recommendation_phase(
                pipeline_id,
                phase,
                message.content
            )

        except Exception as e:
            self.logger.error(f"Failed to initiate decision process: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def route_recommendation_complete(self, pipeline_id: str, recommendations: Dict[str, Any]) -> None:
        """Handle completion of recommendation generation"""
        decision_state = self.active_decisions.get(pipeline_id)
        if not decision_state:
            return

        # Route recommendations to user decision phase
        self.decision_handler.request_user_decision(
            pipeline_id,
            decision_state.phase,
            recommendations
        )

    def handle_user_decision(self, message: ProcessingMessage) -> None:
        """Handle user decision response"""
        try:
            pipeline_id = message.content['pipeline_id']
            decision = message.content['decision']

            decision_state = self.active_decisions.get(pipeline_id)
            if not decision_state:
                raise ValueError(f"No active decision found for pipeline: {pipeline_id}")

            # Update state
            decision_state.status = "completed"
            decision_state.completed_at = datetime.now()

            # Route decision to appropriate phase handler
            self.decision_handler.process_decision(
                pipeline_id,
                decision_state.phase,
                decision
            )

            # Cleanup
            self._cleanup_decision(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to handle user decision: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def get_decision_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of decision process"""
        decision_state = self.active_decisions.get(pipeline_id)
        if not decision_state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'phase': decision_state.phase.value,
            'status': decision_state.status,
            'created_at': decision_state.created_at.isoformat(),
            'completed_at': decision_state.completed_at.isoformat() if decision_state.completed_at else None
        }

    def _cleanup_decision(self, pipeline_id: str) -> None:
        """Clean up completed decision process"""
        if pipeline_id in self.active_decisions:
            del self.active_decisions[pipeline_id]

    def __del__(self):
        """Cleanup manager resources"""
        self.active_decisions.clear()
        super().__del__()