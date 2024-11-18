# core/messaging/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class MessageType(Enum):
    RECOMMENDATION = "recommendation"  # Requires decision
    DECISION = "decision"  # Response to recommendation
    ACTION = "action"  # User/system action required
    INFO = "info"  # Informational only
    WARNING = "warning"  # Warning message
    ERROR = "error"  # Error message
    STATUS_UPDATE = "status_update"  # Stage status update


class ProcessingStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    AWAITING_DECISION = "awaiting_decision"
    REQUIRES_ACTION = "requires_action"


@dataclass
class ModuleIdentifier:
    """Unique identifier for module and method"""
    module_name: str
    method_name: str
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get_tag(self) -> str:
        return f"{self.module_name}.{self.method_name}.{self.instance_id}"


@dataclass
class ProcessingMessage:
    """Enhanced message structure for pipeline communication"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    source_identifier: ModuleIdentifier = field(default=None)
    target_identifier: Optional[ModuleIdentifier] = None
    message_type: MessageType = field(default=None)
    content: Dict[str, Any] = field(default_factory=dict)
    status: ProcessingStatus = field(default=ProcessingStatus.PENDING)
    parent_message_id: Optional[str] = None
    requires_response: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)



