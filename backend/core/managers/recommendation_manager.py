# backend/core/sub_managers/recommendation_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    RecommendationContext,
    RecommendationState
)
from ..managers.base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class RecommendationManager(BaseManager):
    """
    Recommendation Manager that coordinates recommendation generation through message broker.
    Maintains local state but communicates all actions through messages.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(
            message_broker=message_broker,
            component_name="recommendation_manager",
            domain_type="recommendation"
        )

        # Local state tracking
        self.active_processes: Dict[str, RecommendationContext] = {}

        # Register message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Register handlers for all recommendation-related messages"""
        handlers = {
            MessageType.RECOMMENDATION_START_REQUEST: self._handle_start_request,
            MessageType.RECOMMENDATION_ENGINE_SELECTED: self._handle_engine_selected,
            MessageType.RECOMMENDATION_RESULTS_READY: self._handle_results_ready,
            MessageType.RECOMMENDATION_FILTERING_COMPLETE: self._handle_filtering_complete,
            MessageType.RECOMMENDATION_RANKING_COMPLETE: self._handle_ranking_complete,
            MessageType.RECOMMENDATION_AGGREGATION_COMPLETE: self._handle_aggregation_complete,
            MessageType.RECOMMENDATION_ERROR: self._handle_recommendation_error,
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.STAGING_CREATED: self._handle_staging_created
        }

        for message_type, handler in handlers.items():
            self.register_message_handler(message_type, handler)

    async def initiate_recommendation_process(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> str:
        """
        Initiate recommendation generation through message broker
        Returns correlation ID for tracking
        """
        correlation_id = str(uuid.uuid4())

        # Request control point creation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.CONTROL_POINT_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.RECOMMENDATION,
                'config': config
            },
            metadata=MessageMetadata(
                correlation_id=correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Initialize tracking context
        self.active_processes[pipeline_id] = RecommendationContext(
            pipeline_id=pipeline_id,
            correlation_id=correlation_id,
            state=RecommendationState.INITIALIZING,
            enabled_engines=config.get('enabled_engines', []),
            engine_weights=config.get('engine_weights', {}),
            filtering_rules=config.get('filtering_rules', {}),
            ranking_criteria=config.get('ranking_criteria', {})
        )

        return correlation_id

    async def _handle_control_point_created(self, message: ProcessingMessage) -> None:
        """Handle control point creation confirmation"""
        pipeline_id = message.content['pipeline_id']
        control_point_id = message.content['control_point_id']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.control_point_id = control_point_id

        # Request staging area
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'control_point_id': control_point_id,
                'source_type': 'recommendation'
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="staging_manager"
            )
        ))

    async def _handle_staging_created(self, message: ProcessingMessage) -> None:
        """Handle staging area creation confirmation"""
        pipeline_id = message.content['pipeline_id']
        staged_id = message.content['staged_id']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.staged_id = staged_id
        context.state = RecommendationState.ENGINE_SELECTION

        # Begin recommendation processing
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_START_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'staged_id': staged_id,
                'engines': context.enabled_engines,
                'weights': context.engine_weights
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="recommendation_handler"
            )
        ))

    async def _handle_engine_selected(self, message: ProcessingMessage) -> None:
        """Handle engine selection results"""
        pipeline_id = message.content['pipeline_id']
        engine_results = message.content['engine_results']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.state = RecommendationState.FILTERING
        context.add_engine_results(
            message.content['engine'],
            engine_results
        )

        if len(context.engine_results) == len(context.enabled_engines):
            # All engines have reported, proceed to filtering
            await self._start_filtering(pipeline_id)

    async def _start_filtering(self, pipeline_id: str) -> None:
        """Initiate filtering of recommendations"""
        context = self.active_processes[pipeline_id]

        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_FILTER_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'recommendations': context.engine_results,
                'rules': context.filtering_rules
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="recommendation_handler"
            )
        ))

    async def _handle_filtering_complete(self, message: ProcessingMessage) -> None:
        """Handle filtering completion"""
        pipeline_id = message.content['pipeline_id']
        filtered_results = message.content['filtered_results']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.state = RecommendationState.RANKING

        # Start ranking process
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_RANK_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'recommendations': filtered_results,
                'criteria': context.ranking_criteria
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="recommendation_handler"
            )
        ))

    async def _handle_ranking_complete(self, message: ProcessingMessage) -> None:
        """Handle ranking completion"""
        pipeline_id = message.content['pipeline_id']
        ranked_results = message.content['ranked_results']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.state = RecommendationState.AGGREGATING

        # Start aggregation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.RECOMMENDATION_AGGREGATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'recommendations': ranked_results,
                'weights': context.engine_weights
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="recommendation_handler"
            )
        ))

    async def _handle_aggregation_complete(self, message: ProcessingMessage) -> None:
        """Handle aggregation completion"""
        pipeline_id = message.content['pipeline_id']
        final_results = message.content['final_results']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.state = RecommendationState.COMPLETED
        context.aggregated_results = final_results

        # Notify completion
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGE_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.RECOMMENDATION,
                'results': final_results
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Cleanup
        del self.active_processes[pipeline_id]

    async def _handle_recommendation_error(self, message: ProcessingMessage) -> None:
        """Handle recommendation processing errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content['error']

        context = self.active_processes.get(pipeline_id)
        if context:
            context.state = RecommendationState.FAILED
            context.error = error

            # Notify error
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.RECOMMENDATION,
                    'error': error
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.component_name,
                    target_component="control_point_manager"
                )
            ))

            # Cleanup
            del self.active_processes[pipeline_id]

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        try:
            # Notify cleanup for all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self.message_broker.publish(ProcessingMessage(
                    message_type=MessageType.RECOMMENDATION_CLEANUP,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': 'Manager cleanup initiated'
                    }
                ))
                del self.active_processes[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise