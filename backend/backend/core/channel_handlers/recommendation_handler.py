# backend/core/channel_handlers/recommendation_handler.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.channel_handlers.base_channel_handler import BaseChannelHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage
from backend.data_pipeline.recommendation.recommendation_processor import (
    RecommendationProcessor,
    RecommendationPhase
)

logger = logging.getLogger(__name__)


@dataclass
class RecommendationContext:
    """Context for recommendation processing"""
    pipeline_id: str
    user_id: str
    context_type: str
    current_phase: RecommendationPhase
    source_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"


class RecommendationChannelHandler(BaseChannelHandler):
    """
    Handles communication between orchestrator and recommendation processor
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "recommendation_handler")

        # Initialize recommendation processor
        self.recommendation_processor = RecommendationProcessor(message_broker)

        # Track active recommendations
        self.active_recommendations: Dict[str, RecommendationContext] = {}

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers"""
        self.register_callback(
            MessageType.START_RECOMMENDATION,
            self._handle_recommendation_start
        )
        self.register_callback(
            MessageType.GENERATE_RECOMMENDATIONS,
            self._handle_recommendation_request
        )
        self.register_callback(
            MessageType.RECOMMENDATION_UPDATE,
            self._handle_recommendation_update
        )
        self.register_callback(
            MessageType.RECOMMENDATION_COMPLETE,
            self._handle_recommendation_complete
        )
        self.register_callback(
            MessageType.RECOMMENDATION_ERROR,
            self._handle_recommendation_error
        )

    def initiate_recommendations(self, pipeline_id: str, user_id: str,
                               context_type: str, data: Dict[str, Any],
                               metadata: Optional[Dict[str, Any]] = None) -> None:
        """Entry point for recommendation process"""
        try:
            # Create recommendation context
            rec_context = RecommendationContext(
                pipeline_id=pipeline_id,
                user_id=user_id,
                context_type=context_type,
                current_phase=RecommendationPhase.CANDIDATE_GENERATION,
                source_data=data,
                metadata=metadata or {}
            )

            self.active_recommendations[pipeline_id] = rec_context

            # Start recommendation process
            self.recommendation_processor.start_recommendation_process(
                pipeline_id=pipeline_id,
                user_id=user_id,
                context_type=context_type,
                metadata={**metadata, 'source_data': data} if metadata else {'source_data': data}
            )

        except Exception as e:
            self.logger.error(f"Failed to initiate recommendations: {str(e)}")
            self._handle_processing_error(pipeline_id, str(e))

    def _handle_recommendation_start(self, message: ProcessingMessage) -> None:
        """Handle recommendation process start request"""
        pipeline_id = message.content['pipeline_id']
        user_id = message.content['user_id']
        context_type = message.content['context_type']
        data = message.content.get('data', {})
        metadata = message.content.get('metadata', {})

        self.initiate_recommendations(pipeline_id, user_id, context_type, data, metadata)

    def _handle_recommendation_request(self, message: ProcessingMessage) -> None:
        """Process recommendation generation request"""
        try:
            pipeline_id = message.content['pipeline_id']
            user_id = message.content.get('user_id', 'default_user')
            context_type = message.content.get('context_type', 'general')
            data = message.content.get('data', {})
            metadata = message.content.get('metadata', {})

            self.initiate_recommendations(pipeline_id, user_id, context_type, data, metadata)

        except Exception as e:
            self.logger.error(f"Failed to process recommendation request: {str(e)}")
            self._handle_processing_error(message.content.get('pipeline_id'), str(e))

    def _handle_recommendation_update(self, message: ProcessingMessage) -> None:
        """Handle recommendation process updates"""
        pipeline_id = message.content['pipeline_id']
        phase = message.content.get('phase')
        status = message.content.get('status')

        context = self.active_recommendations.get(pipeline_id)
        if context:
            context.current_phase = RecommendationPhase(phase)
            context.status = status

            # Forward update to orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.RECOMMENDATION_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'phase': phase,
                    'status': status,
                    'timestamp': datetime.now().isoformat()
                }
            )

    def _handle_recommendation_complete(self, message: ProcessingMessage) -> None:
        """Handle recommendation process completion"""
        pipeline_id = message.content['pipeline_id']
        context = self.active_recommendations.get(pipeline_id)

        if context:
            # Forward completion to orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.RECOMMENDATIONS_READY,
                content={
                    'pipeline_id': pipeline_id,
                    'recommendations': message.content.get('recommendations', []),
                    'metadata': context.metadata,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Cleanup
            self._cleanup_recommendation(pipeline_id)

    def _handle_recommendation_error(self, message: ProcessingMessage) -> None:
        """Handle recommendation process errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content.get('error')
        phase = message.content.get('phase')

        self._handle_processing_error(pipeline_id, error, phase)

    def _handle_processing_error(self, pipeline_id: str, error: str,
                               phase: Optional[str] = None) -> None:
        """Handle processing errors"""
        context = self.active_recommendations.get(pipeline_id)
        if context:
            # Send error notification
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.RECOMMENDATION_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'phase': phase or context.current_phase.value,
                    'error': error,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Cleanup
            self._cleanup_recommendation(pipeline_id)

    def get_recommendation_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current recommendation status"""
        context = self.active_recommendations.get(pipeline_id)
        if not context:
            return None

        # Get status from both handler and processor
        handler_status = {
            'pipeline_id': pipeline_id,
            'user_id': context.user_id,
            'context_type': context.context_type,
            'phase': context.current_phase.value,
            'status': context.status,
            'created_at': context.created_at.isoformat()
        }

        # Get detailed processor status
        processor_status = self.recommendation_processor.get_process_status(pipeline_id)

        return {
            **handler_status,
            'processor_details': processor_status
        }

    def _cleanup_recommendation(self, pipeline_id: str) -> None:
        """Clean up recommendation resources"""
        if pipeline_id in self.active_recommendations:
            del self.active_recommendations[pipeline_id]

    def __del__(self):
        """Cleanup handler resources"""
        self.active_recommendations.clear()
        super().__del__()