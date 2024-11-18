# message_broker.py
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import uuid
from pathlib import Path


class MessageType(Enum):
    """Types of messages that can flow through the pipeline"""
    RECOMMENDATION = "recommendation"
    DECISION = "decision"
    STATUS_UPDATE = "status_update"
    ERROR = "error"


class MessageStatus(Enum):
    """Status of messages in the system"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_FOR_DECISION = "waiting_for_decision"


@dataclass
class PipelineMessage:
    """
    Represents a message flowing through the pipeline system.

    Attributes:
        message_id (str): Unique identifier for this message
        source_path (str): Path to the source file that generated this message
        module_name (str): Name of the module that generated/should receive this message
        message_type (MessageType): Type of the message (recommendation/decision/etc)
        content (Dict[str, Any]): The actual message content
        status (MessageStatus): Current status of the message
        timestamp (datetime): When the message was created
        parent_message_id (Optional[str]): ID of the parent message if this is a response
        priority (int): Message priority (higher number = higher priority)
    """
    message_id: str
    source_path: str
    module_name: str
    message_type: MessageType
    content: Dict[str, Any]
    status: MessageStatus
    timestamp: datetime
    parent_message_id: Optional[str] = None
    priority: int = 1


class MessageBroker:
    """
    Handles message routing and tracking between different modules in the pipeline.

    This broker maintains the message flow, tracks message chains, and ensures
    proper delivery of messages between modules. It automatically generates unique
    identifiers for messages based on their source and maintains the relationship
    between recommendations and decisions.

    Attributes:
        messages (Dict[str, PipelineMessage]): Storage for all messages
        module_subscriptions (Dict[str, List[Callable]]): Callbacks for module-specific messages
        message_chains (Dict[str, List[str]]): Tracks related messages in chains
    """

    def __init__(self):
        self.messages: Dict[str, PipelineMessage] = {}
        self.module_subscriptions: Dict[str, List[Callable]] = {}
        self.message_chains: Dict[str, List[str]] = {}

    def generate_message_tag(self, source_path: str, module_name: str) -> str:
        """
        Generates a unique tag based on the source file and module name.

        Args:
            source_path (str): Path to the source file
            module_name (str): Name of the module

        Returns:
            str: A unique tag combining file path, module name, and timestamp
        """
        path = Path(source_path)
        base_name = path.stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"{base_name}_{module_name}_{timestamp}_{unique_id}"

    def publish_message(self, source_path: str, module_name: str,
                        message_type: MessageType, content: Dict[str, Any],
                        parent_message_id: Optional[str] = None) -> str:
        """
        Publishes a new message to the broker.

        Args:
            source_path (str): Path to the source file generating the message
            module_name (str): Name of the module sending the message
            message_type (MessageType): Type of the message
            content (Dict[str, Any]): Message content
            parent_message_id (Optional[str]): ID of the parent message if this is a response

        Returns:
            str: The unique message ID generated for this message
        """
        message_id = self.generate_message_tag(source_path, module_name)

        message = PipelineMessage(
            message_id=message_id,
            source_path=source_path,
            module_name=module_name,
            message_type=message_type,
            content=content,
            status=MessageStatus.PENDING,
            timestamp=datetime.now(),
            parent_message_id=parent_message_id
        )

        self.messages[message_id] = message

        if parent_message_id:
            if parent_message_id not in self.message_chains:
                self.message_chains[parent_message_id] = []
            self.message_chains[parent_message_id].append(message_id)

        self._notify_subscribers(message)
        return message_id

    def _notify_subscribers(self, message: PipelineMessage) -> None:
        """
        Notifies all subscribers about a new message.

        Args:
            message (PipelineMessage): The message to notify about
        """
        if message.module_name in self.module_subscriptions:
            for callback in self.module_subscriptions[message.module_name]:
                callback(message)


