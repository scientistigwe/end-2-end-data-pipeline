# backend/core/managers/base/manager_base.py

from typing import Dict, Any, Optional, Callable, Coroutine
import logging
import asyncio
from datetime import datetime
import uuid

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    MessageMetadata,
    ManagerContext,
    ManagerState,
    ManagerMetrics
)
from .manager_types import ChannelManager


class BaseManager:
    """Base manager implementation with comprehensive message handling"""

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str,
            domain_type: str
    ):
        # Core components
        self.message_broker = message_broker
        self.logger = logging.getLogger(f"{component_name}_manager")

        # Context initialization
        self._context: Optional[ManagerContext] = None
        self._initialize_context(component_name, domain_type)

        # Channel management
        self.channel_manager = ChannelManager(logger=self.logger)

        # Message handling
        self._message_handlers: Dict[MessageType, Callable] = {}
        self._async_lock = asyncio.Lock()

        # Background tasks
        self._background_tasks: List[asyncio.Task] = []

        # Initialize manager
        asyncio.create_task(self._initialize_manager())

    def _initialize_context(self, component_name: str, domain_type: str) -> None:
        """Initialize manager context"""
        try:
            self._context = ManagerContext(
                pipeline_id=str(uuid.uuid4()),
                component_name=component_name,
                domain_type=domain_type,
                stage="initializing",
                status="active",
                state=ManagerState.INITIALIZING,
                metrics=ManagerMetrics()
            )
        except Exception as e:
            self.logger.error(f"Context initialization failed: {e}")
            raise

    @property
    def context(self) -> ManagerContext:
        """Access manager context safely"""
        if self._context is None:
            raise AttributeError(f"{self.__class__.__name__} context not initialized")
        return self._context

    async def _initialize_manager(self) -> None:
        """Initialize manager components"""
        try:
            # Setup message handling
            await self._setup_base_handlers()
            await self._setup_domain_handlers()

            # Start monitoring
            self._start_background_tasks()

            # Mark as active
            self.context.state = ManagerState.ACTIVE

        except Exception as e:
            self.logger.error(f"Manager initialization failed: {e}")
            raise

    async def _setup_base_handlers(self) -> None:
        """Setup base message handlers"""
        base_handlers = {
            MessageType.COMPONENT_INIT: self._handle_component_init,
            MessageType.COMPONENT_UPDATE: self._handle_component_update,
            MessageType.COMPONENT_ERROR: self._handle_component_error,
            MessageType.COMPONENT_SYNC: self._handle_component_sync
        }

        for message_type, handler in base_handlers.items():
            await self.register_message_handler(message_type, handler)

    async def _setup_domain_handlers(self) -> None:
        """Setup domain-specific handlers - to be implemented by subclasses"""
        raise NotImplementedError

    def _start_background_tasks(self) -> None:
        """Start background monitoring tasks"""
        tasks = [
            self._monitor_process_timeouts(),
            self._monitor_resource_usage(),
            self._monitor_system_health()
        ]

        for task in tasks:
            self._background_tasks.append(asyncio.create_task(task))

    async def register_message_handler(
            self,
            message_type: MessageType,
            handler: Callable[[ProcessingMessage], Coroutine]
    ) -> None:
        """Register a message handler"""
        async with self._async_lock:
            self._message_handlers[message_type] = handler
            self.context.handlers[message_type.value] = handler.__name__
            await self.message_broker.subscribe(
                self.context.component_name,
                message_type.value,
                self._handle_message
            )

    async def _handle_message(self, message: ProcessingMessage) -> None:
        """Central message handling logic"""
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
            self.logger.error(f"Message handling failed: {e}")
            await self._handle_error(message, e)
            self._update_metrics(success=False)

        finally:
            self.context.state = ManagerState.ACTIVE

    def _update_metrics(self, processing_time: float = 0.0, success: bool = True) -> None:
        """Update performance metrics"""
        metrics = self.context.metrics
        metrics.messages_processed += 1
        if not success:
            metrics.errors_encountered += 1

        if metrics.messages_processed > 0:
            total_time = (metrics.average_processing_time *
                          (metrics.messages_processed - 1) + processing_time)
            metrics.average_processing_time = total_time / metrics.messages_processed

        metrics.last_activity = datetime.now()

    async def cleanup(self) -> None:
        """Cleanup manager resources"""
        try:
            # Update state
            self.context.state = ManagerState.SHUTDOWN

            # Cancel background tasks
            for task in self._background_tasks:
                if not task.done():
                    task.cancel()

            # Cleanup channels
            self.channel_manager.cleanup_channels()

            # Notify cleanup
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.COMPONENT_CLEANUP,
                    content={
                        'component_name': self.context.component_name,
                        'reason': 'Manager shutdown'
                    },
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component="system"
                    )
                )
            )

            # Clear handlers
            self._message_handlers.clear()

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            raise