# core/handlers/channel/decision_handler.py

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
    DecisionContext,
    DecisionState
)
from ..base.base_handler import BaseChannelHandler

logger = logging.getLogger(__name__)


class DecisionHandler(BaseChannelHandler):
    """
    Handler for decision-related operations.
    Communicates exclusively through message broker.
    """

    # Constants
    DECISION_TIMEOUT = timedelta(minutes=30)
    MAX_RETRY_ATTEMPTS = 3
    CHECK_INTERVAL = 60  # seconds

    def __init__(self, message_broker: MessageBroker):
        module_identifier = ModuleIdentifier(
            component_name="decision_handler",
            component_type=ComponentType.DECISION_HANDLER,
            department="decision",
            role="handler"
        )

        super().__init__(
            message_broker=message_broker,
            module_identifier=module_identifier
        )

        # State tracking
        self._active_decisions: Dict[str, DecisionContext] = {}
        self._decision_timeouts: Dict[str, datetime] = {}
        self._retry_attempts: Dict[str, int] = {}

        # Start monitoring task
        asyncio.create_task(self._monitor_decisions())

    def _setup_message_handlers(self) -> None:
        """Setup handlers for decision-specific messages"""
        handlers = {
            # Decision flow
            MessageType.DECISION_GENERATE_REQUEST: self._handle_decision_request,
            MessageType.DECISION_SUBMIT: self._handle_decision_submit,
            MessageType.DECISION_VALIDATE_REQUEST: self._handle_validation_request,
            MessageType.DECISION_VALIDATE_COMPLETE: self._handle_validation_complete,

            # Impact assessment
            MessageType.DECISION_IMPACT_ASSESS_REQUEST: self._handle_impact_request,
            MessageType.DECISION_IMPACT_ASSESS_COMPLETE: self._handle_impact_complete,

            # Control messages
            MessageType.DECISION_TIMEOUT: self._handle_decision_timeout,
            MessageType.DECISION_CANCEL_REQUEST: self._handle_cancel_request,

            # Status and monitoring
            MessageType.DECISION_STATUS_REQUEST: self._handle_status_request,
            MessageType.DECISION_STATUS_UPDATE: self._handle_status_update,

            # Error handling
            MessageType.DECISION_ERROR: self._handle_error,
            MessageType.DECISION_RECOVERY_REQUEST: self._handle_recovery_request
        }

        for message_type, handler in handlers.items():
            self.register_message_handler(message_type, handler)

    async def _handle_decision_request(self, message: ProcessingMessage) -> None:
        """Handle new decision request"""
        try:
            pipeline_id = message.content['pipeline_id']
            decision_id = str(uuid4())

            # Create decision context
            context = DecisionContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.DECISION_MAKING,
                status=ProcessingStatus.IN_PROGRESS,
                correlation_id=message.metadata.correlation_id,
                source_component=message.metadata.source_component,
                decision_type=message.content.get('decision_type', 'standard_decision'),
                options=message.content.get('options', []),
                impacts=message.content.get('impacts', {}),
                constraints=message.content.get('constraints', {}),
                required_validations=message.content.get('required_validations', []),
                requires_confirmation=message.content.get('requires_confirmation', True)
            )

            # Initialize tracking
            self._active_decisions[decision_id] = context
            self._decision_timeouts[decision_id] = datetime.now()

            # Request options generation
            await self._publish_message(
                MessageType.DECISION_OPTIONS_GENERATE_REQUEST,
                {
                    'pipeline_id': pipeline_id,
                    'decision_id': decision_id,
                    'context': context.to_dict()
                },
                target_type=ComponentType.DECISION_PROCESSOR
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_decision_submit(self, message: ProcessingMessage) -> None:
        """Handle decision submission"""
        decision_id = message.content['decision_id']
        context = self._active_decisions.get(decision_id)

        if not context:
            await self._handle_error(message, "Decision context not found")
            return

        try:
            # Update context
            context.status = ProcessingStatus.IN_PROGRESS
            selected_option = message.content['selected_option']
            context.metadata['selected_option'] = selected_option

            # Request impact assessment
            await self._publish_message(
                MessageType.DECISION_IMPACT_ASSESS_REQUEST,
                {
                    'decision_id': decision_id,
                    'pipeline_id': context.pipeline_id,
                    'selected_option': selected_option,
                    'constraints': context.constraints
                },
                target_type=ComponentType.DECISION_PROCESSOR
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_impact_complete(self, message: ProcessingMessage) -> None:
        """Handle impact assessment completion"""
        decision_id = message.content['decision_id']
        context = self._active_decisions.get(decision_id)

        if not context:
            return

        try:
            impacts = message.content['impacts']
            context.impacts.update(impacts)

            if context.requires_confirmation:
                # Request user confirmation
                await self._publish_message(
                    MessageType.DECISION_FEEDBACK_REQUEST,
                    {
                        'decision_id': decision_id,
                        'pipeline_id': context.pipeline_id,
                        'impacts': impacts,
                        'selected_option': context.metadata['selected_option']
                    },
                    target_type=ComponentType.DECISION_MANAGER
                )
            else:
                # Proceed with validation
                await self._request_validation(decision_id)

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _request_validation(self, decision_id: str) -> None:
        """Request validation of decision"""
        context = self._active_decisions.get(decision_id)
        if not context:
            return

        await self._publish_message(
            MessageType.DECISION_VALIDATE_REQUEST,
            {
                'decision_id': decision_id,
                'pipeline_id': context.pipeline_id,
                'selected_option': context.metadata['selected_option'],
                'impacts': context.impacts,
                'required_validations': context.required_validations
            },
            target_type=ComponentType.DECISION_PROCESSOR
        )

    async def _handle_validation_complete(self, message: ProcessingMessage) -> None:
        """Handle validation completion"""
        decision_id = message.content['decision_id']
        context = self._active_decisions.get(decision_id)

        if not context:
            return

        try:
            validation_results = message.content['validation_results']
            is_valid = all(result['valid'] for result in validation_results)

            if is_valid:
                await self._complete_decision(decision_id)
            else:
                await self._handle_validation_failure(decision_id, validation_results)

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _complete_decision(self, decision_id: str) -> None:
        """Handle successful decision completion"""
        context = self._active_decisions.get(decision_id)
        if not context:
            return

        try:
            # Update context
            context.status = ProcessingStatus.COMPLETED
            context.metadata['completion_time'] = datetime.now().isoformat()

            # Notify completion
            await self._publish_message(
                MessageType.DECISION_COMPLETE,
                {
                    'decision_id': decision_id,
                    'pipeline_id': context.pipeline_id,
                    'selected_option': context.metadata['selected_option'],
                    'impacts': context.impacts,
                    'metadata': context.metadata
                },
                target_type=ComponentType.DECISION_MANAGER
            )

            # Cleanup
            await self._cleanup_decision(decision_id)

        except Exception as e:
            await self._handle_error(
                ProcessingMessage(
                    message_type=MessageType.DECISION_ERROR,
                    content={'decision_id': decision_id}
                ),
                str(e)
            )

    async def _monitor_decisions(self) -> None:
        """Monitor active decisions for timeouts"""
        while True:
            try:
                current_time = datetime.now()
                for decision_id, start_time in self._decision_timeouts.items():
                    if (current_time - start_time) > self.DECISION_TIMEOUT:
                        await self._handle_decision_timeout(ProcessingMessage(
                            message_type=MessageType.DECISION_TIMEOUT,
                            content={'decision_id': decision_id}
                        ))
                await asyncio.sleep(self.CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Decision monitoring error: {str(e)}")

    async def _handle_decision_timeout(self, message: ProcessingMessage) -> None:
        """Handle decision timeout"""
        decision_id = message.content['decision_id']
        context = self._active_decisions.get(decision_id)

        if not context:
            return

        try:
            # Check retry attempts
            if self._retry_attempts.get(decision_id, 0) < self.MAX_RETRY_ATTEMPTS:
                await self._attempt_recovery(decision_id, "timeout")
            else:
                await self._fail_decision(
                    decision_id,
                    "Maximum retry attempts exceeded"
                )
        except Exception as e:
            logger.error(f"Timeout handling error: {str(e)}")

    async def _cleanup_decision(self, decision_id: str) -> None:
        """Clean up decision resources"""
        if decision_id in self._active_decisions:
            del self._active_decisions[decision_id]
        if decision_id in self._decision_timeouts:
            del self._decision_timeouts[decision_id]
        if decision_id in self._retry_attempts:
            del self._retry_attempts[decision_id]

    async def cleanup(self) -> None:
        """Clean up handler resources"""
        try:
            # Clean up all active decisions
            for decision_id in list(self._active_decisions.keys()):
                await self._fail_decision(
                    decision_id,
                    "Handler shutdown initiated"
                )
            await super().cleanup()
        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise

    async def _publish_message(
            self,
            message_type: MessageType,
            content: Dict[str, Any],
            target_type: ComponentType
    ) -> None:
        """Helper method to publish messages"""
        target_identifier = ModuleIdentifier(
            component_name=target_type.value,
            component_type=target_type,
            department=target_type.department,
            role=target_type.role
        )

        message = ProcessingMessage(
            message_type=message_type,
            content=content,
            source_identifier=self.module_identifier,
            target_identifier=target_identifier,
            metadata=MessageMetadata(
                source_component=self.module_identifier.component_name,
                target_component=target_type.value,
                domain_type="decision"
            )
        )

        await self.message_broker.publish(message)