# backend/core/handlers/base_channel_handler.py

import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Coroutine
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    MessageMetadata,
    ProcessingContext
)
from ...registry.component_registry import ComponentRegistry, ComponentType


class HandlerState(Enum):
    """Handler operational states"""
    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class HandlerMetrics:
    """Handler performance tracking"""
    messages_processed: int = 0
    errors_encountered: int = 0
    processing_times: List[float] = field(default_factory=list)
    last_active: datetime = field(default_factory=datetime.now)
    retries_count: int = 0
    current_load: int = 0


@dataclass
class ProcessingTask:
    """Represents an active processing task"""
    task_id: str
    message: ProcessingMessage
    start_time: datetime = field(default_factory=datetime.now)
    retries: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30
    processor_context: Dict[str, Any] = field(default_factory=dict)


class BaseChannelHandler:
    """Base implementation for all channel handlers"""

    def __init__(
        self,
        message_broker: MessageBroker,
        handler_name: str,
        domain_type: str
    ):
        # Core components
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.logger = logging.getLogger(f"{handler_name}_handler")

        # Identity and state
        self.handler_name = handler_name
        self.domain_type = domain_type
        self.state = HandlerState.INITIALIZING
        self.metrics = HandlerMetrics()

        # Processing management
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._active_tasks: Dict[str, ProcessingTask] = {}
        self._async_lock = asyncio.Lock()

        # Error handling
        self._error_handlers: Dict[str, Callable] = {}
        self._recovery_attempts = 0
        self._max_recovery_attempts = 3

        # Initialize
        self._initialize()

    def _initialize(self) -> None:
        """Initialize handler and register with system"""
        try:
            # Register with component registry
            self.registry.register_component(
                self.handler_name,
                ComponentType.HANDLER,
                {"domain": self.domain_type}
            )

            # Set state to ready
            self.state = HandlerState.READY
            self.logger.info(f"{self.handler_name} handler initialized successfully")

        except Exception as e:
            self.state = HandlerState.ERROR
            self.logger.error(f"Handler initialization failed: {str(e)}")
            raise

    async def register_message_handler(
        self,
        message_type: MessageType,
        handler: Callable[[ProcessingMessage], Coroutine]
    ) -> None:
        """Register handler for specific message type"""
        async with self._async_lock:
            self._message_handlers[message_type] = handler
            await self.message_broker.subscribe(
                self.handler_name,
                f"{self.domain_type}.{message_type.value}",
                self._handle_message
            )

    async def _handle_message(self, message: ProcessingMessage) -> None:
        """Primary message handling entry point"""
        task = None
        try:
            self.state = HandlerState.PROCESSING
            start_time = datetime.now()

            # Create processing task
            task = ProcessingTask(
                task_id=message.id,
                message=message
            )
            self._active_tasks[task.task_id] = task

            # Get appropriate handler
            handler = self._message_handlers.get(message.message_type)
            if not handler:
                raise ValueError(f"No handler for message type: {message.message_type}")

            # Process message
            result = await handler(message)

            # Send response if required
            if message.metadata.requires_response:
                await self._send_response(message, result)

            # Update metrics
            self._update_metrics(
                processing_time=(datetime.now() - start_time).total_seconds(),
                success=True
            )

        except Exception as e:
            self.logger.error(f"Message handling failed: {str(e)}")
            await self._handle_error(message, e, task)
            self._update_metrics(success=False)

        finally:
            if task and task.task_id in self._active_tasks:
                del self._active_tasks[task.task_id]
            self.state = HandlerState.READY

    async def _handle_error(
        self,
        message: ProcessingMessage,
        error: Exception,
        task: Optional[ProcessingTask] = None
    ) -> None:
        """Handle processing errors with retry logic"""
        try:
            if task and task.retries < task.max_retries:
                # Retry processing
                task.retries += 1
                self.metrics.retries_count += 1
                await self._handle_message(message)
                return

            # Create error message
            error_message = message.create_response(
                MessageType.FLOW_ERROR,
                {
                    'error': str(error),
                    'component': self.handler_name,
                    'retries': task.retries if task else 0
                }
            )

            # Publish error
            await self.message_broker.publish(error_message)

        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")

    async def _send_response(
        self,
        original_message: ProcessingMessage,
        result: Any
    ) -> None:
        """Send processing response"""
        try:
            response = original_message.create_response(
                MessageType.FLOW_COMPLETE,
                {
                    'result': result,
                    'handler': self.handler_name,
                    'processing_time': self.metrics.processing_times[-1]
                }
            )
            await self.message_broker.publish(response)

        except Exception as e:
            self.logger.error(f"Failed to send response: {str(e)}")
            await self._handle_error(original_message, e)

    def _update_metrics(
        self,
        processing_time: float = 0.0,
        success: bool = True
    ) -> None:
        """Update handler metrics"""
        self.metrics.messages_processed += 1
        if not success:
            self.metrics.errors_encountered += 1

        self.metrics.processing_times.append(processing_time)
        if len(self.metrics.processing_times) > 100:
            self.metrics.processing_times.pop(0)

        self.metrics.last_active = datetime.now()
        self.metrics.current_load = len(self._active_tasks)

    def get_status(self) -> Dict[str, Any]:
        """Get handler status information"""
        return {
            'handler_name': self.handler_name,
            'domain_type': self.domain_type,
            'state': self.state.value,
            'metrics': {
                'messages_processed': self.metrics.messages_processed,
                'errors_encountered': self.metrics.errors_encountered,
                'average_processing_time': sum(self.metrics.processing_times) / len(self.metrics.processing_times) if self.metrics.processing_times else 0,
                'last_active': self.metrics.last_active.isoformat(),
                'retries_count': self.metrics.retries_count,
                'current_load': self.metrics.current_load
            },
            'active_tasks': len(self._active_tasks)
        }

    async def cleanup(self) -> None:
        """Cleanup handler resources"""
        try:
            self.state = HandlerState.DISCONNECTED
            self._active_tasks.clear()
            self._message_handlers.clear()
            self.logger.info(f"{self.handler_name} handler cleaned up successfully")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise

    def __del__(self):
        """Cleanup on deletion"""
        if self.state != HandlerState.DISCONNECTED:
            asyncio.create_task(self.cleanup())