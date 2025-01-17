# backend/core/handlers/channel/recommendation_handler.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    RecommendationContext,
    BaseContext
)
from ...staging.staging_manager import StagingManager
from ..base.base_handler import BaseChannelHandler
from data.processing.recommendation.processor.recommendation_processor import RecommendationProcessor

logger = logging.getLogger(__name__)


class RecommendationHandler(BaseChannelHandler):
    """
    Handles communication and routing for recommendation-related messages.
    Coordinates between manager and processor.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            handler_name="recommendation_handler",
            domain_type="recommendation"
        )

        self.staging_manager = staging_manager
        self.processor = RecommendationProcessor(message_broker, staging_manager)

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for recommendation-related messages"""
        self.register_message_handler(
            MessageType.RECOMMENDATION_START,
            self._handle_recommendation_start
        )
        self.register_message_handler(
            MessageType.RECOMMENDATION_UPDATE,
            self._handle_recommendation_update
        )
        self.register_message_handler(
            MessageType.RECOMMENDATION_COMPLETE,
            self._handle_recommendation_complete
        )

    async def _handle_recommendation_start(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle start of recommendation process"""
        try:
            pipeline_id = message.content['pipeline_id']

            # Create recommendation context
            context = RecommendationContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECOMMENDATION,
                status=message.content.get('status', 'pending'),
                source_component=message.metadata.source_component,
                request_type=message.content.get('request_type'),
                engine_types=message.content.get('engine_types', []),
                ranking_rules=message.content.get('ranking_rules', {}),
                aggregation_config=message.content.get('aggregation_config', {}),
                filtering_rules=message.content.get('filtering_rules', {}),
                performance_metrics=message.content.get('performance_metrics', {})
            )

            # Start processing
            state = await self.processor.process_recommendation_request(
                pipeline_id,
                context
            )

            # Create response
            response = message.create_response(
                MessageType.RECOMMENDATION_UPDATE,
                {
                    'pipeline_id': pipeline_id,
                    'state': state.status.value,
                    'current_phase': state.current_phase.value,
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to handle recommendation start: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_recommendation_update(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle recommendation process updates"""
        try:
            pipeline_id = message.content['pipeline_id']
            update_data = message.content.get('update_data', {})

            # Forward update to manager
            response = message.create_response(
                MessageType.RECOMMENDATION_UPDATE,
                {
                    'pipeline_id': pipeline_id,
                    'phase': update_data.get('phase'),
                    'status': update_data.get('status'),
                    'metrics': update_data.get('metrics', {}),
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to handle recommendation update: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_recommendation_complete(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle recommendation process completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            recommendations = message.content.get('recommendations', [])

            # Store recommendations in staging
            staged_id = await self.staging_manager.store_staged_data(
                pipeline_id,
                {
                    'type': 'recommendations',
                    'data': recommendations,
                    'metadata': message.content.get('metadata', {}),
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Create completion response
            response = message.create_response(
                MessageType.RECOMMENDATION_COMPLETE,
                {
                    'pipeline_id': pipeline_id,
                    'staged_id': staged_id,
                    'count': len(recommendations),
                    'metadata': message.content.get('metadata', {}),
                    'timestamp': datetime.now().isoformat()
                }
            )

            await self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to handle recommendation completion: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_error(
            self,
            message: ProcessingMessage,
            error: Exception
    ) -> None:
        """Handle processing errors"""
        error_message = message.create_response(
            MessageType.RECOMMENDATION_ERROR,
            {
                'pipeline_id': message.content.get('pipeline_id'),
                'error': str(error),
                'phase': message.content.get('phase', 'unknown'),
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(error_message)

    async def get_process_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current status of recommendation process"""
        return await self.processor.get_process_status(pipeline_id)

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            await self.processor.cleanup()
            await super().cleanup()

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise