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
from backend.core.channel_handlers.recommendation_handler import RecommendationChannelHandler
from backend.db.repository.recommendation_repository import RecommendationRepository
from backend.core.orchestration.pipeline_manager_helper import (
    PipelineState,
    PipelineStateManager
)
from backend.data_pipeline.recommendation.recommendation_processor import (
    RecommendationPhase,
    RecommendationResult
)

logger = logging.getLogger(__name__)

class RecommendationManager(BaseManager):
    """
    Recommendation manager orchestrating the recommendation generation process
    Responsible for coordinating recommendations and managing their lifecycle
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: Optional[RecommendationRepository] = None,
            recommendation_handler: Optional[RecommendationChannelHandler] = None,
            state_manager: Optional[PipelineStateManager] = None,
            component_name: str = "RecommendationManager"
    ):
        """Initialize recommendation manager with comprehensive components"""
        # Initialize base manager
        super().__init__(
            message_broker=message_broker,
            component_name=component_name
        )

        # Dependency injection
        self.repository = repository
        self.recommendation_handler = recommendation_handler or RecommendationChannelHandler(message_broker)
        self.state_manager = state_manager or PipelineStateManager()

        # Setup event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Setup message handlers for recommendation-related events"""
        try:
            # Subscribe to recommendation handler message patterns
            self.message_broker.subscribe(
                component=self.module_id,
                pattern="recommendation_handler.*",
                callback=self._handle_handler_messages
            )

        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            self._handle_error(None, e)

    async def _handle_handler_messages(self, message: ProcessingMessage) -> None:
        """Central routing for messages from recommendation handler"""
        try:
            if message.message_type == MessageType.RECOMMENDATION_STATUS_UPDATE:
                await self.handle_recommendation_status_update(message)
            elif message.message_type == MessageType.RECOMMENDATION_COMPLETE:
                await self.handle_recommendation_complete(message)
            elif message.message_type == MessageType.RECOMMENDATION_ERROR:
                await self.handle_recommendation_error(message)

        except Exception as e:
            logger.error(f"Error routing handler message: {str(e)}")
            await self._handle_error(
                message.content.get('pipeline_id'),
                e
            )

    async def initiate_recommendation_process(
            self,
            pipeline_id: str,
            data: Dict[str, Any]
    ) -> UUID:
        """Initiate a recommendation process for a specific pipeline"""
        try:
            # Generate unique recommendation ID
            recommendation_id = UUID(uuid.uuid4())

            # Create pipeline state if not exists
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if not pipeline_state:
                pipeline_state = PipelineState(
                    pipeline_id=pipeline_id,
                    current_stage=ProcessingStage.RECOMMENDATION,
                    status=ProcessingStatus.PENDING
                )
                self.state_manager.add_pipeline(pipeline_state)

            # Create initial recommendation record in repository
            if self.repository:
                await self.repository.create_recommendation({
                    'pipeline_id': pipeline_id,
                    'recommendation_id': str(recommendation_id),
                    'status': 'pending',
                    'created_at': datetime.utcnow()
                })

            # Prepare recommendation process message
            recommendation_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="recommendation_handler",
                    component_type=ComponentType.HANDLER
                ),
                message_type=MessageType.RECOMMENDATION_START,
                content={
                    'pipeline_id': pipeline_id,
                    'data': data,
                    'context': {
                        'recommendation_id': str(recommendation_id),
                        'pipeline_id': pipeline_id
                    }
                }
            )

            # Publish message to recommendation handler
            await self.message_broker.publish(recommendation_message)

            return recommendation_id

        except Exception as e:
            logger.error(f"Failed to initiate recommendation process: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def handle_recommendation_status_update(self, message: ProcessingMessage) -> None:
        """Handle status updates from recommendation handler"""
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
                await self.repository.update_recommendation_status(
                    pipeline_id,
                    status=status,
                    progress=progress
                )

        except Exception as e:
            logger.error(f"Error handling recommendation status update: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_recommendation_complete(self, message: ProcessingMessage) -> None:
        """Handle recommendation process completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            results = message.content.get('results', {})

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.COMPLETED
                pipeline_state.current_stage = ProcessingStage.DECISION_MAKING
                pipeline_state.current_progress = 100.0

            # Persist results in repository
            if self.repository:
                await self.repository.save_recommendation_results(
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
                    'stage': ProcessingStage.RECOMMENDATION.value,
                    'results': results
                }
            )
            await self.message_broker.publish(completion_message)

        except Exception as e:
            logger.error(f"Error handling recommendation completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_recommendation_error(self, message: ProcessingMessage) -> None:
        """Handle recommendation process errors"""
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
                await self.repository.log_recommendation_error(
                    pipeline_id,
                    error,
                    stage=ProcessingStage.RECOMMENDATION.value
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
                    'stage': ProcessingStage.RECOMMENDATION.value,
                    'error': error
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling recommendation error: {str(e)}")

    async def _handle_error(
        self,
        pipeline_id: Optional[str],
        error: Exception
    ) -> None:
        """Comprehensive error handling"""
        try:
            # Log error
            logger.error(f"Recommendation manager error: {str(error)}")

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
                    'stage': ProcessingStage.RECOMMENDATION.value,
                    'error': str(error)
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Critical error in recommendation manager error handling: {str(e)}")

    def get_recommendation_status(self, recommendation_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieve status of a specific recommendation process"""
        try:
            # Get status from repository
            if self.repository:
                recommendation_status = self.repository.get_recommendation(recommendation_id)

                # Get process status from handler
                process_status = self.recommendation_handler.get_process_status(str(recommendation_id))

                if recommendation_status:
                    status_details = {
                        'recommendation_id': str(recommendation_id),
                        'status': recommendation_status.status,
                        'created_at': recommendation_status.created_at.isoformat(),
                        'updated_at': recommendation_status.updated_at.isoformat()
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
            logger.error(f"Error retrieving recommendation status: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """Comprehensive cleanup of recommendation manager resources"""
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
                            'stage': ProcessingStage.RECOMMENDATION.value
                        }
                    )
                    await self.message_broker.publish(cancellation_message)

            # Reset state manager
            self.state_manager = PipelineStateManager()

            # Cleanup recommendation handler
            if hasattr(self.recommendation_handler, 'cleanup'):
                await self.recommendation_handler.cleanup()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during recommendation manager cleanup: {str(e)}")

    # Factory method for easy instantiation 
    @classmethod
    def create(
        cls,
        message_broker: Optional[MessageBroker] = None,
        repository: Optional[RecommendationRepository] = None
    ) -> 'RecommendationManager':
        """Factory method to create RecommendationManager with optional dependencies"""
        # Import global message broker if not provided
        if message_broker is None:
            from backend.core.messaging.broker import message_broker

        return cls(
            message_broker=message_broker,
            repository=repository
        )