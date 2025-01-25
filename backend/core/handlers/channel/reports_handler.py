# backend/data_pipeline/reporting/report_handler.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    ReportContext
)

from data.processing.reports.processor.report_processor import ReportProcessor
from data.processing.reports.types.reports_types import ReportStage, ReportStatus

logger = logging.getLogger(__name__)


class ReportHandler:
    """
    Handles communication between reporting components and pipeline.
    Manages message flow and status updates for report generation.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            processor: Optional[ReportProcessor] = None
    ):
        self.message_broker = message_broker
        self.processor = processor or ReportProcessor(message_broker)
        self.active_reports: Dict[str, Dict[str, Any]] = {}

        # Initialize message subscriptions
        self._setup_subscriptions()

    def _setup_subscriptions(self) -> None:
        """Setup message subscriptions"""
        self.message_broker.subscribe(
            pattern="quality.complete",
            callback=self.handle_quality_complete
        )
        self.message_broker.subscribe(
            pattern="insight.complete",
            callback=self.handle_insight_complete
        )
        self.message_broker.subscribe(
            pattern="analytics.complete",
            callback=self.handle_analytics_complete
        )

    async def handle_quality_complete(self, message: ProcessingMessage) -> None:
        """Handle quality insight completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            quality_data = message.content.get('quality_results', {})

            # Process quality report
            report = await self.processor.process_quality_report(
                pipeline_id,
                quality_data
            )

            # Track active report
            self.active_reports[pipeline_id] = {
                'stage': ReportStage.DATA_QUALITY.value,
                'status': ReportStatus.GENERATING.value,
                'report_id': str(report.report_id),
                'started_at': datetime.now().isoformat()
            }

            # Send progress update
            await self._notify_progress(pipeline_id, 0.0)

            # Start report generation
            await self._generate_report(pipeline_id, report, quality_data)

        except Exception as e:
            logger.error(f"Error handling quality completion: {str(e)}")
            await self._notify_error(pipeline_id, str(e))

    async def handle_insight_complete(self, message: ProcessingMessage) -> None:
        """Handle insight insight completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            insight_data = message.content.get('insight_results', {})

            # Process insight report
            report = await self.processor.process_insight_report(
                pipeline_id,
                insight_data
            )

            # Track active report
            self.active_reports[pipeline_id] = {
                'stage': ReportStage.INSIGHT_ANALYSIS.value,
                'status': ReportStatus.GENERATING.value,
                'report_id': str(report.report_id),
                'started_at': datetime.now().isoformat()
            }

            # Send progress update
            await self._notify_progress(pipeline_id, 0.0)

            # Start report generation
            await self._generate_report(pipeline_id, report, insight_data)

        except Exception as e:
            logger.error(f"Error handling insight completion: {str(e)}")
            await self._notify_error(pipeline_id, str(e))

    async def handle_analytics_complete(self, message: ProcessingMessage) -> None:
        """Handle analytics completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            analytics_data = message.content.get('analytics_results', {})

            # Process analytics report
            report = await self.processor.process_analytics_report(
                pipeline_id,
                analytics_data
            )

            # Track active report
            self.active_reports[pipeline_id] = {
                'stage': ReportStage.ADVANCED_ANALYTICS.value,
                'status': ReportStatus.GENERATING.value,
                'report_id': str(report.report_id),
                'started_at': datetime.now().isoformat()
            }

            # Send progress update
            await self._notify_progress(pipeline_id, 0.0)

            # Start report generation
            await self._generate_report(pipeline_id, report, analytics_data)

        except Exception as e:
            logger.error(f"Error handling analytics completion: {str(e)}")
            await self._notify_error(pipeline_id, str(e))

    async def _generate_report(
            self,
            pipeline_id: str,
            report: Any,
            data: Dict[str, Any]
    ) -> None:
        """Generate report and send completion notification"""
        try:
            # Update progress
            await self._notify_progress(pipeline_id, 0.5)

            # Send report generation message
            message = ProcessingMessage(
                message_type=MessageType.REPORT_GENERATING,
                content={
                    'pipeline_id': pipeline_id,
                    'report_id': str(report.report_id),
                    'stage': report.stage.value,
                    'data': data
                }
            )
            await self.message_broker.publish(message)

            # Update report status
            if pipeline_id in self.active_reports:
                self.active_reports[pipeline_id].update({
                    'status': ReportStatus.READY_FOR_REVIEW.value,
                    'completed_at': datetime.now().isoformat()
                })

            # Send completion notification
            await self._notify_completion(pipeline_id, report)

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            await self._notify_error(pipeline_id, str(e))

    async def _notify_progress(self, pipeline_id: str, progress: float) -> None:
        """Send progress update notification"""
        message = ProcessingMessage(
            message_type=MessageType.REPORT_STATUS_UPDATE,
            content={
                'pipeline_id': pipeline_id,
                'status': 'generating',
                'progress': progress,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _notify_completion(self, pipeline_id: str, report: Any) -> None:
        """Send completion notification"""
        message = ProcessingMessage(
            message_type=MessageType.REPORT_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'report_id': str(report.report_id),
                'stage': report.stage.value,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

    async def _notify_error(self, pipeline_id: str, error: str) -> None:
        """Send error notification"""
        message = ProcessingMessage(
            message_type=MessageType.REPORT_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(message)

        # Update report status
        if pipeline_id in self.active_reports:
            self.active_reports[pipeline_id].update({
                'status': ReportStatus.FAILED.value,
                'error': error,
                'failed_at': datetime.now().isoformat()
            })

    def get_report_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get status of report generation"""
        return self.active_reports.get(pipeline_id)

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        # Clean up processor
        await self.processor.cleanup()

        # Clear active reports
        self.active_reports.clear()