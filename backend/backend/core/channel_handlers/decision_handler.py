import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

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
from backend.data_pipeline.decision.decision_processor import (
    DecisionProcessor,
    DecisionPhase
)

logger = logging.getLogger(__name__)


class DecisionChannelHandler(BaseChannelHandler):
    """
    Handles communication and routing for decision-related messages

    Responsibilities:
    - Route decision-related messages
    - Coordinate with decision processor
    - Interface with decision manager
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            process_handler: Optional[CoreProcessHandler] = None,
            decision_processor: Optional[DecisionProcessor] = None
    ):
        """Initialize decision channel handler"""
        super().__init__(message_broker, "decision_handler")

        # Initialize dependencies
        self.process_handler = process_handler or CoreProcessHandler(message_broker)
        self.decision_processor = decision_processor or DecisionProcessor(message_broker)

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers for decision processing"""
        self.register_callback(
            MessageType.DECISION_START,
            self._handle_decision_start
        )
        self.register_callback(
            MessageType.DECISION_COMPLETE,
            self._handle_decision_complete
        )
        self.register_callback(
            MessageType.DECISION_UPDATE,
            self._handle_decision_update
        )
        self.register_callback(
            MessageType.DECISION_ERROR,
            self._handle_decision_error
        )

    def _handle_decision_start(self, message: ProcessingMessage) -> None:
        """Handle decision process start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            data = message.content.get('data', {})
            context = message.content.get('context', {})

            # Create response message to decision manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="decision_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_decision_start"
                ),
                message_type=MessageType.DECISION_STATUS_UPDATE,
                content={
                    'pipeline_id': pipeline_id,
                    'status': 'started',
                    'phase': DecisionPhase.RECOMMENDATION.value
                }
            )

            # Execute process via process handler
            self.process_handler.execute_process(
                self._run_decision_process,
                pipeline_id=pipeline_id,
                stage=ProcessingStage.DECISION_MAKING,
                message_type=MessageType.DECISION_START,
                data=data,
                context=context
            )

            # Publish response to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Failed to start decision process: {e}")
            self._handle_decision_error(
                ProcessingMessage(
                    source_identifier=self.module_id,
                    target_identifier=ModuleIdentifier(
                        component_name="decision_manager",
                        component_type=ComponentType.MANAGER
                    ),
                    message_type=MessageType.DECISION_ERROR,
                    content={
                        'error': str(e),
                        'pipeline_id': message.content.get('pipeline_id')
                    }
                )
            )

    async def _run_decision_process(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Core decision process execution logic"""
        try:
            # Run recommendation phase
            recommendations = await self.decision_processor.generate_recommendations(
                context.get('decision_id'),
                data,
                context
            )

            # Run user decision phase 
            decision_options = await self.decision_processor.prepare_decision_options(
                context.get('decision_id'),
                recommendations
            )

            # Run decision processing phase
            decision_results = await self.decision_processor.process_decision(
                context.get('decision_id'),
                decision_options
            )

            return {
                'recommendations': recommendations,
                'decision_options': decision_options,
                'decision_results': decision_results,
                'pipeline_id': context.get('pipeline_id')
            }

        except Exception as e:
            logger.error(f"Decision process failed: {e}")
            raise

    def _handle_decision_complete(self, message: ProcessingMessage) -> None:
        """Handle decision process completion"""
        try:
            # Create completion response for manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="decision_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_decision_complete"
                ),
                message_type=MessageType.DECISION_COMPLETE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'results': message.content.get('results', {}),
                    'status': 'completed'
                }
            )

            # Publish completion to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling decision completion: {e}")

    def _handle_decision_update(self, message: ProcessingMessage) -> None:
        """Handle decision process updates"""
        try:
            # Forward update to decision manager
            response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="decision_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_decision_update"
                ),
                message_type=MessageType.DECISION_STATUS_UPDATE,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'status': message.content.get('status'),
                    'progress': message.content.get('progress')
                }
            )

            # Publish update to manager
            self.message_broker.publish(response)

        except Exception as e:
            logger.error(f"Error handling decision update: {e}")

    def _handle_decision_error(self, message: ProcessingMessage) -> None:
        """Handle decision process errors"""
        try:
            # Forward error to decision manager
            error_response = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier(
                    component_name="decision_manager",
                    component_type=ComponentType.MANAGER,
                    method_name="handle_decision_error"
                ),
                message_type=MessageType.DECISION_ERROR,
                content={
                    'pipeline_id': message.content.get('pipeline_id'),
                    'error': message.content.get('error')
                }
            )

            # Publish error to manager
            self.message_broker.publish(error_response)

        except Exception as e:
            logger.error(f"Error handling decision error: {e}")

    def get_process_status(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get current process status"""
        return self.process_handler.get_process_status(decision_id)