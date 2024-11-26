from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid
import logging

from backend.core.metrics.metrics_manager import MetricsManager
from backend.core.config.config_manager import ConfigurationManager
from backend.core.messaging.types import (
    ProcessingMessage,
    ModuleIdentifier,
    MessageType,
    ProcessingStatus
)

from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import uuid
import logging
import re


@dataclass
class ModuleSubscription:
    """Subscription information for a module"""
    module_identifier: ModuleIdentifier
    callbacks: List[Callable] = field(default_factory=list)
    last_activity: datetime = field(default_factory=datetime.now)
    message_count: int = 0


class MessageBroker:
    """Enhanced message routing and delivery system with robust registration handling"""

    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        self.messages: Dict[str, ProcessingMessage] = {}
        self.module_subscriptions: Dict[str, ModuleSubscription] = {}
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager or ConfigurationManager()

        # Updated pattern to allow UUID in the last segment
        # First two segments: letters, numbers, underscores
        # Last segment: either standard format or UUID format
        self.module_tag_pattern = re.compile(
            r'^[a-zA-Z_][a-zA-Z0-9_]*\.'  # First segment
            r'[a-zA-Z_][a-zA-Z0-9_]*\.'   # Second segment
            r'(?:[a-zA-Z_][a-zA-Z0-9_]*|'  # Either standard format
            r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})$',  # Or UUID format
            re.IGNORECASE  # Make UUID pattern case-insensitive
        )

        # Pending subscriptions for modules that aren't registered yet
        self.pending_subscriptions: Dict[str, List[Callable]] = {}

        max_workers = self.config_manager.get('broker_max_workers', 4)
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        self.message_retention_hours = self.config_manager.get('message_retention_hours', 24)
        self.metrics_manager = MetricsManager()

    def normalize_module_tag(self, module_tag: str) -> str:
        """Normalize module tag to ensure consistent format"""
        parts = module_tag.split('.')
        if len(parts) == 1:  # Just module name
            return f"{parts[0]}.default.default"
        elif len(parts) == 2:  # Module and method
            return f"{parts[0]}.{parts[1]}.default"
        return module_tag

    def register_module(self, module_identifier: ModuleIdentifier) -> None:
        """Register a module with enhanced validation and pending subscription handling"""
        module_tag = module_identifier.get_tag()

        if not self.module_tag_pattern.match(module_tag):
            raise ValueError(f"Invalid module tag format: {module_tag}")

        normalized_tag = self.normalize_module_tag(module_tag)

        if normalized_tag not in self.module_subscriptions:
            self.module_subscriptions[normalized_tag] = ModuleSubscription(
                module_identifier=module_identifier
            )
            self.logger.info(f"Module registered: {normalized_tag}")

            # Handle any pending subscriptions
            if normalized_tag in self.pending_subscriptions:
                for callback in self.pending_subscriptions[normalized_tag]:
                    self.module_subscriptions[normalized_tag].callbacks.append(callback)
                self.logger.info(
                    f"Processed {len(self.pending_subscriptions[normalized_tag])} pending subscriptions for {normalized_tag}")
                del self.pending_subscriptions[normalized_tag]
        else:
            self.logger.warning(f"Module '{normalized_tag}' is already registered.")

    def subscribe_to_module(self, module_tag: str, callback: Callable) -> None:
        """Subscribe to module messages with enhanced error handling and pending subscription support"""
        try:
            normalized_tag = self.normalize_module_tag(module_tag)

            if not self.module_tag_pattern.match(normalized_tag):
                raise ValueError(f"Invalid module tag format: {normalized_tag}")

            if normalized_tag in self.module_subscriptions:
                self.module_subscriptions[normalized_tag].callbacks.append(callback)
                self.logger.info(f"Subscribed callback to {normalized_tag}")
            else:
                # Store as pending subscription
                if normalized_tag not in self.pending_subscriptions:
                    self.pending_subscriptions[normalized_tag] = []
                self.pending_subscriptions[normalized_tag].append(callback)
                self.logger.info(f"Added pending subscription for {normalized_tag}")
        except Exception as e:
            self.logger.error(f"Subscription error for {module_tag}: {str(e)}")
            raise ValueError(f"Subscription failed: {str(e)}")

    def is_module_registered(self, module_tag: str) -> bool:
        """Check if a module is registered with normalized tag support"""
        normalized_tag = self.normalize_module_tag(module_tag)
        return normalized_tag in self.module_subscriptions

    def publish(self, message: ProcessingMessage) -> str:
        """Publish message with enhanced error handling and metrics tracking"""
        try:
            if not message.message_id:
                message.message_id = str(uuid.uuid4())

            self.messages[message.message_id] = message
            self.metrics_manager.increment('total_messages')

            if message.source_identifier:
                source_tag = self.normalize_module_tag(message.source_identifier.get_tag())

                if source_tag in self.module_subscriptions:
                    subscription = self.module_subscriptions[source_tag]
                    subscription.message_count += 1
                    subscription.last_activity = datetime.now()

                    for callback in subscription.callbacks:
                        self.thread_pool.submit(self._safe_callback_execution, callback, message)

            self._cleanup_old_messages()
            return message.message_id
        except Exception as e:
            self.logger.error(f"Error publishing message: {str(e)}")
            raise

    def _cleanup_old_messages(self) -> None:
        """Clean up messages older than the retention period"""
        cutoff_time = datetime.now() - timedelta(hours=self.message_retention_hours)
        old_messages = [
            msg_id for msg_id, msg in self.messages.items()
            if msg.timestamp < cutoff_time
        ]
        for msg_id in old_messages:
            del self.messages[msg_id]

    def _safe_callback_execution(self, callback: Callable, message: ProcessingMessage) -> None:
        """Execute callback with comprehensive error handling"""
        try:
            callback(message)
        except Exception as e:
            self.metrics_manager.increment('callback_errors')
            self.logger.error(f"Callback execution error: {str(e)}", exc_info=True)

    def get_subscription_status(self) -> Dict[str, Any]:
        """Get current subscription status for monitoring"""
        return {
            'registered_modules': list(self.module_subscriptions.keys()),
            'pending_subscriptions': {k: len(v) for k, v in self.pending_subscriptions.items()},
            'total_callbacks': sum(len(sub.callbacks) for sub in self.module_subscriptions.values())
        }

    def debug_status(self):
        """Get detailed status of message broker"""
        status = {
            'registered_modules': list(self.module_subscriptions.keys()),
            'pending_subscriptions': {k: len(v) for k, v in self.pending_subscriptions.items()},
            'total_callbacks': sum(len(sub.callbacks) for sub in self.module_subscriptions.values()),
            'active_messages': len(self.messages)
        }

        # Use the logger instead of print
        self.logger.debug(f"Message Broker Debug Status: {status}")
        return status

    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)