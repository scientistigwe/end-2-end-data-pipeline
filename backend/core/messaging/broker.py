# backend/core/messaging/broker.py

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Union, Set, Coroutine
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque, defaultdict
import uuid
import random

from .event_types import (
    ProcessingMessage,
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType
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
    def __init__(self):
        # Core storage
        self.subscriptions: Dict[str, List[SubscriptionInfo]] = {}
        self.active_messages: Dict[str, ProcessingMessage] = {}
        self.max_history_per_correlation = 1000
        self.history_cleanup_interval = 3600  # 1 hour
        self.message_history: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=self.max_history_per_correlation)
        )
        self._active_subscriptions: Dict[str, SubscriptionInfo] = {}

        # Department routing
        self.department_routes: Dict[str, Set[str]] = {}  # Department to component mapping
        self.processing_chains: Dict[str, Dict[str, ModuleIdentifier]] = {}  # Chain tracking

        # Performance tracking
        self.stats = {
            'messages_processed': 0,
            'messages_failed': 0,
            'active_subscriptions': 0,
            'departments_active': 0
        }

        # Connection state
        self._connection_state = {
            "is_connected": False,
            "last_ping": None,
            "reconnect_attempts": 0
        }

        # Async support
        self._lock = asyncio.Lock()
        self._message_queues: Dict[str, asyncio.Queue] = {}
        self._is_running = True

        # State management
        self._cleanup_task = None
        self._start_background_tasks()

    async def subscribe(
            self,
            module_identifier: Union[str, ModuleIdentifier],
            message_patterns: Union[str, List[str]],
            callback: Union[Callable, Coroutine]
    ) -> None:
        """
        Subscribe to message patterns with automatic health monitoring.
        """
        async with self._lock:
            try:
                # Normalize patterns
                patterns = [message_patterns] if isinstance(message_patterns, str) else message_patterns

                # Generate subscription key
                sub_key = f"{module_identifier}:{','.join(patterns)}"

                # Check for existing subscription
                if sub_key in self._active_subscriptions:
                    logger.warning(f"Subscription already exists for {sub_key}")
                    return

                # Create subscription info
                sub_info = SubscriptionInfo(
                    component_id=str(uuid.uuid4()),
                    module_identifier=module_identifier,
                    patterns=set(patterns),
                    callback=callback,
                    created_at=datetime.now(),
                    last_message_at=datetime.now()
                )

                # Store in both dictionaries
                self._active_subscriptions[sub_key] = sub_info
                for pattern in patterns:
                    if pattern not in self.subscriptions:
                        self.subscriptions[pattern] = []
                    self.subscriptions[pattern].append(sub_info)

                # Update department routes if applicable
                if isinstance(module_identifier, ModuleIdentifier) and module_identifier.department:
                    dept_routes = self.department_routes.setdefault(
                        module_identifier.department, set()
                    )
                    dept_routes.add(module_identifier.get_routing_key())

                # Update stats
                self.stats['active_subscriptions'] += 1

                # Create monitoring task
                monitor_task = asyncio.create_task(
                    self._monitor_subscription_health(sub_key, sub_info)
                )

                logger.info(
                    f"Component {getattr(module_identifier, 'component_name', module_identifier)} "
                    f"subscribed to patterns: {patterns}"
                )

            except Exception as e:
                logger.error(f"Subscription failed: {str(e)}")
                raise

    async def unsubscribe(
            self,
            module_identifier: ModuleIdentifier,
            pattern: str
    ) -> None:
        """
        Unsubscribe from message patterns.
        """
        async with self._lock:
            try:
                # Remove from active subscriptions
                sub_key = f"{module_identifier}:{pattern}"
                if sub_key in self._active_subscriptions:
                    sub_info = self._active_subscriptions.pop(sub_key)

                    # Remove from subscriptions
                    for p in sub_info.patterns:
                        if p in self.subscriptions:
                            self.subscriptions[p] = [
                                s for s in self.subscriptions[p]
                                if s.component_id != sub_info.component_id
                            ]
                            if not self.subscriptions[p]:
                                del self.subscriptions[p]

                    # Update department routes
                    if module_identifier.department:
                        dept_routes = self.department_routes.get(module_identifier.department, set())
                        dept_routes.discard(module_identifier.get_routing_key())
                        if not dept_routes:
                            self.department_routes.pop(module_identifier.department, None)

                    # Update stats
                    self.stats['active_subscriptions'] = max(0, self.stats['active_subscriptions'] - 1)

                    logger.info(
                        f"Component {module_identifier.component_name} "
                        f"unsubscribed from pattern: {pattern}"
                    )

            except Exception as e:
                logger.error(f"Unsubscription failed: {str(e)}")
                raise

    async def _monitor_subscription_health(
            self,
            sub_key: str,
            subscription: SubscriptionInfo
    ) -> None:
        """
        Monitor subscription health and cleanup if necessary.
        """
        try:
            while self._is_running and subscription.is_active:
                if (datetime.now() - subscription.last_message_at) > timedelta(hours=1):
                    async with self._lock:
                        if sub_key in self._active_subscriptions:
                            await self.unsubscribe(
                                subscription.module_identifier,
                                next(iter(subscription.patterns))
                            )
                            logger.info(f"Cleaned up inactive subscription: {sub_key}")
                            break
                await asyncio.sleep(300)  # Check every 5 minutes
        except Exception as e:
            logger.error(f"Subscription health monitoring failed: {str(e)}")

    async def _cleanup_inactive_subscriptions(self) -> None:
        """
        Cleanup inactive subscriptions periodically.
        """
        try:
            current_time = datetime.now()
            inactive_threshold = timedelta(hours=1)

            async with self._lock:
                inactive_subs = [
                    sub_key for sub_key, sub in self._active_subscriptions.items()
                    if current_time - sub.last_message_at > inactive_threshold
                ]

                for sub_key in inactive_subs:
                    sub_info = self._active_subscriptions[sub_key]
                    await self.unsubscribe(
                        sub_info.module_identifier,
                        next(iter(sub_info.patterns))
                    )

        except Exception as e:
            logger.error(f"Failed to cleanup inactive subscriptions: {str(e)}")

    async def initialize(self) -> None:
        """Initialize the message broker with any startup tasks."""
        try:
            logger.info("Initializing Message Broker")

            # Start background tasks
            self._start_background_tasks()

            # Optional: Add any initial setup tasks
            # For example, registering default system-wide subscriptions
            # or performing initial health checks

            logger.info("Message Broker initialization completed")
        except Exception as e:
            logger.error(f"Message Broker initialization failed: {str(e)}")
            raise

    def initialize_sync(self) -> None:
        """Synchronous wrapper for initialization."""
        try:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.initialize())
        except Exception as e:
            logger.error(f"Synchronous Message Broker initialization failed: {str(e)}")
            raise

    async def _handle_connection_failure(self) -> None:
        """
        Handle connection failures with retry logic.
        """
        self._connection_state["is_connected"] = False
        self._connection_state["reconnect_attempts"] += 1

        try:
            backoff = min(2 ** self._connection_state["reconnect_attempts"], 60)  # Max 60s backoff
            logger.warning(f"Connection lost, attempting reconnect in {backoff}s")

            await asyncio.sleep(backoff)
            await self._attempt_reconnect()

        except Exception as e:
            logger.error(f"Connection recovery failed: {str(e)}")
            if self._connection_state["reconnect_attempts"] >= 5:
                logger.critical("Max reconnection attempts reached")
                await self._handle_fatal_connection_failure()

    async def _attempt_reconnect(self) -> None:
        """
        Attempt to reestablish connection.
        """
        try:
            # Attempt to reestablish connection
            if await self.check_connection_health():
                self._connection_state["is_connected"] = True
                self._connection_state["reconnect_attempts"] = 0
                self._connection_state["last_ping"] = datetime.now()
                logger.info("Connection reestablished successfully")

                # Resubscribe active subscriptions
                await self._resubscribe_active_handlers()
        except Exception as e:
            logger.error(f"Reconnection attempt failed: {str(e)}")
            raise

    async def _resubscribe_active_handlers(self) -> None:
        """
        Resubscribe all active handlers after reconnection.
        """
        async with self._lock:
            for sub_key, subscription in self._active_subscriptions.items():
                try:
                    await self.subscribe(
                        subscription.module_identifier,
                        list(subscription.patterns),
                        subscription.callback
                    )
                except Exception as e:
                    logger.error(f"Failed to resubscribe {sub_key}: {str(e)}")

    async def _handle_fatal_connection_failure(self) -> None:
        """
        Handle fatal connection failures.
        """
        logger.critical("Fatal connection failure occurred")
        try:
            # Notify all active subscribers
            async with self._lock:
                for sub_key, subscription in self._active_subscriptions.items():
                    try:
                        if asyncio.iscoroutinefunction(subscription.callback):
                            await subscription.callback(
                                ProcessingMessage(
                                    message_type=MessageType.GLOBAL_ERROR_NOTIFY,
                                    content={
                                        'error': 'Fatal connection failure',
                                        'timestamp': datetime.now().isoformat()
                                    }
                                )
                            )
                    except Exception as e:
                        logger.error(f"Failed to notify subscriber {sub_key}: {str(e)}")

            # Initiate cleanup
            await self.cleanup()

        except Exception as e:
            logger.error(f"Fatal connection handling failed: {str(e)}")
            raise

    async def publish(self, message: ProcessingMessage) -> None:
        """Enhanced publish with improved routing"""
        try:
            # Store active message
            self.active_messages[message.id] = message

            # Track in history
            if message.metadata.correlation_id:
                history = self.message_history.setdefault(
                    message.metadata.correlation_id, []
                )
                history.append(message)

            # Handle broadcast messages
            if message.metadata.is_broadcast:
                await self._handle_broadcast(message)
                return

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

    async def request_response(
            self,
            message: ProcessingMessage,
            timeout: Optional[int] = 10,
            retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        Send a request and wait for response with retry capability.

        Args:
            message: The message to send
            timeout: Base timeout in seconds for each attempt
            retry_count: Number of retry attempts before giving up

        Returns:
            Dict containing the response content

        Raises:
            TimeoutError: If no response is received within timeout
            Exception: For other errors during request/response cycle
        """
        response_handler_id = None
        response_patterns = None
        handler_identifier = None
        cleanup_required = False

        try:
            # Set up response handling
            response_handler_id = f"temp_response_handler_{message.id}"
            response_event = asyncio.Event()
            response_container = {'response': None, 'error': None}

            # Create handler identifier
            handler_identifier = ModuleIdentifier(
                component_name=response_handler_id,
                component_type=ComponentType.CORE,
                department=message.metadata.department or "core",
                role="response_handler"
            )

            # Set up callback
            async def response_callback(response_message: ProcessingMessage):
                if response_message.metadata.correlation_id == message.metadata.correlation_id:
                    response_container['response'] = response_message.content
                    response_event.set()

            # Subscribe temporary handler
            response_patterns = ['monitoring.response', '*.response']
            await self._setup_temporary_handler(
                handler_identifier,
                response_patterns,
                response_callback
            )
            cleanup_required = True

            # Attempt request with retries
            for attempt in range(retry_count):
                try:
                    response = await self._attempt_request(
                        message,
                        response_event,
                        response_container,
                        timeout,
                        attempt
                    )
                    return response

                except TimeoutError as e:
                    if attempt == retry_count - 1:
                        raise TimeoutError(
                            f"Final retry failed after {retry_count} attempts: {str(e)}"
                        )
                    backoff = self._calculate_backoff(attempt)
                    await self._handle_retry(message, attempt, backoff)

        except Exception as e:
            await self._log_request_error(message, e)
            raise

        finally:
            if cleanup_required:
                await self._cleanup_temporary_handler(
                    handler_identifier,
                    response_patterns,
                    response_handler_id
                )

    async def _setup_temporary_handler(
            self,
            handler_identifier: ModuleIdentifier,
            patterns: List[str],
            callback: Callable
    ) -> None:
        """
        Set up a temporary message handler.

        Args:
            handler_identifier: Identifier for the handler
            patterns: List of message patterns to subscribe to
            callback: Callback function for handling responses
        """
        try:
            await self.subscribe(
                module_identifier=handler_identifier,
                message_patterns=patterns,
                callback=callback
            )
            logger.info(
                f"Temporary handler {handler_identifier.component_name} "
                f"subscribed to patterns: {patterns}"
            )
        except Exception as e:
            logger.error(f"Failed to set up temporary handler: {str(e)}")
            raise

    async def _attempt_request(
            self,
            message: ProcessingMessage,
            response_event: asyncio.Event,
            response_container: Dict[str, Any],
            base_timeout: int,
            attempt: int
    ) -> Dict[str, Any]:
        """
        Attempt a single request-response cycle.

        Args:
            message: Message to send
            response_event: Event to wait for response
            response_container: Container for response data
            base_timeout: Base timeout value
            attempt: Current attempt number

        Returns:
            Dict containing response data

        Raises:
            TimeoutError: If response not received within timeout
        """
        # Log attempt details
        logger.info(
            f"Attempt {attempt + 1}: Sending request: "
            f"ID={message.id}, "
            f"Type={message.message_type}, "
            f"Target={message.metadata.target_component}"
        )

        # Calculate timeout for this attempt
        current_timeout = base_timeout + self._calculate_backoff(attempt)

        # Clear event in case of retry
        response_event.clear()
        response_container['response'] = None

        # Send message
        await self.publish(message)

        try:
            # Wait for response
            await asyncio.wait_for(response_event.wait(), timeout=current_timeout)

            if response_container['response']:
                logger.info(
                    f"Received response for request {message.id} from "
                    f"{message.metadata.target_component}"
                )
                return response_container['response']

            raise TimeoutError("No response content received")

        except asyncio.TimeoutError:
            raise TimeoutError(
                f"Request timed out after {current_timeout}s: "
                f"ID={message.id}, "
                f"Target={message.metadata.target_component}"
            )

    def _calculate_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff time with jitter.

        Args:
            attempt: Current attempt number

        Returns:
            Float representing backoff time in seconds
        """
        base_backoff = min(2 ** attempt, 10)  # Max 10 second backoff
        jitter = random.uniform(0, 0.1 * base_backoff)  # 10% jitter
        return base_backoff + jitter

    async def _handle_retry(
            self,
            message: ProcessingMessage,
            attempt: int,
            backoff: float
    ) -> None:
        """
        Handle retry logic between attempts.

        Args:
            message: The message being retried
            attempt: Current attempt number
            backoff: Calculated backoff time
        """
        logger.warning(
            f"Attempt {attempt + 1} failed for message {message.id}, "
            f"retrying after {backoff:.2f}s backoff"
        )
        await asyncio.sleep(backoff)

    async def _log_request_error(
            self,
            message: ProcessingMessage,
            error: Exception
    ) -> None:
        """
        Log detailed error information for failed requests.

        Args:
            message: The message that failed
            error: The exception that occurred
        """
        logger.error(
            f"Request-response failed: {str(error)}\n"
            f"Message details: ID={message.id}, "
            f"Target={message.metadata.target_component}, "
            f"Department={message.metadata.department}, "
            f"Type={message.message_type}"
        )

    async def _cleanup_temporary_handler(
            self,
            handler_identifier: ModuleIdentifier,
            patterns: List[str],
            handler_id: str
    ) -> None:
        """
        Clean up temporary handler resources.

        Args:
            handler_identifier: Handler's identifier
            patterns: Subscribed patterns
            handler_id: Handler's string ID
        """
        if all([handler_identifier, patterns, handler_id]):
            try:
                await self.unsubscribe(
                    handler_identifier,
                    patterns[0]
                )
                logger.info(f"Cleaned up temporary handler {handler_id}")
            except Exception as cleanup_error:
                logger.error(
                    f"Failed to cleanup handler {handler_id}: {cleanup_error}"
                )

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

    def _clear_storage(self) -> None:
        """Clear all internal storage structures."""
        try:
            self.active_messages.clear()
            self.message_history.clear()
            self.stats['messages_processed'] = 0
            self.stats['messages_failed'] = 0

        except Exception as e:
            logger.error(f"Error clearing storage: {str(e)}")

    async def check_connection_health(self) -> bool:
        try:
            await self._ping()
            return True
        except Exception as e:
            logger.error(f"Connection health check failed: {e}")
            await self._handle_connection_failure()
            return False

    async def _ping(self) -> None:
        ping_message = ProcessingMessage(
            message_type=MessageType.GLOBAL_HEALTH_CHECK,
            content={'timestamp': datetime.now().isoformat()}
        )
        try:
            await asyncio.wait_for(self._send_ping(ping_message), timeout=5.0)
        except asyncio.TimeoutError:
            raise ConnectionError("Broker ping timed out")


async def _send_ping(self, ping_message: ProcessingMessage) -> None:
    """
    Send a ping message and wait for acknowledgment.

    Args:
        ping_message: Ping message to send

    Raises:
        ConnectionError: If ping acknowledgment not received
    """
    ping_received = asyncio.Event()

    async def ping_callback(response: ProcessingMessage):
        if response.message_type == MessageType.GLOBAL_STATUS_RESPONSE:
            ping_received.set()

    try:
        # Set up temporary ping handler
        handler_id = f"ping_handler_{ping_message.id}"
        handler_identifier = ModuleIdentifier(
            component_name=handler_id,
            component_type=ComponentType.CORE,
            department="core",
            role="ping_handler"
        )

        # Subscribe to status response
        await self.subscribe(
            module_identifier=handler_identifier,
            message_patterns=["global.status.response"],
            callback=ping_callback
        )

        # Send health check ping
        ping_message.message_type = MessageType.GLOBAL_HEALTH_CHECK
        await self.publish(ping_message)

        # Wait for status response
        try:
            await asyncio.wait_for(ping_received.wait(), timeout=5.0)
            self._connection_state["last_ping"] = datetime.now()
            return

        except asyncio.TimeoutError:
            raise ConnectionError("Ping acknowledgment not received")

    finally:
        # Cleanup ping handler
        try:
            await self.unsubscribe(handler_identifier, "global.status.response")
        except Exception as e:
            logger.error(f"Failed to cleanup ping handler: {e}")