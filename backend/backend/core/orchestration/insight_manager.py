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
from backend.core.channel_handlers.insight_handler import InsightChannelHandler
from backend.core.orchestration.pipeline_manager_helper import (
    PipelineState,
    PipelineStateManager
)
from backend.database.repository.insight_repository import InsightRepository
from backend.data_pipeline.insight_analysis.insight_processor import (
    InsightPhase
)

logger = logging.getLogger(__name__)


class InsightManager(BaseManager):
    """
    Orchestrates the insight generation process
    Manages communication, state, and persistence of insights
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: Optional[InsightRepository] = None,
            insight_handler: Optional[InsightChannelHandler] = None,
            state_manager: Optional[PipelineStateManager] = None,
            component_name: str = "InsightManager"
    ):
        """
        Initialize insight manager with comprehensive components

        Args:
            message_broker: Message communication system
            repository: Insight repository for data persistence
            insight_handler: Insight channel handler
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
        self.insight_handler = insight_handler or InsightChannelHandler(message_broker)
        self.state_manager = state_manager or PipelineStateManager()

        # Setup event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """
        Setup message handlers for insight-related events
        """
        try:
            # Subscribe to insight handler message patterns
            self.message_broker.subscribe(
                component=self.module_id,
                pattern="insight_handler.*",
                callback=self._handle_handler_messages
            )

        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            self._handle_error(None, e)

    async def _handle_handler_messages(self, message: ProcessingMessage) -> None:
        """
        Central routing for messages from insight handler

        Args:
            message: Incoming processing message
        """
        try:
            if message.message_type == MessageType.INSIGHT_STATUS_UPDATE:
                await self.handle_insight_status_update(message)
            elif message.message_type == MessageType.INSIGHT_COMPLETE:
                await self.handle_insight_complete(message)
            elif message.message_type == MessageType.INSIGHT_ERROR:
                await self.handle_insight_error(message)

        except Exception as e:
            logger.error(f"Error routing handler message: {str(e)}")
            await self._handle_error(
                message.content.get('pipeline_id'),
                e
            )

    async def initiate_insight_generation(
            self,
            pipeline_id: str,
            data: Dict[str, Any],
            business_goals: Dict[str, Any]
    ) -> UUID:
        """
        Initiate insight generation for a specific pipeline

        Args:
            pipeline_id: Unique pipeline identifier
            data: Data for insight generation
            business_goals: Business objectives

        Returns:
            Unique insight identifier
        """
        try:
            # Generate unique insight ID
            insight_id = UUID(uuid.uuid4())

            # Create insight check in repository if available
            if self.repository:
                self.repository.create_insight_check({
                    'pipeline_id': pipeline_id,
                    'dataset_id': data.get('dataset_id'),
                    'business_goals': business_goals,
                    'type': 'standard',
                    'metadata': data.get('metadata', {})
                })

            # Create or update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if not pipeline_state:
                pipeline_state = PipelineState(
                    pipeline_id=pipeline_id,
                    current_stage=ProcessingStage.ANALYSIS_EXECUTION,
                    status=ProcessingStatus.PENDING
                )
                self.state_manager.add_pipeline(pipeline_state)

            # Prepare insight generation message
            insight_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="insight_handler",
                    component_type=ComponentType.HANDLER
                ),
                message_type=MessageType.START_INSIGHT_GENERATION,
                content={
                    'pipeline_id': pipeline_id,
                    'data': data,
                    'business_goals': business_goals,
                    'context': {
                        'insight_id': str(insight_id)
                    }
                }
            )

            # Publish message to insight handler
            await self.message_broker.publish(insight_message)

            return insight_id

        except Exception as e:
            logger.error(f"Failed to initiate insight generation: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def handle_insight_status_update(self, message: ProcessingMessage) -> None:
        """
        Handle status updates from insight handler

        Args:
            message: Processing message with status update
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            insight_id = message.content.get('insight_id')
            status = message.content.get('status')
            progress = message.content.get('progress', 0)

            # Update repository if available
            if self.repository:
                self.repository.update_insight_status(
                    UUID(insight_id),
                    status=status,
                    results={'progress': progress}
                )

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus(status)
                pipeline_state.current_progress = progress

            # Notify pipeline manager about status update
            status_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="pipeline_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.STAGE_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.ANALYSIS_EXECUTION.value,
                    'status': status,
                    'progress': progress
                }
            )
            await self.message_broker.publish(status_message)

        except Exception as e:
            logger.error(f"Error handling insight status update: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_insight_complete(self, message: ProcessingMessage) -> None:
        """
        Handle insight generation completion

        Args:
            message: Processing message with completion details
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            insight_id = message.content.get('insight_id')
            insights = message.content.get('insights', {})

            # Save insight results in repository
            if self.repository:
                self.repository.save_insight_result({
                    'insight_id': insight_id,
                    'pipeline_id': pipeline_id,
                    'raw_insights': insights,
                    'type': 'standard'
                })

                # Update insight check status
                self.repository.update_insight_status(
                    UUID(insight_id),
                    status='completed',
                    results=insights
                )

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.COMPLETED
                pipeline_state.current_stage = ProcessingStage.ANALYSIS_COMPLETE
                pipeline_state.current_progress = 100.0

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
                    'stage': ProcessingStage.ANALYSIS_EXECUTION.value,
                    'results': insights
                }
            )
            await self.message_broker.publish(completion_message)

        except Exception as e:
            logger.error(f"Error handling insight completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_insight_error(self, message: ProcessingMessage) -> None:
        """
        Handle insight generation errors

        Args:
            message: Processing message with error details
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            insight_id = message.content.get('insight_id')
            error = message.content.get('error')

            # Update repository if available
            if self.repository:
                self.repository.update_insight_status(
                    UUID(insight_id),
                    status='failed',
                    error=error
                )

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.FAILED
                pipeline_state.add_error(error)

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
                    'stage': ProcessingStage.ANALYSIS_EXECUTION.value,
                    'error': error
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling insight error: {str(e)}")

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
            logger.error(f"Insight manager error: {str(error)}")

            # Update pipeline state if possible
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
                    'stage': ProcessingStage.ANALYSIS_EXECUTION.value,
                    'error': str(error)
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Critical error in insight manager error handling: {str(e)}")

    def get_insight_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve status of insight generation for a specific pipeline

        Args:
            pipeline_id: Unique pipeline identifier

        Returns:
            Detailed status of insight generation
        """
        try:
            # Get pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)

            if not pipeline_state:
                return None

            # Get insight check from repository if available
            repository_status = None
            if self.repository:
                # Find the most recent insight check for this pipeline
                checks, _ = self.repository.list_insight_checks(
                    {'pipeline_id': pipeline_id},
                    page=1,
                    page_size=1
                )

                if checks:
                    latest_check = checks[0]
                    repository_status = {
                        'status': latest_check.status,
                        'created_at': latest_check.created_at.isoformat(),
                        'updated_at': latest_check.updated_at.isoformat(),
                        'results': latest_check.results
                    }

            return {
                'pipeline_id': pipeline_id,
                'status': pipeline_state.status.value,
                'stage': pipeline_state.current_stage.value,
                'progress': pipeline_state.current_progress,
                'start_time': pipeline_state.start_time.isoformat() if pipeline_state.start_time else None,
                'end_time': pipeline_state.end_time.isoformat() if pipeline_state.end_time else None,
                'repository_details': repository_status
            }

        except Exception as e:
            logger.error(f"Error retrieving insight status: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """
        Comprehensive cleanup of insight manager resources
        """
        try:
            # Cancel all active pipelines
            for pipeline_id in self.state_manager.get_active_pipelines():
                state = self.state_manager.get_pipeline_state(pipeline_id)
                if state and state.status == ProcessingStatus.RUNNING:
                    state.status = ProcessingStatus.CANCELLED

                    # If repository is available, update insight checks
                    if self.repository:
                        checks, _ = self.repository.list_insight_checks(
                            {'pipeline_id': pipeline_id, 'status': 'processing'}
                        )
                        for check in checks:
                            self.repository.update_insight_status(
                                check.id,
                                status='cancelled',
                                error='System cleanup'
                            )

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
                            'stage': ProcessingStage.ANALYSIS_EXECUTION.value
                        }
                    )
                    await self.message_broker.publish(cancellation_message)

            # Reset state manager
            self.state_manager = PipelineStateManager()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during insight manager cleanup: {str(e)}")

    @classmethod
    def create(
            cls,
            message_broker: Optional[MessageBroker] = None,
            repository: Optional[InsightRepository] = None
    ) -> 'InsightManager':
        """
        Factory method to create InsightManager with optional dependencies

        Args:
            message_broker: Optional message broker
            repository: Optional insight repository

        Returns:
            Initialized InsightManager instance
        """
        # Import global message broker if not provided
        if message_broker is None:
            from backend.core.messaging.broker import message_broker

        # Import repository if not provided
        if repository is None:
            from backend.database.session import get_session
            from backend.database.repository.insight_repository import InsightRepository

            # Create a new database session
            db_session = get_session()
            repository = InsightRepository(db_session)

        return cls(
            message_broker=message_broker,
            repository=repository
        )