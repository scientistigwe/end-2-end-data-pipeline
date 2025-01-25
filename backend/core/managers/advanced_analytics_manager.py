# backend/core/sub_managers/analytics_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ProcessingStage,
    MessageMetadata,
    AnalyticsContext
)
from ..managers.base.base_manager import BaseManager, ManagerState

logger = logging.getLogger(__name__)


class AnalyticsManager(BaseManager):
    """
    Analytics Manager that coordinates advanced analytics through message broker.
    Maintains local state but communicates all actions through messages.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(
            message_broker=message_broker,
            component_name="advanced_analytics_manager",
            domain_type="analytics"
        )

        # Local state tracking
        self.active_processes: Dict[str, AnalyticsContext] = {}

        # Register message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Register handlers for all analytics-related messages"""
        handlers = {
            MessageType.ANALYTICS_START_REQUEST: self._handle_start_request,
            MessageType.ANALYTICS_MODEL_SELECTED: self._handle_model_selected,
            MessageType.ANALYTICS_PROCESSING: self._handle_processing_update,
            MessageType.ANALYTICS_COMPLETE: self._handle_process_complete,
            MessageType.ANALYTICS_ERROR: self._handle_analytics_error,
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.STAGING_AREA_CREATED: self._handle_staging_created
        }

        for message_type, handler in handlers.items():
            self.register_message_handler(message_type, handler)

    async def initiate_analytics_process(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> str:
        """
        Initiate analytics process through message broker
        Returns correlation ID for tracking
        """
        correlation_id = str(uuid.uuid4())

        # Request control point creation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.CONTROL_POINT_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.ADVANCED_ANALYTICS,
                'config': config
            },
            metadata=MessageMetadata(
                correlation_id=correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Initialize local tracking
        self.active_processes[pipeline_id] = AnalyticsContext(
            pipeline_id=pipeline_id,
            stage=ProcessingStage.ADVANCED_ANALYTICS,
            status=ProcessingStatus.PENDING,
            model_type=config.get('model_type', 'default_model'),
            parameters=config.get('parameters', {}),
            features=config.get('features', [])
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

        # Request staging area creation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGING_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'control_point_id': control_point_id,
                'source_type': 'analytics'
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

        context.staging_reference = staged_id

        # Start analytics processing
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.ANALYTICS_START,
            content={
                'pipeline_id': pipeline_id,
                'staged_id': staged_id,
                'config': context.parameters
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="analytics_handler"
            )
        ))

    async def _handle_model_selected(self, message: ProcessingMessage) -> None:
        """Handle model selection completion"""
        pipeline_id = message.content['pipeline_id']
        model_info = message.content['model_info']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.training_config.update(model_info)
        context.status = ProcessingStatus.IN_PROGRESS
        context.updated_at = datetime.now()

    async def _handle_processing_update(self, message: ProcessingMessage) -> None:
        """Handle analytics processing updates"""
        pipeline_id = message.content['pipeline_id']
        metrics = message.content.get('metrics', {})

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.performance_metrics.update(metrics)
        context.updated_at = datetime.now()

    async def _handle_process_complete(self, message: ProcessingMessage) -> None:
        """Handle analytics process completion"""
        pipeline_id = message.content['pipeline_id']
        results = message.content['results']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.status = ProcessingStatus.COMPLETED
        context.updated_at = datetime.now()

        # Notify completion
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGE_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.ADVANCED_ANALYTICS,
                'results': results
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Cleanup
        del self.active_processes[pipeline_id]

    async def _handle_analytics_error(self, message: ProcessingMessage) -> None:
        """Handle analytics process errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content['error']

        context = self.active_processes.get(pipeline_id)
        if context:
            context.status = ProcessingStatus.FAILED
            context.error = error

            # Notify error
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.ADVANCED_ANALYTICS,
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
                    message_type=MessageType.ANALYTICS_CLEANUP,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': 'Manager cleanup initiated'
                    }
                ))
                del self.active_processes[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise