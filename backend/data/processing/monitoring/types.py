from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


class MonitoringSource(Enum):
    """
    Enumeration of monitoring data sources in the system.
    Provides standardized source identification for metrics collection.
    """
    SYSTEM = "system"
    APPLICATION = "application"
    NETWORK = "network"
    DATABASE = "database"
    CUSTOM = "custom"
    PIPELINE = "pipeline"
    INFRASTRUCTURE = "infrastructure"


class MonitoringStatus(Enum):
    """
    Represents the current status of a monitoring task or metric collection.
    Provides clear state representation for monitoring processes.
    """
    PENDING = "pending"
    COLLECTING = "collecting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ANOMALY_DETECTED = "anomaly_detected"
    PAUSED = "paused"


class MonitoringPhase(Enum):
    """
    Defines distinct phases within the monitoring workflow.
    Helps track progression of monitoring activities.
    """
    INITIAL = "initial"
    COLLECTION = "collection"
    ANALYSIS = "analysis"
    REPORTING = "reporting"
    ALERTING = "alerting"
    RESOLUTION = "resolution"


class MetricType(Enum):
    """
    Classification of different metric types for precise categorization.
    """
    PERFORMANCE = "performance"
    RESOURCE_UTILIZATION = "resource_utilization"
    ERROR_RATE = "error_rate"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    AVAILABILITY = "availability"
    CUSTOM = "custom"


@dataclass
class MonitoringRequest:
    """
    Represents a structured monitoring data collection request.

    Provides comprehensive configuration for metric collection tasks.
    """
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pipeline_id: Optional[str] = None
    source: MonitoringSource = MonitoringSource.SYSTEM
    metrics_types: List[MetricType] = field(default_factory=list)
    collectors: List[str] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)
    requires_confirmation: bool = False
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ComponentMetrics:
    """
    Represents metrics collected from a specific system component.

    Provides structured storage for detailed monitoring data.
    """
    metrics_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    source: MonitoringSource = MonitoringSource.SYSTEM
    collected_metrics: Dict[str, Any] = field(default_factory=dict)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)
    user_confirmation: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    validated: bool = False


@dataclass
class ComponentUpdate:
    """
    Represents update information from a monitoring component.

    Provides a standardized structure for component status updates.
    """
    component: Optional[str] = None
    metrics_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    status: str = field(default="neutral")
    metrics_details: Dict[str, Any] = field(default_factory=dict)
    requires_action: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class MonitoringState:
    """
    Represents the comprehensive state of a monitoring process.

    Tracks the lifecycle and progression of monitoring activities.
    """
    pipeline_id: Optional[str] = None
    current_metrics: List[ComponentMetrics] = field(default_factory=list)
    pending_metrics: List[ComponentMetrics] = field(default_factory=list)
    completed_metrics: List[ComponentMetrics] = field(default_factory=list)
    status: MonitoringStatus = MonitoringStatus.PENDING
    phase: MonitoringPhase = MonitoringPhase.INITIAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    anomalies: List[Dict[str, Any]] = field(default_factory=list)


class AlertSeverity(Enum):
    """
    Defines severity levels for system alerts.
    Provides standardized alert prioritization.
    """
    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5


@dataclass
class AlertConfiguration:
    """
    Configurable alert settings for monitoring systems.

    Allows flexible and precise alert management.
    """
    severity_threshold: AlertSeverity = AlertSeverity.MEDIUM
    notification_channels: List[str] = field(default_factory=list)
    auto_remediation_enabled: bool = False
    fallback_actions: List[str] = field(default_factory=list)
    persistence_duration: int = 3600  # Seconds alert remains active