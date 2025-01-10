# backend/core/messaging/broker.py

import time
import uuid
import logging
import threading
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from backend.core.messaging.types import (
    ProcessingMessage,
    ModuleIdentifier,
    MessageType,
    ProcessingStatus,
    ComponentType
)

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionContext:
    """Enhanced subscription tracking"""
    component_id: ModuleIdentifier
    callbacks: List[Callable] = field(default_factory=list)
    message_patterns: Set[str] = field(default_factory=set)
    last_activity: datetime = field(default_factory=datetime.now)
    status: str = "active"
    message_count: int = 0
    error_count: int = 0


class MessageBroker:
    """Enhanced message broker for pipeline communication"""

    def __init__(self, max_workers: int = 4):
        self.logger = logging.getLogger(__name__)

        # Subscription management
        self.subscriptions: Dict[str, SubscriptionContext] = {}
        self.pattern_subscriptions: Dict[str, List[str]] = {}

        # Message management
        self.active_messages: Dict[str, ProcessingMessage] = {}
        self.message_history: Dict[str, List[ProcessingMessage]] = {}

        # Thread management
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.RLock()

        # Add debug counter
        self._lock_acquire_count = 0

    def _acquire_lock(self):
        """Debug wrapper for lock acquisition"""
        self._lock_acquire_count += 1
        logger.info(f"[DEBUG] Attempting to acquire lock (count: {self._lock_acquire_count})")
        acquired = self._lock.acquire()
        logger.info(f"[DEBUG] Lock acquired: {acquired}")
        return acquired

    def register_component(self, component: ModuleIdentifier) -> None:
        """Register system component"""

        logger.info(f"[DEBUG] Starting component registration: {component}")
        try:
            component_tag = component.get_tag()
            logger.info(f"[DEBUG] Generated component tag: {component_tag}")

            # create subscription context without lock first
            context = SubscriptionContext(component_id=component)

            # Only lock for the actual dictionary update
            with self._lock:
                self.subscriptions[component_tag] = context
                logger.info(f"[DEBUG] Registered component successfully: {component_tag}")

        except Exception as e:
            logger.error(f"[DEBUG] Registration failed: {str(e)}")
            raise

    def register_handler(self, handler_name: str, callback: Callable) -> None:
        """Register a handler with the message broker"""
        try:
            # Create handler module identifier
            handler_id = ModuleIdentifier(
                component_name=handler_name,
                component_type=ComponentType.HANDLER,
                method_name="handle_message",
                instance_id=str(uuid.uuid4())
            )

            # First register as a component
            self.register_component(handler_id)

            # Subscribe to patterns
            patterns = [
                # Basic handler patterns
                f"{handler_id.get_tag()}.#",  # All messages to this handler
                f"*.{handler_name}.#",  # All messages for this handler type

                # Channel-specific patterns
                f"*.{ComponentType.MANAGER.value}.{handler_name}.*",
                f"*.{ComponentType.HANDLER.value}.{handler_name}.*"
            ]

            for pattern in patterns:
                self.subscribe(
                    component=handler_id,
                    pattern=pattern,
                    callback=callback,
                    timeout=10.0
                )

            logger.info(f"Handler {handler_name} registered successfully")
            return handler_id

        except Exception as e:
            logger.error(f"Failed to register handler {handler_name}: {str(e)}")
            raise

    def subscribe(self, component: ModuleIdentifier, pattern: str,
                  callback: Callable, timeout: float = 5.0) -> None:
        """
        Subscribe to message pattern with improved error handling and timeout

        Args:
            component: Module identifier
            pattern: Message pattern to subscribe to
            callback: Callback function for message handling
            timeout: Maximum time to wait for subscription (in seconds)
        """
        start_time = time.time()
        logger.info(f"[DEBUG] Starting subscription process for pattern: {pattern}")

        try:
            component_tag = component.get_tag()

            # Register component if needed (this has its own lock handling)
            if component_tag not in self.subscriptions:
                self.register_component(component)

            with self._lock:
                subscription = self.subscriptions[component_tag]
                subscription.callbacks.append(callback)
                subscription.message_patterns.add(pattern)

                # Update pattern index
                if pattern not in self.pattern_subscriptions:
                    self.pattern_subscriptions[pattern] = []
                self.pattern_subscriptions[pattern].append(component_tag)

                logger.info(f"[DEBUG] Successfully subscribed: {component_tag} -> {pattern}")

            elapsed = time.time() - start_time
            logger.info(f"[DEBUG] Subscription completed in {elapsed:.2f} seconds")

        except Exception as e:
            logger.error(f"[DEBUG] Subscription failed: {str(e)}")
            raise

    def publish(self, message: ProcessingMessage) -> None:
        """Publish message to subscribers"""
        try:
            # Store message
            self.active_messages[message.message_id] = message

            # Get routing key
            routing_key = message.get_routing_key()
            logger.info(f"Publishing message with routing key: {routing_key}")
            logger.info(f"Available patterns: {list(self.pattern_subscriptions.keys())}")
            logger.info(f"Looking for matching patterns...")

            # Find matching subscribers
            matching_patterns = self._find_matching_patterns(routing_key)
            logger.info(f"Found matching patterns: {matching_patterns}")
            subscribers = set()
            for pattern in matching_patterns:
                subscribers.update(self.pattern_subscriptions.get(pattern, []))

            # Deliver to subscribers
            for subscriber in subscribers:
                subscription = self.subscriptions.get(subscriber)
                if subscription and subscription.status == "active":
                    for callback in subscription.callbacks:
                        self._safe_deliver(callback, message)

                    # Update metrics
                    subscription.message_count += 1
                    subscription.last_activity = datetime.now()

            # Update history
            if message.metadata.pipeline_id:
                if message.metadata.pipeline_id not in self.message_history:
                    self.message_history[message.metadata.pipeline_id] = []
                self.message_history[message.metadata.pipeline_id].append(message)

        except Exception as e:
            self.logger.error(f"Error publishing message: {str(e)}")
            raise

    def _safe_deliver(self, callback: Callable, message: ProcessingMessage) -> None:
        """Safely deliver message to subscriber"""
        try:
            self.thread_pool.submit(callback, message)
        except Exception as e:
            self.logger.error(f"Error delivering message: {str(e)}")
            # Update error metrics
            if message.source_identifier:
                subscription = self.subscriptions.get(message.source_identifier.get_tag())
                if subscription:
                    subscription.error_count += 1

    def _find_matching_patterns(self, routing_key: str) -> List[str]:
        """Find patterns matching routing key"""
        return [
            pattern for pattern in self.pattern_subscriptions
            if self._matches_pattern(routing_key, pattern)
        ]

    def _matches_pattern(self, routing_key: str, pattern: str) -> bool:
        """Check if routing key matches pattern"""
        if pattern == "#":  # Match all
            return True

        pattern_parts = pattern.split(".")
        key_parts = routing_key.split(".")

        if len(pattern_parts) != len(key_parts):
            return False

        # Allow partial matches if pattern has fewer parts
        if len(pattern_parts) <= len(key_parts):
            # Only compare the rightmost parts if pattern is shorter
            key_parts = key_parts[-len(pattern_parts):]

            return all(
                p == "#" or p == "*" or p == k
                for p, k in zip(pattern_parts, key_parts)
            )

        return False

    def get_component_status(self, component: ModuleIdentifier) -> Optional[Dict[str, Any]]:
        """Get component subscription status"""
        subscription = self.subscriptions.get(component.get_tag())
        if not subscription:
            return None

        return {
            'status': subscription.status,
            'message_count': subscription.message_count,
            'error_count': subscription.error_count,
            'last_activity': subscription.last_activity.isoformat(),
            'patterns': list(subscription.message_patterns)
        }

    def diagnose_message_broker(self):
        """Diagnose message broker state"""
        logger.info("Message Broker Diagnostic Information:")
        logger.info(f"Active Subscriptions: {len(self.subscriptions)}")
        logger.info(f"Pattern Subscriptions: {self.pattern_subscriptions}")

        for component_tag, subscription in self.subscriptions.items():
            logger.info(f"Component {component_tag}:")
            logger.info(f"  Status: {subscription.status}")
            logger.info(f"  Patterns: {subscription.message_patterns}")
            logger.info(f"  Callback Count: {len(subscription.callbacks)}")

    def cleanup_old_messages(self, max_age: timedelta = timedelta(hours=24)) -> None:
        """Clean up old messages"""
        current_time = datetime.now()
        with self._lock:
            for msg_id in list(self.active_messages.keys()):
                message = self.active_messages[msg_id]
                if current_time - message.metadata.timestamp > max_age:
                    del self.active_messages[msg_id]

    def __del__(self):
        """Cleanup resources"""
        self.thread_pool.shutdown(wait=True)
