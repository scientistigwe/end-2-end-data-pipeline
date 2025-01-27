# backend/core/services/report_service.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    ReportContext,
    ReportState
)

logger = logging.getLogger(__name__)

class ReportService:
    """
    Report Service: Orchestrates report generation between Manager and Handler.
    - Handles business process orchestration
    - Coordinates data collection
    - Routes messages between manager and handler
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        
        # Service identification
        self.module_identifier = ModuleIdentifier(
            component_name="report_service",
            component_type=ComponentType.REPORT_SERVICE,
            department="report",
            role="service"
        )

        # Active requests
        self.active_requests: Dict[str, ReportContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup service message handlers"""
        handlers = {
            # Manager Messages
            MessageType.REPORT_SERVICE_START: self._handle_service_start,
            MessageType.REPORT_SERVICE_UPDATE: self._handle_service_update,
            MessageType.REPORT_DATA_RECEIVED: self._handle_data_received,

            # Handler Responses
            MessageType.REPORT_HANDLER_COMPLETE: self._handle_handler_complete,
            MessageType.REPORT_HANDLER_ERROR: self._handle_handler_error,
            MessageType.REPORT_HANDLER_STATUS: self._handle_handler_status,

            # Section Messages
            MessageType.REPORT_SECTION_COMPLETE: self._handle_section_complete,
            MessageType.REPORT_VISUALIZATION_COMPLETE: self._handle_visualization_complete
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"report.{message_type.value}.#",
                handler
            )

    async def _handle_service_start(self, message: ProcessingMessage) -> None:
        """Handle service start request from manager"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})

            # Initialize context
            context = ReportContext(
                pipeline_id=pipeline_id,
                state=ReportState.INITIALIZING,
                config=config
            )
            self.active_requests[pipeline_id] = context

            # Track required data sources
            context.required_data = {
                'quality': False,
                'insight': False,
                'analytics': False
            }

            # Forward to handler
            await self._publish_handler_start(
                pipeline_id=pipeline_id,
                config=config
            )

            # Update manager on initialization
            await self._publish_service_status(
                pipeline_id=pipeline_id,
                status=ProcessingStatus.INITIALIZING,
                progress=0.0
            )

        except Exception as e:
            logger.error(f"Service start failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_data_received(self, message: ProcessingMessage) -> None:
        """Handle receipt of input data from a source"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            data_type = message.content.get('data_type')
            data = message.content.get('data')

            context = self.active_requests.get(pipeline_id)
            if not context:
                raise ValueError(f"No active request for pipeline: {pipeline_id}")

            # Store data in context
            context.data_sources[data_type] = data
            context.required_data[data_type] = True

            # Check if all required data is available
            if all(context.required_data.values()):
                await self._start_report_generation(pipeline_id)

        except Exception as e:
            logger.error(f"Data handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _start_report_generation(self, pipeline_id: str) -> None:
        """Start report generation once all data is available"""
        try:
            context = self.active_requests[pipeline_id]
            
            # Forward all data to handler
            await self._publish_handler_generate(
                pipeline_id=pipeline_id,
                data_sources=context.data_sources,
                config=context.config
            )

            # Update status
            await self._publish_service_status(
                pipeline_id=pipeline_id,
                status=ProcessingStatus.IN_PROGRESS,
                progress=25.0
            )

        except Exception as e:
            logger.error(f"Report generation start failed: {str(e)}")
            await self._handle_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _handle_section_complete(self, message: ProcessingMessage) -> None:
        """Handle section completion from handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            section_id = message.content.get('section_id')
            
            context = self.active_requests.get(pipeline_id)
            if context:
                # Track section completion
                context.completed_sections.append(section_id)
                progress = (len(context.completed_sections) / len(context.config['sections'])) * 100

                # Update status
                await self._publish_service_status(
                    pipeline_id=pipeline_id,
                    status=ProcessingStatus.IN_PROGRESS,
                    progress=progress
                )

        except Exception as e:
            logger.error(f"Section completion handling failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _handle_handler_complete(self, message: ProcessingMessage) -> None:
        """Handle completion from handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            report = message.content.get('report')

            context = self.active_requests.get(pipeline_id)
            if context:
                # Forward completion to manager
                await self._publish_service_complete(
                    pipeline_id=pipeline_id,
                    report=report
                )

                # Cleanup
                del self.active_requests[pipeline_id]

        except Exception as e:
            logger.error(f"Handler completion processing failed: {str(e)}")
            await self._handle_error(message, str(e))

    async def _publish_handler_start(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> None:
        """Publish start request to handler"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.REPORT_HANDLER_START,
                content={
                    'pipeline_id': pipeline_id,
                    'config': config,
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

    # ... [Additional publishing methods]

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            # Cleanup active requests
            for pipeline_id in list(self.active_requests.keys()):
                await self._handle_error(
                    ProcessingMessage(content={'pipeline_id': pipeline_id}),
                    "Service cleanup initiated"
                )
                del self.active_requests[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise