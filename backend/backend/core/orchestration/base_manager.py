# backend/core/base/base_manager.py

import logging
import threading
import uuid
from typing import Any, Dict, Optional, List, Callable, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ModuleIdentifier,
    ProcessingMessage,
    ProcessingStatus
)
from backend.core.registry.component_registry import ComponentRegistry

logger = logging.getLogger(__name__)


class ChannelType(Enum):
    """Define main communication channels in priority order"""
    ROUTING = "routing"  # Route determination
    STAGING = "staging"  # Data staging
    DATA_SOURCE = "data_source"  # Data ingestion/response
    PROCESSING = "processing"  # Data processing
    DECISION = "decision"  # User decisions
    INSIGHT = "insight"  # Business insights


class ResourceState(Enum):
    """Resource states with health indication"""
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    RECOVERING = "recovering"


@dataclass
class ChannelMetrics:
    """Track channel health and performance"""
    message_count: int = 0
    error_count: int = 0
    last_processed: Optional[datetime] = None
    backpressure_applied: bool = False
    processing_time: List[float] = field(default_factory=list)
    retry_count: int = 0
    queue_size: int = 0


@dataclass
class ManagerMetadata:
    """Manager component metadata"""
    component_name: str
    instance_id: str
    created_at: datetime = field(default_factory=datetime.now)
    state: ResourceState = ResourceState.ACTIVE
    error_count: int = 0
    last_heartbeat: datetime = field(default_factory=datetime.now)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


