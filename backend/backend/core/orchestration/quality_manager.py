# backend/core/managers/quality_manager.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field

from backend.core.base.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus

# Channel Handler
from backend.core.channel_handlers.quality_handler import QualityChannelHandler
from backend.core.channel_handlers.staging_handler import StagingChannelHandler

logger = logging.getLogger(__name__)


@dataclass
class QualityState:
    """Tracks quality assessment state"""
    pipeline_id: str
    current_phase: str  # detection, analysis, or resolution
    status: ProcessingStatus
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class QualityManager(BaseManager):
    """
    Quality manager orchestrating the data quality analysis process
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "QualityManager")

        # Initialize channel handlers
        self.quality_handler = QualityChannelHandler(message_broker)
        self.staging_handler = StagingChannelHandler(message_broker)

        # Quality process tracking
        self.active_quality_checks: Dict[str, QualityState] = {}

    def initiate_quality_check(self, message: ProcessingMessage) -> None:
        """Entry point for quality check requests"""
        try:
            pipeline_id = message.content['pipeline_id']

            # Create quality state tracking
            quality_state = QualityState(
                pipeline_id=pipeline_id,
                current_phase="detection",
                status=ProcessingStatus.PENDING,
                metadata=message.content.get('metadata', {})
            )

            self.active_quality_checks[pipeline_id] = quality_state

            # Route to quality handler to start detection phase
            self.quality_handler.start_detection_phase(
                pipeline_id,
                message.content.get('data'),
                message.content.get('context', {})
            )

        except Exception as e:
            self.logger.error(f"Failed to initiate quality check: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def route_detection_complete(self, pipeline_id: str, detection_results: Dict[str, Any]) -> None:
        """Route detection results to analysis phase"""
        quality_state = self.active_quality_checks.get(pipeline_id)
        if not quality_state:
            return

        quality_state.current_phase = "analysis"
        self.quality_handler.start_analysis_phase(pipeline_id, detection_results)

    def route_analysis_complete(self, pipeline_id: str, analysis_results: Dict[str, Any]) -> None:
        """Route analysis results to resolution phase"""
        quality_state = self.active_quality_checks.get(pipeline_id)
        if not quality_state:
            return

        quality_state.current_phase = "resolution"
        self.quality_handler.start_resolution_phase(pipeline_id, analysis_results)

    def route_resolution_complete(self, pipeline_id: str, resolution_results: Dict[str, Any]) -> None:
        """Complete quality check process"""
        quality_state = self.active_quality_checks.get(pipeline_id)
        if not quality_state:
            return

        quality_state.status = ProcessingStatus.COMPLETED
        quality_state.end_time = datetime.now()

        # Notify completion
        self.quality_handler.notify_quality_complete(
            pipeline_id,
            resolution_results
        )

        # Cleanup
        self._cleanup_quality_check(pipeline_id)

    def _cleanup_quality_check(self, pipeline_id: str) -> None:
        """Clean up quality check resources"""
        if pipeline_id in self.active_quality_checks:
            del self.active_quality_checks[pipeline_id]

    def get_quality_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of quality check"""
        quality_state = self.active_quality_checks.get(pipeline_id)
        if not quality_state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'phase': quality_state.current_phase,
            'status': quality_state.status.value,
            'start_time': quality_state.start_time.isoformat(),
            'end_time': quality_state.end_time.isoformat() if quality_state.end_time else None
        }

    def __del__(self):
        """Cleanup quality manager resources"""
        self.active_quality_checks.clear()
        super().__del__()