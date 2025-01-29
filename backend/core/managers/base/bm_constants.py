# backend/core/managers/base/bm_constants.py

from enum import Enum


class ChannelType(Enum):
    """Types of communication channels"""
    CONTROL = "control"  # Control and coordination messages
    DATA = "data"  # Data processing messages
    METRICS = "metrics"  # Metrics and monitoring messages
    STATUS = "status"  # Status updates
    ERROR = "error"  # Error handling
    SYSTEM = "system"  # System-level messages
    INTERNAL = "internal"  # Internal component communication
    EXTERNAL = "external"  # External system communication


class ManagerConstants:
    """Constants for manager configuration"""
    MAX_CHANNEL_MESSAGES = 1000  # Maximum messages per channel
    LOCK_TIMEOUT = 1.0  # Lock acquisition timeout in seconds
    MAX_RETRY_ATTEMPTS = 3  # Maximum retry attempts for operations
    MESSAGE_TIMEOUT = 30  # Message timeout in seconds
    MAX_BATCH_SIZE = 100  # Maximum batch size for processing

    # Queue Settings
    QUEUE_SIZE = 1000  # Default queue size
    QUEUE_TIMEOUT = 5.0  # Queue operation timeout

    # Channel Settings
    CHANNEL_BUFFER_SIZE = 1000  # Channel buffer size
    CHANNEL_TIMEOUT = 5.0  # Channel operation timeout

    # Processing Settings
    MAX_PARALLEL_TASKS = 10  # Maximum parallel tasks
    TASK_TIMEOUT = 300  # Task timeout in seconds

    # Monitoring Settings
    METRICS_INTERVAL = 60  # Metrics collection interval in seconds
    HEALTH_CHECK_INTERVAL = 30  # Health check interval in seconds

    # Cleanup Settings
    CLEANUP_INTERVAL = 3600  # Cleanup interval in seconds
    MAX_INACTIVE_TIME = 7200  # Maximum inactive time before cleanup