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
from backend.data_pipeline.recommendation.recommendation_processor import (
    RecommendationProcessor,
    RecommendationPhase
)

logger = logging.getLogger(__name__)


class RecommendationChannelHandler(BaseChannelHandler):
    """
    Handles communication and routing for recommendation-related messages

    Responsibilities:
    - Route recommendation-related messages
    - Coordinate with recommendation processor
    - Interface with recommendation manager
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            process_handler: Optional[CoreProcessHandler] = None,
            recommendation_processor: Optional[RecommendationProcessor] = None
    ):
        """Initialize recommendation channel handler"""
        super().__init__(message_broker, "recommendation_handler")

        # Initialize dependencies
        self.process_handler = process_handler or CoreProcessHandler(message_broker)
        self.recommendation_processor = recommendation_processor or RecommendationProcessor(message_broker)

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers for recommendation processing"""
        self.register_callback(
            MessageType.RECOMMENDATION_START,
            self._handle_recommendation_start
        )
        self.register_callback(
            MessageType.RECOMMENDATION_COMPLETE,
            self._handle_recommendation_complete
        )
        self.register_callback(
            MessageType.RECOMMENDATION_UPDATE,
            self._handle_recommendation_update
        )
        self.register_callback(
            MessageType.RECOMMENDATION_ERROR,
            self._handle_recommendation_error
        )

    def _handle_recommendation_start(self, message: ProcessingMessage) -> None:
        """Handle recommendation process start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            data = message.content.get('data', {})
            context = message.content.get('context', {})

            # Create response message to recommendation manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="recommendation_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_recommendation_start"
                ),
                message_type=MessageType.RECOMMENDATION_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': 'started',
                    'phase': RecommendationPhase.CANDIDATE_GENERATION.value
                }
            )

            # Execute process via process handler
            self.process_handler.execute_process(
                self._run_recommendation_process,
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECOMMENDATION,
                message_type=MessageType.RECOMMENDATION_START,
                data=data,
                context=context
            )

            # Publish response to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to start recommendation process: {e}")
            self._handle_recommendation_error(
                ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="recommendation_manager",
                        component_type=ComponentType.MANAGER
                    ),
                    message_type=MessageType.RECOMMENDATION_ERROR,
                    content={
                        'error': str(e),
                        'pipeline_id': message.content.get('pipeline_id')
                    }
                )
            )

    async def _run_recommendation_process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Core recommendation process execution logic"""
        try:
            # Run candidate generation phase
            candidates = await self.recommendation_processor.generate_candidates(
                context.get('recommendation_id'),
                data,
                context
            )

            # Run ranking phase
            ranked_recommendations = await self.recommendation_processor.rank_recommendations(
                context.get('recommendation_id'),
                candidates
            )

            # Run filtering and finalization phase
            final_recommendations = await self.recommendation_processor.finalize_recommendations(
                context.get('recommendation_id'),
                ranked_recommendations,
                context
            )

            return {
                'candidates': candidates,
                'ranked_recommendations': ranked_recommendations,
                'final_recommendations': final_recommendations,
                'pipeline_id': context.get('pipeline_id')
            }

        except Exception as e:
            logger.error(f"Recommendation process failed: {e}")
            raise

    def _handle_recommendation_complete(self, message: ProcessingMessage) -> None:
        """Handle recommendation process completion"""
        try:
            # Create completion response for manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="recommendation_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_recommendation_complete"
                ),
                message_type=MessageType.RECOMMENDATION_COMPLETE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'results': message.content.get('results', {}),
                    'status': 'completed'
                }
            )

            # Publish completion to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling recommendation completion: {e}")

    def _handle_recommendation_update(self, message: ProcessingMessage) -> None:
        """Handle recommendation process updates"""
        try:
            # Forward update to recommendation manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="recommendation_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_recommendation_update"
                ),
                message_type=MessageType.RECOMMENDATION_STATUS_UPDATE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'status': message.content.get('status'),
                    'progress': message.content.get('progress')
                }
            )

            # Publish update to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling recommendation update: {e}")

    def _handle_recommendation_error(self, message: ProcessingMessage) -> None:
        """Handle recommendation process errors"""
        try:
            # Forward error to recommendation manager
            error_response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="recommendation_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_recommendation_error"
                ),
                message_type=MessageType.RECOMMENDATION_ERROR,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'error': message.content.get('error')
                }
            )

            # Publish error to manager
            self.message_broker.publish(error_response)

        except Exception as e:
            logger.error(f"Error handling recommendation error: {e}")

    def get_process_status(self, recommendation_id: str) -> Optional[Dict[str, Any]]:
        """Get current process status"""
        return self.process_handler.get_process_status(recommendation_id)