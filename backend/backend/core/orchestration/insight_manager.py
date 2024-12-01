# backend/core/managers/insight_manager.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.base.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus

# Channel Handler
from backend.core.channel_handlers.insight_handler import InsightChannelHandler
from backend.core.channel_handlers.staging_handler import StagingChannelHandler

logger = logging.getLogger(__name__)


class InsightPhase(Enum):
    """Refined insight generation phases"""
    OBJECTIVE_MAPPING = "objective_mapping"  # Map business goals to data features
    EXPLORATORY_ANALYSIS = "exploratory_analysis"  # Statistical analysis & relationships
    PATTERN_RECOGNITION = "pattern_recognition"  # Identify patterns/trends
    SEGMENTATION = "segmentation"  # Group analysis
    ADVANCED_ANALYSIS = "advanced_analysis"  # Advanced insight extraction
    VISUALIZATION = "visualization"  # Visualize insights
    RECOMMENDATION = "recommendation"  # Final recommendations


@dataclass
class InsightState:
    """Tracks insight generation process"""
    pipeline_id: str
    current_phase: InsightPhase
    business_goals: Dict[str, Any]
    data_profile: Dict[str, Any]
    status: ProcessingStatus
    metadata: Dict[str, Any]
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None


class InsightManager(BaseManager):
    """
    Orchestrates the insight generation process
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "InsightManager")

        # Initialize channel handlers
        self.insight_handler = InsightChannelHandler(message_broker)
        self.staging_handler = StagingChannelHandler(message_broker)

        # Track insight processes
        self.active_insights: Dict[str, InsightState] = {}

    def initiate_insight_generation(self, message: ProcessingMessage) -> None:
        """Entry point for insight generation process"""
        try:
            pipeline_id = message.content['pipeline_id']

            # Create insight state with cleansed data features
            insight_state = InsightState(
                pipeline_id=pipeline_id,
                current_phase=InsightPhase.OBJECTIVE_MAPPING,
                business_goals=message.content.get('business_goals', {}),
                data_features=message.content.get('data_features', {}),  # From cleansed data
                status=ProcessingStatus.PENDING,
                metadata=message.content.get('metadata', {})
            )

            self.active_insights[pipeline_id] = insight_state

            # Start by mapping business goals to data features
            self.insight_handler.start_objective_mapping(
                pipeline_id,
                insight_state.business_goals,
                insight_state.data_features
            )

        except Exception as e:
            self.logger.error(f"Failed to initiate insight generation: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def route_phase_complete(self, pipeline_id: str, phase_results: Dict[str, Any]) -> None:
        """Route completion of current phase to next phase"""
        insight_state = self.active_insights.get(pipeline_id)
        if not insight_state:
            return

        current_phase = insight_state.current_phase
        next_phase = self._get_next_phase(current_phase)

        if next_phase:
            insight_state.current_phase = next_phase
            self._start_phase(pipeline_id, next_phase, phase_results)
        else:
            self._finalize_insights(pipeline_id)

    def _get_next_phase(self, current_phase: InsightPhase) -> Optional[InsightPhase]:
        """Determine next insight phase"""
        phase_sequence = {
            InsightPhase.OBJECTIVE_MAPPING: InsightPhase.EXPLORATORY_ANALYSIS,
            InsightPhase.EXPLORATORY_ANALYSIS: InsightPhase.PATTERN_RECOGNITION,
            InsightPhase.PATTERN_RECOGNITION: InsightPhase.SEGMENTATION,
            InsightPhase.SEGMENTATION: InsightPhase.ADVANCED_ANALYSIS,
            InsightPhase.ADVANCED_ANALYSIS: InsightPhase.VISUALIZATION,
            InsightPhase.VISUALIZATION: InsightPhase.RECOMMENDATION,
            InsightPhase.RECOMMENDATION: None
        }
        return phase_sequence.get(current_phase)

    def _start_phase(self, pipeline_id: str, phase: InsightPhase,
                     previous_results: Dict[str, Any]) -> None:
        """Start specific insight phase"""
        phase_starters = {
            InsightPhase.DATA_PREPARATION: self.insight_handler.start_data_preparation,
            InsightPhase.EXPLORATORY_ANALYSIS: self.insight_handler.start_exploratory_analysis,
            InsightPhase.PATTERN_RECOGNITION: self.insight_handler.start_pattern_recognition,
            InsightPhase.SEGMENTATION: self.insight_handler.start_segmentation,
            InsightPhase.ADVANCED_ANALYSIS: self.insight_handler.start_advanced_analysis,
            InsightPhase.VISUALIZATION: self.insight_handler.start_visualization,
            InsightPhase.RECOMMENDATION: self.insight_handler.start_recommendation_generation
        }

        starter = phase_starters.get(phase)
        if starter:
            starter(pipeline_id, previous_results)

    def _finalize_insights(self, pipeline_id: str) -> None:
        """Complete insight generation process"""
        insight_state = self.active_insights.get(pipeline_id)
        if not insight_state:
            return

        try:
            insight_state.status = ProcessingStatus.COMPLETED
            insight_state.end_time = datetime.now()

            # Notify completion
            self.insight_handler.notify_insights_complete(
                pipeline_id,
                self.get_insight_status(pipeline_id)
            )

            # Cleanup
            self._cleanup_insight_process(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to finalize insights: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})
            raise

    def get_insight_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of insight generation"""
        insight_state = self.active_insights.get(pipeline_id)
        if not insight_state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'phase': insight_state.current_phase.value,
            'status': insight_state.status.value,
            'start_time': insight_state.start_time.isoformat(),
            'end_time': insight_state.end_time.isoformat() if insight_state.end_time else None
        }

    def _cleanup_insight_process(self, pipeline_id: str) -> None:
        """Clean up insight process resources"""
        if pipeline_id in self.active_insights:
            del self.active_insights[pipeline_id]

    def __del__(self):
        """Cleanup manager resources"""
        self.active_insights.clear()
        super().__del__()