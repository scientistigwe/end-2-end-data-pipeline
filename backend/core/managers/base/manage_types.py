# backend/core/managers/base/manage_types.py

from queue import Queue
from typing import Dict, Callable, Optional, Any
import logging
import threading
from datetime import datetime

from backend.core.messaging.types import ProcessingMessage
from .bm_constants import ChannelType, ManagerConstants
from .bm_metrics import ChannelMetrics


class ChannelManager:
    """
    Advanced channel management with comprehensive tracking and handling.
    """
    def __init__(
            self,
            logger: Optional[logging.Logger] = None,
            max_messages: int = ManagerConstants.MAX_CHANNEL_MESSAGES,
            lock_timeout: float = ManagerConstants.LOCK_TIMEOUT
    ):
        """
        Initialize channel management systems.

        Args:
            logger (Optional[logging.Logger], optional): Logger for tracking. Defaults to None.
            max_messages (int, optional): Maximum messages per channel. Defaults to 1000.
            lock_timeout (float, optional): Lock acquisition timeout. Defaults to 1.0.
        """
        # Logger configuration
        self.logger = logger or logging.getLogger(__name__)

        # Channel configuration
        self.max_messages = max_messages
        self.lock_timeout = lock_timeout

        # Channel-specific queues
        self.message_queues: Dict[ChannelType, Queue] = {}

        # Channel locks
        self.channel_locks: Dict[ChannelType, threading.Lock] = {}

        # Channel metrics tracking
        self.channel_metrics: Dict[ChannelType, ChannelMetrics] = {}

        # Message handlers
        self.message_handlers: Dict[ChannelType, Dict[str, Callable]] = {}

        # Initialize all channels
        self._initialize_channels()

    def _initialize_channels(self) -> None:
        """
        Initialize all communication channels with default configurations.
        """
        try:
            self.logger.info("Initializing communication channels...")

            for channel in ChannelType:
                # Create message queue
                self.message_queues[channel] = Queue(maxsize=self.max_messages)

                # Create channel-specific lock
                self.channel_locks[channel] = threading.Lock()

                # Initialize channel metrics
                self.channel_metrics[channel] = ChannelMetrics(
                    channel_name=channel.value,
                    created_at=datetime.now()
                )

                # Initialize handlers dictionary for channel
                self.message_handlers[channel] = {}

            self.logger.info("Channels initialized successfully")

        except Exception as e:
            self.logger.error(f"Channel initialization failed: {str(e)}")
            raise

    def register_handler(self, channel: ChannelType, message_type: str, handler: Callable) -> None:
        """
        Register a message handler for a specific channel and message type.

        Args:
            channel (ChannelType): Communication channel
            message_type (str): Type of message to handle
            handler (Callable): Handler function for the message
        """
        if channel not in self.message_handlers:
            self.message_handlers[channel] = {}
        self.message_handlers[channel][message_type] = handler
        self.logger.info(f"Handler registered for {channel.value}: {message_type}")

    def get_message_handler(self, channel: ChannelType, message_type: str) -> Optional[Callable]:
        """
        Get handler for a specific message type in a channel.

        Args:
            channel (ChannelType): Channel to search
            message_type (str): Message type to find handler for

        Returns:
            Optional[Callable]: Handler function if exists, None otherwise
        """
        return self.message_handlers.get(channel, {}).get(message_type)

    def acquire_channel_lock(self, channel: ChannelType) -> bool:
        """
        Attempt to acquire a lock for a specific channel.

        Args:
            channel (ChannelType): Channel to lock

        Returns:
            bool: True if lock acquired, False otherwise
        """
        lock = self.channel_locks.get(channel)
        if lock:
            try:
                return lock.acquire(timeout=self.lock_timeout)
            except Exception as e:
                self.logger.error(f"Error acquiring lock for {channel.value}: {e}")
                return False
        return False

    def release_channel_lock(self, channel: ChannelType) -> None:
        """
        Release the lock for a specific channel.

        Args:
            channel (ChannelType): Channel to unlock
        """
        lock = self.channel_locks.get(channel)
        if lock and lock.locked():
            try:
                lock.release()
            except Exception as e:
                self.logger.error(f"Error releasing lock for {channel.value}: {e}")

    def enqueue_message(self, channel: ChannelType, message: ProcessingMessage) -> bool:
        """
        Enqueue a message to a specific channel.

        Args:
            channel (ChannelType): Target channel
            message (ProcessingMessage): Message to enqueue

        Returns:
            bool: True if message enqueued successfully, False otherwise
        """
        try:
            queue = self.message_queues.get(channel)
            metrics = self.channel_metrics.get(channel)

            if queue and not queue.full() and metrics:
                queue.put(message)
                metrics.message_count += 1
                metrics.queue_size = queue.qsize()
                return True

            self.logger.warning(f"Channel {channel.value} queue is full or not initialized")
            return False

        except Exception as e:
            self.logger.error(f"Error enqueuing message: {str(e)}")
            return False

    def get_channel_metrics(self, channel: ChannelType) -> ChannelMetrics:
        """
        Retrieve metrics for a specific channel.

        Args:
            channel (ChannelType): Channel to retrieve metrics for

        Returns:
            ChannelMetrics: Metrics for the specified channel
        """
        return self.channel_metrics.get(
            channel,
            ChannelMetrics(channel_name=channel.value, created_at=datetime.now())
        )

    def verify_channel_setup(self, channel: ChannelType) -> bool:
        """
        Verify the setup of a specific channel.

        Args:
            channel (ChannelType): Channel to verify

        Returns:
            bool: True if channel is properly set up, False otherwise
        """
        try:
            checks = [
                channel in self.message_queues,
                channel in self.channel_locks,
                channel in self.channel_metrics,
                channel in self.message_handlers
            ]

            queue = self.message_queues.get(channel)
            if queue and queue.maxsize != self.max_messages:
                checks.append(False)

            return all(checks)

        except Exception as e:
            self.logger.error(f"Channel verification failed: {str(e)}")
            return False

    def cleanup_channels(self) -> None:
        """
        Clean up channel resources, releasing locks and clearing metrics.
        """
        try:
            for channel in list(self.channel_locks.keys()):
                # Release any held locks
                self.release_channel_lock(channel)

                # Clear the queues
                queue = self.message_queues.get(channel)
                if queue:
                    while not queue.empty():
                        queue.get()

                # Reset metrics
                self.channel_metrics[channel] = ChannelMetrics(
                    channel_name=channel.value,
                    created_at=datetime.now()
                )

            # Optional: Clear collections if a complete reset is desired
            # self.message_queues.clear()
            # self.channel_locks.clear()
            # self.message_handlers.clear()

            self.logger.info("Channel cleanup completed successfully")

        except Exception as e:
            self.logger.error(f"Error during channel cleanup: {str(e)}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the Channel Manager.

        Returns:
            Dict[str, Any]: Status information for all channels
        """
        status = {}
        for channel in ChannelType:
            status[channel.value] = {
                'queue_size': self.message_queues.get(channel, Queue()).qsize(),
                'metrics': {
                    'message_count': self.channel_metrics.get(channel, ChannelMetrics()).message_count,
                    'created_at': self.channel_metrics.get(channel, ChannelMetrics()).created_at.isoformat()
                },
                'handlers': list(self.message_handlers.get(channel, {}).keys())
            }
        return status