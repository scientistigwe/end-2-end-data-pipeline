# core/handlers/channel/decision_handler.py

import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    DecisionContext,
    MessageMetadata
)
from core.handlers.base.base_handler import BaseChannelHandler
from data.processing.decisions.types.decision_types import (
    DecisionSource,
    DecisionRequest,
    ComponentDecision,
    DecisionState,
    ComponentUpdate,
    DecisionPhase,
    DecisionStatus
)
from core.staging.staging_manager import StagingManager
from data.processing.decisions.processor.decision_processor import DecisionProcessor

logger = logging.getLogger(__name__)


class DecisionHandler(BaseChannelHandler):
    """
    Handles communication and routing for decision-related messages.
    Coordinates between manager and processor.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            handler_name="decision_handler",
            domain_type="decision"
        )

        self.staging_manager = staging_manager
        self.processor = DecisionProcessor(message_broker, staging_manager)

    async def _handle_decision_request(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle incoming decision request"""
        try:
            pipeline_id = message.content['pipeline_id']
            source = DecisionSource(message.content['source'])

            # Create decision context
            context = DecisionContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.DECISION_MAKING,
                status=ProcessingStatus.PENDING,
                source_component=message.metadata.source_component,
                decision_type=message.content.get('decision_type'),
                options=message.content.get('options', []),
                impacts=message.content.get('impacts', {}),
                constraints=message.content.get('constraints', {}),
                required_validations=message.content.get('required_validations', []),
                timeout_minutes=message.content.get('timeout_minutes')
            )

            # Process through processor
            request = await self.processor.handle_component_request(
                pipeline_id,
                source,
                message.content,
                context
            )

            # Create response message
            response = message.create_response(
                MessageType.DECISION_OPTIONS,
                {
                    'pipeline_id': pipeline_id,
                    'request_id': request.request_id,
                    'options': request.options,
                    'requires_confirmation': request.requires_confirmation,
                    'context': self._format_context(context)
                }
            )

            await self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to handle decision request: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_decision_submit(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle submitted decision"""
        try:
            pipeline_id = message.content['pipeline_id']
            decision = message.content['decision']

            # Process decision
            component_decision = await self.processor.process_decision(
                pipeline_id,
                ComponentDecision(
                    decision_id=str(uuid.uuid4()),
                    request_id=decision['request_id'],
                    pipeline_id=pipeline_id,
                    source=DecisionSource(decision['source']),
                    selected_option=decision['selected_option'],
                    impacts=decision.get('impacts', {}),
                    user_confirmation=decision.get('user_confirmation', False),
                    metadata=decision.get('metadata', {})
                )
            )

            # Create response
            response_type = (
                MessageType.DECISION_COMPLETE
                if component_decision.validated
                else MessageType.DECISION_ERROR
            )

            response = message.create_response(
                response_type,
                {
                    'pipeline_id': pipeline_id,
                    'decision_id': component_decision.decision_id,
                    'status': 'completed' if component_decision.validated else 'failed',
                    'impacts': component_decision.impacts,
                    'metadata': component_decision.metadata
                }
            )

            await self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to handle decision submit: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_component_update(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle component updates about decision impact"""
        try:
            update = ComponentUpdate(
                component=message.metadata.source_component,
                decision_id=message.content['decision_id'],
                pipeline_id=message.content['pipeline_id'],
                status=message.content['status'],
                impact_details=message.content.get('impact_details', {}),
                requires_action=message.content.get('requires_action', False),
                metadata=message.content.get('metadata', {})
            )

            await self.processor.handle_component_update(update)

            # Notify if action required
            if update.requires_action:
                action_message = message.create_response(
                    MessageType.DECISION_IMPACT,
                    {
                        'pipeline_id': update.pipeline_id,
                        'decision_id': update.decision_id,
                        'component': update.component,
                        'requires_action': True,
                        'impact_details': update.impact_details
                    }
                )
                await self.message_broker.publish(action_message)

        except Exception as e:
            logger.error(f"Failed to handle component update: {str(e)}")
            await self._handle_error(message, e)

    def _format_context(self, context: DecisionContext) -> Dict[str, Any]:
        """Format context for response"""
        return {
            'source_component': context.source_component,
            'decision_type': context.decision_type,
            'constraints': context.constraints,
            'required_validations': context.required_validations,
            'timeout_minutes': context.timeout_minutes,
            'requires_confirmation': context.requires_confirmation
        }

    async def _handle_error(
            self,
            message: ProcessingMessage,
            error: Exception
    ) -> None:
        """Handle processing errors"""
        error_message = message.create_response(
            MessageType.DECISION_ERROR,
            {
                'error': str(error),
                'pipeline_id': message.content.get('pipeline_id'),
                'source': message.metadata.source_component,
                'timestamp': datetime.now().isoformat()
            }
        )
        await self.message_broker.publish(error_message)