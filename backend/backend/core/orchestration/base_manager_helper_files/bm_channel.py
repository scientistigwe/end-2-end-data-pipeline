# backend/core/base/base_manager_channel.py

import threading
from queue import Queue
from typing import Dict, Callable, Optional, Any
import logging
import asyncio

from backend.core.messaging.types import MessageType, ProcessingMessage
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
        # Channel-specific queues
        self._message_queues: Dict[str, Queue] = {}

        # Channel metrics tracking
        self._channel_metrics: Dict[str, ChannelMetrics] = {}

        # Channel locks
        self._channel_locks: Dict[str, threading.Lock] = {}

        # Message handlers
        self._handlers: Dict[str, Dict[MessageType, Callable]] = {}

        # Configuration
        self._max_messages = max_messages
        self._lock_timeout = lock_timeout
        self._logger = logger or logging.getLogger(__name__)

        # Initialize channels
        self._initialize_channels()

    def _initialize_channels(self) -> None:
        """
        Initialize all communication channels with default configurations.
        """
        try:
            self._logger.info("Initializing communication channels...")

            for channel in ChannelType:
                # Create message queue
                self._message_queues[channel.value] = Queue(maxsize=self._max_messages)

                # Create channel-specific lock
                self._channel_locks[channel.value] = threading.Lock()

                # Initialize channel metrics
                self._channel_metrics[channel.value] = ChannelMetrics()

                # Initialize handlers dictionary for channel
                self._handlers[channel.value] = {}

            self._logger.info("Channels initialized successfully")

        except Exception as e:
            self._logger.error(f"Channel initialization failed: {str(e)}")
            raise

    def register_handler(
            self,
            channel: ChannelType,
            message_type: MessageType,
            handler: Callable[[ProcessingMessage], Any]
    ) -> None:
        """
        Register a message handler for a specific channel and message type.

        Args:
            channel (ChannelType): Communication channel
            message_type (MessageType): Type of message to handle
            handler (Callable): Handler function for the message
        """
        try:
            self._handlers[channel.value][message_type] = handler
            self._logger.info(f"Handler registered for {channel.value}: {message_type}")
        except Exception as e:
            self._logger.error(f"Error registering handler: {str(e)}")

    def acquire_channel_lock(self, channel: ChannelType) -> bool:
        """
        Attempt to acquire a lock for a specific channel.

        Args:
            channel (ChannelType): Channel to lock

        Returns:
            bool: True if lock acquired, False otherwise
        """
        try:
            lock = self._channel_locks[channel.value]
            acquired = lock.acquire(timeout=self._lock_timeout)

            if acquired:
                self._logger.debug(f"Lock acquired for channel {channel.value}")
                return True

            self._logger.warning(
                f"Failed to acquire lock for channel {channel.value} after {self._lock_timeout}s"
            )
            return False

        except Exception as e:
            self._logger.error(f"Error acquiring channel lock: {str(e)}")
            return False

    def release_channel_lock(self, channel: ChannelType) -> None:
        """
        Release the lock for a specific channel.

        Args:
            channel (ChannelType): Channel to unlock
        """
        try:
            lock = self._channel_locks[channel.value]
            if lock.locked():
                lock.release()
                self._logger.debug(f"Lock released for channel {channel.value}")
        except Exception as e:
            self._logger.error(f"Error releasing channel lock: {str(e)}")

    def enqueue_message(
            self,
            channel: ChannelType,
            message: ProcessingMessage
    ) -> bool:
        """
        Enqueue a message to a specific channel.

        Args:
            channel (ChannelType): Target channel
            message (ProcessingMessage): Message to enqueue

        Returns:
            bool: True if message enqueued successfully, False otherwise
        """
        try:
            queue = self._message_queues[channel.value]
            metrics = self._channel_metrics[channel.value]

            if not queue.full():
                queue.put(message)
                metrics.message_count += 1
                metrics.queue_size = queue.qsize()
                return True

            self._logger.warning(f"Channel {channel.value} queue is full")
            return False

        except Exception as e:
            self._logger.error(f"Error enqueuing message: {str(e)}")
            return False

    def get_channel_metrics(self, channel: ChannelType) -> ChannelMetrics:
        """
        Retrieve metrics for a specific channel.

        Args:
            channel (ChannelType): Channel to retrieve metrics for

        Returns:
            ChannelMetrics: Metrics for the specified channel
        """
        return self._channel_metrics[channel.value]

    def get_message_handler(
            self,
            channel: ChannelType,
            message_type: MessageType
    ) -> Optional[Callable]:
        """
        Retrieve the handler for a specific message type in a channel.

        Args:
            channel (ChannelType): Channel to search
            message_type (MessageType): Message type to find handler for

        Returns:
            Optional[Callable]: Handler function if exists, None otherwise
        """
        return self._handlers[channel.value].get(message_type)

    def verify_channel_setup(self, channel: ChannelType) -> bool:
        """
        Verify the setup of a specific channel.

        Args:
            channel (ChannelType): Channel to verify

        Returns:
            bool: True if channel is properly set up, False otherwise
        """
        try:
            channel_name = channel.value

            checks = [
                channel_name in self._message_queues,
                channel_name in self._channel_locks,
                channel_name in self._channel_metrics,
                channel_name in self._handlers
            ]

            queue = self._message_queues[channel_name]
            if queue.maxsize != self._max_messages:
                checks.append(False)

            return all(checks)

        except Exception as e:
            self._logger.error(f"Channel verification failed: {str(e)}")
            return False

    def cleanup_channels(self) -> None:
        """
        Perform cleanup of all channels.
        Clear queues, reset metrics, and release locks.
        """
        try:
            for channel in ChannelType:
                channel_name = channel.value

                # Clear queue
                queue = self._message_queues[channel_name]
                while not queue.empty():
                    queue.get()

                # Reset metrics
                self._channel_metrics[channel_name] = ChannelMetrics()

                # Release lock if held
                self.release_channel_lock(channel)

            self._logger.info("Channel cleanup completed successfully")

        except Exception as e:
            self._logger.error(f"Error during channel cleanup: {str(e)}")