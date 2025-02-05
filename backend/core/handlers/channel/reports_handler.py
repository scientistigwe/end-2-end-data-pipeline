# backend/core/handlers/channel/report_handler.py

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
    ReportState,
    ReportContext
)

logger = logging.getLogger(__name__)

class ReportHandler:
    """
    Report Handler: Pure message routing between Service and Processor.
    - Routes report-related messages
    - Transforms message formats
    - No business logic
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        
        # Handler identification
        self.module_identifier = ModuleIdentifier(
            component_name="report_handler",
            component_type=ComponentType.REPORT_HANDLER,
            department="report",
            role="handler"
        )

        # Setup message routing
        self._setup_message_handlers()

    async def _setup_message_handlers(self) -> None:
        """Setup message routing handlers"""
        routing_map = {
            # Service Messages
            MessageType.REPORT_HANDLER_START: self._route_start_request,
            MessageType.REPORT_HANDLER_GENERATE: self._route_generate_request,
            MessageType.REPORT_HANDLER_SECTION: self._route_section_request,
            MessageType.REPORT_HANDLER_VISUALIZATION: self._route_visualization_request,
            MessageType.REPORT_HANDLER_EXPORT: self._route_export_request,

            # Processor Responses
            MessageType.REPORT_PROCESSOR_COMPLETE: self._route_processor_complete,
            MessageType.REPORT_PROCESSOR_ERROR: self._route_processor_error,
            MessageType.REPORT_PROCESSOR_STATUS: self._route_processor_status,
            MessageType.REPORT_SECTION_COMPLETE: self._route_section_complete,
            MessageType.REPORT_VISUALIZATION_COMPLETE: self._route_visualization_complete,

            # Error Handling
            MessageType.REPORT_ERROR: self._handle_error_routing
        }

        for message_type, handler in routing_map.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                f"report.{message_type.value}.#",
                handler
            )

    async def _route_start_request(self, message: ProcessingMessage) -> None:
        """Route start request to processor"""
        try:
            # Transform message
            transformed_message = self._preprocess_message(message)

            # Route to processor
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_PROCESSOR_START,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="report_processor",
                        domain_type="report",
                        processing_stage=ProcessingStage.REPORT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_section_request(self, message: ProcessingMessage) -> None:
        """Route section generation request to processor"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_PROCESSOR_SECTION,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="report_processor",
                        domain_type="report",
                        processing_stage=ProcessingStage.REPORT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_visualization_request(self, message: ProcessingMessage) -> None:
        """Route visualization generation request to processor"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_PROCESSOR_VISUALIZATION,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="report_processor",
                        domain_type="report",
                        processing_stage=ProcessingStage.REPORT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    async def _route_section_complete(self, message: ProcessingMessage) -> None:
        """Route section completion to service"""
        try:
            transformed_message = self._preprocess_message(message)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_HANDLER_SECTION_COMPLETE,
                    content=transformed_message.content,
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="report_service",
                        domain_type="report",
                        processing_stage=ProcessingStage.REPORT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            await self._publish_routing_error(message, str(e))

    def _preprocess_message(self, message: ProcessingMessage) -> ProcessingMessage:
        """
        Preprocess message for routing
        - Validate required fields
        - Normalize message structure
        - Add routing metadata
        """
        required_fields = ['pipeline_id']
        
        # Validate message content
        for field in required_fields:
            if field not in message.content:
                raise ValueError(f"Missing required field: {field}")

        # Add routing metadata
        if not message.metadata:
            message.metadata = MessageMetadata()
            
        message.metadata.domain_type = "report"
        message.metadata.processing_stage = ProcessingStage.REPORT_GENERATION
        
        return message

    async def _publish_routing_error(
            self,
            original_message: ProcessingMessage,
            error: str
    ) -> None:
        """Publish routing error"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.REPORT_ERROR,
                content={
                    'error': error,
                    'original_message': original_message.content,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="report_service",
                    domain_type="report",
                    processing_stage=ProcessingStage.REPORT_GENERATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_error_routing(self, message: ProcessingMessage) -> None:
        """Handle error routing"""
        logger.error(f"Routing error: {message.content}")
        
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.SYSTEM_ERROR,
                    content={
                        'error_source': 'report_handler',
                        'original_message': message.content,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="error_handler",
                        domain_type="report"
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.critical(f"Error handling failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            # Unsubscribe from all patterns
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise