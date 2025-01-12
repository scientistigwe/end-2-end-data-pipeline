# backend/core/utils/rate_limiter.py

import os
from typing import Dict, Any
import asyncio
from enum import Enum
from datetime import time
from uuid import uuid4
from aiohttp import web
from dataclasses import dataclass, field

class AsyncRateLimiter:
    """Rate limiter for async operations"""

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self._calls = []

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def acquire(self):
        """Acquire permission to proceed"""
        now = time.time()
        # Remove old calls
        self._calls = [call for call in self._calls if call > now - self.period]
        if len(self._calls) >= self.max_calls:
            sleep_time = self._calls[0] - (now - self.period)
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
        self._calls.append(now)


# 2. Constants needed in backend/core/messaging/types.py
class ProcessingStage(Enum):
    """Processing stages for the pipeline"""
    INITIAL_VALIDATION = "initial_validation"
    DATA_EXTRACTION = "data_extraction"
    DATA_VALIDATION = "data_validation"
    QUALITY_CHECK = "quality_check"
    PROCESSING = "processing"
    COMPLETED = "completed"


class ComponentType(Enum):
    """Types of components in the system"""
    SERVICE = "service"
    MANAGER = "manager"
    HANDLER = "handler"
    VALIDATOR = "validator"


class MessageType(Enum):
    """Types of messages in the system"""
    FILE_UPLOAD_REQUEST = "file_upload_request"
    FILE_PROCESSING_REQUEST = "file_processing_request"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    PROCESSING_COMPLETE = "processing_complete"


# 3. Reference implementation for ModuleIdentifier
@dataclass
class ModuleIdentifier:
    """Identifier for system modules"""
    component_name: str
    component_type: ComponentType
    method_name: str = ""
    instance_id: str = field(default_factory=lambda: str(uuid4()))

    def get_tag(self) -> str:
        """Get string representation of identifier"""
        return f"{self.component_type.value}.{self.component_name}"


# 4. Config class updates
class Config:
    """Enhanced configuration class"""

    def __init__(self, **kwargs):
        self.UPLOAD_DIRECTORY = kwargs.get('upload_directory', 'uploads')
        self.ALLOWED_FORMATS = kwargs.get('allowed_formats', ['csv', 'xlsx', 'parquet', 'json'])
        self.FILE_SIZE_THRESHOLD_MB = kwargs.get('max_file_size_mb', 50)
        self.CHUNK_SIZE = kwargs.get('chunk_size', 8192)
        self.ENCODING = kwargs.get('encoding', 'utf-8')

        # Create upload directory if it doesn't exist
        os.makedirs(self.UPLOAD_DIRECTORY, exist_ok=True)


# 5. MetricsCollector interface
class MetricsCollector:
    """Metrics collection interface"""

    async def record_validation_metrics(
            self,
            file_id: str,
            duration: float,
            results: Dict[str, Any]
    ) -> None:
        """Record validation metrics"""
        pass  # Implement actual metrics collection


# 6. WebSocket handler utility
class WebSocketManager:
    """WebSocket connection manager"""

    def __init__(self):
        self.connections: Dict[str, web.WebSocketResponse] = {}

    async def send_message(self, connection_id: str, message: Dict[str, Any]) -> None:
        """Send message to WebSocket client"""
        if connection_id in self.connections:
            await self.connections[connection_id].send_json(message)

    async def close_connection(self, connection_id: str) -> None:
        """Close WebSocket connection"""
        if connection_id in self.connections:
            await self.connections[connection_id].close()
            del self.connections[connection_id]