# backend/core/sub_managers/base_manager.py

import logging
import asyncio
from typing import Dict, Any, Callable, Coroutine
from datetime import datetime

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    ManagerContext,
    ManagerState,
    ManagerMetrics
)

logger = logging.getLogger(__name__)


class BaseManager:
    """Base manager implementation using message broker architecture"""

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str,
            domain_type: str
    ):
        self.message_broker = message_broker
        self.logger = logging.getLogger(f"{component_name}_manager")

        # Initialize context
        self.context = ManagerContext(
            pipeline_id=str(uuid.uuid4()),  # Manager instance ID
            component_name=component_name,
            domain_type=domain_type,
            state=ManagerState.INITIALIZING,
            metrics=ManagerMetrics()
        )

        # Message handling
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._async_lock = asyncio.Lock()

        # Setup base handlers
        self._setup_base_handlers()

    async def _setup_base_handlers(self) -> None:
        """Setup base message handlers"""
        handlers = {
            MessageType.COMPONENT_INIT: self._handle_component_init,
            MessageType.COMPONENT_UPDATE: self._handle_component_update,
            MessageType.COMPONENT_ERROR: self._handle_component_error,
            MessageType.COMPONENT_SYNC: self._handle_component_sync
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

        # Notify system about initialization
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.COMPONENT_INIT,
            content={
                'component_name': self.context.component_name,
                'domain_type': self.context.domain_type
            },
            metadata=MessageMetadata(
                source_component=self.context.component_name,
                target_component="system"
            )
        ))

    async def register_message_handler(
            self,
            message_type: MessageType,
            handler: Callable[[ProcessingMessage], Coroutine]
    ) -> None:
        """Register handler for message type"""
        async with self._async_lock:
            self._message_handlers[message_type] = handler
            self.context.handlers[message_type.value] = handler.__name__

            await self.message_broker.subscribe(
                self.context.component_name,
                f"{self.context.domain_type}.{message_type.value}",
                self._handle_message
            )

    async def _handle_message(self, message: ProcessingMessage) -> None:
        """Central message handling"""
        try:
            self.context.state = ManagerState.PROCESSING
            start_time = datetime.now()

            handler = self._message_handlers.get(message.message_type)
            if not handler:
                raise ValueError(f"No handler for message type: {message.message_type}")

            await handler(message)
            self._update_metrics(
                processing_time=(datetime.now() - start_time).total_seconds(),
                success=True
            )

        except Exception as e:
            self.logger.error(f"Message handling failed: {str(e)}")
            await self._handle_error(message, e)
            self._update_metrics(success=False)

        finally:
            self.context.state = ManagerState.ACTIVE

    async def _handle_error(
            self,
            message: ProcessingMessage,
            error: Exception
    ) -> None:
        """Handle processing errors"""
        await self.message_broker.publish(ProcessingMessage(
            message_type=MessageType.COMPONENT_ERROR,
            content={
                'error': str(error),
                'component_name': self.context.component_name,
                'original_message': message.content
            },
            metadata=MessageMetadata(
                source_component=self.context.component_name,
                target_component="system"
            )
        ))

    def _update_metrics(self, processing_time: float = 0.0, success: bool = True) -> None:
        """Update performance metrics"""
        metrics = self.context.metrics
        metrics.messages_processed += 1
        if not success:
            metrics.errors_encountered += 1

        total_time = (metrics.average_processing_time *
                      (metrics.messages_processed - 1) + processing_time)
        metrics.average_processing_time = total_time / metrics.messages_processed
        metrics.last_activity = datetime.now()

    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            self.context.state = ManagerState.SHUTDOWN
            await self.message_broker.publish(ProcessingMessage(
                message_type=MessageType.COMPONENT_CLEANUP,
                content={
                    'component_name': self.context.component_name,
                    'reason': 'Manager shutdown'
                },
                metadata=MessageMetadata(
                    source_component=self.context.component_name,
                    target_component="system"
                )
            ))
            self._message_handlers.clear()
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise

    def __del__(self):
        """Cleanup on deletion"""
        if self.context.state != ManagerState.SHUTDOWN:
            asyncio.create_task(self.cleanup())