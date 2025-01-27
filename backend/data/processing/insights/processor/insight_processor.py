# backend/core/processors/insight_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ComponentType,
    ModuleIdentifier,
    MessageMetadata,
    ProcessingStage,
    ProcessingStatus,
    InsightState,
    InsightContext,
    InsightMetrics
)
from ...insights.generators import (
    pattern_insights,
    trend_insights,
    relationship_insights,
    anomaly_insights,
    business_goal_insights
)
from ...insights.validators import (
    pattern_validator,
    trend_validator,
    relationship_validator,
    anomaly_validator,
    business_goal_validator
)

logger = logging.getLogger(__name__)


class InsightProcessor:
    """
    Insight Processor: Handles direct module interaction and insight generation.
    Maintains message-based coordination while having direct module access.
    """

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker

        # Processor identification
        self.module_identifier = ModuleIdentifier(
            component_name="insight_processor",
            component_type=ComponentType.INSIGHT_PROCESSOR,
            department="insight",
            role="processor"
        )

        # Active processing contexts
        self.active_contexts: Dict[str, InsightContext] = {}

        # Initialize modules
        self._initialize_modules()

        # Setup handlers
        self._setup_message_handlers()

    def _initialize_modules(self) -> None:
        """Initialize insight generation modules"""
        self.generators = {
            'pattern': pattern_insights,
            'trend': trend_insights,
            'relationship': relationship_insights,
            'anomaly': anomaly_insights,
            'business_goal': business_goal_insights
        }

        self.validators = {
            'pattern': pattern_validator,
            'trend': trend_validator,
            'relationship': relationship_validator,
            'anomaly': anomaly_validator,
            'business_goal': business_goal_validator
        }

    def _setup_message_handlers(self) -> None:
        """Setup message handlers for processor"""
        handlers = {
            MessageType.INSIGHT_PROCESSOR_START: self._handle_processor_start,
            MessageType.INSIGHT_PROCESSOR_UPDATE: self._handle_processor_update,
            MessageType.INSIGHT_PROCESSOR_VALIDATE: self._handle_validation_request,
            MessageType.INSIGHT_PROCESSOR_CANCEL: self._handle_cancellation
        }

        for message_type, handler in handlers.items():
            self.message_broker.subscribe(
                self.module_identifier,
                f"insight.{message_type.value}.#",
                handler
            )

    async def _handle_processor_start(self, message: ProcessingMessage) -> None:
        """Handle start of insight generation"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            config = message.content.get('config', {})

            # Initialize context
            context = InsightContext(
                pipeline_id=pipeline_id,
                state=InsightState.INITIALIZING,
                config=config
            )
            self.active_contexts[pipeline_id] = context

            # Start insight generation process
            await self._generate_insights(pipeline_id, config)

        except Exception as e:
            logger.error(f"Processor start failed: {str(e)}")
            await self._handle_processing_error(message, str(e))

    async def _generate_insights(
            self,
            pipeline_id: str,
            config: Dict[str, Any]
    ) -> None:
        """Generate insights using appropriate modules"""
        try:
            context = self.active_contexts[pipeline_id]
            context.state = InsightState.DETECTION_IN_PROGRESS

            # Update status
            await self._publish_status_update(
                pipeline_id,
                "Generating insights",
                progress=0.0
            )

            # Get data from staging
            data = await self._get_staged_data(pipeline_id)

            # Generate insights by type
            insights = {}
            total_types = len(config.get('enabled_types', self.generators.keys()))
            for idx, insight_type in enumerate(config.get('enabled_types', self.generators.keys())):
                if insight_type in self.generators:
                    # Generate insights
                    type_insights = await self.generators[insight_type].generate_insights(
                        data,
                        config.get(f'{insight_type}_config', {})
                    )

                    # Validate insights
                    validated_insights = await self.validators[insight_type].validate_insights(
                        type_insights,
                        config.get('validation_rules', {})
                    )

                    insights[insight_type] = validated_insights

                    # Update progress
                    progress = (idx + 1) / total_types * 100
                    await self._publish_status_update(
                        pipeline_id,
                        f"Generated {insight_type} insights",
                        progress=progress
                    )

            # Store results
            results_id = await self._store_results(pipeline_id, insights)

            # Publish completion
            await self._publish_completion(pipeline_id, results_id, insights)

            # Cleanup
            del self.active_contexts[pipeline_id]

        except Exception as e:
            logger.error(f"Insight generation failed: {str(e)}")
            await self._handle_processing_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                str(e)
            )

    async def _validate_insights(
            self,
            pipeline_id: str,
            insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate generated insights"""
        try:
            validation_results = {}
            for insight_type, type_insights in insights.items():
                if insight_type in self.validators:
                    validation = await self.validators[insight_type].validate(
                        type_insights,
                        self.active_contexts[pipeline_id].config.get('validation_rules', {})
                    )
                    validation_results[insight_type] = validation

            return validation_results

        except Exception as e:
            logger.error(f"Insight validation failed: {str(e)}")
            raise

    async def _store_results(
            self,
            pipeline_id: str,
            insights: Dict[str, Any]
    ) -> str:
        """Store generated insights"""
        # Implementation would store results in your storage system
        # Return storage reference/ID
        return f"insights_{pipeline_id}"

    async def _publish_status_update(
            self,
            pipeline_id: str,
            status: str,
            progress: float
    ) -> None:
        """Publish status update"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_PROCESSOR_STATUS,
                content={
                    'pipeline_id': pipeline_id,
                    'status': status,
                    'progress': progress,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="insight_handler",
                    domain_type="insight",
                    processing_stage=ProcessingStage.INSIGHT_GENERATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _publish_completion(
            self,
            pipeline_id: str,
            results_id: str,
            insights: Dict[str, Any]
    ) -> None:
        """Publish completion message"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.INSIGHT_PROCESSOR_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'results_id': results_id,
                    'insights': insights,
                    'timestamp': datetime.utcnow().isoformat()
                },
                metadata=MessageMetadata(
                    source_component=self.module_identifier.component_name,
                    target_component="insight_handler",
                    domain_type="insight",
                    processing_stage=ProcessingStage.INSIGHT_GENERATION
                ),
                source_identifier=self.module_identifier
            )
        )

    async def _handle_processing_error(
            self,
            message: ProcessingMessage,
            error: str
    ) -> None:
        """Handle processing errors"""
        pipeline_id = message.content.get('pipeline_id')

        if pipeline_id in self.active_contexts:
            context = self.active_contexts[pipeline_id]
            context.state = InsightState.ERROR

            # Publish error
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.INSIGHT_PROCESSOR_ERROR,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': error,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="insight_handler",
                        domain_type="insight",
                        processing_stage=ProcessingStage.INSIGHT_GENERATION
                    ),
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup
            del self.active_contexts[pipeline_id]

    async def cleanup(self) -> None:
        """Cleanup processor resources"""
        try:
            # Cancel all active processing
            for pipeline_id in list(self.active_contexts.keys()):
                await self._handle_processing_error(
                    ProcessingMessage(content={'pipeline_id': pipeline_id}),
                    "Processor cleanup initiated"
                )

            # Unsubscribe from messages
            await self.message_broker.unsubscribe_all(
                self.module_identifier.component_name
            )

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise