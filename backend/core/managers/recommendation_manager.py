# backend/core/managers/recommendation_manager.py

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
    RecommendationState,
    ModuleIdentifier,
    ComponentType
)

logger = logging.getLogger(__name__)

class RecommendationManager:
    """
    Recommendation Manager: Coordinates high-level recommendation workflow.
    - Communicates with CPM
    - Maintains process state
    - Coordinates workflow through messages
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Manager identification
        self.module_identifier = ModuleIdentifier(
            component_name="recommendation_manager",
            component_type=ComponentType.RECOMMENDATION_MANAGER,
            department="recommendation",
            role="manager"
        )

        # Active processes tracking
        self.active_processes: Dict[str, RecommendationContext] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup message handlers"""
        handlers = {
            # CPM Messages
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.CONTROL_POINT_UPDATE: self._handle_control_point_update,
            MessageType.CONTROL_POINT_DECISION: self._handle_control_point_decision,

            # Service Messages
            MessageType.RECOMMENDATION_SERVICE_STATUS: self._handle_service_status,
            MessageType.RECOMMENDATION_SERVICE_COMPLETE: self._handle_service_complete,
            MessageType.RECOMMENDATION_SERVICE_ERROR: self._handle_service_error,

            # Status Messages
            MessageType.RECOMMENDATION_METRICS_UPDATE: self._handle_metrics_update,
            MessageType.RECOMMENDATION_ENGINE_ERROR: self._handle_engine_error
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                message_type.value,
                handler
            )

    async def initiate_recommendation_process(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> str:
        """Initiate new recommendation process"""
        correlation_id = str(uuid.uuid4())

        # Request control point creation
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.CONTROL_POINT_CREATE_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.RECOMMENDATION,
                    'config': config
                },
                metadata=MessageMetadata(
                    correlation_id=correlation_id,
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager"
                ),
                source_identifier=self.module_identifier
            )
        )

        # Initialize context
        self.active_processes[pipeline_id] = RecommendationContext(
            pipeline_id=pipeline_id,
            correlation_id=correlation_id,
            state=RecommendationState.INITIALIZING,
            config=config
        )

        return correlation_id

    async def _handle_control_point_created(self, message: ProcessingMessage) -> None:
        """Handle control point creation confirmation"""
        try:
            pipeline_id = message.content['pipeline_id']
            control_point_id = message.content['control_point_id']

            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            context.control_point_id = control_point_id

            # Start service processing
            await self._publish_service_start(pipeline_id, context.config)

        except Exception as e:
            logger.error(f"Control point handling failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_service_status(self, message: ProcessingMessage) -> None:
        """Handle status update from service"""
        try:
            pipeline_id = message.content['pipeline_id']
            status = message.content['status']
            progress = message.content.get('progress', 0)

            context = self.active_processes.get(pipeline_id)
            if context:
                # Update context
                context.status = status
                context.progress = progress

                # Notify CPM
                await self._publish_status_update(
                    pipeline_id=pipeline_id,
                    status=status,
                    progress=progress
                )

        except Exception as e:
            logger.error(f"Status update failed: {str(e)}")

    async def _handle_service_complete(self, message: ProcessingMessage) -> None:
        """Handle completion from service"""
        try:
            pipeline_id = message.content['pipeline_id']
            results = message.content.get('results', {})

            context = self.active_processes.get(pipeline_id)
            if context:
                # Notify CPM of completion
                await self._publish_completion(
                    pipeline_id=pipeline_id,
                    results=results
                )

                # Cleanup
                del self.active_processes[pipeline_id]

        except Exception as e:
            logger.error(f"Completion handling failed: {str(e)}")

    async def _publish_service_start(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> None:
        """Publish service start request"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.RECOMMENDATION_SERVICE_START,
                content={
                    'pipeline_id': pipeline_id,
                    'config': config,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="recommendation_service",
                    domain_type="recommendation",
                    processing_stage=ProcessingStage.RECOMMENDATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _publish_status_update(
            self,
            pipeline_id: str,
            status: str,
            progress: float
    ) -> None:
        """Publish status update to CPM"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_STATUS,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.RECOMMENDATION,
                    'status': status,
                    'progress': progress,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager",
                    domain_type="recommendation"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _publish_completion(
            self,
            pipeline_id: str,
            results: Dict[str, Any]
    ) -> None:
        """Publish completion to CPM"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.RECOMMENDATION,
                    'results': results,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager",
                    domain_type="recommendation"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _publish_error(self, pipeline_id: str, error: str) -> None:
        """Publish error to CPM"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.RECOMMENDATION,
                    'error': error,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="control_point_manager",
                    domain_type="recommendation"
                ),
                source_identifier=self.module_identifier
            )
        )

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            # Notify cleanup for active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self._publish_error(
                    pipeline_id,
                    "Manager cleanup initiated"
                )
                del self.active_processes[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise