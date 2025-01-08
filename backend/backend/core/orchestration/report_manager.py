# backend/core/managers/report_manager.py

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.base.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus

# Channel Handler
from backend.core.channel_handlers.report_handler import ReportChannelHandler

logger = logging.getLogger(__name__)


class ReportType(Enum):
    """Types of reports"""
    DATA_QUALITY = "data_quality"
    PIPELINE_PERFORMANCE = "pipeline_performance"
    INSIGHT_SUMMARY = "insight_summary"
    RECOMMENDATION_SUMMARY = "recommendation_summary"
    AUDIT = "audit"
    EXECUTIVE_SUMMARY = "executive_summary"


@dataclass
class ReportState:
    """Tracks report generation state"""
    pipeline_id: str
    report_type: ReportType
    parameters: Dict[str, Any]
    status: ProcessingStatus
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ReportManager(BaseManager):
    """
    Manages report generation and delivery process
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "ReportManager")
        self.report_handler = ReportChannelHandler(message_broker)
        self.active_reports: Dict[str, ReportState] = {}

    def generate_report(self, message: ProcessingMessage) -> None:
        """Entry point for report generation"""
        try:
            pipeline_id = message.content['pipeline_id']
            report_type = ReportType(message.content.get('type', 'insight_summary'))

            # Create report state
            report_state = ReportState(
                pipeline_id=pipeline_id,
                report_type=report_type,
                parameters=message.content.get('parameters', {}),
                status=ProcessingStatus.PENDING,
                metadata=message.content.get('metadata', {})
            )

            self.active_reports[pipeline_id] = report_state

            # Route to handler for generation
            self.report_handler.generate_report(
                pipeline_id,
                report_type,
                report_state.parameters
            )

        except Exception as e:
            self.logger.error(f"Failed to generate report: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def handle_generation_complete(self, pipeline_id: str, report_data: Dict[str, Any]) -> None:
        """Handle completion of report generation"""
        report_state = self.active_reports.get(pipeline_id)
        if not report_state:
            return

        try:
            report_state.status = ProcessingStatus.COMPLETED
            report_state.end_time = datetime.now()

            # Notify completion
            self.report_handler.notify_report_complete(
                pipeline_id,
                report_data
            )

            # Cleanup
            self._cleanup_report(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to handle report completion: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})
            raise

    def handle_generation_error(self, message: ProcessingMessage) -> None:
        """Handle report generation errors"""
        try:
            pipeline_id = message.content['pipeline_id']
            error = message.content['error']

            report_state = self.active_reports.get(pipeline_id)
            if report_state:
                report_state.status = ProcessingStatus.ERROR
                report_state.end_time = datetime.now()

            # Notify error
            self.report_handler.notify_report_error(
                pipeline_id,
                error
            )

            # Cleanup
            self._cleanup_report(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to handle report error: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def get_report_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of report generation"""
        report_state = self.active_reports.get(pipeline_id)
        if not report_state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'type': report_state.report_type.value,
            'status': report_state.status.value,
            'start_time': report_state.start_time.isoformat(),
            'end_time': report_state.end_time.isoformat() if report_state.end_time else None,
            'metadata': report_state.metadata
        }

    def _cleanup_report(self, pipeline_id: str) -> None:
        """Clean up report resources"""
        if pipeline_id in self.active_reports:
            del self.active_reports[pipeline_id]

    def __del__(self):
        """Cleanup manager resources"""
        self.active_reports.clear()
        super().__del__()