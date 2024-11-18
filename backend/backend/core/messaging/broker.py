# core/messaging/broker.py

from typing import Dict, List, Any
from backend.backend.core.messaging.types import ProcessingMessage, ModuleIdentifier, MessageType

class MessageBroker:
    """Enhanced message broker with dynamic routing and tracking"""

    def __init__(self):
        self.messages: Dict[str, ProcessingMessage] = {}
        self.module_subscriptions: Dict[str, List[callable]] = {}
        self.message_chains: Dict[str, List[str]] = {}
        self.pending_decisions: Dict[str, ProcessingMessage] = {}
        self.active_modules: Dict[str, ModuleIdentifier] = {}

    def register_module(self, module_identifier: ModuleIdentifier):
        """Register a module with the broker"""
        self.active_modules[module_identifier.get_tag()] = module_identifier

    def subscribe_to_module(self, module_tag: str, callback: callable):
        """Subscribe to messages from a specific module"""
        if module_tag not in self.module_subscriptions:
            self.module_subscriptions[module_tag] = []
        self.module_subscriptions[module_tag].append(callback)

    def publish(self, message: ProcessingMessage) -> str:
        """Publish a message with enhanced routing"""
        self.messages[message.message_id] = message

        # Track message chains
        if message.parent_message_id:
            if message.parent_message_id not in self.message_chains:
                self.message_chains[message.parent_message_id] = []
            self.message_chains[message.parent_message_id].append(message.message_id)

        # Track pending decisions
        if message.message_type == MessageType.RECOMMENDATION:
            self.pending_decisions[message.message_id] = message

        # Route to subscribers
        if message.source_identifier:
            source_tag = message.source_identifier.get_tag()
            if source_tag in self.module_subscriptions:
                for callback in self.module_subscriptions[source_tag]:
                    callback(message)

        return message.message_id

    def submit_decision(self, message_id: str, decision: Dict[str, Any]) -> str:
        """Submit a decision for a recommendation"""
        if message_id not in self.pending_decisions:
            raise ValueError("No pending recommendation found for this decision")

        original_msg = self.pending_decisions[message_id]
        decision_msg = ProcessingMessage(
            source_identifier=original_msg.target_identifier,
            target_identifier=original_msg.source_identifier,
            message_type=MessageType.DECISION,
            content=decision,
            parent_message_id=message_id
        )

        del self.pending_decisions[message_id]
        return self.publish(decision_msg)

