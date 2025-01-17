import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
import uuid

from backend.core.orchestration.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    ComponentType,
    ModuleIdentifier
)
from backend.core.channel_handlers.report_handler import ReportHandler
from backend.db.repository.report_repository import ReportRepository
from backend.core.orchestration.pipeline_manager_helper import (
    PipelineState,
    PipelineStateManager
)
from backend.data_pipeline.reporting.report_processor import ReportPhase

logger = logging.getLogger(__name__)

class ReportManager(BaseManager):
    """
    Report manager orchestrating the report generation process
    Responsible for coordinating report generation and managing their lifecycle
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: Optional[ReportRepository] = None,
            report_handler: Optional[ReportHandler] = None,
            state_manager: Optional[PipelineStateManager] = None,
            component_name: str = "ReportManager"
    ):
        """Initialize report manager with comprehensive components"""
        # Initialize base manager
        super().__init__(
            message_broker=message_broker,
            component_name=component_name
        )

        # Dependency injection
        self.repository = repository
        self.report_handler = report_handler or ReportHandler(message_broker)
        self.state_manager = state_manager or PipelineStateManager()

        # Setup event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Setup message handlers for report-related events"""
        try:
            # Subscribe to report handler message patterns
            self.message_broker.subscribe(
                component=self.module_id,
                pattern="report_handler.*",
                callback=self._handle_handler_messages
            )

        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            self._handle_error(None, e)

    async def _handle_handler_messages(self, message: ProcessingMessage) -> None:
        """Central routing for messages from report handler"""
        try:
            if message.message_type == MessageType.REPORT_STATUS_UPDATE:
                await self.handle_report_status_update(message)
            elif message.message_type == MessageType.REPORT_COMPLETE:
                await self.handle_report_complete(message)
            elif message.message_type == MessageType.REPORT_ERROR:
                await self.handle_report_error(message)
            elif message.message_type == MessageType.SECTION_COMPLETE:
                await self.handle_section_complete(message)
            elif message.message_type == MessageType.VISUALIZATION_COMPLETE:
                await self.handle_visualization_complete(message)
            elif message.message_type == MessageType.VALIDATION_COMPLETE:
                await self.handle_validation_complete(message)

        except Exception as e:
            logger.error(f"Error routing handler message: {str(e)}")
            await self._handle_error(
                message.content.get('pipeline_id'),
                e
            )

    async def initiate_report_generation(
            self,
            pipeline_id: str,
            report_type: str,
            template_id: Optional[UUID] = None,
            parameters: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """Initiate a report generation process"""
        try:
            # Generate unique run ID
            run_id = UUID(uuid.uuid4())

            # Create pipeline state if not exists
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if not pipeline_state:
                pipeline_state = PipelineState(
                    pipeline_id=pipeline_id,
                    current_stage=ProcessingStage.REPORT_GENERATION,
                    status=ProcessingStatus.PENDING
                )
                self.state_manager.add_pipeline(pipeline_state)

            # Create initial record in repository
            if self.repository:
                template_data = {}
                if template_id:
                    template = await self.repository.get_template(template_id)
                    if template:
                        template_data = template.content
                        await self.repository.increment_template_usage(template_id)

                await self.repository.create_report_run({
                    'name': f"{report_type.title()} Report",
                    'pipeline_id': pipeline_id,
                    'report_type': report_type,
                    'template_id': template_id,
                    'parameters': parameters or {},
                    'status': 'pending',
                    'started_at': datetime.utcnow()
                })

            # Prepare report generation message
            report_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="report_handler",
                    component_type=ComponentType.HANDLER
                ),
                message_type=MessageType.REPORT_START,
                content={
                    'pipeline_id': pipeline_id,
                    'report_type': report_type,
                    'template_data': template_data,
                    'parameters': parameters or {},
                    'context': {
                        'run_id': str(run_id),
                        'pipeline_id': pipeline_id
                    }
                }
            )

            # Publish message to report handler
            await self.message_broker.publish(report_message)

            return run_id

        except Exception as e:
            logger.error(f"Failed to initiate report generation: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def handle_report_status_update(self, message: ProcessingMessage) -> None:
        """Handle status updates from report handler"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            status = message.content.get('status')
            progress = message.content.get('progress', 0)
            phase = message.content.get('phase')

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus(status)
                pipeline_state.current_progress = progress

            # Update repository if available
            if self.repository:
                await self.repository.update_run_status(
                    pipeline_id,
                    status=status,
                    progress=progress,
                    phase=phase
                )

            # Update section and visualization statuses if provided
            section_status = message.content.get('section_status')
            if section_status and self.repository:
                for section_id, status_data in section_status.items():
                    await self.repository.update_section_status(
                        UUID(section_id),
                        status=status_data.get('status'),
                        generation_time=status_data.get('generation_time')
                    )

            viz_status = message.content.get('visualization_status')
            if viz_status and self.repository:
                for viz_id, status_data in viz_status.items():
                    await self.repository.update_visualization_status(
                        UUID(viz_id),
                        status=status_data.get('status'),
                        generation_time=status_data.get('generation_time')
                    )

        except Exception as e:
            logger.error(f"Error handling report status update: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_report_complete(self, message: ProcessingMessage) -> None:
        """Handle report process completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            results = message.content.get('results', {})
            output_url = message.content.get('output_url')
            output_size = message.content.get('output_size')

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.COMPLETED
                pipeline_state.current_stage = ProcessingStage.DELIVERY
                pipeline_state.current_progress = 100.0

            # Save results in repository
            if self.repository:
                await self.repository.update_run_status(
                    pipeline_id,
                    status='completed',
                    output_url=output_url,
                    output_size=output_size
                )

            # Notify pipeline manager about stage completion
            completion_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.REPORT_GENERATION.value,
                    'results': {
                        'output_url': output_url,
                        'output_size': output_size,
                        'report_data': results
                    }
                }
            )
            await self.message_broker.publish(completion_message)

        except Exception as e:
            logger.error(f"Error handling report completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_report_error(self, message: ProcessingMessage) -> None:
        """Handle report process errors"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            error = message.content.get('error')
            phase = message.content.get('phase')
            context = message.content.get('context', {})

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.FAILED
                pipeline_state.add_error(error)

            # Save error in repository
            if self.repository:
                await self.repository.update_run_status(
                    pipeline_id,
                    status='failed',
                    error=error,
                    error_details={
                        'phase': phase,
                        'context': context,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                )

            # Notify pipeline manager about stage failure
            error_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.STAGE_FAILED,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.REPORT_GENERATION.value,
                    'error': error,
                    'phase': phase
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling report error: {str(e)}")

    async def handle_section_complete(self, message: ProcessingMessage) -> None:
        """Handle section completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            section_id = message.content.get('section_id')
            section_data = message.content.get('section_data', {})
            generation_time = message.content.get('generation_time')

            if self.repository:
                await self.repository.update_section_completion(
                    UUID(section_id),
                    section_data,
                    generation_time
                )

        except Exception as e:
            logger.error(f"Error handling section completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_visualization_complete(self, message: ProcessingMessage) -> None:
        """Handle visualization completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            visualization_id = message.content.get('visualization_id')
            visualization_data = message.content.get('visualization_data', {})
            generation_time = message.content.get('generation_time')

            if self.repository:
                await self.repository.update_visualization_completion(
                    UUID(visualization_id),
                    visualization_data,
                    generation_time
                )

        except Exception as e:
            logger.error(f"Error handling visualization completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_validation_complete(self, message: ProcessingMessage) -> None:
        """Handle validation completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            validation_id = message.content.get('validation_id')
            validation_results = message.content.get('validation_results', {})
            status = message.content.get('status')
            execution_time = message.content.get('execution_time')

            if self.repository:
                await self.repository.update_validation_completion(
                    UUID(validation_id),
                    validation_results,
                    status,
                    execution_time
                )

        except Exception as e:
            logger.error(f"Error handling validation completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_error(
            self,
            pipeline_id: Optional[str],
            error: Exception
    ) -> None:
        """Comprehensive error handling"""
        try:
            # Log error
            logger.error(f"Report manager error: {str(error)}")

            # Update pipeline state
            if pipeline_id:
                pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
                if pipeline_state:
                    pipeline_state.status = ProcessingStatus.FAILED
                    pipeline_state.add_error(str(error))

            # Publish error message
            error_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.REPORT_GENERATION.value,
                    'error': str(error)
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Critical error in report manager error handling: {str(e)}")

    def get_report_status(self, run_id: UUID) -> Optional[Dict[str, Any]]:
        """Get status of a specific report run"""
        try:
            # Get status from repository
            if self.repository:
                report_run = self.repository.get_report_run(run_id)
                process_status = self.report_handler.get_process_status(str(run_id))

                if report_run:
                    status = {
                        'run_id': str(run_id),
                        'name': report_run.name,
                        'type': report_run.report_type,
                        'status': report_run.status,
                        'progress': report_run.progress,
                        'started_at': report_run.started_at.isoformat(),
                        'section_count': len(report_run.sections),
                        'visualization_count': len(report_run.visualizations)
                    }

                    # Add process details if available
                    if process_status:
                        status.update({
                            'phase': process_status.get('phase'),
                            'active': True,
                            'processing_details': process_status
                        })

                    return status

            return None

        except Exception as e:
            logger.error(f"Error retrieving report status: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """Comprehensive cleanup of report manager resources"""
        try:
            # Cancel all active pipelines
            for pipeline_id in self.state_manager.get_active_pipelines():
                state = self.state_manager.get_pipeline_state(pipeline_id)
                if state and state.status == ProcessingStatus.RUNNING:
                    state.status = ProcessingStatus.CANCELLED

                    # Publish cancellation message
                    cancellation_message = ProcessingMessage(
                        source_identifier=self.module_id,
                        target_identifier=ModuleIdentifier(
                            component_name="pipeline_manager",
                            component_type=ComponentType.MANAGER
                        ),
                        message_type=MessageType.STAGE_CANCELLED,
                        content={
                            'pipeline_id': pipeline_id,
                            'stage': ProcessingStage.REPORT_GENERATION.value
                        }
                    )
                    await self.message_broker.publish(cancellation_message)

            # Reset state manager
            self.state_manager = PipelineStateManager()

            # Cleanup report handler
            if hasattr(self.report_handler, 'cleanup'):
                await self.report_handler.cleanup()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during report manager cleanup: {str(e)}")

    # Factory method for easy instantiation
    @classmethod
    def create(
            cls,
            message_broker: Optional[MessageBroker] = None,
            repository: Optional[ReportRepository] = None
    ) -> 'ReportManager':
        """Factory method to create ReportManager with optional dependencies"""
        # Import global message broker if not provided
        if message_broker is None:
            from backend.core.messaging.broker import message_broker

        return cls(
            message_broker=message_broker,
            repository=repository
        )