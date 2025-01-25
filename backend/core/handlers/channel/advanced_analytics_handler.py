# backend/core/handlers/channel/analytics_handler.py

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
    AnalyticsContext
)
from ..base.base_handler import BaseChannelHandler


class AdvancedAnalyticsHandler(BaseChannelHandler):
    def __init__(self, message_broker: MessageBroker):
        module_identifier = ModuleIdentifier(
            component_name="advanced_analytics_handler",
            component_type=ComponentType.ANALYTICS_HANDLER,
            department="analytics",
            role="handler"
        )
        super().__init__(message_broker=message_broker, module_identifier=module_identifier)

        # State tracking
        self._active_contexts: Dict[str, AnalyticsContext] = {}
        self._task_timeouts: Dict[str, datetime] = {}
        self._recovery_attempts: Dict[str, int] = {}

        # Start monitoring tasks
        asyncio.create_task(self._monitor_tasks())

    def _setup_message_handlers(self) -> None:
        handlers = {
            # Process flow messages
            MessageType.ANALYTICS_PROCESS_REQUEST: self._handle_process_request,
            MessageType.ANALYTICS_PROCESS_COMPLETE: self._handle_process_complete,

            # Stage control messages
            MessageType.ANALYTICS_STAGE_START: self._handle_stage_start,
            MessageType.ANALYTICS_STAGE_COMPLETE: self._handle_stage_complete,
            MessageType.ANALYTICS_STAGE_FAILED: self._handle_stage_failed,

            # Control messages
            MessageType.ANALYTICS_PAUSE_REQUEST: self._handle_pause_request,
            MessageType.ANALYTICS_RESUME_REQUEST: self._handle_resume_request,
            MessageType.ANALYTICS_CANCEL_REQUEST: self._handle_cancel_request,

            # Status messages
            MessageType.ANALYTICS_STATUS_REQUEST: self._handle_status_request,
            MessageType.ANALYTICS_STATUS_UPDATE: self._handle_status_update,

            # Error handling
            MessageType.ANALYTICS_ERROR: self._handle_error,
            MessageType.ANALYTICS_RECOVERY_REQUEST: self._handle_recovery_request
        }

        for message_type, handler in handlers.items():
            self.register_message_handler(message_type, handler)

    async def _handle_process_request(self, message: ProcessingMessage) -> None:
        """Handle new analytics process request"""
        try:
            pipeline_id = message.content['pipeline_id']
            context = AnalyticsContext(
                pipeline_id=pipeline_id,
                stage=ProcessingStage.ADVANCED_ANALYTICS,
                status=ProcessingStatus.IN_PROGRESS,
                metadata=message.content
            )

            # Initialize tracking
            self._active_contexts[pipeline_id] = context
            self._task_timeouts[pipeline_id] = datetime.now()

            # Request first stage
            await self._request_next_stage(pipeline_id)

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _monitor_tasks(self) -> None:
        """Monitor active tasks for timeouts"""
        while True:
            try:
                await self._check_timeouts()
                await asyncio.sleep(self.TIMEOUT_CHECK_INTERVAL)
            except Exception as e:
                self.logger.error(f"Task monitoring error: {str(e)}")

    async def _check_timeouts(self) -> None:
        """Check for timed out tasks"""
        current_time = datetime.now()
        for pipeline_id, start_time in self._task_timeouts.items():
            if (current_time - start_time) > self.TASK_TIMEOUT:
                await self._handle_timeout(pipeline_id)

    async def _handle_timeout(self, pipeline_id: str) -> None:
        """Handle task timeout"""
        context = self._active_contexts.get(pipeline_id)
        if context:
            # Attempt recovery if under max attempts
            if self._recovery_attempts.get(pipeline_id, 0) < self.MAX_RECOVERY_ATTEMPTS:
                await self._attempt_recovery(pipeline_id, "timeout")
            else:
                await self._fail_process(
                    pipeline_id,
                    "Maximum recovery attempts exceeded"
                )

    async def _attempt_recovery(self, pipeline_id: str, reason: str) -> None:
        """Attempt to recover failed process"""
        context = self._active_contexts.get(pipeline_id)
        if not context:
            return

        self._recovery_attempts[pipeline_id] = \
            self._recovery_attempts.get(pipeline_id, 0) + 1

        # Determine recovery strategy
        strategy = self._get_recovery_strategy(context.stage, reason)

        # Execute recovery
        await self._publish_message(
            MessageType.ANALYTICS_RECOVERY_REQUEST,
            {
                'pipeline_id': pipeline_id,
                'stage': context.stage.value,
                'strategy': strategy,
                'attempt': self._recovery_attempts[pipeline_id]
            },
            target_type=ComponentType.ANALYTICS_PROCESSOR
        )

    def _get_recovery_strategy(
            self,
            stage: ProcessingStage,
            reason: str
    ) -> Dict[str, Any]:
        """Determine recovery strategy based on stage and failure reason"""
        strategies = {
            (ProcessingStage.DATA_PREPARATION, "timeout"): {
                "action": "retry",
                "chunk_size": "reduced"
            },
            (ProcessingStage.MODEL_TRAINING, "timeout"): {
                "action": "simplify",
                "complexity": "reduced"
            },
            (ProcessingStage.MODEL_EVALUATION, "resource_error"): {
                "action": "redistribute",
                "batch_size": "reduced"
            }
        }
        return strategies.get(
            (stage, reason),
            {"action": "retry", "backoff": "exponential"}
        )

    async def _handle_stage_failed(self, message: ProcessingMessage) -> None:
        """Handle stage failure"""
        pipeline_id = message.content['pipeline_id']
        error = message.content.get('error', 'Unknown error')

        # Attempt recovery if under max attempts
        if self._recovery_attempts.get(pipeline_id, 0) < self.MAX_RECOVERY_ATTEMPTS:
            await self._attempt_recovery(pipeline_id, error)
        else:
            await self._fail_process(pipeline_id, error)

    async def _fail_process(self, pipeline_id: str, reason: str) -> None:
        """Handle final process failure"""
        context = self._active_contexts.get(pipeline_id)
        if context:
            context.status = ProcessingStatus.FAILED
            context.metadata['failure_reason'] = reason

            # Notify manager
            await self._publish_message(
                MessageType.ANALYTICS_ERROR,
                {
                    'pipeline_id': pipeline_id,
                    'error': reason,
                    'context': context.to_dict()
                },
                target_type=ComponentType.ANALYTICS_MANAGER
            )

            # Cleanup
            await self._cleanup_process(pipeline_id)

    async def _cleanup_process(self, pipeline_id: str) -> None:
        """Clean up process resources"""
        if pipeline_id in self._active_contexts:
            del self._active_contexts[pipeline_id]
        if pipeline_id in self._task_timeouts:
            del self._task_timeouts[pipeline_id]
        if pipeline_id in self._recovery_attempts:
            del self._recovery_attempts[pipeline_id]