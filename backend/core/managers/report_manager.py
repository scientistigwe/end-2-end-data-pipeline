# backend/data_pipeline/reporting/report_manager.py

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
    MessageMetadata,
    ReportContext,
    ReportState
)
from core.managers.base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class ReportManager(BaseManager):
    """
    Report Manager that coordinates report generation through message broker.
    Maintains local state but communicates all actions through messages.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(
            message_broker=message_broker,
            component_name="report_manager",
            domain_type="report"
        )

        # Local state tracking
        self.active_processes: Dict[str, ReportContext] = {}

        # Register message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Register handlers for all report-related messages"""
        handlers = {
            MessageType.REPORT_START_REQUEST: self._handle_start_request,
            MessageType.QUALITY_COMPLETE: self._handle_quality_complete,
            MessageType.INSIGHT_COMPLETE: self._handle_insight_complete,
            MessageType.ANALYTICS_COMPLETE: self._handle_analytics_complete,
            MessageType.REPORT_DATA_READY: self._handle_data_ready,
            MessageType.REPORT_SECTION_READY: self._handle_section_ready,
            MessageType.REPORT_REVIEW_COMPLETE: self._handle_review_complete,
            MessageType.REPORT_ERROR: self._handle_report_error,
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.STAGING_CREATED: self._handle_staging_created
        }

        for message_type, handler in handlers.items():
            self.register_message_handler(message_type, handler)

    async def initiate_report_generation(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> str:
        """
        Initiate report generation through message broker
        Returns correlation ID for tracking
        """
        correlation_id = str(uuid.uuid4())

        # Request control point creation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.CONTROL_POINT_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.REPORT_GENERATION,
                'config': config
            },
            metadata=MessageMetadata(
                correlation_id=correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Initialize context
        self.active_processes[pipeline_id] = ReportContext(
            pipeline_id=pipeline_id,
            correlation_id=correlation_id,
            report_type=config.get('report_type', 'default_report'),
            format=config.get('format', 'html'),
            sections=config.get('sections', []),
            template_name=config.get('template')
        )

        return correlation_id

    async def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """Handle quality analysis completion"""
        pipeline_id = message.content['pipeline_id']
        quality_data = message.content['quality_results']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.add_section_data('quality', quality_data)
        await self._check_data_completeness(pipeline_id)

    async def _handle_insight_complete(self, message: ProcessingMessage) -> None:
        """Handle insight analysis completion"""
        pipeline_id = message.content['pipeline_id']
        insight_data = message.content['insight_results']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.add_section_data('insights', insight_data)
        await self._check_data_completeness(pipeline_id)

    async def _handle_analytics_complete(self, message: ProcessingMessage) -> None:
        """Handle analytics completion"""
        pipeline_id = message.content['pipeline_id']
        analytics_data = message.content['analytics_results']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.add_section_data('analytics', analytics_data)
        await self._check_data_completeness(pipeline_id)

    async def _check_data_completeness(self, pipeline_id: str) -> None:
        """Check if all required data is available"""
        context = self.active_processes[pipeline_id]
        required_sections = set(context.sections)
        available_sections = set(context.collected_data.keys())

        if required_sections.issubset(available_sections):
            context.state = ReportState.GENERATING
            await self._start_report_generation(pipeline_id)

    async def _start_report_generation(self, pipeline_id: str) -> None:
        """Start report generation process"""
        context = self.active_processes[pipeline_id]

        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.REPORT_START_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'sections': context.sections,
                'format': context.format,
                'template': context.template_name,
                'data': context.collected_data
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="report_handler"
            )
        ))

    async def _handle_section_ready(self, message: ProcessingMessage) -> None:
        """Handle completion of a report section"""
        pipeline_id = message.content['pipeline_id']
        section = message.content['section']
        content = message.content['content']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.generated_sections[section] = content

        if len(context.generated_sections) == len(context.sections):
            context.state = ReportState.REVIEWING
            await self._request_report_review(pipeline_id)

    async def _handle_review_complete(self, message: ProcessingMessage) -> None:
        """Handle report review completion"""
        pipeline_id = message.content['pipeline_id']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.state = ReportState.COMPLETED

        # Notify completion
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGE_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.REPORT_GENERATION,
                'report': context.generated_sections
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Cleanup
        del self.active_processes[pipeline_id]

    async def _handle_report_error(self, message: ProcessingMessage) -> None:
        """Handle report generation errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content['error']

        context = self.active_processes.get(pipeline_id)
        if context:
            context.state = ReportState.FAILED
            context.error = error

            # Notify error
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.REPORT_GENERATION,
                    'error': error
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.component_name,
                    target_component="control_point_manager"
                )
            ))

            # Cleanup
            del self.active_processes[pipeline_id]

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        try:
            # Notify cleanup for all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self.message_broker.publish(ProcessingMessage(
                    message_type=MessageType.REPORT_CLEANUP,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': 'Manager cleanup initiated'
                    }
                ))
                del self.active_processes[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise