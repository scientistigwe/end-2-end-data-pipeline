# backend/core/channel_handlers/insight_handler.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.channel_handlers.base_channel_handler import BaseChannelHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage

# Import the insight module manager
from backend.data_pipeline.insight_analysis.insight_processor import InsightProcessor

logger = logging.getLogger(__name__)


@dataclass
class InsightContext:
    """Context for insight processing"""
    pipeline_id: str
    business_goals: Dict[str, Any]
    data_features: Dict[str, Any]
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"


class InsightChannelHandler(BaseChannelHandler):
    """
    Handles communication between orchestrator and insight module manager
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "insight_handler")

        # Initialize insight module manager
        self.insight_manager = InsightModuleManager(message_broker)

        # Track active insight processes
        self.active_insights: Dict[str, InsightContext] = {}

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers"""
        self.register_callback(
            MessageType.START_INSIGHT_GENERATION,
            self._handle_insight_start
        )
        self.register_callback(
            MessageType.INSIGHT_UPDATE,
            self._handle_insight_update
        )
        self.register_callback(
            MessageType.INSIGHT_COMPLETE,
            self._handle_insight_complete
        )
        self.register_callback(
            MessageType.INSIGHT_ERROR,
            self._handle_insight_error
        )

    def initiate_insight_generation(self, pipeline_id: str,
                                    data: Dict[str, Any],
                                    business_goals: Dict[str, Any],
                                    context: Dict[str, Any]) -> None:
        """Entry point for insight generation"""
        try:
            # Create insight context
            insight_context = InsightContext(
                pipeline_id=pipeline_id,
                business_goals=business_goals,
                data_features=data,
                metadata=context
            )

            self.active_insights[pipeline_id] = insight_context

            # Route to insight manager
            self.insight_manager.start_insight_process(
                pipeline_id,
                data,
                business_goals,
                context
            )

        except Exception as e:
            self.logger.error(f"Failed to initiate insight generation: {str(e)}")
            self._handle_insight_error(pipeline_id, str(e))

    def _handle_insight_start(self, message: ProcessingMessage) -> None:
        """Handle insight generation start request"""
        pipeline_id = message.content['pipeline_id']
        data = message.content.get('data', {})
        business_goals = message.content.get('business_goals', {})
        context = message.content.get('context', {})

        self.initiate_insight_generation(
            pipeline_id,
            data,
            business_goals,
            context
        )

    def _handle_insight_update(self, message: ProcessingMessage) -> None:
        """Handle insight generation updates"""
        pipeline_id = message.content['pipeline_id']
        status = message.content.get('status')
        progress = message.content.get('progress')

        context = self.active_insights.get(pipeline_id)
        if context:
            context.status = status

            # Forward update to orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.INSIGHT_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': status,
                    'progress': progress
                }
            )

    def _handle_insight_complete(self, message: ProcessingMessage) -> None:
        """Handle insight generation completion"""
        pipeline_id = message.content['pipeline_id']
        insights = message.content.get('insights', {})

        context = self.active_insights.get(pipeline_id)
        if context:
            # Forward completion to orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.INSIGHT_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'insights': insights,
                    'business_goals': context.business_goals,
                    'metadata': context.metadata
                }
            )

            # Cleanup
            self._cleanup_insight_process(pipeline_id)

    def _handle_insight_error(self, pipeline_id: str, error: str) -> None:
        """Handle insight generation errors"""
        context = self.active_insights.get(pipeline_id)
        if context:
            # Send error notification
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.INSIGHT_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'error': error,
                    'business_goals': context.business_goals
                }
            )

            # Cleanup
            self._cleanup_insight_process(pipeline_id)

    def get_insight_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current insight generation status"""
        context = self.active_insights.get(pipeline_id)
        if not context:
            return None

        # Get status from both handler and insight manager
        handler_status = {
            'pipeline_id': pipeline_id,
            'status': context.status,
            'created_at': context.created_at.isoformat(),
            'business_goals': context.business_goals
        }

        # Get detailed insight status
        insight_status = self.insight_manager.get_process_status(pipeline_id)

        return {
            **handler_status,
            'insight_details': insight_status
        }

    def _cleanup_insight_process(self, pipeline_id: str) -> None:
        """Clean up insight process resources"""
        if pipeline_id in self.active_insights:
            del self.active_insights[pipeline_id]

    def __del__(self):
        """Cleanup handler resources"""
        self.active_insights.clear()
        super().__del__()
