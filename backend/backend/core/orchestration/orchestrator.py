# Standard library imports
import functools
import logging
import os
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Type

# Third-party imports
from pydantic import BaseModel

# Core imports
from backend.core.config.data_processing_enums import (
    DataIssueType,
    ProcessingModule,
    build_routing_graph
)
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ModuleIdentifier,
    ProcessingMessage,
    ProcessingStatus
)
from backend.core.metrics.performance_tracker import PerformanceTracker
from backend.core.orchestration.conductor import DataConductor
from backend.core.registry.component_registry import ComponentRegistry
from backend.core.staging.staging_area import EnhancedStagingArea

# Pipeline source managers
from backend.data_pipeline.source.api.api_manager import ApiManager
from backend.data_pipeline.source.cloud.s3_data_manager import S3DataManager
from backend.data_pipeline.source.database.db_data_manager import DBDataManager
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.stream.stream_manager import StreamManager

# Output handlers
from backend.core.output.handlers import (
    APIOutputHandler,
    DatabaseOutputHandler,
    FileOutputHandler,
    StreamOutputHandler
)

# Configure logging
logger = logging.getLogger(__name__)



class ProcessingStatus(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    ERROR = "ERROR"
    WAITING = "WAITING"







