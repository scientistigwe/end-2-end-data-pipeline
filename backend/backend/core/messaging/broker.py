# backend/core/messaging/broker.py

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
        self._lock = threading.Lock()

    def register_component(self, component: ModuleIdentifier) -> None:
        """Register system component"""
        with self._lock:
            component_tag = component.get_tag()
            if component_tag not in self.subscriptions:
                self.subscriptions[component_tag] = SubscriptionContext(
                    component_id=component
                )
                self.logger.info(f"Registered component: {component_tag}")

    def subscribe(self, component: ModuleIdentifier, pattern: str,
                  callback: Callable) -> None:
        """Subscribe to message pattern"""
        with self._lock:
            component_tag = component.get_tag()

            # Ensure component is registered
            if component_tag not in self.subscriptions:
                self.register_component(component)

            # Add subscription
            subscription = self.subscriptions[component_tag]
            subscription.callbacks.append(callback)
            subscription.message_patterns.add(pattern)

            # Update pattern index
            if pattern not in self.pattern_subscriptions:
                self.pattern_subscriptions[pattern] = []
            self.pattern_subscriptions[pattern].append(component_tag)

            self.logger.info(f"Added subscription: {component_tag} -> {pattern}")

    def publish(self, message: ProcessingMessage) -> None:
        """Publish message to subscribers"""
        try:
            # Store message
            self.active_messages[message.message_id] = message

            # Get routing key
            routing_key = message.get_routing_key()

            # Find matching subscribers
            matching_patterns = self._find_matching_patterns(routing_key)
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

        return all(
            p == "#" or p == "*" or p == k
            for p, k in zip(pattern_parts, key_parts)
        )

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
