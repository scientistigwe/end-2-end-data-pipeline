"""
Enhanced ReportProcessor with message-based architecture and comprehensive report generation capabilities.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    ReportMessageType, ReportState, ReportType,
    ReportFormat, ReportContext, ReportSection,
    Visualization, ReportTemplate, ModuleIdentifier,
    ComponentType, ProcessingMessage, MessageMetadata
)

from ..formatters import (
    quality_formatter, insight_formatter,
    analytics_formatter, summary_formatter
)
from ..templates import template_loader
from ..visualization import (
    chart_generator, graph_generator,
    dashboard_builder
)

logger = logging.getLogger(__name__)


class ReportProcessor:
    """Enhanced report processor with comprehensive report generation capabilities"""

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.active_processes: Dict[str, ReportContext] = {}

        self.module_identifier = ModuleIdentifier(
            component_name="report_processor",
            component_type=ComponentType.REPORT_PROCESSOR,
            department="report",
            role="processor"
        )

        self._initialize_components()
        self._setup_subscriptions()

    def _initialize_components(self) -> None:
        """Initialize report generation components"""
        self.formatters = {
            ReportType.QUALITY_REPORT: quality_formatter,
            ReportType.INSIGHT_REPORT: insight_formatter,
            ReportType.ANALYTICS_REPORT: analytics_formatter,
            ReportType.SUMMARY_REPORT: summary_formatter
        }

        self.templates = template_loader.load_templates()

    def _setup_subscriptions(self) -> None:
        """Setup comprehensive message subscriptions"""
        handlers = {
            # Core Process Flow
            ReportMessageType.REPORT_PROCESS_START: self._handle_process_start,

            # Data Preparation
            ReportMessageType.REPORT_DATA_PREPARE_REQUEST: self._handle_data_preparation,

            # Section Generation
            ReportMessageType.REPORT_SECTION_GENERATE_REQUEST: self._handle_section_generation,

            # Visualization
            ReportMessageType.REPORT_VISUALIZATION_REQUEST: self._handle_visualization_request,
            ReportMessageType.REPORT_CHART_GENERATE: self._handle_chart_generation,

            # Format and Layout
            ReportMessageType.REPORT_FORMAT_REQUEST: self._handle_formatting,
            ReportMessageType.REPORT_LAYOUT_APPLY: self._handle_layout,

            # Validation
            ReportMessageType.REPORT_VALIDATE_REQUEST: self._handle_validation,

            # Export
            ReportMessageType.REPORT_EXPORT_REQUEST: self._handle_export
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"report.{message_type.value}",
                handler
            )

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle report generation initialization"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = ReportContext(
                pipeline_id=pipeline_id,
                report_type=message.content["report_type"],
                report_format=message.content["report_format"],
                template_name=message.content.get("template_name"),
                style_config=message.content.get("style_config", {})
            )
            self.active_processes[pipeline_id] = context

            await self._publish_status_update(
                pipeline_id,
                ReportState.INITIALIZING,
                "Starting report generation"
            )

            await self._initiate_data_preparation(pipeline_id, message.content)

        except Exception as e:
            logger.error(f"Process start failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_data_preparation(self, message: ProcessingMessage) -> None:
        """Handle report data preparation"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(ReportState.DATA_PREPARATION)

            # Load and validate data sources
            for source_name, source_data in message.content.get("data_sources", {}).items():
                validated_data = await self._validate_data_source(source_data)
                context.data_sources[source_name] = validated_data

            # Load template
            template = self._load_template(context.report_type, context.template_name)
            context.sections = template.sections

            await self._initiate_section_generation(pipeline_id)

        except Exception as e:
            logger.error(f"Data preparation failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_section_generation(self, message: ProcessingMessage) -> None:
        """Handle report section generation"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(ReportState.SECTION_GENERATION)

            formatter = self.formatters[context.report_type]

            for section in context.sections:
                if section["id"] not in context.completed_sections:
                    context.current_section = section["id"]

                    # Generate section content
                    content = await formatter.format_section(
                        section,
                        context.data_sources,
                        context.style_config
                    )

                    # Handle visualizations if needed
                    if content.get("visualizations"):
                        await self._handle_section_visualizations(
                            pipeline_id,
                            section["id"],
                            content["visualizations"]
                        )

                    context.completed_sections.append(section["id"])
                    context.section_status[section["id"]] = "completed"

                    await self._publish_section_complete(pipeline_id, section["id"])

            await self._initiate_formatting(pipeline_id)

        except Exception as e:
            logger.error(f"Section generation failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_visualization_request(self, message: ProcessingMessage) -> None:
        """Handle visualization generation"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(ReportState.VISUALIZATION_CREATION)

            visualization_config = message.content["visualization"]
            viz_type = visualization_config["type"]

            if viz_type == "chart":
                result = await chart_generator.generate_chart(
                    visualization_config["data"],
                    visualization_config["config"]
                )
            elif viz_type == "graph":
                result = await graph_generator.generate_graph(
                    visualization_config["data"],
                    visualization_config["config"]
                )
            else:
                result = await dashboard_builder.create_visualization(
                    visualization_config["data"],
                    visualization_config["config"]
                )

            context.visualizations[visualization_config["id"]] = result

            await self._publish_visualization_complete(
                pipeline_id,
                visualization_config["id"]
            )

        except Exception as e:
            logger.error(f"Visualization generation failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_formatting(self, message: ProcessingMessage) -> None:
        """Handle report formatting"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(ReportState.FORMATTING)

            formatter = self.formatters[context.report_type]

            # Apply formatting
            formatted_content = await formatter.apply_formatting(
                sections=context.sections,
                visualizations=context.visualizations,
                style_config=context.style_config,
                output_format=context.report_format
            )

            # Store formatted content
            context.formatted_content = formatted_content

            await self._initiate_validation(pipeline_id)

        except Exception as e:
            logger.error(f"Formatting failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_validation(self, message: ProcessingMessage) -> None:
        """Handle report validation"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(ReportState.REVIEW)

            validation_results = await self._validate_report(
                context.formatted_content,
                context.validation_rules
            )

            context.validation_results = validation_results

            if validation_results["valid"]:
                await self._initiate_export(pipeline_id)
            else:
                await self._handle_validation_failure(pipeline_id, validation_results)

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_export(self, message: ProcessingMessage) -> None:
        """Handle report export"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(ReportState.EXPORT)

            # Export based on format
            if context.report_format == ReportFormat.HTML:
                exported = await self._export_html(context)
            elif context.report_format == ReportFormat.PDF:
                exported = await self._export_pdf(context)
            else:
                exported = await self._export_markdown(context)

            await self._publish_completion(pipeline_id, exported)

        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _publish_status_update(
            self,
            pipeline_id: str,
            state: ReportState,
            message: str
    ) -> None:
        """Publish report status update"""
        status_message = ProcessingMessage(
            message_type=ReportMessageType.REPORT_PROCESS_PROGRESS,
            content={
                "pipeline_id": pipeline_id,
                "state": state.value,
                "message": message,
                "timestamp": datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                correlation_id=pipeline_id,
                source_component=self.module_identifier.component_name
            ),
            source_identifier=self.module_identifier
        )
        await self.message_broker.publish(status_message)

    async def _publish_completion(self, pipeline_id: str, exported_report: Dict[str, Any]) -> None:
        """Publish report generation completion"""
        message = ProcessingMessage(
            message_type=ReportMessageType.REPORT_PROCESS_COMPLETE,
            content={
                "pipeline_id": pipeline_id,
                "report": exported_report,
                "timestamp": datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                correlation_id=pipeline_id,
                source_component=self.module_identifier.component_name
            ),
            source_identifier=self.module_identifier
        )
        await self.message_broker.publish(message)

    async def _publish_error(self, pipeline_id: str, error: str) -> None:
        """Publish report generation error"""
        message = ProcessingMessage(
            message_type=ReportMessageType.REPORT_PROCESS_FAILED,
            content={
                "pipeline_id": pipeline_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                correlation_id=pipeline_id,
                source_component=self.module_identifier.component_name
            ),
            source_identifier=self.module_identifier
        )
        await self.message_broker.publish(message)

    async def cleanup(self) -> None:
        """Cleanup report processor resources"""
        try:
            # Export any remaining reports
            for context in self.active_processes.values():
                if context.formatted_content:
                    await self._handle_export(
                        ProcessingMessage(
                            message_type=ReportMessageType.REPORT_EXPORT_REQUEST,
                            content={"pipeline_id": context.pipeline_id}
                        )
                    )

            # Clear active processes
            self.active_processes.clear()

        except Exception as e:
            logger.error(f"Report processor cleanup failed: {str(e)}")
            raise