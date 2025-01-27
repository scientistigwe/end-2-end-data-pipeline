# backend/core/processors/report_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    ReportState,
    ReportContext,
    ReportSection,
    ReportFormat
)

from data.processing.reports.formatters import (
    quality_formatter,
    insight_formatter,
    analytics_formatter,
    summary_formatter
)
from data.processing.reports.visualization import (
    chart_generator,
    graph_generator,
    dashboard_builder
)
from data.processing.reports.templates import template_loader

logger = logging.getLogger(__name__)

class ReportProcessor:
    """
    Report Processor: Handles actual report generation.
    - Direct module access
    - Content generation
    - Message-based coordination
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        
        # Processor identification
        self.module_identifier = ModuleIdentifier(
            component_name="report_processor",
            component_type=ComponentType.REPORT_PROCESSOR,
            department="report",
            role="processor"
        )

        # Active processing contexts
        self.active_contexts: Dict[str, ReportContext] = {}
        
        # Initialize components
        self._initialize_components()
        
        # Setup message handlers
        self._setup_message_handlers()

    def _initialize_components(self) -> None:
        """Initialize report generation components"""
        self.formatters = {
            'quality': quality_formatter,
            'insight': insight_formatter,
            'analytics': analytics_formatter,
            'summary': summary_formatter
        }

        self.visualization_generators = {
            'chart': chart_generator,
            'graph': graph_generator,
            'dashboard': dashboard_builder
        }

        self.templates = template_loader.load_templates()

    def _setup_message_handlers(self) -> None:
        """Setup processor message handlers"""
        handlers = {
            # Core Processing
            MessageType.REPORT_PROCESSOR_START: self._handle_processor_start,
            MessageType.REPORT_PROCESSOR_UPDATE: self._handle_processor_update,
            
            # Section Processing
            MessageType.REPORT_PROCESSOR_SECTION: self._handle_section_generation,
            MessageType.REPORT_PROCESSOR_VISUALIZATION: self._handle_visualization_generation,
            
            # Export
            MessageType.REPORT_PROCESSOR_EXPORT: self._handle_export,
            
            # Control Messages
            MessageType.REPORT_PROCESSOR_CANCEL: self._handle_cancellation
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"report.{message_type.value}.#",
                handler
            )

    async def _handle_processor_start(self, message: ProcessingMessage) -> None:
        """Handle start of report generation"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})
            data_sources = message.content.get('data_sources', {})

            # Initialize context
            context = ReportContext(
                pipeline_id=pipeline_id,
                state=ReportState.INITIALIZING,
                config=config,
                data_sources=data_sources
            )
            self.active_contexts[pipeline_id] = context

            # Load template
            template = self._load_template(
                template_name=config.get('template_name'),
                report_type=config.get('report_type')
            )
            context.template = template

            # Start section generation
            await self._generate_sections(pipeline_id)

        except Exception as e:
            logger.error(f"Processor start failed: {str(e)}")
            await self._handle_processing_error(message, str(e))

    async def _generate_sections(self, pipeline_id: str) -> None:
        """Generate report sections"""
        try:
            context = self.active_contexts[pipeline_id]
            context.state = ReportState.SECTION_GENERATION

            for section in context.template.sections:
                try:
                    # Generate section content
                    if section.section_type in self.formatters:
                        formatter = self.formatters[section.section_type]
                        content = await formatter.generate_content(
                            data=context.data_sources.get(section.section_type),
                            config=context.config
                        )

                        # Generate visualizations if needed
                        visualizations = await self._generate_visualizations(
                            section_type=section.section_type,
                            data=content,
                            config=context.config
                        )

                        # Store section results
                        section_result = {
                            'content': content,
                            'visualizations': visualizations
                        }

                        context.sections[section.section_id] = section_result

                        # Notify section completion
                        await self._publish_section_complete(
                            pipeline_id,
                            section.section_id,
                            section_result
                        )

                except Exception as section_error:
                    logger.error(f"Section generation failed: {str(section_error)}")
                    await self._publish_section_error(
                        pipeline_id,
                        section.section_id,
                        str(section_error)
                    )

            # Start export if all sections complete
            if len(context.sections) == len(context.template.sections):
                await self._start_export(pipeline_id)

        except Exception as e:
            logger.error(f"Sections generation failed: {str(e)}")
            await self._handle_processing_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _generate_visualizations(
            self,
            section_type: str,
            data: Dict[str, Any],
            config: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate visualizations for section"""
        visualizations = []
        viz_config = config.get('visualizations', {}).get(section_type, [])

        for viz_spec in viz_config:
            try:
                generator = self.visualization_generators.get(viz_spec['type'])
                if generator:
                    viz = await generator.generate(
                        data=data,
                        config=viz_spec
                    )
                    visualizations.append(viz)
            except Exception as viz_error:
                logger.error(f"Visualization generation failed: {str(viz_error)}")

        return visualizations

    async def _start_export(self, pipeline_id: str) -> None:
        """Start report export process"""
        try:
            context = self.active_contexts[pipeline_id]
            context.state = ReportState.EXPORT

            report_format = context.config.get('format', ReportFormat.HTML)

            # Export based on format
            if report_format == ReportFormat.HTML:
                result = await self._export_html(context)
            elif report_format == ReportFormat.PDF:
                result = await self._export_pdf(context)
            else:
                result = await self._export_markdown(context)

            # Complete processing
            await self._complete_processing(pipeline_id, result)

        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            await self._handle_processing_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _complete_processing(
            self,
            pipeline_id: str,
            report: Dict[str, Any]
    ) -> None:
        """Complete report generation"""
        try:
            context = self.active_contexts[pipeline_id]
            context.state = ReportState.COMPLETED

            # Publish completion
            await self._publish_completion(pipeline_id, report)

            # Cleanup
            del self.active_contexts[pipeline_id]

        except Exception as e:
            logger.error(f"Completion failed: {str(e)}")
            await self._handle_processing_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _publish_completion(
            self,
            pipeline_id: str,
            report: Dict[str, Any]
    ) -> None:
        """Publish completion message"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.REPORT_PROCESSOR_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'report': report,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="report_handler",
                    domain_type="report",
                    processing_stage=ProcessingStage.REPORT_GENERATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def cleanup(self) -> None:
        """Cleanup processor resources"""
        try:
            # Export any remaining reports
            for pipeline_id in list(self.active_contexts.keys()):
                context = self.active_contexts[pipeline_id]
                if context.sections:
                    await self._start_export(pipeline_id)
                else:
                    await self._handle_processing_error(
                        ProcessingMessage(content={'pipeline_id': pipeline_id}),
                        "Processor cleanup initiated"
                    )

            # Clear contexts
            self.active_contexts.clear()

        except Exception as e:
            logger.error(f"Processor cleanup failed: {str(e)}")
            raise