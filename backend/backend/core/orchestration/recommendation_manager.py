# backend/core/managers/recommendation_manager.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.base.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus

# Channel Handler
from backend.core.channel_handlers.recommendation_handler import RecommendationChannelHandler

logger = logging.getLogger(__name__)


class RecommendationType(Enum):
    """Types of recommendations"""
    DATA_QUALITY = "data_quality"
    PROCESS_OPTIMIZATION = "process_optimization"
    INSIGHT_BASED = "insight_based"
    ACTION_ITEMS = "action_items"
    ALERTS = "alerts"


@dataclass
class RecommendationState:
    """Tracks recommendation process state"""
    pipeline_id: str
    rec_type: RecommendationType
    context: Dict[str, Any]
    status: ProcessingStatus
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RecommendationManager(BaseManager):
    """
    Manages generation and tracking of recommendations
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "RecommendationManager")
        self.recommendation_handler = RecommendationChannelHandler(message_broker)
        self.active_recommendations: Dict[str, RecommendationState] = {}

    def generate_recommendations(self, message: ProcessingMessage) -> None:
        """Entry point for recommendation generation"""
        try:
            pipeline_id = message.content['pipeline_id']
            rec_type = RecommendationType(message.content.get('type', 'insight_based'))

            # Create recommendation state
            rec_state = RecommendationState(
                pipeline_id=pipeline_id,
                rec_type=rec_type,
                context=message.content.get('context', {}),
                status=ProcessingStatus.PENDING,
                metadata=message.content.get('metadata', {})
            )

            self.active_recommendations[pipeline_id] = rec_state

            # Route to handler for generation
            self.recommendation_handler.generate_recommendations(
                pipeline_id,
                rec_type,
                rec_state.context
            )

        except Exception as e:
            self.logger.error(f"Failed to generate recommendations: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def handle_generation_complete(self, pipeline_id: str,
                                   recommendations: Dict[str, Any]) -> None:
        """Handle completion of recommendation generation"""
        rec_state = self.active_recommendations.get(pipeline_id)
        if not rec_state:
            return

        try:
            rec_state.status = ProcessingStatus.COMPLETED
            rec_state.end_time = datetime.now()

            # Notify completion
            self.recommendation_handler.notify_recommendations_complete(
                pipeline_id,
                recommendations
            )

            # Cleanup
            self._cleanup_recommendations(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to handle recommendation completion: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})
            raise

    def handle_generation_error(self, message: ProcessingMessage) -> None:
        """Handle recommendation generation errors"""
        try:
            pipeline_id = message.content['pipeline_id']
            error = message.content['error']

            rec_state = self.active_recommendations.get(pipeline_id)
            if rec_state:
                rec_state.status = ProcessingStatus.ERROR
                rec_state.end_time = datetime.now()

            # Notify error
            self.recommendation_handler.notify_recommendations_error(
                pipeline_id,
                error
            )

            # Cleanup
            self._cleanup_recommendations(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to handle recommendation error: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def get_recommendation_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of recommendation process"""
        rec_state = self.active_recommendations.get(pipeline_id)
        if not rec_state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'type': rec_state.rec_type.value,
            'status': rec_state.status.value,
            'start_time': rec_state.start_time.isoformat(),
            'end_time': rec_state.end_time.isoformat() if rec_state.end_time else None,
            'metadata': rec_state.metadata
        }

    def _cleanup_recommendations(self, pipeline_id: str) -> None:
        """Clean up recommendation resources"""
        if pipeline_id in self.active_recommendations:
            del self.active_recommendations[pipeline_id]

    def __del__(self):
        """Cleanup manager resources"""
        self.active_recommendations.clear()
        super().__del__()

