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
from backend.core.messaging.types import ComponentType

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

        # Component identification with proper ComponentType
        self.module_id = ModuleIdentifier(
            component_name=component_name,
            component_type=ComponentType.MANAGER,  # Use enum instead of string
            method_name="manage",
            instance_id=self.registry.get_component_uuid(component_name)
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
            # Step 1: Initialize messaging system
            self._initialize_messaging()

            # Step 2: Initialize channels
            self._initialize_channels()

            # Step 3: Initialize handlers
            self._initialize_handlers()

            # Step 4: Verify everything is set up correctly
            self._verify_initialization()

            # Step 5: Start health monitoring
            self._start_health_monitor()

            self.logger.info(f"{self.metadata.component_name} initialized successfully")

        except Exception as e:
            self.logger.error(f"Manager initialization failed: {str(e)}")
            self.metadata.state = ResourceState.ERROR
            raise

    def _initialize_messaging(self) -> None:
        """Initialize base messaging system"""
        try:
            self.logger.info("Initializing base messaging system...")

            # Register with message broker
            self.message_broker.register_component(self.module_id)

            # Initialize base channels and subscriptions
            for channel in ChannelType:
                try:
                    self._subscribe_to_channel(channel)
                except Exception as e:
                    self.logger.error(f"Failed to subscribe to channel {channel.value}: {str(e)}")
                    raise

            self.logger.info("Base messaging system initialized successfully")
        except Exception as e:
            self.logger.error(f"Base messaging initialization failed: {str(e)}")
            raise

    def _initialize_handlers(self) -> None:
        """Initialize message handlers for each channel"""
        try:
            self.logger.info("Initializing message handlers...")

            # Initialize handler dictionaries for each channel
            for channel in ChannelType:
                if channel.value not in self._handlers:
                    self._handlers[channel.value] = {}

            # Set up default handlers
            self._setup_default_handlers()

            self.logger.info("Message handlers initialized successfully")
        except Exception as e:
            self.logger.error(f"Handler initialization failed: {str(e)}")
            raise

    def _setup_default_handlers(self) -> None:
        """Set up default message handlers"""
        # Base handlers for common message types
        default_handlers = {
            ChannelType.ROUTING.value: {
                MessageType.ROUTE_REQUEST: self._default_routing_handler,
                MessageType.ROUTE_UPDATE: self._default_routing_handler,
                MessageType.ROUTE_CHANGE: self._default_routing_handler,
                MessageType.ROUTE_COMPLETE: self._default_routing_handler
            },
            ChannelType.PROCESSING.value: {
                MessageType.SOURCE_EXTRACT: self._default_processing_handler,
                MessageType.QUALITY_ANALYZE: self._default_processing_handler,
                MessageType.INSIGHT_GENERATE: self._default_processing_handler
            },
            ChannelType.STAGING.value: {
                MessageType.STAGE_STORE: self._default_staging_handler,
                MessageType.STAGE_RETRIEVE: self._default_staging_handler,
                MessageType.STAGE_UPDATE: self._default_staging_handler
            },
            ChannelType.DATA_SOURCE.value: {
                MessageType.SOURCE_CONNECT: self._default_source_handler,
                MessageType.SOURCE_READ: self._default_source_handler,
                MessageType.SOURCE_VALIDATE: self._default_source_handler
            },
            ChannelType.DECISION.value: {
                MessageType.DECISION_START: self._default_decision_handler,
                MessageType.USER_DECISION_REQUEST: self._default_decision_handler,
                MessageType.DECISION_PROCESS: self._default_decision_handler
            },
            ChannelType.INSIGHT.value: {
                MessageType.INSIGHT_START: self._default_insight_handler,
                MessageType.INSIGHT_GENERATE: self._default_insight_handler,
                MessageType.INSIGHT_UPDATE: self._default_insight_handler
            }
        }

        # Update handlers dictionary with defaults
        for channel, handlers in default_handlers.items():
            if channel in self._handlers:
                self._handlers[channel].update(handlers)

    def _default_routing_handler(self, message: ProcessingMessage) -> None:
        """Default handler for routing messages"""
        self.logger.warning(f"Default routing handler called for message type: {message.message_type}")
        # Implement default routing logic here if needed

    def _default_staging_handler(self, message: ProcessingMessage) -> None:
        """Default handler for staging messages"""
        self.logger.warning(f"Default staging handler called for message type: {message.message_type}")

    def _default_source_handler(self, message: ProcessingMessage) -> None:
        """Default handler for data source messages"""
        self.logger.warning(f"Default source handler called for message type: {message.message_type}")

    def _default_decision_handler(self, message: ProcessingMessage) -> None:
        """Default handler for decision messages"""
        self.logger.warning(f"Default decision handler called for message type: {message.message_type}")

    def _default_insight_handler(self, message: ProcessingMessage) -> None:
        """Default handler for insight messages"""
        self.logger.warning(f"Default insight handler called for message type: {message.message_type}")

    def _default_processing_handler(self, message: ProcessingMessage) -> None:
        """Default handler for processing messages"""
        self.logger.warning(f"Default processing handler called for message type: {message.message_type}")
        # Implement default processing logic here if needed

    def _initialize_channels(self) -> None:
        """Initialize channels in priority order"""
        try:
            self.logger.info("Starting channel initialization...")

            # Initialize channels dictionary if not exists
            if not hasattr(self, '_handlers'):
                self._handlers = {}

            # Initialize each channel
            for channel in ChannelType:
                try:
                    self.logger.info(f"Setting up channel: {channel.value}")
                    self._setup_channel(channel)
                    self._verify_channel_setup(channel)
                    self.logger.info(f"Channel {channel.value} initialized successfully")
                except Exception as e:
                    self.logger.error(f"Failed to initialize channel {channel.value}: {str(e)}")
                    raise

            self.logger.info("All channels initialized successfully")

        except Exception as e:
            self.logger.error(f"Channel initialization failed: {str(e)}")
            raise

    def _setup_channel(self, channel: ChannelType) -> None:
        """Set up a specific communication channel with monitoring"""
        try:
            channel_name = channel.value
            # Initialize basic handlers dictionary if not exists
            if channel_name not in self._handlers:
                self._handlers[channel_name] = {}

            # Initialize lock if not exists
            if channel_name not in self._locks:
                self._locks[channel_name] = threading.Lock()

            # Initialize message queue if not exists
            if channel_name not in self._message_queues:
                self._message_queues[channel_name] = Queue(maxsize=self.MAX_CHANNEL_MESSAGES)

            # Initialize metrics if not exists
            if channel_name not in self._channel_metrics:
                self._channel_metrics[channel_name] = ChannelMetrics()

            # Set up channel monitoring
            self._setup_channel_monitoring(channel)

            # Mark channel as initialized
            if channel_name not in self._handlers:
                self._handlers[channel_name] = {}
            self._handlers[channel_name]['initialized'] = True

            self.logger.info(f"Channel {channel_name} setup completed")

        except Exception as e:
            self.logger.error(f"Error setting up channel {channel.value}: {str(e)}")
            raise

    def _verify_channel_setup(self, channel: ChannelType) -> None:
        """Verify channel is properly set up"""
        channel_name = channel.value
        try:
            # Log verification attempt
            self.logger.debug(f"Verifying channel setup: {channel_name}")

            # Check all required components
            if not all([
                channel_name in self._handlers,
                channel_name in self._locks,
                channel_name in self._message_queues,
                channel_name in self._channel_metrics,
                self._handlers.get(channel_name, {}).get('initialized', False)  # Check initialization flag
            ]):
                # Log which components are missing
                self.logger.error(f"Channel {channel_name} verification failed:")
                self.logger.error(f"Handlers exist: {channel_name in self._handlers}")
                self.logger.error(f"Locks exist: {channel_name in self._locks}")
                self.logger.error(f"Message queues exist: {channel_name in self._message_queues}")
                self.logger.error(f"Metrics exist: {channel_name in self._channel_metrics}")
                self.logger.error(f"Initialized flag: {self._handlers.get(channel_name, {}).get('initialized', False)}")

                raise RuntimeError(f"Channel {channel_name} not properly initialized")

            self.logger.debug(f"Channel {channel_name} verified successfully")

        except Exception as e:
            self.logger.error(f"Channel verification failed for {channel_name}: {str(e)}")
            raise

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

        logger.info(f"Publishing message with routing key: {message.get_routing_key()}")

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

    def _subscribe_to_channel(self, channel: ChannelType) -> None:
        """Subscribe to a messaging channel"""
        try:
            channel_name = channel.value
            if channel_name not in self._message_queues:
                self._message_queues[channel_name] = Queue(maxsize=self.MAX_CHANNEL_MESSAGES)
            if channel_name not in self._locks:
                self._locks[channel_name] = threading.Lock()
            if channel_name not in self._channel_metrics:
                self._channel_metrics[channel_name] = ChannelMetrics()

            # Subscribe through message broker with correct parameters
            self.message_broker.subscribe(
                component=self.module_id,  # Use the module_id created in __init__
                pattern=channel_name,  # Use channel name as pattern
                callback=self._handle_received_message,
                timeout=10.0
            )
            self.logger.debug(f"Subscribed to channel: {channel_name}")

        except Exception as e:
            self.logger.error(f"Error subscribing to channel {channel_name}: {str(e)}")
            raise

    def _setup_channel_monitoring(self, channel: ChannelType) -> None:
        """Setup monitoring for a specific channel"""
        try:
            metrics = self._channel_metrics.get(channel.value)
            if not metrics:
                metrics = ChannelMetrics()
                self._channel_metrics[channel.value] = metrics

            def monitor():
                while True:
                    try:
                        self._check_channel_health(channel)
                        threading.Event().wait(30)  # Check every 30 seconds
                    except Exception as e:
                        self.logger.error(f"Channel monitoring error: {str(e)}")

            threading.Thread(target=monitor, daemon=True).start()
        except Exception as e:
            self.logger.error(f"Error setting up channel monitoring: {str(e)}")
            raise

    def _check_channel_health(self, channel: Optional[ChannelType] = None) -> None:
        """Check health of channels"""
        channels = [channel] if channel else list(ChannelType)
        for ch in channels:
            try:
                metrics = self._channel_metrics.get(ch.value)
                if metrics:
                    # Check for error threshold
                    if metrics.error_count > 5:
                        self._apply_circuit_breaker(ch)
                    # Check for queue overflow
                    if metrics.queue_size >= self.MAX_CHANNEL_MESSAGES * 0.9:
                        self._handle_backpressure(ch)
            except Exception as e:
                self.logger.error(f"Error checking channel health: {str(e)}")

    def _apply_circuit_breaker(self, channel: ChannelType) -> None:
        """Apply circuit breaker pattern to channel"""
        try:
            metrics = self._channel_metrics[channel.value]
            metrics.backpressure_applied = True
            self.logger.warning(f"Circuit breaker applied to channel {channel.value}")

            # Start recovery thread
            def recovery():
                threading.Event().wait(60)  # Wait 60 seconds
                metrics.error_count = 0
                metrics.backpressure_applied = False

            threading.Thread(target=recovery, daemon=True).start()
        except Exception as e:
            self.logger.error(f"Error applying circuit breaker: {str(e)}")

    def _handle_backpressure(self, channel: ChannelType) -> None:
        """Handle backpressure situation"""
        try:
            metrics = self._channel_metrics[channel.value]
            metrics.backpressure_applied = True

            # Clear some messages from queue
            queue = self._message_queues[channel.value]
            while not queue.empty() and queue.qsize() > self.MAX_CHANNEL_MESSAGES * 0.7:
                queue.get_nowait()

            metrics.queue_size = queue.qsize()
            self.logger.warning(f"Backpressure handled for channel {channel.value}")
        except Exception as e:
            self.logger.error(f"Error handling backpressure: {str(e)}")

    def _check_backpressure(self, channel: ChannelType) -> bool:
        """Check if backpressure is being applied"""
        try:
            metrics = self._channel_metrics.get(channel.value)
            return metrics and metrics.backpressure_applied
        except Exception as e:
            self.logger.error(f"Error checking backpressure: {str(e)}")
            return False

    def _get_message_channel(self, message_type: MessageType) -> ChannelType:
        """Get appropriate channel for message type"""
        try:
            # Map message types to channels
            channel_mapping = {
                MessageType.PIPELINE_CONTROL: ChannelType.ROUTING,
                MessageType.PIPELINE_STATUS: ChannelType.ROUTING,
                MessageType.DATA_VALIDATION: ChannelType.PROCESSING,
                MessageType.DATA_PROCESSING: ChannelType.PROCESSING,
                # Add other mappings as needed
            }
            return channel_mapping.get(message_type, ChannelType.PROCESSING)
        except Exception as e:
            self.logger.error(f"Error getting message channel: {str(e)}")
            return ChannelType.PROCESSING

    def _publish_with_retry(self, message: ProcessingMessage, retries: int = 3) -> None:
        """Publish message with retry logic"""
        try:
            for attempt in range(retries):
                try:
                    self.message_broker.publish(message)
                    return
                except Exception as e:
                    if attempt == retries - 1:
                        raise
                    self.logger.warning(f"Retry attempt {attempt + 1} for message {message.message_id}")
                    threading.Event().wait(1)  # Wait 1 second between retries
        except Exception as e:
            self.logger.error(f"Error publishing message: {str(e)}")
            self._handle_publish_error(message.message_id, e)

    def _handle_publish_error(self, message_id: str, error: Exception) -> None:
        """Handle message publishing errors"""
        try:
            self._failed_messages.add(message_id)
            self.logger.error(f"Failed to publish message {message_id}: {str(error)}")

            if message_id in self._pending_acks:
                del self._pending_acks[message_id]
        except Exception as e:
            self.logger.error(f"Error handling publish error: {str(e)}")

    def _start_ack_timeout(self, message_id: str) -> None:
        """Start acknowledgment timeout monitoring"""

        def check_timeout():
            threading.Event().wait(self.ACK_TIMEOUT)
            if message_id in self._pending_acks:
                self._handle_message_timeout(message_id)

        threading.Thread(target=check_timeout, daemon=True).start()

    def _handle_message_timeout(self, message_id: str) -> None:
        """Handle message timeout"""
        try:
            if message_id in self._pending_acks:
                del self._pending_acks[message_id]
                self.logger.warning(f"Message {message_id} timed out")
        except Exception as e:
            self.logger.error(f"Error handling message timeout: {str(e)}")

    def _check_message_timeouts(self) -> None:
        """Check for message timeouts"""
        try:
            current_time = datetime.now()
            timeout_messages = [
                msg_id for msg_id, timestamp in self._pending_acks.items()
                if (current_time - timestamp).total_seconds() > self.ACK_TIMEOUT
            ]

            for message_id in timeout_messages:
                self._handle_message_timeout(message_id)
        except Exception as e:
            self.logger.error(f"Error checking message timeouts: {str(e)}")

    def _verify_initialization(self) -> None:
        """Verify all components are properly initialized"""
        try:
            # Verify channels
            for channel in ChannelType:
                self._verify_channel_setup(channel)

            # Verify core components
            if not all([
                self.message_broker,
                self.registry,
                self.module_id,
                self.metadata
            ]):
                raise RuntimeError("Core components not properly initialized")

            self.logger.info("Initialization verification completed successfully")
        except Exception as e:
            self.logger.error(f"Initialization verification failed: {str(e)}")
            raise

    def _acquire_channel_lock(self, channel: str) -> bool:
        """Acquire lock for a messaging channel"""
        try:
            # Implementation of channel locking logic
            if not hasattr(self, '_channel_locks'):
                self._channel_locks = {}

            if channel not in self._channel_locks:
                self._channel_locks[channel] = False

            if not self._channel_locks[channel]:
                self._channel_locks[channel] = True
                return True

            return False
        except Exception as e:
            self.logger.error(f"Error acquiring channel lock: {str(e)}")
            return False

    def _update_manager_status(self) -> None:
        """Update manager status and health metrics"""
        try:
            current_time = datetime.now()

            # Update heartbeat
            self.metadata.last_heartbeat = current_time

            # Calculate performance metrics
            total_messages = sum(m.message_count for m in self._channel_metrics.values())
            total_errors = sum(m.error_count for m in self._channel_metrics.values())
            total_queued = sum(m.queue_size for m in self._channel_metrics.values())

            # Update performance metrics
            self.metadata.performance_metrics.update({
                'messages_processed': total_messages,
                'error_rate': (total_errors / total_messages) if total_messages > 0 else 0,
                'queue_utilization': total_queued,
                'uptime_seconds': (current_time - self.metadata.created_at).total_seconds(),
                'channel_status': {
                    channel: {
                        'active': not metrics.backpressure_applied,
                        'error_count': metrics.error_count,
                        'message_count': metrics.message_count,
                        'last_processed': metrics.last_processed.isoformat() if metrics.last_processed else None,
                        'avg_processing_time': sum(metrics.processing_time) / len(
                            metrics.processing_time) if metrics.processing_time else 0
                    }
                    for channel, metrics in self._channel_metrics.items()
                }
            })

            # Update overall state based on metrics
            if total_errors > 0 and self.metadata.state != ResourceState.ERROR:
                self._evaluate_health_state(total_errors, total_messages)

            self.logger.debug(f"Manager status updated: {self.metadata.state.value}")

        except Exception as e:
            self.logger.error(f"Error updating manager status: {str(e)}")
            self.metadata.state = ResourceState.ERROR

    def _evaluate_health_state(self, total_errors: int, total_messages: int) -> None:
        """Evaluate and update manager health state"""
        try:
            error_rate = total_errors / total_messages if total_messages > 0 else 0

            if error_rate > 0.25:  # More than 25% errors
                self.metadata.state = ResourceState.ERROR
            elif error_rate > 0.10:  # More than 10% errors
                self.metadata.state = ResourceState.DEGRADED
            elif error_rate > 0.05:  # More than 5% errors
                self.metadata.state = ResourceState.RECOVERING
            elif any(m.backpressure_applied for m in self._channel_metrics.values()):
                self.metadata.state = ResourceState.BUSY
            else:
                self.metadata.state = ResourceState.ACTIVE

        except Exception as e:
            self.logger.error(f"Error evaluating health state: {str(e)}")
            self.metadata.state = ResourceState.ERROR

    def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle and log errors with context"""
        try:
            # Increment error count
            self.metadata.error_count += 1

            # Prepare error details
            error_details = {
                'error_type': type(error).__name__,
                'error_message': str(error),
                'timestamp': datetime.now().isoformat(),
                'component': self.metadata.component_name,
                'instance_id': self.metadata.instance_id,
                'context': context or {},
                'stack_trace': getattr(error, '__traceback__', None)
            }

            # Log error with context
            self.logger.error(
                f"Error in {self.metadata.component_name}: {str(error)}",
                extra={'error_details': error_details}
            )

            # Update manager state if necessary
            if self.metadata.error_count > 10:  # Threshold for state change
                self.metadata.state = ResourceState.ERROR

            # Trigger recovery if needed
            if self.metadata.state == ResourceState.ERROR:
                self._trigger_recovery()

            return error_details

        except Exception as e:
            self.logger.error(f"Error handling error: {str(e)}")
            return {
                'error_type': 'ErrorHandlingFailure',
                'error_message': f"Failed to handle error: {str(e)}",
                'timestamp': datetime.now().isoformat()
            }

    def _trigger_recovery(self) -> None:
        """Trigger recovery procedures"""
        try:
            # Set state to recovering
            self.metadata.state = ResourceState.RECOVERING

            # Clear error counts
            self.metadata.error_count = 0
            for metrics in self._channel_metrics.values():
                metrics.error_count = 0
                metrics.backpressure_applied = False

            # Clear message queues
            for queue in self._message_queues.values():
                while not queue.empty():
                    queue.get_nowait()

            # Reset channel metrics
            for channel in list(self._channel_metrics.keys()):
                self._channel_metrics[channel] = ChannelMetrics()

            self.logger.info(f"Recovery triggered for {self.metadata.component_name}")

            # Schedule state check
            def check_recovery():
                threading.Event().wait(60)  # Wait 60 seconds
                if self.metadata.state == ResourceState.RECOVERING:
                    self.metadata.state = ResourceState.ACTIVE

            threading.Thread(target=check_recovery, daemon=True).start()

        except Exception as e:
            self.logger.error(f"Error triggering recovery: {str(e)}")
            self.metadata.state = ResourceState.ERROR

    def cleanup(self) -> None:
        """Enhanced cleanup operations with safety checks"""
        try:
            # Clean up pending messages
            for message_id in list(self._pending_acks.keys()):
                try:
                    self._handle_message_timeout(message_id)
                except Exception as e:
                    self.logger.error(f"Error cleaning up message {message_id}: {str(e)}")

            # Clear channel queues safely
            for queue in self._message_queues.values():
                try:
                    while not queue.empty():
                        try:
                            queue.get_nowait()
                        except Exception:
                            break
                except Exception as e:
                    self.logger.error(f"Error clearing queue: {str(e)}")

            # Reset channel metrics safely
            for channel in ChannelType:
                try:
                    channel_name = channel.value
                    if channel_name in self._locks:
                        lock = self._locks[channel_name]
                        if lock.locked():
                            try:
                                lock.release()
                            except Exception:
                                pass  # Lock might already be released

                    if channel_name in self._channel_metrics:
                        self._channel_metrics[channel_name] = ChannelMetrics()
                except Exception as e:
                    self.logger.error(f"Error resetting channel {channel.value}: {str(e)}")

            # Clear all data structures safely
            try:
                self._message_queues.clear()
                self._channel_metrics.clear()
                self._pending_acks.clear()
                self._failed_messages.clear()
                self._locks.clear()
            except Exception as e:
                self.logger.error(f"Error clearing data structures: {str(e)}")

            self.metadata.state = ResourceState.INACTIVE
            self.logger.info(f"Cleanup completed for {self.metadata.component_name}")

        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")
            # Don't re-raise to allow cleanup to continue

    def __del__(self):
        """Safe deletion with error handling"""
        try:
            self.cleanup()
        except Exception as e:
            # Log but don't raise as this is called during garbage collection
            logging.error(f"Error during manager deletion: {str(e)}")

