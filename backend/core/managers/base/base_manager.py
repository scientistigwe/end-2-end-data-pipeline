# backend/core/managers/base_manager.py

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
from ...control.cpm import ControlPointManager
from ...registry.component_registry import ComponentRegistry, ComponentType


class ManagerState(Enum):
    """Manager operational states"""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PROCESSING = "processing"
    ERROR = "error"
    SHUTDOWN = "shutdown"


@dataclass
class ManagerMetrics:
    """Track manager performance metrics"""
    messages_processed: int = 0
    errors_encountered: int = 0
    average_processing_time: float = 0.0
    last_activity: datetime = field(default_factory=datetime.now)
    active_processes: int = 0


class BaseManager:
    """Base manager implementation for domain-specific managers"""

    def __init__(
        self,
        message_broker: MessageBroker,
        control_point_manager: ControlPointManager,
        component_name: str,
        domain_type: str
    ):
        # Core dependencies
        self.message_broker = message_broker
        self.cpm = control_point_manager
        self.registry = ComponentRegistry()
        self.logger = logging.getLogger(f"{component_name}_manager")

        # Identity and state
        self.component_name = component_name
        self.domain_type = domain_type
        self.state = ManagerState.INITIALIZING
        self.metrics = ManagerMetrics()

        # Message handling
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._active_processes: Dict[str, ProcessingContext] = {}
        self._async_lock = asyncio.Lock()

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize manager and register with system"""
        try:
            # Register with component registry
            self.registry.register_component(
                self.component_name,
                ComponentType.MANAGER,
                {"domain": self.domain_type}
            )

            # Setup message handlers
            self._setup_message_handlers()

            # Set state to active
            self.state = ManagerState.ACTIVE
            self.logger.info(f"{self.component_name} manager initialized successfully")

        except Exception as e:
            self.state = ManagerState.ERROR
            self.logger.error(f"Manager initialization failed: {str(e)}")
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
                self.component_name,
                f"{self.domain_type}.{message_type.value}",
                self._handle_message
            )

    async def _handle_message(self, message: ProcessingMessage) -> None:
        """Central message handling entry point"""
        try:
            self.state = ManagerState.PROCESSING
            start_time = datetime.now()

            # Get appropriate handler
            handler = self._message_handlers.get(message.message_type)
            if not handler:
                raise ValueError(f"No handler for message type: {message.message_type}")

            # Process message
            await handler(message)

            # Update metrics
            self._update_metrics(
                processing_time=(datetime.now() - start_time).total_seconds(),
                success=True
            )

        except Exception as e:
            self.logger.error(f"Message handling failed: {str(e)}")
            await self._handle_error(message, e)
            self._update_metrics(success=False)

        finally:
            self.state = ManagerState.ACTIVE

    async def _handle_error(
        self,
        message: ProcessingMessage,
        error: Exception
    ) -> None:
        """Handle processing errors"""
        try:
            # Create error message
            error_message = ProcessingMessage(
                message_type=MessageType.FLOW_ERROR,
                content={
                    'error': str(error),
                    'original_message_id': message.id,
                    'component': self.component_name
                },
                metadata=MessageMetadata(
                    correlation_id=message.metadata.correlation_id,
                    source_component=self.component_name,
                    target_component="control_point_manager",
                    domain_type=self.domain_type
                )
            )

            # Publish error
            await self.message_broker.publish(error_message)

        except Exception as e:
            self.logger.error(f"Error handling failed: {str(e)}")

    def _update_metrics(self, processing_time: float = 0.0, success: bool = True) -> None:
        """Update manager metrics"""
        self.metrics.messages_processed += 1
        if not success:
            self.metrics.errors_encountered += 1

        # Update processing time average
        total_time = (self.metrics.average_processing_time *
                     (self.metrics.messages_processed - 1) + processing_time)
        self.metrics.average_processing_time = total_time / self.metrics.messages_processed
        self.metrics.last_activity = datetime.now()

    def get_status(self) -> Dict[str, Any]:
        """Get manager status information"""
        return {
            'component_name': self.component_name,
            'domain_type': self.domain_type,
            'state': self.state.value,
            'metrics': {
                'messages_processed': self.metrics.messages_processed,
                'errors_encountered': self.metrics.errors_encountered,
                'average_processing_time': self.metrics.average_processing_time,
                'last_activity': self.metrics.last_activity.isoformat(),
                'active_processes': self.metrics.active_processes
            }
        }

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            self.state = ManagerState.SHUTDOWN
            self._active_processes.clear()
            self._message_handlers.clear()
            self.logger.info(f"{self.component_name} manager cleaned up successfully")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise

    def __del__(self):
        """Cleanup on deletion"""
        if self.state != ManagerState.SHUTDOWN:
            asyncio.create_task(self.cleanup())