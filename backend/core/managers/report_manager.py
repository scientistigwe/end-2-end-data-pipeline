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
    ManagerState,
    ReportContext,
    ReportState
)

from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class ReportManager(BaseManager):
    """
    Report Manager: Coordinates high-level report workflow.
    - Communicates with CPM
    - Tracks data dependencies
    - Coordinates through messages
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str = "report_manager",
            domain_type: str = "report"
    ):
        # Call base class initialization first
        super().__init__(
            message_broker=message_broker,
            component_name=component_name,
            domain_type=domain_type
        )

        # Active processes and contexts
        self.active_processes: Dict[str, ReportContext] = {}

        # Report configuration
        self.report_thresholds = {
            "max_section_size": 1024 * 1024,  # 1MB
            "max_processing_time": 1800,  # 30 minutes
            "validation_threshold": 0.8
        }

    async def _initialize_manager(self) -> None:
        """Initialize report manager components"""
        try:
            # Initialize base components - this will also start background tasks
            await super()._initialize_manager()

            # Setup report-specific message handlers
            await self._setup_domain_handlers()

            # Update state
            self.state = ManagerState.ACTIVE
            logger.info(f"Report manager initialized successfully: {self.context.component_name}")

        except Exception as e:
            logger.error(f"Failed to initialize report manager: {str(e)}")
            self.state = ManagerState.ERROR
            raise

    async def _setup_domain_handlers(self) -> None:
        """Setup report-specific message handlers"""
        handlers = {
            # Report generation
            MessageType.REPORT_GENERATE_REQUEST: self._handle_generate_request,
            MessageType.REPORT_SECTION_GENERATE_REQUEST: self._handle_section_generate,
            MessageType.REPORT_VISUALIZATION_GENERATE_REQUEST: self._handle_visualization_generate,

            # Report validation
            MessageType.REPORT_VALIDATE_REQUEST: self._handle_validate_request,
            MessageType.REPORT_VALIDATE_COMPLETE: self._handle_validate_complete,
            MessageType.REPORT_VALIDATE_REJECT: self._handle_validate_reject,

            # Report delivery
            MessageType.REPORT_EXPORT_REQUEST: self._handle_export_request,
            MessageType.REPORT_DELIVERY_REQUEST: self._handle_delivery_request,

            # Report formatting
            MessageType.REPORT_FORMAT_REQUEST: self._handle_format_request,
            MessageType.REPORT_STYLE_UPDATE: self._handle_style_update,
            MessageType.REPORT_TEMPLATE_UPDATE: self._handle_template_update
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

    async def _handle_section_generate(self, message: ProcessingMessage) -> None:
        """Handle request to generate a specific report section"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            section_type = message.content.get('section_type')
            section_config = message.content.get('config', {})

            # Update context state
            context.current_section = section_type
            context.updated_at = datetime.now()

            # Request section generation from service
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_SECTION_GENERATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'section_type': section_type,
                        'config': section_config,
                        'template_name': context.template_name
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="report_service",
                        domain_type="report"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Section generation request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_visualization_generate(self, message: ProcessingMessage) -> None:
        """Handle request to generate report visualization"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            visualization_type = message.content.get('visualization_type')
            data = message.content.get('data', {})
            viz_config = message.content.get('config', {})

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_VISUALIZATION_GENERATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'visualization_type': visualization_type,
                        'data': data,
                        'config': viz_config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="report_service",
                        domain_type="report"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Visualization generation request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validate_request(self, message: ProcessingMessage) -> None:
        """Handle request to validate report"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            validation_config = message.content.get('validation_config', {})

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_VALIDATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'sections': context.sections,
                        'config': validation_config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="report_service",
                        domain_type="report"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Report validation request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validate_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of report validation"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            validation_results = message.content.get('validation_results', {})

            if validation_results.get('is_valid', False):
                # Proceed with export
                await self._handle_export_request(
                    ProcessingMessage(
                        message_type=MessageType.REPORT_EXPORT_REQUEST,
                        content={
                            'pipeline_id': pipeline_id,
                            'format': context.format
                        }
                    )
                )
            else:
                await self._handle_validate_reject(
                    ProcessingMessage(
                        message_type=MessageType.REPORT_VALIDATE_REJECT,
                        content={
                            'pipeline_id': pipeline_id,
                            'validation_results': validation_results
                        }
                    )
                )

        except Exception as e:
            logger.error(f"Validation completion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validate_reject(self, message: ProcessingMessage) -> None:
        """Handle report validation rejection"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            validation_results = message.content.get('validation_results', {})
            context.validation_issues = validation_results.get('issues', [])

            # Notify about validation failure
            await self._publish_error(
                pipeline_id,
                f"Report validation failed: {validation_results.get('reason', 'Unknown reason')}"
            )

        except Exception as e:
            logger.error(f"Validation rejection handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_export_request(self, message: ProcessingMessage) -> None:
        """Handle request to export report"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            export_format = message.content.get('format', context.format)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_EXPORT_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'format': export_format,
                        'sections': context.sections,
                        'metadata': context.metadata
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="report_service",
                        domain_type="report"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Export request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_delivery_request(self, message: ProcessingMessage) -> None:
        """Handle request to deliver report"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            delivery_config = message.content.get('delivery_config', {})

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_DELIVERY_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'report_location': context.report_location,
                        'config': delivery_config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="report_service",
                        domain_type="report"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Delivery request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_format_request(self, message: ProcessingMessage) -> None:
        """Handle request to format report"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            format_config = message.content.get('format_config', {})

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_FORMAT_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'sections': context.sections,
                        'config': format_config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.context.component_name,
                        target_component="report_service",
                        domain_type="report"
                    )
                )
            )

        except Exception as e:
            logger.error(f"Format request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_style_update(self, message: ProcessingMessage) -> None:
        """Handle report style updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            style_updates = message.content.get('style_updates', {})
            context.style_config.update(style_updates)

            # Apply style updates to report
            await self._apply_style_updates(pipeline_id, style_updates)

        except Exception as e:
            logger.error(f"Style update failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_template_update(self, message: ProcessingMessage) -> None:
        """Handle report template updates"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            new_template = message.content.get('template_name')
            if new_template:
                context.template_name = new_template
                await self._apply_template_update(pipeline_id, new_template)

        except Exception as e:
            logger.error(f"Template update failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_generate_request(self, message: ProcessingMessage) -> None:
        """Handle report generation request"""
        try:
            pipeline_id = message.content['pipeline_id']
            report_config = message.content.get('config', {})

            # Initialize report context
            self.report_contexts[pipeline_id] = {
                'status': 'initializing',
                'config': report_config,
                'sections': [],
                'visualizations': [],
                'created_at': datetime.now()
            }

            # Start report generation
            await self._generate_report_sections(pipeline_id, report_config)

        except Exception as e:
            await self._handle_error(message, e)

    async def _generate_report_sections(self, pipeline_id: str, config: Dict[str, Any]) -> None:
        """Generate report sections based on config"""
        raise NotImplementedError

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