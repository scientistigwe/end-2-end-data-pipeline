# backend/core/orchestration/base_manager_helper_files.py

import logging
import asyncio
import uuid
from datetime import datetime
from typing import Any, Dict, Optional, List, Callable

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ModuleIdentifier,
    ProcessingMessage,
    ProcessingStage,
    ComponentType
)
from backend.core.registry.component_registry import ComponentRegistry

# Import helper components
from backend.core.orchestration.base_manager_helper_files.bm_constants import (
    ChannelType,
    ResourceState,
    ManagerConstants
)
from backend.core.orchestration.base_manager_helper_files.bm_metrics import (
    ManagerMetadata,
    ChannelMetrics
)
from backend.core.orchestration.base_manager_helper_files.bm_control_point import (
    ControlPointManager,
    ControlPoint
)
from backend.core.orchestration.base_manager_helper_files.bm_channel import (
    ChannelManager
)

logger = logging.getLogger(__name__)


class BaseManager:
    """
    Enhanced base manager with modular, composable architecture.

    Responsibilities:
    - Coordinate messaging between components
    - Manage control points
    - Handle message routing
    - Provide system-wide monitoring and health checks
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str,
            control_point_timeout: int = ManagerConstants.CONTROL_POINT_DEFAULT_TIMEOUT
    ):
        """
        Initialize the base manager with comprehensive components.

        Args:
            message_broker (MessageBroker): Message communication system
            component_name (str): Name of the component
            control_point_timeout (int, optional): Timeout for control points
        """
        # Core components
        self.message_broker = message_broker
        self.registry = ComponentRegistry()

        # Component identification
        self.module_id = ModuleIdentifier(
            component_name=component_name,
            component_type=ComponentType.MANAGER,
            method_name="manage",
            instance_id=self.registry.get_component_uuid(component_name)
        )

        # Metadata management
        self.metadata = ManagerMetadata(
            component_name=component_name,
            instance_id=self.module_id.instance_id,
            state=ResourceState.ACTIVE
        )

        # Modular component managers
        self.channel_manager = ChannelManager(logger=logger)
        self.control_point_manager = ControlPointManager(
            metadata=self.metadata,
            message_broker=message_broker,
            logger=logger
        )

        # Async event loop
        self.loop = asyncio.get_event_loop() if not asyncio.get_event_loop().is_running() else None

        # Initialize system components
        self._initialize_manager()

    def _initialize_manager(self) -> None:
        """
        Comprehensive initialization sequence for the manager.
        """
        try:
            # Step 1: Register with message broker
            self.message_broker.register_component(self.module_id)

            # Step 2: Initialize channels
            self._initialize_messaging_channels()

            # Step 3: Set up default message handlers
            self._setup_default_handlers()

            # Step 4: Start background monitoring
            self._start_background_tasks()

            logger.info(f"{self.metadata.component_name} manager initialized successfully")

        except Exception as e:
            logger.error(f"Manager initialization failed: {str(e)}")
            self.metadata.state = ResourceState.ERROR
            raise

    def _initialize_messaging_channels(self) -> None:
        """
        Initialize and subscribe to all communication channels.
        """
        try:
            # Subscribe to all defined channels
            for channel in ChannelType:
                self._subscribe_to_channel(channel)

            logger.info("Messaging channels initialized successfully")

        except Exception as e:
            logger.error(f"Channel initialization failed: {str(e)}")
            raise

    async def _subscribe_to_channel(self, channel: ChannelType) -> None:
        """
        Subscribe to a specific channel with a default handler
        """
        self.logger = logger
        try:
            # Provide a default handler if needed
            default_handler = self._handle_received_message

            await self.message_broker.subscribe(
                component=self.module_id,
                pattern=channel.value,
                callback=default_handler,
                timeout=10.0
            )

            self.logger.info(f"Subscribed to channel: {channel.value}")

        except Exception as e:
            self.logger.error(f"Error subscribing to channel {channel.value}: {str(e)}")
            raise

    def _setup_default_handlers(self) -> None:
        """
        Set up default message handlers for various channels and message types.
        """
        # Define default handlers for different message types
        default_handlers = {
            ChannelType.ROUTING: {
                MessageType.ROUTE_REQUEST: self._default_routing_handler,
                MessageType.ROUTE_UPDATE: self._default_routing_handler
            },
            ChannelType.PROCESSING: {
                MessageType.SOURCE_EXTRACT: self._default_processing_handler,
                MessageType.QUALITY_ANALYZE: self._default_processing_handler
            },
            # Add more default handlers as needed
        }

        # Register default handlers using channel manager
        for channel, handlers in default_handlers.items():
            for message_type, handler in handlers.items():
                self.channel_manager.register_handler(
                    channel,
                    message_type,
                    handler
                )

    async def _handle_received_message(self, message: ProcessingMessage) -> None:
        """
        Primary message handling method for all incoming messages.

        Args:
            message (ProcessingMessage): Incoming message to process
        """
        try:
            # Determine message channel
            channel = self._get_message_channel(message.message_type)

            # Attempt to acquire channel lock
            if not self.channel_manager.acquire_channel_lock(channel):
                logger.warning(f"Failed to acquire lock for channel {channel.value}")
                return

            try:
                # Retrieve appropriate handler
                handler = self.channel_manager.get_message_handler(channel, message.message_type)

                if handler:
                    # Execute handler with timing
                    start_time = asyncio.get_event_loop().time()
                    await handler(message) if asyncio.iscoroutinefunction(handler) else handler(message)
                    processing_time = asyncio.get_event_loop().time() - start_time

                    # Update channel metrics
                    metrics = self.channel_manager.get_channel_metrics(channel)
                    metrics.update_processing_time(processing_time)
                else:
                    logger.warning(f"No handler for message type {message.message_type}")

            finally:
                # Always release channel lock
                self.channel_manager.release_channel_lock(channel)

        except Exception as e:
            logger.error(f"Error handling received message: {str(e)}")
            await self._handle_message_error(message, e)

    def _get_message_channel(self, message_type: MessageType) -> ChannelType:
        """
        Determine the appropriate channel for a message type.

        Args:
            message_type (MessageType): Message type to route

        Returns:
            ChannelType: Appropriate communication channel
        """
        # Enhanced channel routing logic
        channel_mapping = {
            MessageType.SOURCE_CONNECT: ChannelType.DATA_SOURCE,
            MessageType.QUALITY_ANALYZE: ChannelType.PROCESSING,
            MessageType.CONTROL_POINT_REACHED: ChannelType.CONTROL,
            # Add more mappings as needed
        }
        return channel_mapping.get(message_type, ChannelType.PROCESSING)

    async def _handle_message_error(self, message: ProcessingMessage, error: Exception) -> None:
        """
        Handle errors that occur during message processing.

        Args:
            message (ProcessingMessage): Original message that caused error
            error (Exception): Error that occurred
        """
        try:
            # Log error details
            logger.error(f"Message processing error: {str(error)}")

            # Update metadata
            self.metadata.error_count += 1

            # Create and send error notification
            error_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=message.source_identifier,
                message_type=MessageType.ERROR,
                content={
                    'original_message_id': message.message_id,
                    'error_details': str(error)
                }
            )
            await self.message_broker.publish(error_message)

        except Exception as e:
            logger.error(f"Error in error handling: {str(e)}")

    def _start_background_tasks(self) -> None:
        """
        Start background monitoring and maintenance tasks.
        """

        async def background_monitor():
            while True:
                try:
                    await self._send_heartbeat()
                    await self._check_system_health()
                    await asyncio.sleep(ManagerConstants.HEARTBEAT_INTERVAL)
                except Exception as e:
                    logger.error(f"Background monitoring error: {str(e)}")

        # Create background task
        if self.loop:
            self.loop.create_task(background_monitor())

    async def _send_heartbeat(self) -> None:
        """
        Send periodic heartbeat to indicate system health.
        """
        try:
            heartbeat_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("monitoring_manager"),
                message_type=MessageType.STATUS_UPDATE,
                content={
                    'type': 'heartbeat',
                    'component': self.metadata.component_name,
                    'state': self.metadata.state.value,
                    'timestamp': asyncio.get_event_loop().time()
                }
            )
            await self.message_broker.publish(heartbeat_message)
        except Exception as e:
            logger.error(f"Heartbeat sending failed: {str(e)}")

    async def _check_system_health(self) -> None:
        """
        Comprehensive system health check.
        """
        try:
            # Perform system health checks
            health_status = {
                'message_broker': await self._check_message_broker_health(),
                'channels': self._check_channel_health(),
                'control_points': self._check_control_point_health()
            }

            # Update system state based on health checks
            self._update_system_state(health_status)

        except Exception as e:
            logger.error(f"System health check failed: {str(e)}")

    async def _check_message_broker_health(self) -> Dict[str, Any]:
        """
        Check message broker connectivity and performance.

        Returns:
            Dict[str, Any]: Message broker health status
        """
        try:
            return {
                'healthy': self.message_broker.is_connected(),
                'pending_messages': len(self.message_broker.active_messages)
            }
        except Exception as e:
            logger.error(f"Message broker health check failed: {str(e)}")
            return {'healthy': False, 'error': str(e)}

    def _check_channel_health(self) -> Dict[str, Any]:
        """
        Check health of all communication channels.

        Returns:
            Dict[str, Any]: Channel health status
        """
        channel_health = {}
        for channel in ChannelType:
            metrics = self.channel_manager.get_channel_metrics(channel)
            channel_health[channel.value] = {
                'message_count': metrics.message_count,
                'error_count': metrics.error_count,
                'queue_size': metrics.queue_size
            }
        return channel_health

    def _check_control_point_health(self) -> Dict[str, Any]:
        """
        Check health of active control points.

        Returns:
            Dict[str, Any]: Control point health status
        """
        return {
            'active_points': self.metadata.control_point_metrics.active_control_points,
            'pending_decisions': self.metadata.control_point_metrics.decisions_pending,
            'timeout_rate': self.metadata.control_point_metrics.decisions_timeout /
                            max(1, self.metadata.control_point_metrics.decisions_completed)
        }

    def _update_system_state(self, health_status: Dict[str, Any]) -> None:
        """
        Update system state based on health checks.

        Args:
            health_status (Dict[str, Any]): Comprehensive health status
        """
        # Determine overall system health
        is_healthy = all(
            status.get('healthy', False)
            for status in health_status.values()
        )

        # Update system state
        self.metadata.state = (
            ResourceState.ACTIVE if is_healthy
            else ResourceState.DEGRADED
        )

    async def cleanup(self) -> None:
        """
        Comprehensive cleanup of manager resources.
        """
        try:
            # Cleanup control points
            self.control_point_manager.cleanup_expired_control_points(
                datetime.now()
            )

            # Clear channel resources
            self.channel_manager.cleanup_channels()

            # Additional cleanup logic can be added here
            logger.info(f"{self.metadata.component_name} manager cleaned up successfully")

        except Exception as e:
            logger.error(f"Cleanup failed: {str(e)}")

    # Default handler methods (can be overridden by child classes)
    def _default_routing_handler(self, message: ProcessingMessage) -> None:
        """Default handler for routing-related messages."""
        logger.info(f"Default routing handler: {message.message_type}")

    def _default_processing_handler(self, message: ProcessingMessage) -> None:
        """Default handler for processing-related messages."""
        logger.info(f"Default processing handler: {message.message_type}")

    def __del__(self):
        """
        Ensure cleanup when object is garbage collected.
        """
        try:
            if self.loop and not self.loop.is_closed():
                self.loop.run_until_complete(self.cleanup())
        except Exception as e:
            logger.error(f"Error during object deletion: {str(e)}")