import logging
import uuid
import asyncio
import threading
from typing import Dict, Any, Optional, List, Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ModuleIdentifier,
    ProcessingMessage,
    ProcessingStatus,
    ComponentType
)

logger = logging.getLogger(__name__)


class HandlerStatus(Enum):
    """Handler operational status"""
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    DISCONNECTED = "disconnected"


@dataclass
class MessageContext:
    """Context for message processing"""
    message_id: str
    source_id: str
    target_id: str
    timestamp: datetime = field(default_factory=datetime.now)
    retries: int = 0
    max_retries: int = 3
    timeout: timedelta = field(default_factory=lambda: timedelta(seconds=30))


@dataclass
class HandlerMetrics:
    """Handler performance metrics"""
    messages_processed: int = 0
    errors_count: int = 0
    average_processing_time: float = 0.0
    last_active: datetime = field(default_factory=datetime.now)
    retry_count: int = 0


class BaseChannelHandler:
    """
    Base async handler providing common functionality for all channel handlers
    """

    def __init__(self, message_broker: MessageBroker, handler_name: str):
        """Initialize base handler"""
        self.message_broker = message_broker
        self.handler_name = handler_name
        self.logger = logging.getLogger(f"{handler_name}_handler")

        # Handler state
        self.status = HandlerStatus.READY
        self.metrics = HandlerMetrics()

        # Message handling
        self._callbacks: Dict[str, Callable[[ProcessingMessage], Coroutine]] = {}
        self._active_contexts: Dict[str, MessageContext] = {}
        self._async_lock = asyncio.Lock()

        # Error handling
        self._error_recovery_attempts = 0
        self._max_recovery_attempts = 3
        self._error_states: Dict[str, Any] = {}

    async def initialize(self) -> None:
        """Asynchronous initialization of handler"""
        try:
            # Register with message broker
            await self.message_broker.register_component(
                ModuleIdentifier(
                    component_name=self.handler_name,
                    component_type=ComponentType.HANDLER
                ),
                default_callback=self.handle_message
            )

            # Setup error handling
            await self._setup_error_handling()

            self.logger.info(f"{self.handler_name} handler initialized")
        except Exception as e:
            self.status = HandlerStatus.ERROR
            self.logger.error(f"Handler initialization failed: {str(e)}")
            raise

    async def register_callback(self, event_type: MessageType, callback: Callable[[ProcessingMessage], Coroutine]) -> None:
        """Register async callback for specific event type"""
        async with self._async_lock:
            self._callbacks[event_type.value] = callback
            self.logger.debug(f"Registered callback for {event_type}")

    async def handle_message(self, message: ProcessingMessage) -> None:
        """Asynchronous message handling entry point"""
        try:
            context = self._create_message_context(message)
            self._active_contexts[context.message_id] = context

            # Process message
            await self._process_message(message, context)

            # Update metrics
            self._update_metrics(True)

        except Exception as e:
            await self._handle_error(message, e)
            self._update_metrics(False)

    async def _process_message(self, message: ProcessingMessage, context: MessageContext) -> None:
        """Process incoming message asynchronously"""
        self.status = HandlerStatus.BUSY

        try:
            # Get appropriate callback
            callback = self._callbacks.get(message.message_type)
            if not callback:
                raise ValueError(f"No callback registered for {message.message_type}")

            # Execute callback
            await callback(message)

            # Cleanup context
            self._cleanup_context(context.message_id)

        finally:
            self.status = HandlerStatus.READY

    async def send_response(self, 
                             target_id: ModuleIdentifier, 
                             message_type: MessageType,
                             content: Dict[str, Any]) -> None:
        """Send response message asynchronously"""
        try:
            message = ProcessingMessage(
                message_id=str(uuid.uuid4()),
                source_identifier=ModuleIdentifier(self.handler_name),
                target_identifier=target_id,
                message_type=message_type,
                content=content
            )

            await self.message_broker.publish(message)

        except Exception as e:
            self.logger.error(f"Failed to send response: {str(e)}")
            raise

    def _create_message_context(self, message: ProcessingMessage) -> MessageContext:
        """Create context for message processing"""
        return MessageContext(
            message_id=message.message_id,
            source_id=str(message.source_identifier),
            target_id=str(message.target_identifier)
        )

    async def _handle_error(self, message: ProcessingMessage, error: Exception) -> None:
        """Handle processing errors asynchronously"""
        context = self._active_contexts.get(message.message_id)
        if not context:
            self.logger.error("No context found for error handling")
            return

        self.logger.error(f"Error processing message: {str(error)}")

        if context.retries < context.max_retries:
            # Retry processing
            context.retries += 1
            await self._process_message(message, context)
        else:
            # Send error notification
            await self.send_response(
                message.source_identifier,
                MessageType.ERROR,
                {
                    'error': str(error),
                    'context': {
                        'message_id': context.message_id,
                        'retries': context.retries
                    }
                }
            )
            self._cleanup_context(context.message_id)

    async def _setup_error_handling(self) -> None:
        """Setup async error handling and recovery mechanisms"""
        try:
            # Register error message handlers
            error_types = [
                MessageType.SOURCE_ERROR, 
                MessageType.PIPELINE_ERROR, 
                MessageType.QUALITY_ERROR, 
                MessageType.STAGE_ERROR, 
                MessageType.ROUTE_ERROR
            ]

            for error_type in error_types:
                await self.register_callback(error_type, self._handle_error_message)

            self.logger.info(f"Error handling setup complete for {self.handler_name}")
        except Exception as e:
            self.logger.error(f"Failed to setup error handling: {str(e)}")
            raise

    async def _handle_error_message(self, message: ProcessingMessage) -> None:
        """Handle incoming error messages asynchronously"""
        try:
            error_info = message.content.get('error', {})
            error_source = message.source_identifier.get_tag()

            self.logger.error(f"Error from {error_source}: {error_info}")

            # Track error state
            self._error_states[message.message_id] = {
                'source': error_source,
                'error': error_info,
                'timestamp': datetime.now().isoformat(),
                'recovery_attempted': False
            }

            # Attempt recovery if possible
            if self._error_recovery_attempts < self._max_recovery_attempts:
                await self._attempt_error_recovery(message)
            else:
                self.logger.error(f"Max recovery attempts reached for {message.message_id}")
                # Propagate error up
                await self.send_response(
                    target_id=message.source_identifier,
                    message_type=MessageType.SOURCE_ERROR,
                    content={
                        'error': 'Max recovery attempts reached',
                        'original_error': error_info,
                        'handler': self.handler_name
                    }
                )

        except Exception as e:
            self.logger.error(f"Error handling error message: {str(e)}")
            raise

    async def _attempt_error_recovery(self, message: ProcessingMessage) -> None:
        """Attempt to recover from error state asynchronously"""
        try:
            self._error_recovery_attempts += 1
            error_state = self._error_states.get(message.message_id)

            if error_state and not error_state['recovery_attempted']:
                error_state['recovery_attempted'] = True

                # Notify about recovery attempt
                await self.send_response(
                    target_id=message.source_identifier,
                    message_type=MessageType.SOURCE_VALIDATE,
                    content={
                        'action': 'recovery_attempt',
                        'attempt_number': self._error_recovery_attempts,
                        'handler': self.handler_name,
                        'original_message_id': message.message_id
                    }
                )

                self.logger.info(f"Recovery attempt {self._error_recovery_attempts} initiated for {message.message_id}")
        except Exception as e:
            self.logger.error(f"Error recovery attempt failed: {str(e)}")
            raise

    def _update_metrics(self, success: bool) -> None:
        """Update handler metrics"""
        with threading.Lock():
            self.metrics.messages_processed += 1
            if not success:
                self.metrics.errors_count += 1
            self.metrics.last_active = datetime.now()

    def _cleanup_context(self, message_id: str) -> None:
        """Clean up message context"""
        if message_id in self._active_contexts:
            del self._active_contexts[message_id]

    def get_status(self) -> Dict[str, Any]:
        """Get handler status information"""
        return {
            'handler_name': self.handler_name,
            'status': self.status.value,
            'metrics': {
                'messages_processed': self.metrics.messages_processed,
                'errors_count': self.metrics.errors_count,
                'average_processing_time': self.metrics.average_processing_time,
                'last_active': self.metrics.last_active.isoformat(),
                'retry_count': self.metrics.retry_count
            }
        }

    async def cleanup(self) -> None:
        """Asynchronous cleanup of handler resources"""
        self.status = HandlerStatus.DISCONNECTED
        self._active_contexts.clear()