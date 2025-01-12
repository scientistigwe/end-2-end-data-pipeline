import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID
import uuid

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
from backend.data_pipeline.insight_analysis.insight_processor import (
    InsightProcessor,
    InsightPhase
)

logger = logging.getLogger(__name__)


class InsightChannelHandler(BaseChannelHandler):
    """
    Handles communication and routing for insight-related messages

    Responsibilities:
    - Route insight-related messages
    - Coordinate with insight processor
    - Interface with insight manager
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            process_handler: Optional[CoreProcessHandler] = None,
            insight_processor: Optional[InsightProcessor] = None
    ):
        """
        Initialize insight channel handler

        Args:
            message_broker: Message broker for communication
            process_handler: Optional process handler
            insight_processor: Optional insight processor
        """
        super().__init__(message_broker, "insight_handler")

        # Initialize dependencies
        self.process_handler = process_handler or CoreProcessHandler(message_broker)
        self.insight_processor = insight_processor or InsightProcessor(message_broker)

        # Active insights tracking
        self.active_insights: Dict[str, Dict[str, Any]] = {}

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers for insight processing"""
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

    def _handle_insight_start(self, message: ProcessingMessage) -> None:
        """
        Handle insight generation start request

        Args:
            message: Processing message initiating insight generation
        """
        try:
            pipeline_id = message.content.get('pipeline_id')
            data = message.content.get('data', {})
            business_goals = message.content.get('business_goals', {})
            context = message.content.get('context', {})

            # Generate unique insight ID
            insight_id = str(uuid.uuid4())

            # Prepare context for process tracking
            context.update({
                'insight_id': insight_id,
                'pipeline_id': pipeline_id
            })

            # Track active insight
            self.active_insights[insight_id] = {
                'pipeline_id': pipeline_id,
                'business_goals': business_goals,
                'status': 'started'
            }

            # Execute insight generation process
            insight_process = self.process_handler.execute_process(
                self._run_insight_generation,
                pipeline_id=pipeline_id,
                stage=ProcessingStage.ANALYSIS_EXECUTION,
                message_type=MessageType.START_INSIGHT_GENERATION,
                data=data,
                business_goals=business_goals,
                context=context
            )

            # Publish start status to insight manager
            start_response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="insight_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.INSIGHT_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'insight_id': insight_id,
                    'status': 'started'
                }
            )
            self.message_broker.publish(start_response)

        except Exception as e:
            logger.error(f"Failed to start insight generation: {e}")
            self._handle_insight_error(
                ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="insight_manager",
                        component_type=ComponentType.MANAGER
                    ),
                    message_type=MessageType.INSIGHT_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': str(e)
                    }
                )
            )

    async def _run_insight_generation(
            self,
            data: Dict[str, Any],
            business_goals: Dict[str, Any],
            context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Core insight generation logic

        Args:
            data: Input data for insight generation
            business_goals: Business objectives
            context: Processing context

        Returns:
            Generated insights
        """
        try:
            # Run objective mapping
            objective_mapping = await self.insight_processor.map_objectives(
                data,
                business_goals
            )

            # Run exploratory analysis
            exploratory_analysis = await self.insight_processor.run_exploratory_analysis(
                data,
                objective_mapping
            )

            # Run advanced analysis
            advanced_insights = await self.insight_processor.run_advanced_analysis(
                data,
                exploratory_analysis
            )

            # Generate recommendations
            final_insights = await self.insight_processor.generate_recommendations(
                advanced_insights,
                business_goals
            )

            return {
                'pipeline_id': context.get('pipeline_id'),
                'insight_id': context.get('insight_id'),
                'objective_mapping': objective_mapping,
                'exploratory_analysis': exploratory_analysis,
                'advanced_insights': advanced_insights,
                'recommendations': final_insights
            }

        except Exception as e:
            logger.error(f"Insight generation failed: {e}")
            raise

    def _handle_insight_update(self, message: ProcessingMessage) -> None:
        """
        Handle insight generation updates

        Args:
            message: Processing message with insight update
        """
        try:
            insight_id = message.content.get('insight_id')
            pipeline_id = message.content.get('pipeline_id')
            status = message.content.get('status')
            progress = message.content.get('progress', 0)

            # Update active insight status
            if insight_id in self.active_insights:
                self.active_insights[insight_id]['status'] = status

            # Forward update to insight manager
            update_response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="insight_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.INSIGHT_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'insight_id': insight_id,
                    'status': status,
                    'progress': progress
                }
            )
            self.message_broker.publish(update_response)

        except Exception as e:
            logger.error(f"Error handling insight update: {e}")

    def _handle_insight_complete(self, message: ProcessingMessage) -> None:
        """
        Handle insight generation completion

        Args:
            message: Processing message about insight generation completion
        """
        try:
            insight_id = message.content.get('insight_id')
            pipeline_id = message.content.get('pipeline_id')
            insights = message.content.get('results', {})

            # Remove from active insights
            active_insight = self.active_insights.pop(insight_id, {})

            # Forward completion to insight manager
            completion_response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="insight_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.INSIGHT_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'insight_id': insight_id,
                    'insights': insights,
                    'business_goals': active_insight.get('business_goals', {})
                }
            )
            self.message_broker.publish(completion_response)

        except Exception as e:
            logger.error(f"Error handling insight completion: {e}")

    def _handle_insight_error(self, message: ProcessingMessage) -> None:
        """
        Handle insight generation errors

        Args:
            message: Processing message with error details
        """
        try:
            insight_id = message.content.get('insight_id')
            pipeline_id = message.content.get('pipeline_id')
            error = message.content.get('error')

            # Remove from active insights
            active_insight = self.active_insights.pop(insight_id, {})

            # Forward error to insight manager
            error_response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="insight_manager",
                    component_type=ComponentType.MANAGER
                ),
                message_type=MessageType.INSIGHT_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'insight_id': insight_id,
                    'error': error,
                    'business_goals': active_insight.get('business_goals', {})
                }
            )
            self.message_broker.publish(error_response)

        except Exception as e:
            logger.error(f"Error handling insight error: {e}")

    def get_insight_status(self, insight_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current insight generation status

        Args:
            insight_id: Unique insight identifier

        Returns:
            Status dictionary or None
        """
        return self.active_insights.get(insight_id)

    def __del__(self):
        """Cleanup handler resources"""
        self.active_insights.clear()
        super().__del__()