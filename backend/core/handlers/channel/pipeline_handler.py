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
    PipelineState,
    ComponentType,
    ModuleIdentifier
)
from .base.base_handler import BaseChannelHandler

logger = logging.getLogger(__name__)


class PipelineHandler(BaseChannelHandler):
    """
    Handler for pipeline operations.
    Routes messages between service layer and processing components.
    """

    def __init__(self, message_broker: MessageBroker):
        self.module_identifier = ModuleIdentifier(
            component_name="pipeline_handler",
            component_type=ComponentType.PIPELINE_HANDLER,
            department="pipeline",
            role="handler"
        )

        super().__init__(
            message_broker=message_broker,
            module_identifier=self.module_identifier
        )

        # Track routing contexts
        self.routing_contexts: Dict[str, Dict[str, Any]] = {}

    async def _setup_message_handlers(self) -> None:
        """Setup routing message handlers"""
        handlers = {
            # Quality Flow
            MessageType.QUALITY_SERVICE_START: self._route_to_quality,
            MessageType.QUALITY_SERVICE_COMPLETE: self._route_from_quality,

            # Insight Flow
            MessageType.INSIGHT_SERVICE_START: self._route_to_insight,
            MessageType.INSIGHT_SERVICE_COMPLETE: self._route_from_insight,

            # Analytics Flow
            MessageType.ANALYTICS_SERVICE_START: self._route_to_analytics,
            MessageType.ANALYTICS_SERVICE_COMPLETE: self._route_from_analytics,

            # Decision Flow
            MessageType.DECISION_SERVICE_START: self._route_to_decision,
            MessageType.DECISION_SERVICE_COMPLETE: self._route_from_decision,

            # Recommendation Flow
            MessageType.RECOMMENDATION_SERVICE_START: self._route_to_recommendation,
            MessageType.RECOMMENDATION_SERVICE_COMPLETE: self._route_from_recommendation,

            # Monitoring Flow
            MessageType.MONITORING_SERVICE_START: self._route_to_monitoring,
            MessageType.MONITORING_SERVICE_UPDATE: self._route_from_monitoring,

            # Report Flow
            MessageType.REPORT_SERVICE_START: self._route_to_report,
            MessageType.REPORT_SERVICE_COMPLETE: self._route_from_report,

            # Error Routing
            MessageType.QUALITY_ERROR: self._route_error,
            MessageType.INSIGHT_ERROR: self._route_error,
            MessageType.ANALYTICS_ERROR: self._route_error,
            MessageType.DECISION_ERROR: self._route_error,
            MessageType.RECOMMENDATION_ERROR: self._route_error,
            MessageType.MONITORING_ERROR: self._route_error,
            MessageType.REPORT_ERROR: self._route_error
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                f"pipeline.{message_type.value}",
                handler
            )

    async def _route_to_quality(self, message: ProcessingMessage) -> None:
        """Route to quality component"""
        try:
            pipeline_id = message.content['pipeline_id']
            self._track_routing(pipeline_id, 'quality', message.metadata.correlation_id)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_CHECK_REQUEST,
                    content=message.content,
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="quality_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            await self._handle_routing_error(message, str(e))

    async def _route_from_quality(self, message: ProcessingMessage) -> None:
        """Route from quality component"""
        try:
            pipeline_id = message.content['pipeline_id']
            routing = self._get_routing(pipeline_id)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STAGE_COMPLETE,
                    content=message.content,
                    metadata=MessageMetadata(
                        correlation_id=routing.get('correlation_id'),
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            await self._handle_routing_error(message, str(e))

    # Similar route_to/route_from methods for other components...

    async def _route_to_monitoring(self, message: ProcessingMessage) -> None:
        """Route to monitoring component"""
        try:
            pipeline_id = message.content['pipeline_id']
            self._track_routing(pipeline_id, 'monitoring', message.metadata.correlation_id)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_START,
                    content=message.content,
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="monitoring_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            await self._handle_routing_error(message, str(e))

    async def _route_from_monitoring(self, message: ProcessingMessage) -> None:
        """Route from monitoring component"""
        try:
            pipeline_id = message.content['pipeline_id']
            routing = self._get_routing(pipeline_id)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_SERVICE_UPDATE,
                    content=message.content,
                    metadata=MessageMetadata(
                        correlation_id=routing.get('correlation_id'),
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            await self._handle_routing_error(message, str(e))

    async def _route_to_report(self, message: ProcessingMessage) -> None:
        """Route to report component"""
        try:
            pipeline_id = message.content['pipeline_id']
            self._track_routing(pipeline_id, 'report', message.metadata.correlation_id)

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.REPORT_GENERATE_REQUEST,
                    content=message.content,
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="report_handler"
                    ),
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            await self._handle_routing_error(message, str(e))

    async def _route_error(self, message: ProcessingMessage) -> None:
        """Route component errors back to service"""
        try:
            pipeline_id = message.content['pipeline_id']
            routing = self._get_routing(pipeline_id)

            # Add routing context to error
            error_content = {
                **message.content,
                'component': message.metadata.source_component,
                'routing_context': routing
            }

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_STAGE_ERROR,
                    content=error_content,
                    metadata=MessageMetadata(
                        correlation_id=routing.get('correlation_id'),
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup routing context
            self._cleanup_routing(pipeline_id)

        except Exception as e:
            logger.error(f"Error routing failed: {str(e)}")

    def _track_routing(self, pipeline_id: str, component: str, correlation_id: str) -> None:
        """Track message routing context"""
        self.routing_contexts[pipeline_id] = {
            'component': component,
            'correlation_id': correlation_id,
            'timestamp': datetime.now().isoformat()
        }

    def _get_routing(self, pipeline_id: str) -> Dict[str, Any]:
        """Get routing context"""
        return self.routing_contexts.get(pipeline_id, {})

    def _cleanup_routing(self, pipeline_id: str) -> None:
        """Cleanup routing context"""
        if pipeline_id in self.routing_contexts:
            del self.routing_contexts[pipeline_id]

    async def _handle_routing_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle routing errors"""
        try:
            pipeline_id = message.content.get('pipeline_id')

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_HANDLER_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': f"Routing error: {error}",
                        'original_message': message.content
                    },
                    metadata=MessageMetadata(
                        correlation_id=message.metadata.correlation_id,
                        source_component=self.module_identifier.component_name,
                        target_component="pipeline_service"
                    ),
                    source_identifier=self.module_identifier
                )
            )

            if pipeline_id:
                self._cleanup_routing(pipeline_id)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            # Clear all routing contexts
            self.routing_contexts.clear()
            await super().cleanup()
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise