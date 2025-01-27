# backend/core/messaging/broker.py

import asyncio
import logging
<<<<<<< HEAD
from typing import Dict, List, Any, Optional, Callable, Union, Set, Coroutine
from datetime import datetime, timedelta
from dataclasses import dataclass, field
=======
from typing import Dict, List, Any, Optional, Callable, Union, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
import uuid

from .event_types import (
    ProcessingMessage,
    MessageType,
    ProcessingStage,
    ProcessingStatus,
<<<<<<< HEAD
    MessageMetadata,
    ModuleIdentifier,
    ComponentType
)


=======
    MessageMetadata
)

>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
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


<<<<<<< HEAD
@dataclass
class SubscriptionInfo:
    """Enhanced subscription information"""
    component_id: str
    module_identifier: ModuleIdentifier
    patterns: Set[str]
    callback: Union[Callable, Coroutine]
    created_at: datetime = field(default_factory=datetime.now)
    last_message_at: datetime = field(default_factory=datetime.now)
    messages_processed: int = 0
    is_active: bool = True


class MessageBroker:
    """Enhanced message broker with department-based routing"""
=======
class MessageBroker:
    """Enhanced message broker with comprehensive message handling"""
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce

    def __init__(self):
        # Core storage
        self.subscriptions: Dict[str, List[SubscriptionInfo]] = {}
        self.active_messages: Dict[str, ProcessingMessage] = {}
        self.message_history: Dict[str, List[ProcessingMessage]] = {}

<<<<<<< HEAD
        # Department routing
        self.department_routes: Dict[str, Set[str]] = {}  # Department to component mapping
        self.processing_chains: Dict[str, Dict[str, ModuleIdentifier]] = {}  # Chain tracking

=======
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
        # Performance tracking
        self.stats = {
            'messages_processed': 0,
            'messages_failed': 0,
<<<<<<< HEAD
            'active_subscriptions': 0,
            'departments_active': 0
=======
            'active_subscriptions': 0
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
        }

        # Async support
        self._lock = asyncio.Lock()
        self._message_queues: Dict[str, asyncio.Queue] = {}
        self._is_running = True

        # State management
        self._cleanup_task = None
        self._start_background_tasks()

<<<<<<< HEAD
    async def subscribe(
            self,
            module_identifier: ModuleIdentifier,
            message_patterns: Union[str, List[str]],
            callback: Union[Callable, Coroutine],
    ) -> None:
        """Enhanced subscribe with module identification"""
        async with self._lock:
            try:
                # Normalize patterns
=======
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
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
                patterns = [message_patterns] if isinstance(message_patterns, str) else message_patterns

                # Create subscription info
                sub_info = SubscriptionInfo(
<<<<<<< HEAD
                    component_id=str(uuid.uuid4()),
                    module_identifier=module_identifier,
=======
                    component_id=component_id,
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
                    patterns=set(patterns),
                    callback=callback
                )

                # Store subscription
                for pattern in patterns:
                    if pattern not in self.subscriptions:
                        self.subscriptions[pattern] = []
                    self.subscriptions[pattern].append(sub_info)

<<<<<<< HEAD
                # Update department routes
                if module_identifier.department:
                    dept_routes = self.department_routes.setdefault(
                        module_identifier.department, set()
                    )
                    dept_routes.add(module_identifier.get_routing_key())

                # Create message queue if needed
                queue_key = module_identifier.get_routing_key()
                if queue_key not in self._message_queues:
                    self._message_queues[queue_key] = asyncio.Queue()

                self.stats['active_subscriptions'] += 1
                logger.info(
                    f"Component {module_identifier.component_name} "
                    f"subscribed to patterns: {patterns}"
                )
=======
                # Create message queue if needed
                if component_id not in self._message_queues:
                    self._message_queues[component_id] = asyncio.Queue()

                self.stats['active_subscriptions'] += 1
                logger.info(f"Component {component_id} subscribed to patterns: {patterns}")
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce

            except Exception as e:
                logger.error(f"Subscription failed: {str(e)}")
                raise

    async def publish(self, message: ProcessingMessage) -> None:
<<<<<<< HEAD
        """Enhanced publish with improved routing"""
=======
        """Publish a message to subscribers"""
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
        try:
            # Store active message
            self.active_messages[message.id] = message

            # Track in history
            if message.metadata.correlation_id:
                history = self.message_history.setdefault(
                    message.metadata.correlation_id, []
                )
                history.append(message)

<<<<<<< HEAD
            # Handle broadcast messages
            if message.metadata.is_broadcast:
                await self._handle_broadcast(message)
                return

=======
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
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

<<<<<<< HEAD
    async def _handle_broadcast(self, message: ProcessingMessage) -> None:
        """Handle broadcast messages to all relevant components"""
        try:
            department = message.metadata.department
            if department and department in self.department_routes:
                for route in self.department_routes[department]:
                    await self._route_message(message, route)
            else:
                # Broadcast to all subscribers
                for sub_list in self.subscriptions.values():
                    for sub in sub_list:
                        if sub.is_active:
                            await self._deliver_message(sub, message)

        except Exception as e:
            logger.error(f"Broadcast handling failed: {str(e)}")
            raise

    def _find_matching_subscriptions(
            self,
            message: ProcessingMessage
    ) -> List[SubscriptionInfo]:
        """Enhanced subscription matching with module identification"""
        matched = []

        # Get routing key from message
        routing_key = message.target_identifier.get_routing_key() if message.target_identifier else None
        if not routing_key:
            # Fallback to metadata-based routing
            routing_key = f"{message.metadata.source_component}.{message.message_type.value}"

        # Check all patterns
        for pattern, subs in self.subscriptions.items():
            for sub in subs:
                if sub.is_active and (
                        sub.module_identifier.matches_pattern(pattern) or
                        self._matches_pattern(routing_key, pattern)
                ):
                    matched.append(sub)

        return matched

    async def register_processing_chain(
            self,
            chain_id: str,
            manager: ModuleIdentifier,
            handler: ModuleIdentifier,
            processor: ModuleIdentifier
    ) -> None:
        """Register a processing chain for routing"""
        self.processing_chains[chain_id] = {
            'manager': manager,
            'handler': handler,
            'processor': processor
        }

        # Set up department routes
        dept = manager.department
        if dept:
            routes = self.department_routes.setdefault(dept, set())
            routes.update([
                manager.get_routing_key(),
                handler.get_routing_key(),
                processor.get_routing_key()
            ])

    def _start_background_tasks(self):
        """Initialize background tasks with more robust management"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self._cleanup_task = loop.create_task(self._manage_periodic_cleanup())

    async def _manage_periodic_cleanup(self):
        """
        Managed periodic cleanup for message broker with enhanced error handling.

        Provides a robust wrapper around cleanup methods with:
        - Continuous running while _is_running is True
        - Exponential backoff for error recovery
        - Logging of cleanup attempts and failures
        """
        base_interval = 300  # 5 minutes
        max_interval = base_interval * 10
        current_interval = base_interval

        while self._is_running:
            try:
                # Perform individual cleanup tasks
                await self._cleanup_expired_messages()
                await self._cleanup_inactive_subscriptions()

                # Reset interval on successful cleanup
                current_interval = base_interval
                await asyncio.sleep(current_interval)

            except asyncio.CancelledError:
                # Handle task cancellation gracefully
                logger.info("Periodic message broker cleanup task was cancelled")
                break

            except Exception as e:
                # Log error and implement exponential backoff
                logger.error(f"Cleanup error: {str(e)}")

                # Exponential backoff with jitter
                current_interval = min(current_interval * 2, max_interval)
                jitter = current_interval * 0.1  # Add 10% jitter
                await asyncio.sleep(current_interval + random.uniform(-jitter, jitter))

    async def cleanup(self) -> None:
        """
        Enhanced asynchronous cleanup of message broker resources.
        Ensures orderly shutdown of all broker components.
        """
        try:
            logger.info("Starting message broker cleanup")

            # Stop background processing
            self._is_running = False

            # Cancel cleanup task if running
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Process any remaining messages
            await self._process_remaining_messages()

            # Clear all registrations and storage
            await self._clear_subscriptions()
            self._clear_storage()

            logger.info("Message broker cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during message broker cleanup: {str(e)}")
            raise

=======
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
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

<<<<<<< HEAD
=======
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

>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
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

<<<<<<< HEAD
=======
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

>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
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

<<<<<<< HEAD
=======
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

>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
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
<<<<<<< HEAD
        } if subscriptions else None

    def sync_cleanup(self) -> None:
        """
        Synchronous wrapper for cleanup method.
        Ensures cleanup can be called in both async and sync contexts.
        Handles event loop management internally.
        """
        try:
            # Try to get the current event loop
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # If no loop is running, create a new one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Execute cleanup based on loop state
            if loop.is_running():
                loop.create_task(self.cleanup())
                # Give the task a chance to run
                loop.run_until_complete(asyncio.sleep(0))
            else:
                loop.run_until_complete(self.cleanup())

            logger.info("Synchronous message broker cleanup completed successfully")

        except Exception as e:
            logger.error(f"Error during synchronous message broker cleanup: {str(e)}")
            raise
        finally:
            # Ensure background tasks are properly handled
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()

    async def _process_remaining_messages(self) -> None:
        """Process any messages remaining in queues during cleanup."""
        try:
            # Process any remaining messages with a timeout
            remaining_messages = []
            for queue in self._message_queues.values():
                while not queue.empty():
                    try:
                        message = queue.get_nowait()
                        remaining_messages.append(message)
                    except asyncio.QueueEmpty:
                        break

            if remaining_messages:
                logger.info(f"Processing {len(remaining_messages)} remaining messages")
                await asyncio.gather(*[self._process_message(msg) for msg in remaining_messages])

        except Exception as e:
            logger.error(f"Error processing remaining messages: {str(e)}")

    async def _clear_subscriptions(self) -> None:
        """Clear all subscriptions and routes."""
        try:
            self.subscriptions.clear()
            self.department_routes.clear()
            self.processing_chains.clear()
            self.stats['active_subscriptions'] = 0
            self.stats['departments_active'] = 0

            # Clear message queues
            for queue in self._message_queues.values():
                while not queue.empty():
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
            self._message_queues.clear()

        except Exception as e:
            logger.error(f"Error clearing subscriptions: {str(e)}")

    async def unsubscribe(self, module_identifier: ModuleIdentifier, pattern: str) -> None:
        """
        Unsubscribe a module from a specific message pattern.

        Args:
            module_identifier: The identifier of the module unsubscribing
            pattern: The message pattern to unsubscribe from
        """
        async with self._lock:
            try:
                # Check if pattern exists in subscriptions
                if pattern not in self.subscriptions:
                    logger.warning(f"Pattern {pattern} not found in subscriptions")
                    return

                # Filter out the specific module's subscription for this pattern
                self.subscriptions[pattern] = [
                    sub for sub in self.subscriptions[pattern]
                    if sub.module_identifier.get_routing_key() != module_identifier.get_routing_key()
                ]

                # Remove pattern if no subscriptions remain
                if not self.subscriptions[pattern]:
                    del self.subscriptions[pattern]

                # Update department routes if applicable
                if module_identifier.department:
                    dept_routes = self.department_routes.get(module_identifier.department, set())
                    dept_routes.discard(module_identifier.get_routing_key())
                    if not dept_routes:
                        del self.department_routes[module_identifier.department]

                # Decrement active subscriptions
                self.stats['active_subscriptions'] = max(0, self.stats['active_subscriptions'] - 1)

                logger.info(
                    f"Module {module_identifier.component_name} "
                    f"unsubscribed from pattern: {pattern}"
                )

            except Exception as e:
                logger.error(f"Unsubscription failed: {str(e)}")
                raise

    def _clear_storage(self) -> None:
        """Clear all internal storage structures."""
        try:
            self.active_messages.clear()
            self.message_history.clear()
            self.stats['messages_processed'] = 0
            self.stats['messages_failed'] = 0

        except Exception as e:
            logger.error(f"Error clearing storage: {str(e)}")
=======
        } if subscriptions else None
>>>>>>> 7d1206c3f3fa3bbf7c91fb7ae42a8171039851ce
