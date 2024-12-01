# backend/core/messaging/types.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid


class MessageType(Enum):
    # Source Operations
    SOURCE_CONNECT = "source.connect"
    SOURCE_READ = "source.read"
    SOURCE_VALIDATE = "source.validate"
    SOURCE_EXTRACT = "source.extract"
    SOURCE_ERROR = "source.error"
    SOURCE_SUCCESS = "source.success"

    # Quality Operations
    QUALITY_START = "quality.start"
    QUALITY_DETECT = "quality.detect"
    QUALITY_ANALYZE = "quality.analyze"
    QUALITY_RESOLVE = "quality.resolve"
    QUALITY_UPDATE = "quality.update"
    QUALITY_COMPLETE = "quality.complete"
    QUALITY_ERROR = "quality.error"

    # Insight Operations
    INSIGHT_START = "insight.start"
    INSIGHT_GENERATE = "insight.generate"
    INSIGHT_UPDATE = "insight.update"
    INSIGHT_COMPLETE = "insight.complete"
    INSIGHT_ERROR = "insight.error"

    # Decision Operations
    DECISION_START = "decision.start"
    RECOMMENDATION_GENERATE = "decision.recommend.generate"
    RECOMMENDATION_READY = "decision.recommend.ready"
    USER_DECISION_REQUEST = "decision.user.request"
    USER_DECISION_SUBMIT = "decision.user.submit"
    DECISION_PROCESS = "decision.process"
    DECISION_COMPLETE = "decision.complete"
    DECISION_ERROR = "decision.error"

    # Routing Operations
    ROUTE_REQUEST = "route.request"
    ROUTE_UPDATE = "route.update"
    ROUTE_CHANGE = "route.change"
    ROUTE_COMPLETE = "route.complete"
    ROUTE_ERROR = "route.error"

    # Staging Operations
    STAGE_STORE = "stage.store"
    STAGE_RETRIEVE = "stage.retrieve"
    STAGE_UPDATE = "stage.update"
    STAGE_DELETE = "stage.delete"
    STAGE_SUCCESS = "stage.success"
    STAGE_ERROR = "stage.error"

    # Pipeline Operations
    PIPELINE_START = "pipeline.start"
    PIPELINE_PAUSE = "pipeline.pause"
    PIPELINE_RESUME = "pipeline.resume"
    PIPELINE_CANCEL = "pipeline.cancel"
    PIPELINE_UPDATE = "pipeline.update"
    PIPELINE_COMPLETE = "pipeline.complete"
    PIPELINE_ERROR = "pipeline.error"


class ProcessingStatus(Enum):
    # General Statuses
    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    FAILED = "failed"

    # Stage-specific Statuses
    EXTRACTING = "extracting"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    AWAITING_DECISION = "awaiting_decision"
    RESOLVING = "resolving"


class ComponentType(Enum):
    """Types of system components"""
    ORCHESTRATOR = "orchestrator"
    HANDLER = "handler"
    MANAGER = "manager"
    MODULE = "module"


@dataclass
class ModuleIdentifier:
    """Enhanced identifier for system components"""
    component_name: str
    component_type: ComponentType
    method_name: str
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def get_tag(self) -> str:
        """Get standardized message routing tag"""
        return f"{self.component_type.value}.{self.component_name}.{self.method_name}.{self.instance_id}"


@dataclass
class MessageMetadata:
    """Enhanced message metadata"""
    pipeline_id: Optional[str] = None
    stage: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    retry_count: int = 0
    priority: int = 1
    timeout_seconds: int = 30
    requires_acknowledgment: bool = False
    custom_attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingMessage:
    """Enhanced message for pipeline communication"""
    # Core Message Properties
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_identifier: ModuleIdentifier
    target_identifier: ModuleIdentifier
    message_type: MessageType
    content: Dict[str, Any] = field(default_factory=dict)

    # Status and Control
    status: ProcessingStatus = field(default=ProcessingStatus.PENDING)
    requires_response: bool = False
    is_retry: bool = False

    # Context and Tracking
    metadata: MessageMetadata = field(default_factory=MessageMetadata)
    parent_message_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def get_routing_key(self) -> str:
        """Get message routing key"""
        return f"{self.target_identifier.get_tag()}.{self.message_type.value}"

    def create_response(self, message_type: MessageType, content: Dict[str, Any]) -> 'ProcessingMessage':
        """Create a response message"""
        return ProcessingMessage(
            source_identifier=self.target_identifier,
            target_identifier=self.source_identifier,
            message_type=message_type,
            content=content,
            parent_message_id=self.message_id,
            correlation_id=self.correlation_id or self.message_id,
            metadata=MessageMetadata(
                pipeline_id=self.metadata.pipeline_id,
                stage=self.metadata.stage
            )
        )
