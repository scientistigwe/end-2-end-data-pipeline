import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

from backend.core.channel_handlers.base_channel_handler import BaseChannelHandler
from backend.core.channel_handlers.core_process_handler import CoreProcessHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    ModuleIdentifier,
    ComponentType
)
from backend.data_pipeline.reporting.report_processor import (
    ReportProcessor,
    ReportPhase
)

logger = logging.getLogger(__name__)


class ReportHandler(BaseChannelHandler):
    """
    Handles communication and routing for report-related messages

    Responsibilities:
    - Route report-related messages
    - Coordinate with report processor
    - Interface with report manager
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            process_handler: Optional[CoreProcessHandler] = None,
            report_processor: Optional[ReportProcessor] = None
    ):
        """Initialize report handler"""
        super().__init__(message_broker, "report_handler")

        # Initialize dependencies
        self.process_handler = process_handler or CoreProcessHandler(message_broker)
        self.report_processor = report_processor or ReportProcessor(message_broker)

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers for report processing"""
        self.register_callback(
            MessageType.REPORT_START,
            self._handle_report_start
        )
        self.register_callback(
            MessageType.REPORT_COMPLETE,
            self._handle_report_complete
        )
        self.register_callback(
            MessageType.REPORT_UPDATE,
            self._handle_report_update
        )
        self.register_callback(
            MessageType.REPORT_ERROR,
            self._handle_report_error
        )

    def _handle_report_start(self, message: ProcessingMessage) -> None:
        """Handle report generation start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            data = message.content.get('data', {})
            context = message.content.get('context', {})

            # Create response message to report manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="report_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_report_start"
                ),
                message_type=MessageType.REPORT_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': 'started',
                    'phase': ReportPhase.DATA_GATHERING.value
                }
            )

            # Execute process via process handler
            self.process_handler.execute_process(
                self._run_report_process,
                pipeline_id=pipeline_id,
                stage=ProcessingStage.REPORT_GENERATION,
                message_type=MessageType.REPORT_START,
                data=data,
                context=context
            )

            # Publish response to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to start report process: {e}")
            self._handle_report_error(
                ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="report_manager",
                        component_type=ComponentType.MANAGER
                    ),
                    message_type=MessageType.REPORT_ERROR,
                    content={
                        'error': str(e),
                        'pipeline_id': message.content.get('pipeline_id')
                    }
                )
            )

    async def _run_report_process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Core report process execution logic"""
        try:
            # Gather necessary data
            report_data = await self.report_processor.gather_data(
                context.get('run_id'),
                data,
                context
            )

            # Generate report sections
            sections = await self.report_processor.generate_sections(
                context.get('run_id'),
                report_data,
                context
            )

            # Generate visualizations
            visualizations = await self.report_processor.generate_visualizations(
                context.get('run_id'),
                sections,
                context
            )

            # Run validations
            validations = await self.report_processor.run_validations(
                context.get('run_id'),
                report_data,
                context
            )

            # Compile final report
            final_report = await self.report_processor.compile_report(
                context.get('run_id'),
                report_data,
                sections,
                visualizations,
                validations,
                context
            )

            return {
                'report_data': report_data,
                'sections': sections,
                'visualizations': visualizations,
                'validations': validations,
                'final_report': final_report,
                'pipeline_id': context.get('pipeline_id')
            }

        except Exception as e:
            logger.error(f"Report process failed: {e}")
            raise

    def _handle_report_complete(self, message: ProcessingMessage) -> None:
        """Handle report process completion"""
        try:
            # Create completion response for manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="report_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_report_complete"
                ),
                message_type=MessageType.REPORT_COMPLETE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'results': message.content.get('results', {}),
                    'status': 'completed',
                    'output_url': message.content.get('output_url'),
                    'output_size': message.content.get('output_size')
                }
            )

            # Publish completion to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling report completion: {e}")

    def _handle_report_update(self, message: ProcessingMessage) -> None:
        """Handle report process updates"""
        try:
            # Forward update to report manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="report_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_report_update"
                ),
                message_type=MessageType.REPORT_STATUS_UPDATE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'status': message.content.get('status'),
                    'progress': message.content.get('progress'),
                    'phase': message.content.get('phase'),
                    'section_status': message.content.get('section_status', {}),
                    'visualization_status': message.content.get('visualization_status', {})
                }
            )

            # Publish update to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling report update: {e}")

    def _handle_report_error(self, message: ProcessingMessage) -> None:
        """Handle report process errors"""
        try:
            # Forward error to report manager
            error_response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="report_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_report_error"
                ),
                message_type=MessageType.REPORT_ERROR,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'error': message.content.get('error'),
                    'phase': message.content.get('phase'),
                    'context': message.content.get('context', {})
                }
            )

            # Publish error to manager
            self.message_broker.publish(error_response)

        except Exception as e:
            logger.error(f"Error handling report error: {e}")

    def _handle_section_complete(self, message: ProcessingMessage) -> None:
        """Handle section generation completion"""
        try:
            # Forward section completion to report manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="report_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_section_complete"
                ),
                message_type=MessageType.SECTION_COMPLETE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'section_id': message.content.get('section_id'),
                    'section_data': message.content.get('section_data', {}),
                    'generation_time': message.content.get('generation_time')
                }
            )

            # Publish section completion
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling section completion: {e}")

    def _handle_visualization_complete(self, message: ProcessingMessage) -> None:
        """Handle visualization generation completion"""
        try:
            # Forward visualization completion to report manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="report_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_visualization_complete"
                ),
                message_type=MessageType.VISUALIZATION_COMPLETE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'section_id': message.content.get('section_id'),
                    'visualization_id': message.content.get('visualization_id'),
                    'visualization_data': message.content.get('visualization_data', {}),
                    'generation_time': message.content.get('generation_time')
                }
            )

            # Publish visualization completion
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling visualization completion: {e}")

    def _handle_validation_complete(self, message: ProcessingMessage) -> None:
        """Handle validation completion"""
        try:
            # Forward validation completion to report manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="report_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_validation_complete"
                ),
                message_type=MessageType.VALIDATION_COMPLETE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'validation_id': message.content.get('validation_id'),
                    'validation_results': message.content.get('validation_results', {}),
                    'status': message.content.get('status'),
                    'execution_time': message.content.get('execution_time')
                }
            )

            # Publish validation completion
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling validation completion: {e}")

    def get_process_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get current process status"""
        return self.process_handler.get_process_status(run_id)

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            # Cleanup process handler
            if hasattr(self.process_handler, 'cleanup'):
                await self.process_handler.cleanup()

            # Cleanup report processor
            if hasattr(self.report_processor, 'cleanup'):
                await self.report_processor.cleanup()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during report handler cleanup: {e}")