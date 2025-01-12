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
from backend.core.channel_handlers.quality_handler import QualityChannelHandler
from backend.database.repository.quality_repository import QualityRepository
from backend.core.orchestration.pipeline_manager_helper import (
    PipelineState,
    PipelineStateManager
)
from backend.data_pipeline.quality_analysis.data_quality_processor import (
    QualityPhase,
    QualityAnalysisResult
)

logger = logging.getLogger(__name__)


class QualityManager(BaseManager):
    """
    Quality manager orchestrating the data quality analysis process
    Responsible for coordinating quality checks and managing their lifecycle
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: Optional[QualityRepository] = None,
            quality_handler: Optional[QualityChannelHandler] = None,
            state_manager: Optional[PipelineStateManager] = None,
            component_name: str = "QualityManager"
    ):
        """
        Initialize quality manager with comprehensive components

        Args:
            message_broker: Message communication system
            repository: Database repository for quality operations
            quality_handler: Quality channel handler
            state_manager: Pipeline state management
            component_name: Name of the component
        """
        # Initialize base manager
        super().__init__(
            message_broker=message_broker,
            component_name=component_name
        )

        # Dependency injection
        self.repository = repository
        self.quality_handler = quality_handler or QualityChannelHandler(message_broker)
        self.state_manager = state_manager or PipelineStateManager()

        # Setup event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """
        Setup message handlers for quality-related events
        """
        try:
            # Subscribe to quality handler message patterns
            self.message_broker.subscribe(
                component=self.module_id,
                pattern="quality_handler.*",
                callback=self._handle_handler_messages
            )

        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            self._handle_error(None, e)

    async def _handle_handler_messages(self, message: ProcessingMessage) -> None:
        """
        Central routing for messages from quality handler

        Args:
            message: Incoming processing message
        """
        try:
            if message.message_type == MessageType.QUALITY_STATUS_UPDATE:
                await self.handle_quality_status_update(message)
            elif message.message_type == MessageType.QUALITY_COMPLETE:
                await self.handle_quality_complete(message)
            elif message.message_type == MessageType.QUALITY_ERROR:
                await self.handle_quality_error(message)

        except Exception as e:
            logger.error(f"Error routing handler message: {str(e)}")
            await self._handle_error(
                message.content.get('pipeline_id'),
                e
            )

    async def initiate_quality_check(
            self,
            pipeline_id: str,
            data: Dict[str, Any]
    ) -> UUID:
        """
        Initiate a quality check for a specific pipeline

        Args:
            pipeline_id: Unique pipeline identifier
            data: Data to be quality checked

        Returns:
            Unique check identifier
        """
        try:
            # Generate unique check ID
            check_id = UUID(uuid.uuid4())

            # Create pipeline state if not exists
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if not pipeline_state:
                pipeline_state = PipelineState(
                    pipeline_id=pipeline_id,
                    current_stage=ProcessingStage.QUALITY_CHECK,
                    status=ProcessingStatus.PENDING
                )
                self.state_manager.add_pipeline(pipeline_state)

            # Prepare quality check message
            quality_check_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="quality_handler",
                    component_type=ComponentType.HANDLER
                ),
                message_type=MessageType.QUALITY_START,
                content={
                    'pipeline_id': pipeline_id,
                    'data': data,
                    'context': {
                        'check_id': str(check_id),
                        'pipeline_id': pipeline_id
                    }
                }
            )

            # Publish message to quality handler
            await self.message_broker.publish(quality_check_message)

            return check_id

        except Exception as e:
            logger.error(f"Failed to initiate quality check: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def handle_quality_status_update(self, message: ProcessingMessage) -> None:
        """
        Handle status updates from quality handler

        Args:
            message: Processing message with status update
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            status = message.content.get('status')
            progress = message.content.get('progress', 0)

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus(status)
                pipeline_state.current_progress = progress

            # Update repository if available
            if self.repository:
                self.repository.update_pipeline_status(
                    pipeline_id,
                    status=status,
                    progress=progress
                )

        except Exception as e:
            logger.error(f"Error handling quality status update: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_quality_complete(self, message: ProcessingMessage) -> None:
        """
        Handle quality check completion

        Args:
            message: Processing message with completion details
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            results = message.content.get('results', {})

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.COMPLETED
                pipeline_state.current_stage = ProcessingStage.ANALYSIS_PREP
                pipeline_state.current_progress = 100.0

            # Persist results in repository
            if self.repository:
                self.repository.save_quality_results(
                    pipeline_id,
                    results
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
                    'stage': ProcessingStage.QUALITY_CHECK.value,
                    'results': results
                }
            )
            await self.message_broker.publish(completion_message)

        except Exception as e:
            logger.error(f"Error handling quality completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_quality_error(self, message: ProcessingMessage) -> None:
        """
        Handle quality check errors

        Args:
            message: Processing message with error details
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            error = message.content.get('error')

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.FAILED
                pipeline_state.add_error(error)

            # Persist error in repository
            if self.repository:
                self.repository.log_pipeline_error(
                    pipeline_id,
                    error,
                    stage=ProcessingStage.QUALITY_CHECK.value
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
                    'stage': ProcessingStage.QUALITY_CHECK.value,
                    'error': error
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling quality error: {str(e)}")

    async def _handle_error(
        self,
        pipeline_id: Optional[str],
        error: Exception
    ) -> None:
        """
        Comprehensive error handling

        Args:
            pipeline_id: Optional pipeline identifier
            error: Exception to handle
        """
        try:
            # Log error
            logger.error(f"Quality manager error: {str(error)}")

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
                    'stage': ProcessingStage.QUALITY_CHECK.value,
                    'error': str(error)
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Critical error in quality manager error handling: {str(e)}")

    def get_quality_check_status(self, check_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve status of a specific quality check

        Args:
            check_id: Unique check identifier

        Returns:
            Detailed status of the quality check
        """
        try:
            # Get status from repository
            if self.repository:
                check_status = self.repository.get_check(check_id)

                # Get process status from handler
                process_status = self.quality_handler.get_process_status(str(check_id))

                if check_status:
                    status_details = {
                        'check_id': str(check_id),
                        'status': check_status.status,
                        'created_at': check_status.created_at.isoformat(),
                        'updated_at': check_status.updated_at.isoformat()
                    }

                    # Enhance with process details if available
                    if process_status:
                        status_details.update({
                            'phase': process_status.get('phase'),
                            'progress': process_status.get('progress', 0),
                            'active': True,
                            'metadata': process_status.get('metadata', {})
                        })

                    return status_details

            return None

        except Exception as e:
            logger.error(f"Error retrieving quality check status: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """
        Comprehensive cleanup of quality manager resources
        """
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
                            'stage': ProcessingStage.QUALITY_CHECK.value
                        }
                    )
                    await self.message_broker.publish(cancellation_message)

            # Reset state manager
            self.state_manager = PipelineStateManager()

            # Cleanup quality handler
            if hasattr(self.quality_handler, 'cleanup'):
                await self.quality_handler.cleanup()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during quality manager cleanup: {str(e)}")

    # Factory method for easy instantiation
    @classmethod
    def create(
        cls,
        message_broker: Optional[MessageBroker] = None,
        repository: Optional[QualityRepository] = None
    ) -> 'QualityManager':
        """
        Factory method to create QualityManager with optional dependencies

        Args:
            message_broker: Optional message broker
            repository: Optional quality repository

        Returns:
            Initialized QualityManager instance
        """
        # Import global message broker if not provided
        if message_broker is None:
            from backend.core.messaging.broker import message_broker

        return cls(
            message_broker=message_broker,
            repository=repository
        )