# core/sub_managers/decision_manager.py

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
    DecisionContext,
    MessageMetadata
)
from ..managers.base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class DecisionManager(BaseManager):
    """
    Decision Manager that coordinates decision making through message broker.
    Maintains local state but communicates all actions through messages.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(
            message_broker=message_broker,
            component_name="decision_manager",
            domain_type="decision"
        )

        # Local state tracking
        self.active_processes: Dict[str, DecisionContext] = {}

        # Register message handlers
        self._setup_message_handlers()

    def _setup_message_handlers(self) -> None:
        """Register handlers for all decision-related messages"""
        handlers = {
            MessageType.DECISION_REQUEST: self._handle_decision_request,
            MessageType.DECISION_SUBMIT: self._handle_decision_submit,
            MessageType.DECISION_VALIDATE_RESULT: self._handle_validation_result,
            MessageType.DECISION_IMPACT: self._handle_impact_analysis,
            MessageType.DECISION_COMPLETE: self._handle_decision_complete,
            MessageType.DECISION_TIMEOUT: self._handle_decision_timeout,
            MessageType.DECISION_ERROR: self._handle_decision_error,
            MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
            MessageType.STAGING_CREATED: self._handle_staging_created,
            MessageType.DECISION_FEEDBACK: self._handle_decision_feedback
        }

        for message_type, handler in handlers.items():
            self.register_message_handler(message_type, handler)

    async def request_decision(
            self,
            pipeline_id: str,
            options: Dict[str, Any]
    ) -> str:
        """
        Initiate decision request through message broker
        Returns correlation ID for tracking
        """
        correlation_id = str(uuid.uuid4())

        # Request control point creation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.CONTROL_POINT_CREATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.DECISION_MAKING,
                'options': options
            },
            metadata=MessageMetadata(
                correlation_id=correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Initialize tracking context
        self.active_processes[pipeline_id] = DecisionContext(
            pipeline_id=pipeline_id,
            stage=ProcessingStage.DECISION_MAKING,
            status=ProcessingStatus.PENDING,
            options=options,
            correlation_id=correlation_id
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
                'source_type': 'decision'
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

        # Start decision processing
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.DECISION_START,
            content={
                'pipeline_id': pipeline_id,
                'staged_id': staged_id,
                'options': context.options
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="decision_handler"
            )
        ))

    async def _handle_decision_request(self, message: ProcessingMessage) -> None:
        """Handle incoming decision request"""
        pipeline_id = message.content['pipeline_id']
        context = self.active_processes.get(pipeline_id)

        if context:
            context.status = ProcessingStatus.AWAITING_DECISION
            context.requires_confirmation = message.content.get('requires_confirmation', True)

            # Notify about decision needed
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.DECISION_NEEDED,
                content={
                    'pipeline_id': pipeline_id,
                    'options': context.options,
                    'requires_confirmation': context.requires_confirmation
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.component_name,
                    target_component="control_point_manager"
                )
            ))

    async def _handle_decision_submit(self, message: ProcessingMessage) -> None:
        """Handle submitted decision"""
        pipeline_id = message.content['pipeline_id']
        decision = message.content['decision']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.status = ProcessingStatus.IN_PROGRESS

        # Request validation
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.DECISION_VALIDATE_REQUEST,
            content={
                'pipeline_id': pipeline_id,
                'decision': decision,
                'constraints': context.constraints
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="decision_handler"
            )
        ))

    async def _handle_validation_result(self, message: ProcessingMessage) -> None:
        """Handle decision validation results"""
        pipeline_id = message.content['pipeline_id']
        is_valid = message.content['is_valid']
        issues = message.content.get('issues', [])

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        if is_valid:
            # Request impact analysis
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.DECISION_IMPACT_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'decision': context.options
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.component_name,
                    target_component="decision_handler"
                )
            ))
        else:
            # Notify about validation failure
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.DECISION_VALIDATION_FAILED,
                content={
                    'pipeline_id': pipeline_id,
                    'issues': issues
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.component_name,
                    target_component="control_point_manager"
                )
            ))

    async def _handle_impact_analysis(self, message: ProcessingMessage) -> None:
        """Handle impact analysis results"""
        pipeline_id = message.content['pipeline_id']
        impacts = message.content['impacts']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.impacts = impacts

        # Proceed with decision processing
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.DECISION_PROCESS,
            content={
                'pipeline_id': pipeline_id,
                'decision': context.options,
                'impacts': impacts
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="decision_handler"
            )
        ))

    async def _handle_decision_complete(self, message: ProcessingMessage) -> None:
        """Handle decision process completion"""
        pipeline_id = message.content['pipeline_id']
        result = message.content['result']

        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        context.status = ProcessingStatus.COMPLETED

        # Notify completion
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.STAGE_COMPLETE,
            content={
                'pipeline_id': pipeline_id,
                'stage': ProcessingStage.DECISION_MAKING,
                'result': result
            },
            metadata=MessageMetadata(
                correlation_id=context.correlation_id,
                source_component=self.component_name,
                target_component="control_point_manager"
            )
        ))

        # Cleanup
        del self.active_processes[pipeline_id]

    async def _handle_decision_timeout(self, message: ProcessingMessage) -> None:
        """Handle decision timeout"""
        pipeline_id = message.content['pipeline_id']

        context = self.active_processes.get(pipeline_id)
        if context:
            context.status = ProcessingStatus.DECISION_TIMEOUT

            # Notify timeout
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.STAGE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': ProcessingStage.DECISION_MAKING,
                    'error': 'Decision timeout'
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.component_name,
                    target_component="control_point_manager"
                )
            ))

            del self.active_processes[pipeline_id]

    async def _handle_decision_error(self, message: ProcessingMessage) -> None:
        """Handle decision processing errors"""
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
                    'stage': ProcessingStage.DECISION_MAKING,
                    'error': error
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.component_name,
                    target_component="control_point_manager"
                )
            ))

            del self.active_processes[pipeline_id]

    async def _handle_decision_feedback(self, message: ProcessingMessage) -> None:
        """Handle decision feedback"""
        pipeline_id = message.content['pipeline_id']
        feedback = message.content['feedback']

        context = self.active_processes.get(pipeline_id)
        if context:
            # Record feedback
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.DECISION_FEEDBACK_RECORDED,
                content={
                    'pipeline_id': pipeline_id,
                    'feedback': feedback
                },
                metadata=MessageMetadata(
                    correlation_id=context.correlation_id,
                    source_component=self.component_name,
                    target_component="decision_handler"
                )
            ))

    async def cleanup(self) -> None:
        """Clean up manager resources"""
        try:
            # Notify cleanup for all active processes
            for pipeline_id in list(self.active_processes.keys()):
                await self.message_broker.publish(ProcessingMessage(
                    message_type=MessageType.DECISION_CLEANUP,
                    content={
                        'pipeline_id': pipeline_id,
                        'reason': 'Manager cleanup initiated'
                    }
                ))
                del self.active_processes[pipeline_id]

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")
            raise