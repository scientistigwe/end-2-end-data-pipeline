# backend/core/channel_handlers/base_handler.py

import logging
import threading
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ModuleIdentifier,
    ProcessingMessage,
    ProcessingStatus
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


class BaseHandler:
    """
    Base handler providing common functionality for all channel handlers
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
        self._callbacks: Dict[str, Callable] = {}
        self._active_contexts: Dict[str, MessageContext] = {}
        self._lock = threading.Lock()

        # Initialize handler
        self._initialize_handler()

    def _initialize_handler(self) -> None:
        """Initialize handler components"""
        try:
            self._register_with_broker()
            self._setup_error_handling()
            self.logger.info(f"{self.handler_name} handler initialized")
        except Exception as e:
            self.status = HandlerStatus.ERROR
            self.logger.error(f"Handler initialization failed: {str(e)}")
            raise

    def _register_with_broker(self) -> None:
        """Register handler with message broker"""
        try:
            self.message_broker.register_handler(
                self.handler_name,
                self.handle_message
            )
        except Exception as e:
            self.logger.error(f"Failed to register with broker: {str(e)}")
            raise

    def register_callback(self, event_type: str, callback: Callable) -> None:
        """Register callback for specific event type"""
        with self._lock:
            self._callbacks[event_type] = callback
            self.logger.debug(f"Registered callback for {event_type}")

    def handle_message(self, message: ProcessingMessage) -> None:
        """Main message handling entry point"""
        try:
            context = self._create_message_context(message)
            self._active_contexts[context.message_id] = context

            # Process message
            self._process_message(message, context)

            # Update metrics
            self._update_metrics(True)

        except Exception as e:
            self._handle_error(message, e)
            self._update_metrics(False)

    def _process_message(self, message: ProcessingMessage,
                         context: MessageContext) -> None:
        """Process incoming message"""
        self.status = HandlerStatus.BUSY

        try:
            # Get appropriate callback
            callback = self._callbacks.get(message.message_type)
            if not callback:
                raise ValueError(f"No callback registered for {message.message_type}")

            # Execute callback
            callback(message)

            # Cleanup context
            self._cleanup_context(context.message_id)

        finally:
            self.status = HandlerStatus.READY

    def send_response(self, target_id: str, message_type: MessageType,
                      content: Dict[str, Any]) -> None:
        """Send response message"""
        try:
            message = ProcessingMessage(
                message_id=str(uuid.uuid4()),
                source_identifier=ModuleIdentifier(self.handler_name),
                target_identifier=target_id,
                message_type=message_type,
                content=content
            )

            self.message_broker.publish(message)

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

    def _handle_error(self, message: ProcessingMessage, error: Exception) -> None:
        """Handle processing errors"""
        context = self._active_contexts.get(message.message_id)
        if not context:
            self.logger.error("No context found for error handling")
            return

        self.logger.error(f"Error processing message: {str(error)}")

        if context.retries < context.max_retries:
            # Retry processing
            context.retries += 1
            self._process_message(message, context)
        else:
            # Send error notification
            self.send_response(
                context.source_id,
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

    def _update_metrics(self, success: bool) -> None:
        """Update handler metrics"""
        with self._lock:
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

    def __del__(self):
        """Cleanup handler resources"""
        self.status = HandlerStatus.DISCONNECTED
        self._active_contexts.clear()
