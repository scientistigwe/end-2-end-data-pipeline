# backend/core/managers/recommendation_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    RecommendationContext,
    MessageMetadata
)
from ..control.cpm import ControlPointManager
from .base.base_manager import BaseManager
from ..handlers.channel.recommendation_handler import RecommendationHandler
from ..staging.staging_manager import StagingManager

from data.processing.recommendation.types.recommendation_types import (
    RecommendationType,
    RecommendationPhase,
    RecommendationStatus
)

logger = logging.getLogger(__name__)


class RecommendationManager(BaseManager):
    """
    Manager for recommendation orchestration.
    Coordinates recommendation process and integrates with pipeline.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            control_point_manager=control_point_manager,
            component_name="recommendation_manager",
            domain_type="recommendation"
        )

        self.staging_manager = staging_manager
        self.recommendation_handler = RecommendationHandler(
            message_broker=message_broker,
            staging_manager=staging_manager
        )

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
        self.register_message_handler(
            MessageType.RECOMMENDATION_ERROR,
            self._handle_recommendation_error
        )

    async def initiate_recommendations(
            self,
            pipeline_id: str,
            source_component: str,
            config: Dict[str, Any]
    ) -> None:
        """Initiate recommendation process"""
        try:
            # Create control point
            control_point = await self.control_point_manager.create_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECOMMENDATION,
                metadata={
                    'source_component': source_component,
                    'config': config
                }
            )

            # Create context
            context = RecommendationContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECOMMENDATION,
                status=ProcessingStatus.PENDING,
                source_component=source_component,
                request_type=config.get('request_type', 'default'),
                engine_types=config.get('engine_types', []),
                ranking_rules=config.get('ranking_rules', {}),
                aggregation_config=config.get('aggregation_config', {}),
                filtering_rules=config.get('filtering_rules', {}),
                performance_metrics={}
            )

            # Start recommendation process
            start_message = ProcessingMessage(
                message_type=MessageType.RECOMMENDATION_START,
                content={
                    'pipeline_id': pipeline_id,
                    'request_type': context.request_type,
                    'config': config
                },
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component="recommendation_handler",
                    correlation_id=control_point.id
                ),
                context=context
            )

            await self.message_broker.publish(start_message)

        except Exception as e:
            logger.error(f"Failed to initiate recommendations: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_recommendation_start(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle recommendation process start"""
        try:
            pipeline_id = message.content['pipeline_id']

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECOMMENDATION,
                status=ProcessingStatus.IN_PROGRESS,
                metadata={
                    'started_at': datetime.now().isoformat(),
                    'config': message.content.get('config', {})
                }
            )

            # Forward to handler
            await self.recommendation_handler._handle_recommendation_start(message)

        except Exception as e:
            logger.error(f"Failed to handle recommendation start: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_recommendation_update(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle recommendation process updates"""
        try:
            pipeline_id = message.content['pipeline_id']
            phase = message.content.get('phase')
            status = message.content.get('status')

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECOMMENDATION,
                metadata={
                    'phase': phase,
                    'status': status,
                    'updated_at': datetime.now().isoformat(),
                    'metrics': message.content.get('metrics', {})
                }
            )

            # Forward to handler
            await self.recommendation_handler._handle_recommendation_update(message)

        except Exception as e:
            logger.error(f"Failed to handle recommendation update: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_recommendation_complete(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle recommendation process completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            staged_id = message.content.get('staged_id')

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECOMMENDATION,
                status=ProcessingStatus.COMPLETED,
                metadata={
                    'completed_at': datetime.now().isoformat(),
                    'staged_id': staged_id,
                    'metrics': message.content.get('metadata', {})
                }
            )

            # Notify pipeline manager
            completion_message = ProcessingMessage(
                message_type=MessageType.STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.RECOMMENDATION.value,
                    'staged_id': staged_id,
                    'metrics': message.content.get('metadata', {})
                },
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component="pipeline_manager"
                )
            )

            await self.message_broker.publish(completion_message)

        except Exception as e:
            logger.error(f"Failed to handle recommendation completion: {str(e)}")
            await self._handle_error(pipeline_id, e)

    async def _handle_recommendation_error(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle recommendation process errors"""
        try:
            pipeline_id = message.content['pipeline_id']
            error = message.content.get('error')

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECOMMENDATION,
                status=ProcessingStatus.FAILED,
                metadata={
                    'error': error,
                    'failed_at': datetime.now().isoformat(),
                    'phase': message.content.get('phase')
                }
            )

            # Notify pipeline manager
            error_message = ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.RECOMMENDATION.value,
                    'error': error,
                    'phase': message.content.get('phase')
                },
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component="pipeline_manager"
                )
            )

            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Failed to handle recommendation error: {str(e)}")

    async def get_recommendation_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current status of recommendation process"""
        try:
            # Get handler status
            handler_status = await self.recommendation_handler.get_process_status(
                pipeline_id
            )

            # Get control point status
            control_point = await self.control_point_manager.get_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.RECOMMENDATION
            )

            if handler_status or control_point:
                return {
                    'pipeline_id': pipeline_id,
                    'handler_status': handler_status,
                    'control_point': control_point,
                    'timestamp': datetime.now().isoformat()
                }

            return None

        except Exception as e:
            logger.error(f"Failed to get recommendation status: {str(e)}")
            return None

    async def _handle_error(
            self,
            pipeline_id: str,
            error: Exception
    ) -> None:
        """Handle errors in recommendation manager"""
        try:
            error_message = ProcessingMessage(
                message_type=MessageType.RECOMMENDATION_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'error': str(error),
                    'component': self.component_name,
                    'timestamp': datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.component_name,
                    target_component="pipeline_manager"
                )
            )

            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            # Cleanup handler
            await self.recommendation_handler.cleanup()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise