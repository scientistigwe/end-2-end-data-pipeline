# core/managers/decision_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    DecisionContext,
    MessageMetadata
)
from ..control.cpm import ControlPointManager
from .base.base_manager import BaseManager
from ..staging.staging_manager import StagingManager
from ..handlers.channel.decision_handler import DecisionHandler
from data.processing.decisions.types.decision_types import (
    DecisionSource,
    DecisionState,
    DecisionPhase,
    DecisionStatus,
    ComponentDecision
)

logger = logging.getLogger(__name__)


class DecisionManager(BaseManager):
    """
    Manager for decision orchestration.
    Coordinates between CPM, Handler, and other components.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            control_point_manager: ControlPointManager,
            staging_manager: StagingManager
    ):
        super().__init__(
            message_broker=message_broker,
            control_point_manager=control_point_manager,
            component_name="decision_manager",
            domain_type="decision"
        )

        self.staging_manager = staging_manager
        self.decision_handler = DecisionHandler(
            message_broker=message_broker,
            staging_manager=staging_manager
        )

        # Active decisions tracking
        self.active_decisions: Dict[str, DecisionState] = {}

        # Setup message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Setup handlers for decision-related messages"""
        self.register_message_handler(
            MessageType.DECISION_REQUEST,
            self._handle_decision_request
        )
        self.register_message_handler(
            MessageType.DECISION_SUBMIT,
            self._handle_decision_submit
        )
        self.register_message_handler(
            MessageType.DECISION_UPDATE,
            self._handle_decision_update
        )
        self.register_message_handler(
            MessageType.DECISION_COMPLETE,
            self._handle_decision_complete
        )

    async def _handle_decision_request(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle when a decision is required"""
        try:
            pipeline_id = message.content['pipeline_id']
            source = message.metadata.source_component

            # Create decision context
            context = DecisionContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.DECISION_MAKING,
                status=ProcessingStatus.AWAITING_DECISION,
                source_component=source,
                decision_type=message.content.get('decision_type'),
                options=message.content.get('options', []),
                impacts=message.content.get('impacts', {}),
                constraints=message.content.get('constraints', {})
            )

            # Create control point
            control_point = await self.control_point_manager.create_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.DECISION_MAKING,
                metadata={
                    'source': source,
                    'context': self._format_context(context)
                }
            )

            # Initialize decision state
            self.active_decisions[pipeline_id] = DecisionState(
                pipeline_id=pipeline_id,
                current_requests=[],
                pending_decisions=[],
                completed_decisions=[],
                status=DecisionStatus.AWAITING_INPUT,
                phase=DecisionPhase.ANALYSIS
            )

            # Forward to handler
            await self.decision_handler._handle_decision_request(message)

        except Exception as e:
            logger.error(f"Failed to handle decision request: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_decision_submit(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle when a decision is submitted"""
        try:
            pipeline_id = message.content['pipeline_id']
            decision_data = message.content['decision']

            state = self.active_decisions.get(pipeline_id)
            if not state:
                raise ValueError(f"No active decision state for pipeline: {pipeline_id}")

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.DECISION_MAKING,
                status=ProcessingStatus.IN_PROGRESS,
                metadata={
                    'decision': decision_data,
                    'submitted_at': datetime.now().isoformat()
                }
            )

            # Forward to handler
            await self.decision_handler._handle_decision_submit(message)

        except Exception as e:
            logger.error(f"Failed to handle decision submit: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_decision_update(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle updates about decision processing"""
        try:
            pipeline_id = message.content['pipeline_id']
            update_data = message.content['update']

            state = self.active_decisions.get(pipeline_id)
            if state:
                # Update state based on update type
                if update_data.get('type') == 'validation':
                    state.status = DecisionStatus.VALIDATING
                elif update_data.get('type') == 'impact':
                    state.status = DecisionStatus.ANALYZING

                state.metadata.update(update_data)
                state.updated_at = datetime.now()

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.DECISION_MAKING,
                metadata={
                    'update': update_data,
                    'updated_at': datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Failed to handle decision update: {str(e)}")
            await self._handle_error(message, e)

    async def _handle_decision_complete(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle decision completion"""
        try:
            pipeline_id = message.content['pipeline_id']
            result = message.content['result']

            state = self.active_decisions.get(pipeline_id)
            if state:
                # Update state
                state.status = DecisionStatus.COMPLETED
                state.completed_decisions.append(
                    ComponentDecision(**result['decision'])
                )

                # Cleanup
                del self.active_decisions[pipeline_id]

            # Update control point
            await self.control_point_manager.update_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.DECISION_MAKING,
                status=ProcessingStatus.COMPLETED,
                metadata={
                    'result': result,
                    'completed_at': datetime.now().isoformat()
                }
            )

            # Notify completion
            await self._notify_completion(pipeline_id, result)

        except Exception as e:
            logger.error(f"Failed to handle decision complete: {str(e)}")
            await self._handle_error(message, e)

    async def _notify_completion(
            self,
            pipeline_id: str,
            result: Dict[str, Any]
    ) -> None:
        """Notify about decision completion"""
        message = ProcessingMessage(
            message_type=MessageType.DECISION_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'result': result,
                'timestamp': datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                source_component="decision_manager",
                target_component="pipeline_manager"
            )
        )
        await self.message_broker.publish(message)

    def _format_context(self, context: DecisionContext) -> Dict[str, Any]:
        """Format context for storage"""
        return {
            'stage': context.stage.value,
            'status': context.status.value,
            'source_component': context.source_component,
            'decision_type': context.decision_type,
            'options': context.options,
            'impacts': context.impacts,
            'constraints': context.constraints
        }

    async def get_decision_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current status of decision process"""
        try:
            state = self.active_decisions.get(pipeline_id)
            if not state:
                return None

            control_point = await self.control_point_manager.get_control_point(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.DECISION_MAKING
            )

            return {
                'pipeline_id': pipeline_id,
                'status': state.status.value,
                'phase': state.phase.value,
                'pending_decisions': len(state.pending_decisions),
                'completed_decisions': len(state.completed_decisions),
                'control_point': control_point,
                'updated_at': state.updated_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get decision status: {str(e)}")
            return None

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            # Cleanup active decisions
            self.active_decisions.clear()

            # Cleanup handler
            await self.decision_handler.cleanup()

            # Call parent cleanup
            await super().cleanup()

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise