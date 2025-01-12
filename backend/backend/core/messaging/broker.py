# backend/core/messaging/broker.py

import asyncio
import uuid
import logging
import threading
from typing import Dict, List, Any, Optional, Callable, Set, Union, Coroutine
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, Future

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
    """
    Enhanced subscription tracking with advanced features
    """
    component_id: ModuleIdentifier
    callbacks: List[Union[Callable, Coroutine]] = field(default_factory=list)
    message_patterns: Set[str] = field(default_factory=set)
    last_activity: datetime = field(default_factory=datetime.now)
    status: str = "active"
    message_count: int = 0
    error_count: int = 0
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class MessageRoutingConfig:
    """
    Configuration for message routing and handling
    """
    default_timeout: float = 10.0
    max_queue_size: int = 1000
    message_expiry: timedelta = timedelta(hours=24)
    retry_backoff_factor: float = 1.5


class MessageBroker:
    """
    Advanced message broker with improved routing, error handling, and async support
    """

    def __init__(
            self,
            max_workers: int = 8,
            config: Optional[MessageRoutingConfig] = None
    ):
        """
        Initialize an enhanced message broker

        Args:
            max_workers (int, optional): Maximum number of worker threads. Defaults to 8.
            config (Optional[MessageRoutingConfig], optional): Routing configuration
        """
        # Configuration
        self.config = config or MessageRoutingConfig()

        # Logging
        self.logger = logging.getLogger(__name__)

        # Subscription management
        self.subscriptions: Dict[str, SubscriptionContext] = {}
        self.pattern_subscriptions: Dict[str, List[str]] = {}

        # Message management
        self.active_messages: Dict[str, ProcessingMessage] = {}
        self.message_history: Dict[str, List[ProcessingMessage]] = {}
        self.message_queues: Dict[str, asyncio.Queue] = {}

        # Concurrency management
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self._async_lock = asyncio.Lock()
        self._sync_lock = threading.Lock()

        # Error tracking
        self.error_tracking: Dict[str, List[Dict[str, Any]]] = {}

    async def register_component(
            self,
            component: ModuleIdentifier,
            default_callback: Optional[Union[Callable, Coroutine]] = None
    ) -> None:
        """
        Asynchronously register a system component with optional default callback

        Args:
            component (ModuleIdentifier): Component to register
            default_callback (Optional[Union[Callable, Coroutine]], optional): Default message handler
        """
        async with self._async_lock:
            try:
                component_tag = component.get_tag()

                # Create subscription context
                context = SubscriptionContext(
                    component_id=component,
                    callbacks=[default_callback] if default_callback else []
                )

                # Store subscription
                self.subscriptions[component_tag] = context

                # Create message queue for component
                self.message_queues[component_tag] = asyncio.Queue(
                    maxsize=self.config.max_queue_size
                )

                self.logger.info(f"Component registered: {component_tag}")

            except Exception as e:
                self.logger.error(f"Component registration failed: {str(e)}")
                raise

    async def subscribe(
            self,
            component: ModuleIdentifier,
            pattern: str,
            callback: Optional[Union[Callable, Coroutine]] = None,
            timeout: Optional[float] = None
    ) -> None:
        """
        Subscribe to a message pattern with advanced features

        Args:
            component (ModuleIdentifier): Subscribing component
            pattern (str): Message pattern to subscribe to
            callback (Optional[Union[Callable, Coroutine]], optional): Message handler
            timeout (Optional[float], optional): Subscription timeout
        """
        async with self._async_lock:
            try:
                component_tag = component.get_tag()

                # Register component if not exists
                if component_tag not in self.subscriptions:
                    await self.register_component(component)

                # Get or create subscription context
                subscription = self.subscriptions[component_tag]

                # Add callback if provided
                if callback and callback not in subscription.callbacks:
                    subscription.callbacks.append(callback)

                # Update message patterns
                subscription.message_patterns.add(pattern)

                # Update pattern subscriptions
                if pattern not in self.pattern_subscriptions:
                    self.pattern_subscriptions[pattern] = []
                self.pattern_subscriptions[pattern].append(component_tag)

                self.logger.info(f"Subscribed: {component_tag} -> {pattern}")

            except Exception as e:
                self.logger.error(f"Subscription failed: {str(e)}")
                raise

    async def publish(
            self,
            message: ProcessingMessage,
            retry: bool = True
    ) -> List[Future]:
        """
        Publish a message with advanced routing and error handling

        Args:
            message (ProcessingMessage): Message to publish
            retry (bool, optional): Enable retry mechanism. Defaults to True.

        Returns:
            List[Future]: List of futures for message delivery
        """
        delivery_futures: List[Future] = []

        try:
            # Store message
            self.active_messages[message.message_id] = message

            # Get routing key
            routing_key = message.get_routing_key()

            # Find matching subscribers
            matching_patterns = self._find_matching_patterns(routing_key)
            subscribers = set()
            for pattern in matching_patterns:
                subscribers.update(
                    self.pattern_subscriptions.get(pattern, [])
                )

            # Deliver to subscribers
            for subscriber in subscribers:
                subscription = self.subscriptions.get(subscriber)
                if not subscription or subscription.status != "active":
                    continue

                for callback in subscription.callbacks:
                    future = self._safe_deliver(callback, message, retry)
                    delivery_futures.append(future)

                # Update subscription metrics
                subscription.message_count += 1
                subscription.last_activity = datetime.now()

            # Update message history
            if message.metadata.pipeline_id:
                if message.metadata.pipeline_id not in self.message_history:
                    self.message_history[message.metadata.pipeline_id] = []
                self.message_history[message.metadata.pipeline_id].append(message)

            return delivery_futures

        except Exception as e:
            self.logger.error(f"Message publishing failed: {str(e)}")
            raise

    def _safe_deliver(
            self,
            callback: Union[Callable, Coroutine],
            message: ProcessingMessage,
            retry: bool = True
    ) -> Future:
        """
        Safely deliver a message with optional retry mechanism

        Args:
            callback (Union[Callable, Coroutine]): Message handler
            message (ProcessingMessage): Message to deliver
            retry (bool, optional): Enable retry mechanism. Defaults to True.

        Returns:
            Future: Future representing message delivery
        """

        def execute_callback():
            try:
                # Execute sync or async callback
                if asyncio.iscoroutinefunction(callback):
                    # For async functions, run in event loop
                    asyncio.run(callback(message))
                else:
                    # For sync functions, call directly
                    callback(message)
                return True
            except Exception as e:
                # Log and potentially retry
                self.logger.error(f"Message delivery failed: {str(e)}")

                # Track error
                if message.source_identifier:
                    error_key = message.source_identifier.get_tag()
                    if error_key not in self.error_tracking:
                        self.error_tracking[error_key] = []

                    self.error_tracking[error_key].append({
                        'message_id': message.message_id,
                        'error': str(e),
                        'timestamp': datetime.now()
                    })

                return False

        # Submit to thread pool
        return self.thread_pool.submit(execute_callback)

    def _find_matching_patterns(self, routing_key: str) -> List[str]:
        """
        Find all matching patterns for a routing key

        Args:
            routing_key (str): Message routing key

        Returns:
            List[str]: Matching message patterns
        """
        return [
            pattern for pattern in self.pattern_subscriptions
            if self._matches_pattern(routing_key, pattern)
        ]

    def _matches_pattern(self, routing_key: str, pattern: str) -> bool:
        """
        Advanced pattern matching with more flexible rules

        Args:
            routing_key (str): Message routing key
            pattern (str): Subscription pattern

        Returns:
            bool: Whether the routing key matches the pattern
        """
        # Wildcard matching
        if pattern == "#":  # Match all
            return True

        pattern_parts = pattern.split(".")
        key_parts = routing_key.split(".")

        # Exact match
        if len(pattern_parts) == len(key_parts):
            return all(
                p == "#" or p == "*" or p == k
                for p, k in zip(pattern_parts, key_parts)
            )

        # Partial match with wildcard support
        if len(pattern_parts) <= len(key_parts):
            # Compare last N parts
            key_parts = key_parts[-len(pattern_parts):]

            return all(
                p == "#" or p == "*" or p == k
                for p, k in zip(pattern_parts, key_parts)
            )

        return False

    async def cleanup(self) -> None:
        """
        Comprehensive cleanup of broker resources
        """
        try:
            # Cleanup thread pool
            self.thread_pool.shutdown(wait=True)

            # Clear active messages older than configured expiry
            current_time = datetime.now()
            expired_messages = [
                msg_id for msg_id, msg in self.active_messages.items()
                if current_time - msg.metadata.timestamp > self.config.message_expiry
            ]
            for msg_id in expired_messages:
                del self.active_messages[msg_id]

            # Clear message history
            self.message_history.clear()

            # Reset subscriptions
            self.subscriptions.clear()
            self.pattern_subscriptions.clear()
            self.message_queues.clear()

            self.logger.info("Message Broker cleaned up successfully")

        except Exception as e:
            self.logger.error(f"Error during Message Broker cleanup: {str(e)}")

    def get_component_status(self, component: ModuleIdentifier) -> Dict[str, Any]:
        """
        Get comprehensive status of a registered component

        Args:
            component (ModuleIdentifier): Component to check

        Returns:
            Dict[str, Any]: Detailed component status
        """
        component_tag = component.get_tag()
        subscription = self.subscriptions.get(component_tag)

        if not subscription:
            return {
                'status': 'not_registered',
                'message_count': 0,
                'error_count': 0
            }

        return {
            'status': subscription.status,
            'message_count': subscription.message_count,
            'error_count': subscription.error_count,
            'last_activity': subscription.last_activity.isoformat(),
            'patterns': list(subscription.message_patterns),
            'recent_errors': self.error_tracking.get(component_tag, [])[:5]
        }

    def diagnose(self) -> Dict[str, Any]:
        """
        Comprehensive system diagnosis

        Returns:
            Dict[str, Any]: Detailed broker diagnostics
        """
        return {
            'active_messages': len(self.active_messages),
            'subscriptions': {
                tag: {
                    'callbacks': len(context.callbacks),
                    'patterns': len(context.message_patterns),
                    'status': context.status
                }
                for tag, context in self.subscriptions.items()
            },
            'pattern_subscriptions': len(self.pattern_subscriptions),
            'message_history_size': sum(
                len(history) for history in self.message_history.values()
            ),
            'error_tracking': {
                tag: len(errors) for tag, errors in self.error_tracking.items()
            }
        }