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

    async def _setup_message_handlers(self) -> None:
        """Setup service message handlers"""
        handlers = {
            # Report Process Flow
            MessageType.REPORT_PROCESS_START: self._handle_service_start,
            MessageType.REPORT_PROCESS_FAILED: self._handle_error,
            MessageType.REPORT_PROCESS_COMPLETE: self._handle_handler_complete,

            # Data and Section Handling
            MessageType.REPORT_DATA_PREPARE_REQUEST: self._handle_data_received,
            MessageType.REPORT_SECTION_GENERATE_REQUEST: self._handle_section_generation,
            MessageType.REPORT_SECTION_GENERATE_COMPLETE: self._handle_section_complete,

            # Visualization and Reporting
            MessageType.REPORT_VISUALIZATION_GENERATE_REQUEST: self._handle_visualization_request,
            MessageType.REPORT_VISUALIZATION_GENERATE_COMPLETE: self._handle_visualization_complete,

            # Validation and Review
            MessageType.REPORT_VALIDATE_REQUEST: self._handle_report_validation,
            MessageType.REPORT_VALIDATE_COMPLETE: self._handle_validation_complete,

            # Configuration and Updates
            MessageType.REPORT_CONFIG_UPDATE: self._handle_config_update,

            # Error Handling
            MessageType.REPORT_COMPONENT_ERROR: self._handle_component_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def _handle_component_error(self, message: ProcessingMessage) -> None:
        """
        Handle errors reported by a specific report component

        Args:
            message (ProcessingMessage): Message containing component error details
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_requests.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for component error in pipeline {pipeline_id}")
                return

            # Extract error details
            error_component = message.content.get('component', 'unknown')
            error_details = message.content.get('error', {})

            # Log the error
            logger.error(f"Report component error: {error_details}")

            # Publish comprehensive error notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'component': error_component,
                        'error_details': error_details,
                        'timestamp': datetime.now().isoformat(),
                        'current_state': context.state.value
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        processing_stage=ProcessingStage.REPORT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Attempt error recovery
            await self._handle_error_recovery(context, error_component, error_details)

        except Exception as e:
            logger.error(f"Component error handling failed: {str(e)}")
            await self._handle_error(message, f"Component error handling failed: {str(e)}")

    async def _handle_error_recovery(self, context: ReportContext, error_component: str,
                                     error_details: Dict[str, Any]) -> None:
        """
        Attempt to recover from component error

        Args:
            context (ReportContext): Current report context
            error_component (str): Component that reported the error
            error_details (Dict[str, Any]): Error details
        """
        # Determine error severity
        error_severity = error_details.get('severity', 'medium')

        # Track error attempts
        error_count = context.retry_counts.get(error_component, 0) + 1
        context.retry_counts[error_component] = error_count

        # Recovery strategy
        if error_severity in ['low', 'medium'] and error_count <= 3:
            # Attempt to restart or recover the component
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_PROCESS_PROGRESS,
                    content={
                        'pipeline_id': context.pipeline_id,
                        'component': error_component,
                        'action': 'recover',
                        'retry_count': error_count
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )
        else:
            # Critical error or max retries exceeded
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.REPORT_PROCESS_FAILED,
                    content={
                        'pipeline_id': context.pipeline_id,
                        'reason': f'Unrecoverable error in {error_component}',
                        'error_details': error_details
                    }
                ),
                f"Unrecoverable error in component {error_component}"
            )

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """
        Handle configuration update for report service

        Args:
            message (ProcessingMessage): Message containing configuration updates
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_requests.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for config update in pipeline {pipeline_id}")
                return

            # Extract configuration updates
            config_updates = message.content.get('config', {})

            # Update context configuration
            context.config.update(config_updates)

            # Publish configuration update acknowledgment
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_CONFIG_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'updated',
                        'applied_configs': list(config_updates.keys())
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

            # Trigger reconfiguration of report components
            await self._apply_config_updates(context, config_updates)

        except Exception as e:
            logger.error(f"Configuration update failed: {str(e)}")
            await self._handle_error(message, f"Config update error: {str(e)}")

    async def _handle_report_validation(self, message: ProcessingMessage) -> None:
        """
        Handle report validation request

        Args:
            message (ProcessingMessage): Message containing validation request
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_requests.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for report validation in pipeline {pipeline_id}")
                return

            # Update context state
            context.state = ReportState.VALIDATION

            # Publish validation start
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_VALIDATE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'report_data': context.data_sources,
                        'validation_rules': context.config.get('validation_rules', {})
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        processing_stage=ProcessingStage.REPORT_GENERATION
                    )
                )
            )

        except Exception as e:
            logger.error(f"Report validation request failed: {str(e)}")
            await self._handle_error(message, f"Validation request error: {str(e)}")

    async def _handle_validation_complete(self, message: ProcessingMessage) -> None:
        """
        Handle completion of report validation

        Args:
            message (ProcessingMessage): Message containing validation results
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_requests.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for validation completion in pipeline {pipeline_id}")
                return

            # Process validation results
            validation_result = message.content.get('validation_result', {})
            is_valid = validation_result.get('is_valid', False)

            if is_valid:
                # Validation passed, proceed to visualization
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.REPORT_VALIDATE_APPROVE,
                        content={
                            'pipeline_id': pipeline_id,
                            'validation_details': validation_result
                        },
                        metadata=MessageMetadata(
                            correlation_id=context.correlation_id,
                            source_component=self.module_identifier.component_name
                        )
                    )
                )

                # Trigger visualization generation
                await self._handle_visualization_request(
                    ProcessingMessage(
                        content={
                            'pipeline_id': pipeline_id
                        }
                    )
                )
            else:
                # Validation failed
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.REPORT_VALIDATE_REJECT,
                        content={
                            'pipeline_id': pipeline_id,
                            'validation_details': validation_result,
                            'errors': validation_result.get('errors', [])
                        },
                        metadata=MessageMetadata(
                            correlation_id=context.correlation_id,
                            source_component=self.module_identifier.component_name
                        )
                    )
                )

                # Handle validation failure
                await self._handle_validation_failure(context, validation_result)

        except Exception as e:
            logger.error(f"Validation completion processing failed: {str(e)}")
            await self._handle_error(message, f"Validation completion error: {str(e)}")

    async def _handle_visualization_request(self, message: ProcessingMessage) -> None:
        """
        Handle request to generate report visualizations

        Args:
            message (ProcessingMessage): Message containing visualization request
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_requests.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for visualization in pipeline {pipeline_id}")
                return

            # Update context state
            context.state = ReportState.VISUALIZATION_CREATION

            # Publish visualization generation start
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_VISUALIZATION_GENERATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'data_sources': context.data_sources,
                        'visualization_config': context.config.get('visualization', {})
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        processing_stage=ProcessingStage.REPORT_GENERATION
                    )
                )
            )

        except Exception as e:
            logger.error(f"Visualization request failed: {str(e)}")
            await self._handle_error(message, f"Visualization request error: {str(e)}")

    async def _handle_visualization_complete(self, message: ProcessingMessage) -> None:
        """
        Handle completion of report visualization generation

        Args:
            message (ProcessingMessage): Message containing visualization results
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_requests.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for visualization completion in pipeline {pipeline_id}")
                return

            # Store visualizations
            visualizations = message.content.get('visualizations', [])
            context.visualizations = visualizations

            # Publish visualization completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_VISUALIZATION_GENERATE_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'visualization_count': len(visualizations)
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

            # Proceed to report generation
            await self._start_final_report_generation(context)

        except Exception as e:
            logger.error(f"Visualization completion processing failed: {str(e)}")
            await self._handle_error(message, f"Visualization completion error: {str(e)}")

    async def _handle_section_generation(self, message: ProcessingMessage) -> None:
        """
        Handle request to generate specific report sections

        Args:
            message (ProcessingMessage): Message containing section generation request
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = self.active_requests.get(pipeline_id)

            if not context:
                logger.warning(f"No context found for section generation in pipeline {pipeline_id}")
                return

            # Determine sections to generate
            requested_sections = message.content.get('sections', context.config.get('sections', []))

            # Publish section generation request
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_SECTION_GENERATE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'sections': requested_sections,
                        'data_sources': context.data_sources
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        processing_stage=ProcessingStage.REPORT_GENERATION
                    )
                )
            )

        except Exception as e:
            logger.error(f"Section generation failed: {str(e)}")
            await self._handle_error(message, f"Section generation error: {str(e)}")

    async def _handle_error(self, message: ProcessingMessage, error_message: str) -> None:
        """
        Handle processing errors

        Args:
            message (ProcessingMessage): Original message that caused the error
            error_message (str): Detailed error description
        """
        try:
            pipeline_id = message.content.get('pipeline_id')

            if not pipeline_id:
                logger.error(f"Error without pipeline ID: {error_message}")
                return

            context = self.active_requests.get(pipeline_id)

            # Publish error notification
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error_message,
                        'timestamp': datetime.now().isoformat()
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id if context else None,
                        source_component=self.module_identifier.component_name
                    )
                )
            )

            # Cleanup context if exists
            if context:
                context.state = ReportState.FAILED
                del self.active_requests[pipeline_id]

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _start_final_report_generation(self, context: ReportContext) -> None:
        """
        Initiate final report generation after visualizations

        Args:
            context (ReportContext): Current report context
        """
        try:
            # Publish final report generation request
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_GENERATE_REQUEST,
                    content={
                        'pipeline_id': context.pipeline_id,
                        'data_sources': context.data_sources,
                        'visualizations': context.visualizations,
                        'config': context.config
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name,
                        processing_stage=ProcessingStage.REPORT_GENERATION
                    )
                )
            )

        except Exception as e:
            logger.error(f"Final report generation failed: {str(e)}")
            await self._handle_error(
                ProcessingMessage(content={'pipeline_id': context.pipeline_id}),
                f"Final report generation error: {str(e)}"
            )

    async def _handle_validation_failure(self, context: ReportContext, validation_result: Dict[str, Any]) -> None:
        """
        Handle validation failure scenarios

        Args:
            context (ReportContext): Current report context
            validation_result (Dict[str, Any]): Validation result details
        """
        retry_count = context.retry_counts.get('validation', 0) + 1
        context.retry_counts['validation'] = retry_count

        if retry_count <= 3:
            # Attempt to regenerate or correct data
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_VALIDATE_RETRY,
                    content={
                        'pipeline_id': context.pipeline_id,
                        'validation_errors': validation_result.get('errors', []),
                        'retry_count': retry_count
                    },
                    metadata=MessageMetadata(
                        correlation_id=context.correlation_id,
                        source_component=self.module_identifier.component_name
                    )
                )
            )
        else:
            # Max retries exceeded
            await self._handle_error(
                ProcessingMessage(content={'pipeline_id': context.pipeline_id}),
                "Maximum validation retries exceeded"
            )

    async def _apply_config_updates(self, context: ReportContext, config_updates: Dict[str, Any]) -> None:
        """
        Apply configuration updates to report components

        Args:
            context (ReportContext): Current report context
            config_updates (Dict[str, Any]): Configuration updates to apply
        """
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.REPORT_TEMPLATE_UPDATE,
                content={
                    'pipeline_id': context.pipeline_id,
                    'config_updates': config_updates
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="report_handler"
                )
            )
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