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
from backend.core.channel_handlers.decision_handler import DecisionChannelHandler
from backend.database.repository.decision_repository import DecisionRepository
from backend.core.orchestration.pipeline_manager_helper import (
    PipelineState,
    PipelineStateManager
)
from backend.data_pipeline.decision.decision_processor import (
    DecisionPhase,
    DecisionResult
)

logger = logging.getLogger(__name__)

class DecisionManager(BaseManager):
    """
    Decision manager orchestrating the decision-making process
    Responsible for coordinating decisions and managing their lifecycle
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            repository: Optional[DecisionRepository] = None,
            decision_handler: Optional[DecisionChannelHandler] = None,
            state_manager: Optional[PipelineStateManager] = None,
            component_name: str = "DecisionManager"
    ):
        """Initialize decision manager with comprehensive components"""
        # Initialize base manager
        super().__init__(
            message_broker=message_broker,
            component_name=component_name
        )

        # Dependency injection
        self.repository = repository
        self.decision_handler = decision_handler or DecisionChannelHandler(message_broker)
        self.state_manager = state_manager or PipelineStateManager()

        # Setup event handlers
        self._setup_event_handlers()

    def _setup_event_handlers(self) -> None:
        """Setup message handlers for decision-related events"""
        try:
            # Subscribe to decision handler message patterns
            self.message_broker.subscribe(
                component=self.module_id,
                pattern="decision_handler.*",
                callback=self._handle_handler_messages
            )

        except Exception as e:
            logger.error(f"Failed to setup event handlers: {str(e)}")
            self._handle_error(None, e)

    async def _handle_handler_messages(self, message: ProcessingMessage) -> None:
        """Central routing for messages from decision handler"""
        try:
            if message.message_type == MessageType.DECISION_STATUS_UPDATE:
                await self.handle_decision_status_update(message)
            elif message.message_type == MessageType.DECISION_COMPLETE:
                await self.handle_decision_complete(message)
            elif message.message_type == MessageType.DECISION_ERROR:
                await self.handle_decision_error(message)

        except Exception as e:
            logger.error(f"Error routing handler message: {str(e)}")
            await self._handle_error(
                message.content.get('pipeline_id'),
                e
            )

    async def initiate_decision_process(
            self,
            pipeline_id: str,
            data: Dict[str, Any]
    ) -> UUID:
        """Initiate a decision process for a specific pipeline"""
        try:
            # Generate unique decision ID
            decision_id = UUID(uuid.uuid4())

            # Create pipeline state if not exists
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if not pipeline_state:
                pipeline_state = PipelineState(
                    pipeline_id=pipeline_id,
                    current_stage=ProcessingStage.DECISION_MAKING,
                    status=ProcessingStatus.PENDING
                )
                self.state_manager.add_pipeline(pipeline_state)

            # Prepare decision process message
            decision_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="decision_handler",
                    component_type=ComponentType.HANDLER
                ),
                message_type=MessageType.DECISION_START,
                content={
                    'pipeline_id': pipeline_id,
                    'data': data,
                    'context': {
                        'decision_id': str(decision_id),
                        'pipeline_id': pipeline_id
                    }
                }
            )

            # Publish message to decision handler
            await self.message_broker.publish(decision_message)

            return decision_id

        except Exception as e:
            logger.error(f"Failed to initiate decision process: {str(e)}")
            await self._handle_error(pipeline_id, e)
            raise

    async def handle_decision_status_update(self, message: ProcessingMessage) -> None:
        """Handle status updates from decision handler"""
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
                await self.repository.update_decision_status(
                    pipeline_id,
                    status=status,
                    progress=progress
                )

        except Exception as e:
            logger.error(f"Error handling decision status update: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_decision_complete(self, message: ProcessingMessage) -> None:
        """Handle decision process completion"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            results = message.content.get('results', {})

            # Update pipeline state
            pipeline_state = self.state_manager.get_pipeline_state(pipeline_id)
            if pipeline_state:
                pipeline_state.status = ProcessingStatus.COMPLETED
                pipeline_state.current_stage = ProcessingStage.IMPLEMENTATION
                pipeline_state.current_progress = 100.0

            # Persist results in repository
            if self.repository:
                await self.repository.save_decision_results(
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
                    'stage': ProcessingStage.DECISION_MAKING.value,
                    'results': results
                }
            )
            await self.message_broker.publish(completion_message)

        except Exception as e:
            logger.error(f"Error handling decision completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def handle_decision_error(self, message: ProcessingMessage) -> None:
        """Handle decision process errors"""
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
                await self.repository.log_decision_error(
                    pipeline_id,
                    error,
                    stage=ProcessingStage.DECISION_MAKING.value
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
                    'stage': ProcessingStage.DECISION_MAKING.value,
                    'error': error
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling decision error: {str(e)}")

    async def _handle_error(
            self,
            pipeline_id: Optional[str],
            error: Exception
    ) -> None:
        """Comprehensive error handling"""
        try:
            # Log error
            logger.error(f"Decision manager error: {str(error)}")

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
                    'stage': ProcessingStage.DECISION_MAKING.value,
                    'error': str(error)
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Critical error in decision manager error handling: {str(e)}")

    def get_decision_status(self, decision_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieve status of a specific decision process"""
        try:
            # Get status from repository
            if self.repository:
                decision_status = self.repository.get_decision(decision_id)

                # Get process status from handler
                process_status = self.decision_handler.get_process_status(str(decision_id))

                if decision_status:
                    status_details = {
                        'decision_id': str(decision_id),
                        'status': decision_status.status,
                        'created_at': decision_status.created_at.isoformat(),
                        'updated_at': decision_status.updated_at.isoformat()
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
            logger.error(f"Error retrieving decision status: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """Comprehensive cleanup of decision manager resources"""
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
                            'stage': ProcessingStage.DECISION_MAKING.value
                        }
                    )
                    await self.message_broker.publish(cancellation_message)

            # Reset state manager
            self.state_manager = PipelineStateManager()

            # Cleanup decision handler
            if hasattr(self.decision_handler, 'cleanup'):
                await self.decision_handler.cleanup()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during decision manager cleanup: {str(e)}")

    # Factory method for easy instantiation
    @classmethod
    def create(
            cls,
            message_broker: Optional[MessageBroker] = None,
            repository: Optional[DecisionRepository] = None
    ) -> 'DecisionManager':
        """Factory method to create DecisionManager with optional dependencies"""
        # Import global message broker if not provided
        if message_broker is None:
            from backend.core.messaging.broker import message_broker

        return cls(
            message_broker=message_broker,
            repository=repository
        )