class BaseManager:
    """
    Enhanced base manager providing core functionality for all specialized managers.
    Includes improved channel management, error handling, and monitoring.
    """

    MAX_CHANNEL_MESSAGES = 1000  # Maximum messages per channel
    ACK_TIMEOUT = 30  # Seconds to wait for acknowledgment
    LOCK_TIMEOUT = 1.0  # Seconds to wait for lock acquisition

    def __init__(self, message_broker: MessageBroker, component_name: str):
        """Initialize base manager"""
        # Core components
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.logger = logging.getLogger(__name__)

        # Component identification
        self.module_id = ModuleIdentifier(
            component_name,
            "manage",
            self.registry.get_component_uuid(component_name)
        )

        # Enhanced metadata and state tracking
        self.metadata = ManagerMetadata(
            component_name=component_name,
            instance_id=self.module_id.instance_id
        )

        # Channel and handler management
        self._message_queues: Dict[str, Queue] = {}
        self._handlers: Dict[str, Dict[str, Callable]] = {}
        self._locks: Dict[str, threading.Lock] = {}
        self._channel_metrics: Dict[str, ChannelMetrics] = {}
        self._pending_acks: Dict[str, datetime] = {}
        self._failed_messages: Set[str] = set()

        # Initialize system
        self._initialize_manager()
        self._start_health_monitor()

    def _initialize_manager(self) -> None:
        """Initialize manager in correct order"""
        try:
            self._initialize_messaging()
            self._initialize_channels()
            self._initialize_handlers()
            self._verify_initialization()
            self.logger.info(f"{self.metadata.component_name} initialized successfully")
        except Exception as e:
            self.logger.error(f"Manager initialization failed: {str(e)}")
            self.metadata.state = ResourceState.ERROR
            raise

    def _initialize_channels(self) -> None:
        """Initialize channels in priority order"""
        for channel in ChannelType:
            try:
                self._setup_channel(channel)
                self._verify_channel_setup(channel)
                self.logger.debug(f"Channel {channel.value} initialized")
            except Exception as e:
                self.logger.error(f"Channel {channel.value} initialization failed: {str(e)}")
                raise

    def _setup_channel(self, channel: ChannelType) -> None:
        """Set up a specific communication channel with monitoring"""
        channel_name = channel.value
        self._handlers[channel_name] = {}
        self._locks[channel_name] = threading.Lock()
        self._message_queues[channel_name] = Queue(maxsize=self.MAX_CHANNEL_MESSAGES)
        self._channel_metrics[channel_name] = ChannelMetrics()
        self._setup_channel_monitoring(channel)

    def _verify_channel_setup(self, channel: ChannelType) -> None:
        """Verify channel is properly set up"""
        channel_name = channel.value
        if not all([
            self._handlers.get(channel_name),
            self._locks.get(channel_name),
            self._message_queues.get(channel_name),
            self._channel_metrics.get(channel_name)
        ]):
            raise RuntimeError(f"Channel {channel_name} not properly initialized")

    def publish_message(self, target_identifier: ModuleIdentifier,
                        message_type: MessageType, content: Dict[str, Any]) -> None:
        """Publish message with acknowledgment tracking and retry logic"""
        message_id = str(uuid.uuid4())
        message = ProcessingMessage(
            message_id=message_id,
            source_identifier=self.module_id,
            target_identifier=target_identifier,
            message_type=message_type,
            content=content,
            timestamp=datetime.now()
        )

        try:
            # Check channel backpressure
            channel = self._get_message_channel(message_type)
            if self._check_backpressure(channel):
                self._handle_backpressure(channel)
                return

            # Add to queue
            queue = self._message_queues[channel.value]
            if not queue.full():
                queue.put(message)
                self._publish_with_retry(message)
                self._pending_acks[message_id] = datetime.now()
                self._start_ack_timeout(message_id)
            else:
                raise RuntimeError(f"Channel {channel.value} queue full")

        except Exception as e:
            self._handle_publish_error(message_id, e)

    def _handle_received_message(self, message: ProcessingMessage) -> None:
        """Handle received message with proper channel routing"""
        try:
            channel = self._get_message_channel(message.message_type)

            if self._acquire_channel_lock(channel):
                try:
                    metrics = self._channel_metrics[channel.value]
                    metrics.message_count += 1
                    metrics.last_processed = datetime.now()

                    handler = self._get_message_handler(channel, message)
                    if handler:
                        handler(message)
                    else:
                        self.logger.warning(
                            f"No handler for message type {message.message_type} in channel {channel.value}")

                finally:
                    self._release_channel_lock(channel)
            else:
                self.logger.warning(f"Failed to acquire lock for channel {channel.value}")

        except Exception as e:
            self._handle_message_error(message, e)

    def _get_message_handler(self, channel: ChannelType, message: ProcessingMessage) -> Optional[Callable]:
        """Get appropriate handler for message type"""
        handlers = self._handlers.get(channel.value, {})
        return handlers.get(str(message.message_type))

    def _handle_message_error(self, message: ProcessingMessage, error: Exception) -> None:
        """Handle message processing errors"""
        error_details = self.handle_error(error, {
            'message_id': message.message_id,
            'message_type': str(message.message_type),
            'source': message.source_identifier.get_tag()
        })

        channel = self._get_message_channel(message.message_type)
        metrics = self._channel_metrics[channel.value]
        metrics.error_count += 1

        if metrics.error_count > 5:
            self._apply_circuit_breaker(channel)

    def _start_health_monitor(self) -> None:
        """Start health monitoring thread"""

        def monitor_health():
            while True:
                try:
                    self._check_channel_health()
                    self._check_message_timeouts()
                    self._update_manager_status()
                    threading.Event().wait(30)  # Check every 30 seconds
                except Exception as e:
                    self.logger.error(f"Health monitoring error: {str(e)}")

        threading.Thread(target=monitor_health, daemon=True).start()

    def cleanup(self) -> None:
        """Enhanced cleanup operations"""
        try:
            # Clean up pending messages
            for message_id in list(self._pending_acks.keys()):
                self._handle_message_timeout(message_id)

            # Clear channel queues
            for queue in self._message_queues.values():
                while not queue.empty():
                    queue.get_nowait()

            # Reset channel metrics
            for channel in ChannelType:
                if self._acquire_channel_lock(channel):
                    try:
                        self._channel_metrics[channel.value] = ChannelMetrics()
                    finally:
                        self._locks[channel.value].release()

            self.metadata.state = ResourceState.INACTIVE
            self.logger.info(f"Cleanup completed for {self.metadata.component_name}")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            raise

    def __del__(self):
        """Ensure proper cleanup on deletion"""
        self.cleanup()