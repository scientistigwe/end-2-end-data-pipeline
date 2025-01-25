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
    ProcessingStage
)
from ...staging.staging_manager import StagingManager

logger = logging.getLogger(__name__)

def initialize_services(app):
    services = {
        'report_service': ReportService(
            staging_manager=staging_manager,
            message_broker=message_broker,
            initialize_async=True
        )
    }
    return services

class ReportService:
    """
    Service layer for report functionality.
    Acts as message handler for report-related requests from CPM.
    """
    def __init__(self, staging_manager, message_broker, initialize_async=False):
        self.staging_manager = staging_manager
        self.message_broker = message_broker

        self.module_identifier = ModuleIdentifier(
            component_name="report_service",
            component_type=ComponentType.REPORT_SERVICE,
            department="report",
            role="service"
        )

        self.logger = logger

        if initialize_async:
            asyncio.run(self._initialize_async())

    async def _initialize_async(self):
        await self._initialize_message_handlers()

    async def _initialize_message_handlers(self) -> None:
        handlers = {
            MessageType.REPORT_CREATE_REQUEST: self._handle_create_request,
            MessageType.REPORT_GENERATE_REQUEST: self._handle_generate_request,
            MessageType.REPORT_STATUS_REQUEST: self._handle_status_request,
            MessageType.REPORT_TEMPLATE_REQUEST: self._handle_template_request,
            MessageType.REPORT_SCHEDULE_REQUEST: self._handle_schedule_request,
            MessageType.REPORT_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=f"report.{message_type.value}.#",
                callback=handler
            )
    def _setup_message_handlers(self) -> None:
        """Setup handlers for report-related messages"""
        handlers = {
            MessageType.REPORT_CREATE_REQUEST: self._handle_create_request,
            MessageType.REPORT_GENERATE_REQUEST: self._handle_generate_request,
            MessageType.REPORT_STATUS_REQUEST: self._handle_status_request,
            MessageType.REPORT_TEMPLATE_REQUEST: self._handle_template_request,
            MessageType.REPORT_SCHEDULE_REQUEST: self._handle_schedule_request,
            MessageType.REPORT_ERROR: self._handle_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                component=self.module_identifier.component_name,
                pattern=f"report.{message_type.value}.#",
                callback=handler
            )

    async def _handle_create_request(self, message: ProcessingMessage) -> None:
        """Handle report creation request"""
        try:
            request_data = message.content.get('request_data', {})

            # Store in staging
            staged_id = await self.staging_manager.store_incoming_data(
                pipeline_id=request_data.get('pipeline_id'),
                data=request_data,
                source_type='report_config',
                metadata={
                    'type': 'report_creation',
                    'report_type': request_data.get('report_type'),
                    'template_id': request_data.get('template_id')
                }
            )

            # Forward to report manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_CREATE,
                    content={
                        'staged_id': staged_id,
                        'config': request_data,
                        'pipeline_id': request_data.get('pipeline_id')
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="report_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle create request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_generate_request(self, message: ProcessingMessage) -> None:
        """Handle report generation request"""
        try:
            staged_id = message.content.get('staged_id')
            generation_data = message.content.get('generation_data', {})

            # Forward to report manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_GENERATE,
                    content={
                        'staged_id': staged_id,
                        'generation_data': generation_data,
                        'sections': generation_data.get('sections', []),
                        'visualizations': generation_data.get('visualizations', [])
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="report_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle generate request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_status_request(self, message: ProcessingMessage) -> None:
        """Handle report status request"""
        try:
            staged_id = message.content.get('staged_id')

            # Get staged data
            staged_data = await self.staging_manager.retrieve_data(
                staged_id,
                'REPORT'
            )
            if not staged_data:
                raise ValueError(f"Report {staged_id} not found")

            # Send status response
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_STATUS_RESPONSE,
                    content={
                        'staged_id': staged_id,
                        'status': staged_data.get('status', 'unknown'),
                        'progress': staged_data.get('progress', 0),
                        'sections_completed': staged_data.get('sections_completed', []),
                        'output_url': staged_data.get('output_url'),
                        'created_at': staged_data.get('created_at'),
                        'error': staged_data.get('error')
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component=message.metadata.source_component,
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle status request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_template_request(self, message: ProcessingMessage) -> None:
        """Handle report template request"""
        try:
            template_data = message.content.get('template_data', {})

            # Store template in staging
            staged_id = await self.staging_manager.store_incoming_data(
                pipeline_id=None,
                data=template_data,
                source_type='report_template',
                metadata={
                    'type': 'template_creation',
                    'template_type': template_data.get('template_type')
                }
            )

            # Forward to report manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_TEMPLATE_CREATE,
                    content={
                        'staged_id': staged_id,
                        'template_data': template_data
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="report_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle template request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_schedule_request(self, message: ProcessingMessage) -> None:
        """Handle report schedule request"""
        try:
            schedule_data = message.content.get('schedule_data', {})

            # Store schedule in staging
            staged_id = await self.staging_manager.store_incoming_data(
                pipeline_id=schedule_data.get('pipeline_id'),
                data=schedule_data,
                source_type='report_schedule',
                metadata={
                    'type': 'schedule_creation',
                    'frequency': schedule_data.get('frequency'),
                    'timezone': schedule_data.get('timezone', 'UTC')
                }
            )

            # Forward to report manager
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_SCHEDULE_CREATE,
                    content={
                        'staged_id': staged_id,
                        'schedule_data': schedule_data
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="report_manager",
                        correlation_id=message.metadata.correlation_id
                    )
                )
            )

        except Exception as e:
            self.logger.error(f"Failed to handle schedule request: {str(e)}")
            await self._notify_error(message, str(e))

    async def _handle_error(self, message: ProcessingMessage) -> None:
        """Handle report-related errors"""
        error = message.content.get('error', 'Unknown error')
        self.logger.error(f"Report error received: {error}")

        await self._notify_error(message, error)

    async def _notify_error(self, original_message: ProcessingMessage, error: str) -> None:
        """Notify CPM about errors"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.SERVICE_ERROR,
                content={
                    'service': self.module_identifier.component_name,
                    'error': error,
                    'original_message': original_message.content
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager",
                    correlation_id=original_message.metadata.correlation_id
                )
            )
        )

    async def cleanup(self) -> None:
        """Cleanup service resources"""
        try:
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")