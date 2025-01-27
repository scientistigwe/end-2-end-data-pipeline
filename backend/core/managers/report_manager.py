# backend/core/managers/report_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
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


class ReportManager:
    """
    Report Manager: Coordinates high-level report workflow.
    - Communicates with CPM
    - Tracks data dependencies
    - Coordinates through messages
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Manager identification
        self.module_identifier = ModuleIdentifier(
            component_name="report_manager",
            component_type=ComponentType.REPORT_MANAGER,
            department="report",
            role="manager"
        )

        # Active processes
        self.active_processes: Dict[str, ReportContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup message handlers"""
        handlers = {
            # CPM Messages
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.CONTROL_POINT_UPDATE: self._handle_control_point_update,

            # Data Source Messages
            MessageType.QUALITY_COMPLETE: self._handle_quality_complete,
            MessageType.INSIGHT_COMPLETE: self._handle_insight_complete,
            MessageType.ANALYTICS_COMPLETE: self._handle_analytics_complete,

            # Service Messages
            MessageType.REPORT_SERVICE_STATUS: self._handle_service_status,
            MessageType.REPORT_SERVICE_COMPLETE: self._handle_service_complete,
            MessageType.REPORT_SERVICE_ERROR: self._handle_service_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_control_point_created(self, message: ProcessingMessage) -> None:
        """Handle new control point for report generation"""
        try:
            pipeline_id = message.content['pipeline_id']
            control_point_id = message.content['control_point_id']
            config = message.content.get('config', {})

            # Initialize context
            context = ReportContext(
                pipeline_id=pipeline_id,
                report_type=config.get('report_type', 'default'),
                format=config.get('format', 'html'),
                sections=config.get('sections', []),
                template_name=config.get('template')
            )
            self.active_processes[pipeline_id] = context

            # Start service processing
            await self._publish_service_start(pipeline_id, config)

        except Exception as e:
            logger.error(f"Control point handling failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """Handle quality analysis completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            quality_data = message.content['quality_results']

            context = self.active_processes.get(pipeline_id)
            if context:
                # Forward quality data to service
                await self._publish_service_data(
                    pipeline_id=pipeline_id,
                    data_type="quality",
                    data=quality_data
                )

        except Exception as e:
            logger.error(f"Quality data handling failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_service_status(self, message: ProcessingMessage) -> None:
        """Handle status from service"""
        try:
            pipeline_id = message.content['pipeline_id']
            status = message.content['status']

            # Forward status to CPM
            await self._publish_status_update(
                pipeline_id=pipeline_id,
                status=status
            )

        except Exception as e:
            logger.error(f"Status handling failed: {str(e)}")

    async def _publish_service_start(self, pipeline_id: str, config: Dict[str, Any]) -> None:
        """
        Initiate report service processing

        Args:
            pipeline_id (str): Unique identifier for the processing pipeline
            config (Dict[str, Any]): Configuration for report generation
        """
        try:
            message = ProcessingMessage(
                message_type=MessageType.REPORT_SERVICE_START,
                content={
                    'pipeline_id': pipeline_id,
                    'config': config,
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier,
                target_identifier=ModuleIdentifier(
                    component_name="report_service",
                    component_type=ComponentType.REPORT_SERVICE,
                    department="report",
                    role="service"
                ),
                metadata=MessageMetadata(
                    source_component="report_manager",
                    target_component="report_service",
                    domain_type="report",
                    processing_stage=ProcessingStage.REPORT_GENERATION,
                    correlation_id=pipeline_id
                )
            )
            await self.message_broker.publish(message)
            logger.info(f"Report service start initiated for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Failed to publish report service start: {str(e)}")
            await self._publish_error(pipeline_id, f"Service start error: {str(e)}")

    async def _publish_error(self, pipeline_id: str, error_message: str) -> None:
        """
        Publish error messages to the system

        Args:
            pipeline_id (str): Unique identifier for the processing pipeline
            error_message (str): Detailed error description
        """
        try:
            message = ProcessingMessage(
                message_type=MessageType.FLOW_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'error': error_message,
                    'component': 'report_manager',
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier,
                target_identifier=ModuleIdentifier(
                    component_name="control_point_manager",
                    component_type=ComponentType.ORCHESTRATOR,
                    department="control",
                    role="manager"
                ),
                metadata=MessageMetadata(
                    source_component="report_manager",
                    target_component="control_point_manager",
                    domain_type="error",
                    processing_stage=ProcessingStage.ERROR_HANDLING,
                    correlation_id=pipeline_id
                )
            )
            await self.message_broker.publish(message)
            logger.error(f"Error reported for pipeline {pipeline_id}: {error_message}")
        except Exception as e:
            logger.critical(f"Failed to publish error message: {str(e)}")

    async def _publish_service_data(self, pipeline_id: str, data_type: str, data: Any) -> None:
        """
        Send data to report service for processing

        Args:
            pipeline_id (str): Unique identifier for the processing pipeline
            data_type (str): Type of data being sent (e.g., 'quality', 'insight')
            data (Any): Data payload to be processed
        """
        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No active context found for pipeline {pipeline_id}")
                return

            message = ProcessingMessage(
                message_type=MessageType.REPORT_DATA_RECEIVED,
                content={
                    'pipeline_id': pipeline_id,
                    'data_type': data_type,
                    'data': data,
                    'report_type': context.report_type,
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier,
                target_identifier=ModuleIdentifier(
                    component_name="report_service",
                    component_type=ComponentType.REPORT_SERVICE,
                    department="report",
                    role="service"
                ),
                metadata=MessageMetadata(
                    source_component="report_manager",
                    target_component="report_service",
                    domain_type="report",
                    processing_stage=ProcessingStage.DATA_PROCESSING,
                    correlation_id=pipeline_id
                )
            )
            await self.message_broker.publish(message)
            logger.info(f"Sent {data_type} data to report service for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Failed to publish service data: {str(e)}")
            await self._publish_error(pipeline_id, f"Service data error: {str(e)}")

    async def _publish_status_update(self, pipeline_id: str, status: ProcessingStatus) -> None:
        """
        Update the Control Point Manager about current processing status

        Args:
            pipeline_id (str): Unique identifier for the processing pipeline
            status (ProcessingStatus): Current status of the report generation
        """
        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No active context found for pipeline {pipeline_id}")
                return

            message = ProcessingMessage(
                message_type=MessageType.PROCESSING_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': status.value,
                    'report_type': context.report_type,
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier,
                target_identifier=ModuleIdentifier(
                    component_name="control_point_manager",
                    component_type=ComponentType.ORCHESTRATOR,
                    department="control",
                    role="manager"
                ),
                metadata=MessageMetadata(
                    source_component="report_manager",
                    target_component="control_point_manager",
                    domain_type="report",
                    processing_stage=ProcessingStage.REPORT_GENERATION,
                    correlation_id=pipeline_id
                )
            )
            await self.message_broker.publish(message)
            logger.info(f"Status update for pipeline {pipeline_id}: {status}")
        except Exception as e:
            logger.error(f"Failed to publish status update: {str(e)}")
            await self._publish_error(pipeline_id, f"Status update error: {str(e)}")

    async def _handle_control_point_update(self, message: ProcessingMessage) -> None:
        """
        Handle updates to the control point for report generation

        Args:
            message (ProcessingMessage): Message containing control point update details
        """
        try:
            pipeline_id = message.content['pipeline_id']
            update_type = message.content.get('update_type')

            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No active context for pipeline {pipeline_id}")
                return

            # Perform specific actions based on update type
            if update_type == 'template_change':
                context.template_name = message.content.get('template_name')
            elif update_type == 'format_change':
                context.format = message.content.get('format')

            logger.info(f"Control point update processed for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Control point update failed: {str(e)}")
            await self._publish_error(pipeline_id, f"Control point update error: {str(e)}")

    async def _handle_insight_complete(self, message: ProcessingMessage) -> None:
        """
        Process completed insight data for report generation

        Args:
            message (ProcessingMessage): Message containing insight data
        """
        try:
            pipeline_id = message.content['pipeline_id']
            insight_data = message.content['insight_results']

            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No active context for pipeline {pipeline_id}")
                return

            # Forward insight data to report service
            await self._publish_service_data(
                pipeline_id=pipeline_id,
                data_type="insight",
                data=insight_data
            )
            logger.info(f"Insight data processed for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Insight data handling failed: {str(e)}")
            await self._publish_error(pipeline_id, f"Insight processing error: {str(e)}")

    async def _handle_analytics_complete(self, message: ProcessingMessage) -> None:
        """
        Process completed analytics data for report generation

        Args:
            message (ProcessingMessage): Message containing analytics data
        """
        try:
            pipeline_id = message.content['pipeline_id']
            analytics_data = message.content['analytics_results']

            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No active context for pipeline {pipeline_id}")
                return

            # Forward analytics data to report service
            await self._publish_service_data(
                pipeline_id=pipeline_id,
                data_type="analytics",
                data=analytics_data
            )
            logger.info(f"Analytics data processed for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Analytics data handling failed: {str(e)}")
            await self._publish_error(pipeline_id, f"Analytics processing error: {str(e)}")

    async def _handle_service_complete(self, message: ProcessingMessage) -> None:
        """
        Handle successful completion of report service

        Args:
            message (ProcessingMessage): Message containing service completion details
        """
        try:
            pipeline_id = message.content['pipeline_id']
            report_location = message.content.get('report_location')
            report_metadata = message.content.get('report_metadata', {})

            context = self.active_processes.get(pipeline_id)
            if not context:
                logger.warning(f"No active context for pipeline {pipeline_id}")
                return

            # Update context with final report details
            context.state = ReportState.COMPLETED
            context.report_location = report_location
            context.metadata = report_metadata

            # Notify CPM about successful report generation
            await self._publish_status_update(
                pipeline_id=pipeline_id,
                status=ProcessingStatus.COMPLETED
            )

            # Cleanup active process
            del self.active_processes[pipeline_id]
            logger.info(f"Report generation completed for pipeline {pipeline_id}")
        except Exception as e:
            logger.error(f"Service completion handling failed: {str(e)}")
            await self._publish_error(pipeline_id, f"Service completion error: {str(e)}")

    async def _handle_service_error(self, message: ProcessingMessage) -> None:
        """
        Handle errors from report service

        Args:
            message (ProcessingMessage): Message containing service error details
        """
        try:
            pipeline_id = message.content['pipeline_id']
            error_details = message.content.get('error', 'Unknown error')

            context = self.active_processes.get(pipeline_id)
            if context:
                context.state = ReportState.FAILED

            # Publish detailed error
            await self._publish_error(
                pipeline_id=pipeline_id,
                error_message=f"Report service error: {error_details}"
            )

            # Notify CPM about failure
            await self._publish_status_update(
                pipeline_id=pipeline_id,
                status=ProcessingStatus.FAILED
            )

            # Cleanup active process
            if pipeline_id in self.active_processes:
                del self.active_processes[pipeline_id]

            logger.error(f"Report service error for pipeline {pipeline_id}: {error_details}")
        except Exception as e:
            logger.critical(f"Error handling service error failed: {str(e)}")