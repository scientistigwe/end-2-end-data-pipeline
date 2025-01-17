# backend/core/messaging/broker.py

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
import uuid

from .event_types import (
    ProcessingMessage,
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata
)

logger = logging.getLogger(__name__)


@dataclass
class SubscriptionInfo:
    """Information about a component's subscription"""
    component_id: str
    patterns: Set[str]
    callback: Union[Callable, Coroutine]
    created_at: datetime = field(default_factory=datetime.now)
    last_message_at: datetime = field(default_factory=datetime.now)
    messages_processed: int = 0
    is_active: bool = True


class MessageBroker:
    """Enhanced message broker with comprehensive message handling"""

    def __init__(self):
        # Core storage
        self.subscriptions: Dict[str, List[SubscriptionInfo]] = {}
        self.active_messages: Dict[str, ProcessingMessage] = {}
        self.message_history: Dict[str, List[ProcessingMessage]] = {}

        # Performance tracking
        self.stats = {
            'messages_processed': 0,
            'messages_failed': 0,
            'active_subscriptions': 0
        }

        # Async support
        self._lock = asyncio.Lock()
        self._message_queues: Dict[str, asyncio.Queue] = {}
        self._is_running = True

        # State management
        self._cleanup_task = None
        self._start_background_tasks()

    def _start_background_tasks(self):
        """Initialize background tasks"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self._cleanup_task = loop.create_task(self._periodic_cleanup())

    async def subscribe(
            self,
            component_id: str,
            message_patterns: Union[str, List[str]],
            callback: Union[Callable, Coroutine]
    ) -> None:
        """Subscribe to message patterns"""
        async with self._lock:
            try:
                # Normalize patterns to list
                patterns = [message_patterns] if isinstance(message_patterns, str) else message_patterns

                # Create subscription info
                sub_info = SubscriptionInfo(
                    component_id=component_id,
                    patterns=set(patterns),
                    callback=callback
                )

                # Store subscription
                for pattern in patterns:
                    if pattern not in self.subscriptions:
                        self.subscriptions[pattern] = []
                    self.subscriptions[pattern].append(sub_info)

                # Create message queue if needed
                if component_id not in self._message_queues:
                    self._message_queues[component_id] = asyncio.Queue()

                self.stats['active_subscriptions'] += 1
                logger.info(f"Component {component_id} subscribed to patterns: {patterns}")

            except Exception as e:
                logger.error(f"Subscription failed: {str(e)}")
                raise

    async def publish(self, message: ProcessingMessage) -> None:
        """Publish a message to subscribers"""
        try:
            # Store active message
            self.active_messages[message.id] = message

            # Track in history
            if message.metadata.correlation_id:
                history = self.message_history.setdefault(
                    message.metadata.correlation_id, []
                )
                history.append(message)

            # Find matching subscribers
            matched_subscriptions = self._find_matching_subscriptions(message)

            # Deliver to subscribers
            delivery_tasks = []
            for sub_info in matched_subscriptions:
                delivery_tasks.append(
                    self._deliver_message(sub_info, message)
                )

            if delivery_tasks:
                await asyncio.gather(*delivery_tasks)

            self.stats['messages_processed'] += 1

        except Exception as e:
            logger.error(f"Message publishing failed: {str(e)}")
            self.stats['messages_failed'] += 1
            raise

    async def _deliver_message(
            self,
            sub_info: SubscriptionInfo,
            message: ProcessingMessage
    ) -> None:
        """Deliver message to a subscriber"""
        try:
            if asyncio.iscoroutinefunction(sub_info.callback):
                await sub_info.callback(message)
            else:
                sub_info.callback(message)

            # Update subscription stats
            sub_info.messages_processed += 1
            sub_info.last_message_at = datetime.now()

        except Exception as e:
            logger.error(f"Message delivery failed: {str(e)}")
            await self._handle_delivery_error(sub_info, message, e)

    def _find_matching_subscriptions(
            self,
            message: ProcessingMessage
    ) -> List[SubscriptionInfo]:
        """Find subscriptions matching a message"""
        matched = []

        # Create message routing key
        routing_key = f"{message.metadata.source_component}.{message.message_type.value}"

        # Check all patterns
        for pattern, subs in self.subscriptions.items():
            if self._matches_pattern(routing_key, pattern):
                matched.extend([sub for sub in subs if sub.is_active])

        return matched

    def _matches_pattern(self, routing_key: str, pattern: str) -> bool:
        """Check if routing key matches pattern"""
        if pattern == "#":
            return True

        pattern_parts = pattern.split(".")
        key_parts = routing_key.split(".")

        if len(pattern_parts) != len(key_parts):
            return False

        return all(
            p == "#" or p == "*" or p == k
            for p, k in zip(pattern_parts, key_parts)
        )

    async def _handle_delivery_error(
            self,
            sub_info: SubscriptionInfo,
            message: ProcessingMessage,
            error: Exception
    ) -> None:
        """Handle message delivery errors"""
        try:
            # Create error message
            error_message = ProcessingMessage(
                message_type=MessageType.FLOW_ERROR,
                content={
                    'original_message_id': message.id,
                    'error': str(error),
                    'component_id': sub_info.component_id
                },
                metadata=MessageMetadata(
                    correlation_id=message.metadata.correlation_id,
                    source_component="message_broker",
                    target_component="error_handler"
                )
            )

            # Publish error message
            await self.publish(error_message)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _periodic_cleanup(self):
        """Periodic cleanup of expired messages and inactive subscriptions"""
        while self._is_running:
            try:
                await self._cleanup_expired_messages()
                await self._cleanup_inactive_subscriptions()
                await asyncio.sleep(300)  # Run every 5 minutes

            except Exception as e:
                logger.error(f"Cleanup error: {str(e)}")
                await asyncio.sleep(60)

    async def _cleanup_expired_messages(self):
        """Clean up expired messages"""
        current_time = datetime.now()
        message_timeout = timedelta(hours=1)

        expired_messages = [
            msg_id for msg_id, msg in self.active_messages.items()
            if current_time - msg.metadata.timestamp > message_timeout
        ]

        for msg_id in expired_messages:
            del self.active_messages[msg_id]

    async def _cleanup_inactive_subscriptions(self):
        """Clean up inactive subscriptions"""
        current_time = datetime.now()
        inactive_timeout = timedelta(hours=1)

        for pattern in list(self.subscriptions.keys()):
            self.subscriptions[pattern] = [
                sub for sub in self.subscriptions[pattern]
                if sub.is_active and
                   current_time - sub.last_message_at <= inactive_timeout
            ]

            # Remove empty pattern
            if not self.subscriptions[pattern]:
                del self.subscriptions[pattern]

    async def cleanup(self):
        """Clean up broker resources"""
        self._is_running = False

        if self._cleanup_task:
            self._cleanup_task.cancel()

        # Clear all storage
        self.subscriptions.clear()
        self.active_messages.clear()
        self.message_history.clear()
        self._message_queues.clear()

        logger.info("Message Broker cleaned up successfully")

    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics"""
        return {
            'messages_processed': self.stats['messages_processed'],
            'messages_failed': self.stats['messages_failed'],
            'active_subscriptions': self.stats['active_subscriptions'],
            'active_patterns': len(self.subscriptions),
            'active_messages': len(self.active_messages)
        }

    def get_subscription_info(self, component_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a component's subscriptions"""
        subscriptions = []
        for pattern, subs in self.subscriptions.items():
            for sub in subs:
                if sub.component_id == component_id:
                    subscriptions.append({
                        'pattern': pattern,
                        'messages_processed': sub.messages_processed,
                        'last_message_at': sub.last_message_at.isoformat(),
                        'is_active': sub.is_active
                    })

        return {
            'component_id': component_id,
            'subscriptions': subscriptions
        } if subscriptions else None