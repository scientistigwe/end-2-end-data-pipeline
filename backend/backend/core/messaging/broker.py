import logging
import re
import uuid
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from backend.core.metrics.metrics_manager import MetricsManager
from backend.core.config.config_manager import ConfigurationManager
from backend.core.registry.component_registry import ComponentRegistry

from backend.core.messaging.types import (
    ProcessingMessage,
    ModuleIdentifier,
    MessageType,
    ProcessingStatus
)

logger = logging.getLogger(__name__)


@dataclass
class ModuleSubscription:
    """Subscription information for a module with enhanced tracking"""
    module_identifier: ModuleIdentifier
    callbacks: List[Callable] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.now)


class MessageBroker:
    """Enhanced message routing and delivery system with robust registration handling"""

    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        # Initialize logger first
        self.logger = logging.getLogger(__name__)

        # Other initializations
        self.messages: Dict[str, ProcessingMessage] = {}
        self.module_subscriptions: Dict[str, ModuleSubscription] = {}
        self.config_manager = config_manager or ConfigurationManager()
        self.registry = ComponentRegistry()

        # Updated pattern to allow UUID in the last segment
        self.module_tag_pattern = re.compile(
            r'^[a-zA-Z_][a-zA-Z0-9_]*\.'  # First segment
            r'[a-zA-Z_][a-zA-Z0-9_]*\.'  # Second segment
            r'(?:[a-zA-Z_][a-zA-Z0-9_]*|'  # Either standard format
            r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$',  # Or UUID format
            re.IGNORECASE  # Make UUID pattern case-insensitive
        )

        # Configure thread pool
        max_workers = self.config_manager.get('broker_max_workers', 4)
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.message_retention_hours = self.config_manager.get('message_retention_hours', 24)
        self.metrics_manager = MetricsManager()

        # Pending subscriptions
        self.pending_subscriptions: Dict[str, List[Callable]] = {}

        self.logger.info("MessageBroker initialized successfully")

    def register_module(self, module: ModuleIdentifier) -> None:
        """Register module with enhanced validation and UUID management"""
        try:
            # Get consistent UUID from registry
            component_uuid = self.registry.get_component_uuid(module.module_name)
            module.instance_id = component_uuid

            # Create normalized tag
            normalized_tag = self._create_normalized_tag(module)

            if not self.module_tag_pattern.match(normalized_tag):
                raise ValueError(f"Invalid module tag format: {normalized_tag}")

            if normalized_tag not in self.module_subscriptions:
                self.module_subscriptions[normalized_tag] = ModuleSubscription(
                    module_identifier=module,
                    created_at=datetime.now()
                )
                logger.info(f"Registered module: {normalized_tag}")

                # Handle any pending subscriptions
                self._process_pending_subscriptions(normalized_tag)
            else:
                logger.debug(f"Module already registered: {normalized_tag}")

        except Exception as e:
            logger.error(f"Error registering module: {str(e)}")
            raise

    def subscribe_to_module(self, tag: str, callback) -> None:
        """Subscribe to module with proper tag normalization"""
        # Extract base tag without UUID
        base_tag = '.'.join(tag.split('.')[:2])
        component_name = base_tag.split('.')[0]

        # Get consistent UUID
        component_uuid = self.registry.get_component_uuid(component_name)
        normalized_tag = f"{base_tag}.{component_uuid}"

        if normalized_tag not in self.module_subscriptions:
            # Create new ModuleSubscription if it doesn't exist
            self.module_subscriptions[normalized_tag] = ModuleSubscription(
                module_identifier=ModuleIdentifier(component_name, base_tag.split('.')[1], component_uuid)
            )

        # Add callback to existing subscription
        self.module_subscriptions[normalized_tag].callbacks.append(callback)
        self.logger.info(f"Subscribed to {normalized_tag}")

    def _safe_callback_execution(self, callback: Callable, message: ProcessingMessage) -> None:
        """Execute callback with comprehensive error handling"""
        try:
            callback(message)
        except Exception as e:
            self.metrics_manager.increment('callback_errors')
            self.logger.error(f"Callback execution error: {str(e)}", exc_info=True)

    def publish(self, message: ProcessingMessage) -> str:
        """Publish message with consistent routing and better error handling"""
        try:
            # Generate message ID
            message.message_id = str(uuid.uuid4())

            # Log publish attempt
            self.logger.info(f"Publishing message {message.message_id} to: {message.target_identifier.get_tag()}")

            # Update UUIDs
            if message.source_identifier:
                source_uuid = self.registry.get_component_uuid(
                    message.source_identifier.module_name
                )
                message.source_identifier.instance_id = source_uuid

            if message.target_identifier:
                target_uuid = self.registry.get_component_uuid(
                    message.target_identifier.module_name
                )
                message.target_identifier.instance_id = target_uuid

            # Store message
            target_tag = message.target_identifier.get_tag()
            self.messages[message.message_id] = message

            # Process subscriptions - Access callbacks through ModuleSubscription object
            if target_tag in self.module_subscriptions:
                subscription = self.module_subscriptions[target_tag]
                for callback in subscription.callbacks:  # Access the callbacks list
                    self.thread_pool.submit(self._safe_callback_execution, callback, message)
                self.logger.info(f"Message {message.message_id} published successfully")
            else:
                self.logger.warning(f"No subscribers found for: {target_tag}")

            return message.message_id

        except Exception as e:
            self.logger.error(f"Error publishing message: {str(e)}", exc_info=True)
            raise

    def _ensure_consistent_uuids(self, message: ProcessingMessage) -> None:
        """Ensure message identifiers have consistent UUIDs"""
        if message.source_identifier:
            source_uuid = self.registry.get_component_uuid(
                message.source_identifier.module_name
            )
            message.source_identifier.instance_id = source_uuid

        if message.target_identifier:
            target_uuid = self.registry.get_component_uuid(
                message.target_identifier.module_name
            )
            message.target_identifier.instance_id = target_uuid

    def _create_normalized_tag(self, module: ModuleIdentifier) -> str:
        """Create normalized tag from ModuleIdentifier"""
        return f"{module.module_name}.{module.method_name}.{module.instance_id}"

    def _create_normalized_tag_from_string(self, tag: str) -> str:
        """Create normalized tag from string"""
        parts = tag.split('.')
        if len(parts) >= 2:
            component_name = parts[0]
            method_name = parts[1]
            component_uuid = self.registry.get_component_uuid(component_name)
            return f"{component_name}.{method_name}.{component_uuid}"
        return tag

    def _process_pending_subscriptions(self, tag: str) -> None:
        """Process any pending subscriptions for a newly registered module"""
        if tag in self.pending_subscriptions:
            for callback in self.pending_subscriptions[tag]:
                self.module_subscriptions[tag].callbacks.append(callback)
            logger.info(f"Processed {len(self.pending_subscriptions[tag])} pending subscriptions for {tag}")
            del self.pending_subscriptions[tag]

    def get_module_status(self, module_tag: str) -> Dict[str, Any]:
        """Get detailed status for a specific module"""
        normalized_tag = self._create_normalized_tag_from_string(module_tag)
        if normalized_tag in self.module_subscriptions:
            subscription = self.module_subscriptions[normalized_tag]
            return {
                'status': subscription.status,
                'message_count': subscription.message_count,
                'last_activity': subscription.last_activity.isoformat(),
                'callback_count': len(subscription.callbacks),
                'created_at': subscription.created_at.isoformat()
            }
        return {'status': 'not_found'}

    def __del__(self):
        """Enhanced cleanup with logging"""
        try:
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=True)
                logger.info("MessageBroker thread pool shut down successfully")
        except Exception as e:
            logger.error(f"Error during MessageBroker cleanup: {str(e)}")