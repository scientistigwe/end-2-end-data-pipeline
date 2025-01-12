# backend/core/base/base_manager_constants.py

from enum import Enum
from datetime import timedelta


class ChannelType(Enum):
    """Define main communication channels in priority order"""
    ROUTING = "routing"  # Route determination
    STAGING = "staging"  # Data staging
    DATA_SOURCE = "data_source"  # Data ingestion/response
    PROCESSING = "processing"  # Data processing
    DECISION = "decision"  # User decisions
    INSIGHT = "insight"  # Business insights
    CONTROL = "control"  # Control points
    STATUS = "status"  # Status updates


class ResourceState(Enum):
    """Resource states with health indication"""
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    RECOVERING = "recovering"
    AWAITING_DECISION = "awaiting_decision"  # Added for control points
    DECISION_TIMEOUT = "decision_timeout"  # Added for control points


class ManagerConstants:
    """Centralized constants for base manager"""

    # Message handling
    MAX_CHANNEL_MESSAGES = 1000
    ACK_TIMEOUT = timedelta(seconds=30)
    LOCK_TIMEOUT = 1.0
    CONTROL_POINT_DEFAULT_TIMEOUT = timedelta(hours=1)

    # Error thresholds
    ERROR_RATE_THRESHOLD_WARNING = 0.05
    ERROR_RATE_THRESHOLD_CRITICAL = 0.1

    # Monitoring intervals
    HEARTBEAT_INTERVAL = 30  # seconds
    CLEANUP_INTERVAL = 60  # seconds

    # Retry configurations
    MAX_PUBLISH_RETRIES = 3
    RETRY_DELAY = 1  # second