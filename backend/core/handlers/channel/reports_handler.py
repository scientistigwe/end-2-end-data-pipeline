# backend/core/handlers/channel/report_handler.py

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
    ReportContext,
    ReportState,
    ReportSection,
    ReportConfig
)
from ..base.base_handler import BaseChannelHandler

logger = logging.getLogger(__name__)


class ReportHandler(BaseChannelHandler):
    """
    Handler for report generation operations.
    Communicates exclusively through message broker.
    """

    # Configuration constants
    REPORT_TIMEOUT = timedelta(minutes=45)
    MAX_RETRY_ATTEMPTS = 3
    CHECK_INTERVAL = 60  # seconds

    def __init__(self, message_broker: MessageBroker):
        module_identifier = ModuleIdentifier(
            component_name="report_handler",
            component_type=ComponentType.REPORT_HANDLER,
            department="report",
            role="handler"
        )

        super().__init__(
            message_broker=message_broker,
            module_identifier=module_identifier
        )

        # State tracking
        self._active_contexts: Dict[str, EnhancedReportContext] = {}
        self._report_timeouts: Dict[str, datetime] = {}
        self._retry_attempts: Dict[str, int] = {}

        # Start monitoring
        asyncio.create_task(self._monitor_reports())

    def _setup_message_handlers(self) -> None:
        """Setup handlers for report-specific messages"""
        handlers = {
            # Source data completion
            MessageType.QUALITY_COMPLETE: self._handle_quality_complete,
            MessageType.INSIGHT_COMPLETE: self._handle_insight_complete,
            MessageType.ANALYTICS_COMPLETE: self._handle_analytics_complete,

            # Report generation flow
            MessageType.REPORT_SECTION_COMPLETE: self._handle_section_complete,
            MessageType.REPORT_VALIDATION_COMPLETE: self._handle_validation_complete,

            # Control operations
            MessageType.REPORT_PAUSE_REQUEST: self._handle_pause_request,
            MessageType.REPORT_RESUME_REQUEST: self._handle_resume_request,

            # Status and monitoring
            MessageType.REPORT_STATUS_REQUEST: self._handle_status_request,
            MessageType.REPORT_STATUS_UPDATE: self._handle_status_update
        }

        for message_type, handler in handlers.items():
            self.register_message_handler(message_type, handler)

    async def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """Handle quality analysis completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            quality_data = message.content.get('quality_results', {})

            context = await self._initialize_or_update_context(
                pipeline_id,
                'quality',
                quality_data
            )

            if self._can_start_report_generation(context):
                await self._start_report_generation(pipeline_id)

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_insight_complete(self, message: ProcessingMessage) -> None:
        """Handle insight analysis completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            insight_data = message.content.get('insight_results', {})

            context = await self._initialize_or_update_context(
                pipeline_id,
                'insight',
                insight_data
            )

            if self._can_start_report_generation(context):
                await self._start_report_generation(pipeline_id)

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_analytics_complete(self, message: ProcessingMessage) -> None:
        """Handle analytics completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            analytics_data = message.content.get('analytics_results', {})

            context = await self._initialize_or_update_context(
                pipeline_id,
                'analytics',
                analytics_data
            )

            if self._can_start_report_generation(context):
                await self._start_report_generation(pipeline_id)

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _initialize_or_update_context(
            self,
            pipeline_id: str,
            data_type: str,
            data: Dict[str, Any]
    ) -> EnhancedReportContext:
        """Initialize or update report context with data"""
        if pipeline_id not in self._active_contexts:
            context = EnhancedReportContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.REPORT_GENERATION,
                status=ProcessingStatus.IN_PROGRESS,
                config=ReportConfig(
                    template_id="default",
                    sections=["overview", "quality", "insight", "analytics", "summary"],
                    output_formats=["html", "pdf"]
                )
            )
            self._active_contexts[pipeline_id] = context
            self._report_timeouts[pipeline_id] = datetime.now()

        context = self._active_contexts[pipeline_id]

        # Update appropriate data field
        if data_type == 'quality':
            context.quality_data = data
        elif data_type == 'insight':
            context.insight_data = data
        elif data_type == 'analytics':
            context.analytics_data = data

        context.update_metrics()
        return context

    def _can_start_report_generation(self, context: EnhancedReportContext) -> bool:
        """Check if all required data is available"""
        return all([
            context.quality_data is not None,
            context.insight_data is not None,
            context.analytics_data is not None
        ])

    async def _start_report_generation(self, pipeline_id: str) -> None:
        """Start report generation process"""
        context = self._active_contexts.get(pipeline_id)
        if not context:
            return

        try:
            context.report_state = ReportState.GENERATING

            # Initialize sections
            self._initialize_report_sections(context)

            # Start processing first section
            await self._process_next_section(pipeline_id)

        except Exception as e:
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.REPORT_ERROR,
                    content={'pipeline_id': pipeline_id}
                ),
                str(e)
            )

    def _initialize_report_sections(self, context: EnhancedReportContext) -> None:
        """Initialize report sections based on configuration"""
        section_configs = {
            'overview': {
                'dependencies': [],
                'title': 'Overview'
            },
            'quality': {
                'dependencies': ['overview'],
                'title': 'Quality Analysis'
            },
            'insight': {
                'dependencies': ['quality'],
                'title': 'Insights Analysis'
            },
            'analytics': {
                'dependencies': ['insight'],
                'title': 'Advanced Analytics'
            },
            'summary': {
                'dependencies': ['analytics'],
                'title': 'Summary and Recommendations'
            }
        }

        for section_type in context.config.sections:
            config = section_configs.get(section_type, {})
            section = ReportSection(
                section_type=section_type,
                title=config.get('title', section_type.title()),
                content={},
                dependencies=config.get('dependencies', [])
            )
            context.add_section(section)

    async def _process_next_section(self, pipeline_id: str) -> None:
        """Process next available report section"""
        context = self._active_contexts.get(pipeline_id)
        if not context:
            return

        next_section_id = context.get_next_section()
        if not next_section_id:
            if self._is_report_complete(context):
                await self._complete_report(pipeline_id)
            return

        section = context.sections[next_section_id]
        context.current_section = next_section_id

        await self._publish_message(
            MessageType.REPORT_SECTION_GENERATE_REQUEST,
            {
                'pipeline_id': pipeline_id,
                'section_id': section.section_id,
                'section_type': section.section_type,
                'quality_data': context.quality_data if section.section_type == 'quality' else None,
                'insight_data': context.insight_data if section.section_type == 'insight' else None,
                'analytics_data': context.analytics_data if section.section_type == 'analytics' else None,
                'config': context.config.__dict__
            },
            target_type=ComponentType.REPORT_PROCESSOR
        )

    def _is_report_complete(self, context: EnhancedReportContext) -> bool:
        """Check if all sections are completed"""
        return all(
            section.status == "completed"
            for section in context.sections.values()
        )

    async def _handle_section_complete(self, message: ProcessingMessage) -> None:
        """Handle section completion"""
        pipeline_id = message.content['pipeline_id']
        context = self._active_contexts.get(pipeline_id)

        if not context:
            return

        try:
            section_id = message.content['section_id']
            section_content = message.content['section_content']
            visualizations = message.content.get('visualizations', [])

            # Update section
            context.complete_section(section_id)
            section = context.sections[section_id]
            section.content = section_content

            # Add visualizations
            for viz in visualizations:
                context.add_visualization(section_id, viz)

            # Process next section
            await self._process_next_section(pipeline_id)

        except Exception as e:
            await self._handle_error(message, str(e))


async def _complete_report(self, pipeline_id: str) -> None:
    """Complete report generation process"""
    context = self._active_contexts.get(pipeline_id)
    if not context:
        return

    try:
        context.report_state = ReportState.COMPLETED
        context.status = ProcessingStatus.COMPLETED

        await self._publish_message(
            MessageType.REPORT_COMPLETE,
            {
                'pipeline_id': pipeline_id,
                'sections': [
                    {
                        'section_id': section.section_id,
                        'type': section.section_type,
                        'title': section.title,
                        'content': section.content,
                        'visualizations': section.visualizations
                    }
                    for section in context.sections.values()
                ],
                'metrics': context.metrics.__dict__,
                'completion_time': datetime.now().isoformat()
            },
            target_type=ComponentType.REPORT_MANAGER
        )

        # Cleanup
        await self._cleanup_report(pipeline_id)

    except Exception as e:
        logger.error(f"Report completion error: {str(e)}")


async def _monitor_reports(self) -> None:
    """Monitor active reports for timeouts"""
    while True:
        try:
            current_time = datetime.now()
            for pipeline_id, start_time in self._report_timeouts.items():
                if (current_time - start_time) > self.REPORT_TIMEOUT:
                    await self._handle_timeout(pipeline_id)
            await asyncio.sleep(self.CHECK_INTERVAL)
        except Exception as e:
            logger.error(f"Report monitoring error: {str(e)}")


async def _handle_timeout(self, pipeline_id: str) -> None:
    """Handle report timeout"""
    context = self._active_contexts.get(pipeline_id)
    if not context:
        return

    try:
        retry_count = self._retry_attempts.get(pipeline_id, 0)
        if retry_count < self.MAX_RETRY_ATTEMPTS:
            await self._attempt_recovery(pipeline_id, "timeout")
        else:
            await self._fail_report(
                pipeline_id,
                "Maximum retry attempts exceeded"
            )
    except Exception as e:
        logger.error(f"Timeout handling error: {str(e)}")


async def _attempt_recovery(self, pipeline_id: str, reason: str) -> None:
    """Attempt to recover failed process"""
    context = self._active_contexts.get(pipeline_id)
    if not context:
        return

    self._retry_attempts[pipeline_id] = \
        self._retry_attempts.get(pipeline_id, 0) + 1

    # Reset timeout
    self._report_timeouts[pipeline_id] = datetime.now()

    # Retry current section if exists
    if context.current_section:
        section = context.sections[context.current_section]
        await self._publish_message(
            MessageType.REPORT_SECTION_GENERATE_REQUEST,
            {
                'pipeline_id': pipeline_id,
                'section_id': section.section_id,
                'section_type': section.section_type,
                'quality_data': context.quality_data,
                'insight_data': context.insight_data,
                'analytics_data': context.analytics_data,
                'config': context.config.__dict__,
                'is_retry': True,
                'retry_count': self._retry_attempts[pipeline_id]
            },
            target_type=ComponentType.REPORT_PROCESSOR
        )


async def _fail_report(self, pipeline_id: str, reason: str) -> None:
    """Handle report failure"""
    context = self._active_contexts.get(pipeline_id)
    if not context:
        return

    try:
        context.report_state = ReportState.FAILED
        context.status = ProcessingStatus.FAILED

        await self._publish_message(
            MessageType.REPORT_ERROR,
            {
                'pipeline_id': pipeline_id,
                'error': reason,
                'state': context.report_state.value,
                'current_section': context.current_section,
                'completed_sections': [
                    section.section_id
                    for section in context.sections.values()
                    if section.status == "completed"
                ],
                'metrics': context.metrics.__dict__
            },
            target_type=ComponentType.REPORT_MANAGER
        )

        # Cleanup
        await self._cleanup_report(pipeline_id)

    except Exception as e:
        logger.error(f"Report failure error: {str(e)}")


async def _handle_status_request(self, message: ProcessingMessage) -> None:
    """Handle status request"""
    pipeline_id = message.content['pipeline_id']
    context = self._active_contexts.get(pipeline_id)

    status_response = {
        'pipeline_id': pipeline_id,
        'found': False
    }

    if context:
        status_response.update({
            'found': True,
            'state': context.report_state.value,
            'status': context.status.value,
            'current_section': context.current_section,
            'completed_sections': [
                section.section_id
                for section in context.sections.values()
                if section.status == "completed"
            ],
            'metrics': context.metrics.__dict__,
            'retry_count': self._retry_attempts.get(pipeline_id, 0)
        })

    await self._publish_message(
        MessageType.REPORT_STATUS_RESPONSE,
        status_response,
        target_type=ComponentType.REPORT_MANAGER
    )


async def _cleanup_report(self, pipeline_id: str) -> None:
    """Clean up report resources"""
    if pipeline_id in self._active_contexts:
        del self._active_contexts[pipeline_id]
    if pipeline_id in self._report_timeouts:
        del self._report_timeouts[pipeline_id]
    if pipeline_id in self._retry_attempts:
        del self._retry_attempts[pipeline_id]


async def cleanup(self) -> None:
    """Clean up handler resources"""
    try:
        # Fail all active reports
        for pipeline_id in list(self._active_contexts.keys()):
            await self._fail_report(
                pipeline_id,
                "Handler shutdown initiated"
            )
        await super().cleanup()
    except Exception as e:
        logger.error(f"Cleanup failed: {str(e)}")
        raise