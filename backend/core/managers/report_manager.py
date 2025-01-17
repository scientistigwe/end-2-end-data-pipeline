# backend/data_pipeline/reporting/report_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage
)
from core.managers.base.base_manager import BaseManager
from core.handlers.channel.reports_handler import ReportHandler

logger = logging.getLogger(__name__)


class ReportManager(BaseManager):
    """
    Manages report generation and coordination.
    Integrates with the pipeline and other components.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            template_dir: Optional[Path] = None,
            config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message_broker=message_broker,
            component_name="report_manager"
        )

        # Initialize handler
        self.report_handler = ReportHandler(
            message_broker=message_broker,
            template_dir=template_dir,
            config=config
        )

        # Set up message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup message handlers for report-related events"""
        self.register_handler(
            MessageType.QUALITY_COMPLETE,
            self._handle_quality_complete
        )
        self.register_handler(
            MessageType.INSIGHT_COMPLETE,
            self._handle_insight_complete
        )
        self.register_handler(
            MessageType.ANALYTICS_COMPLETE,
            self._handle_analytics_complete
        )
        self.register_handler(
            MessageType.PIPELINE_COMPLETE,
            self._handle_pipeline_complete
        )
        self.register_handler(
            MessageType.REPORT_STATUS_UPDATE,
            self._handle_report_update
        )
        self.register_handler(
            MessageType.REPORT_ERROR,
            self._handle_report_error
        )

    async def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """Handle quality analysis completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            quality_data = message.content.get('quality_results', {})

            # Request quality report generation
            await self.report_handler.handle_report_request(ProcessingMessage(
                message_type=MessageType.REPORT_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': 'data_quality',
                    'data': quality_data,
                    'format': 'html'  # Default format
                }
            ))

        except Exception as e:
            logger.error(f"Error handling quality completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_insight_complete(self, message: ProcessingMessage) -> None:
        """Handle insight analysis completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            insight_data = message.content.get('insight_results', {})

            # Request insight report generation
            await self.report_handler.handle_report_request(ProcessingMessage(
                message_type=MessageType.REPORT_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': 'insight_analysis',
                    'data': insight_data,
                    'format': 'html'
                }
            ))

        except Exception as e:
            logger.error(f"Error handling insight completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_analytics_complete(self, message: ProcessingMessage) -> None:
        """Handle analytics completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            analytics_data = message.content.get('analytics_results', {})

            # Request analytics report generation
            await self.report_handler.handle_report_request(ProcessingMessage(
                message_type=MessageType.REPORT_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': 'advanced_analytics',
                    'data': analytics_data,
                    'format': 'html'
                }
            ))

        except Exception as e:
            logger.error(f"Error handling analytics completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_pipeline_complete(self, message: ProcessingMessage) -> None:
        """Handle pipeline completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            pipeline_data = message.content.get('pipeline_results', {})

            # Request summary report generation
            await self.report_handler.handle_report_request(ProcessingMessage(
                message_type=MessageType.REPORT_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': 'pipeline_summary',
                    'data': pipeline_data,
                    'format': 'html',
                    'include_components': [
                        'quality_summary',
                        'insight_summary',
                        'analytics_summary'
                    ]
                }
            ))

        except Exception as e:
            logger.error(f"Error handling pipeline completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_report_update(self, message: ProcessingMessage) -> None:
        """Handle report status updates"""
        try:
            pipeline_id = message.content['pipeline_id']
            status = message.content.get('status')

            # Forward status to pipeline manager
            update_message = ProcessingMessage(
                message_type=MessageType.STAGE_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.REPORT_GENERATION.value,
                    'status': status,
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(update_message)

        except Exception as e:
            logger.error(f"Error handling report update: {str(e)}")

    async def _handle_report_error(self, message: ProcessingMessage) -> None:
        """Handle report generation errors"""
        try:
            pipeline_id = message.content['pipeline_id']
            error = message.content.get('error')

            # Notify pipeline manager about error
            error_message = ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.REPORT_GENERATION.value,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling report error: {str(e)}")

    async def generate_report(
            self,
            pipeline_id: str,
            stage: str,
            data: Dict[str, Any],
            format: str = 'html'
    ) -> None:
        """Generate report for specific stage"""
        try:
            # Create report request
            request = ProcessingMessage(
                message_type=MessageType.REPORT_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': stage,
                    'data': data,
                    'format': format
                }
            )

            # Forward request to handler
            await self.report_handler.handle_report_request(request)

        except Exception as e:
            logger.error(f"Error initiating report generation: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_error(self, pipeline_id: str, error: Exception) -> None:
        """Handle errors in report manager"""
        try:
            error_message = ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.REPORT_GENERATION.value,
                    'error': str(error),
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error in error handling: {str(e)}")

    def get_report_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get status of report generation"""
        return self.report_handler.get_report_status(pipeline_id)

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            await self.report_handler.cleanup()
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise