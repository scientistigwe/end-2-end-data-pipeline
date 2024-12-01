# backend/core/channel_handlers/source_handler.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.channel_handlers.base_handler import BaseHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage

# Source Managers
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.api.api_manager import ApiManager
from backend.data_pipeline.source.database.db_data_manager import DBDataManager
from backend.data_pipeline.source.stream.stream_manager import StreamManager
from backend.data_pipeline.source.cloud.s3_data_manager import S3DataManager

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """Types of data sources"""
    FILE = "file"
    API = "api"
    DATABASE = "database"
    STREAM = "stream"
    S3 = "s3"


class SourceOperation(Enum):
    """Source operations"""
    CONNECT = "connect"
    READ = "read"
    VALIDATE = "validate"
    EXTRACT = "extract"
    DISCONNECT = "disconnect"


@dataclass
class SourceContext:
    """Context for source operations"""
    pipeline_id: str
    source_type: SourceType
    operation: SourceOperation
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)


class SourceHandler(BaseHandler):
    """
    Handles communication between pipeline manager and source managers
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "source_handler")

        # Initialize source managers
        self.source_managers = self._initialize_source_managers(message_broker)

        # Track active source operations
        self.active_sources: Dict[str, SourceContext] = {}

        # Register operation handlers
        self._register_operation_handlers()

    def _initialize_source_managers(self, message_broker: MessageBroker) -> Dict[str, Any]:
        """Initialize all source managers"""
        return {
            SourceType.FILE: FileManager(message_broker),
            SourceType.API: ApiManager(message_broker),
            SourceType.DATABASE: DBDataManager(message_broker),
            SourceType.STREAM: StreamManager(message_broker),
            SourceType.S3: S3DataManager(message_broker)
        }

    def _register_operation_handlers(self) -> None:
        """Register handlers for source operations"""
        self.register_callback(
            MessageType.SOURCE_CONNECT,
            self._handle_source_connect
        )
        self.register_callback(
            MessageType.SOURCE_READ,
            self._handle_source_read
        )
        self.register_callback(
            MessageType.SOURCE_VALIDATE,
            self._handle_source_validate
        )
        self.register_callback(
            MessageType.SOURCE_EXTRACT,
            self._handle_source_extract
        )

    def handle_source_request(self, pipeline_id: str, source_type: str,
                              request_data: Dict[str, Any]) -> None:
        """Entry point for source requests"""
        try:
            source_type_enum = SourceType(source_type)
            source_manager = self.source_managers.get(source_type_enum)

            if not source_manager:
                raise ValueError(f"No manager found for source type: {source_type}")

            # Create source context
            context = SourceContext(
                pipeline_id=pipeline_id,
                source_type=source_type_enum,
                operation=SourceOperation.CONNECT,
                metadata=request_data.get('metadata', {})
            )

            self.active_sources[pipeline_id] = context

            # Route to appropriate source manager
            source_manager.handle_request(pipeline_id, request_data)

        except Exception as e:
            self.logger.error(f"Failed to handle source request: {str(e)}")
            self._handle_source_error(pipeline_id, str(e))

    def route_to_source_manager(self, pipeline_id: str, operation: SourceOperation,
                                data: Dict[str, Any]) -> None:
        """Route operation to appropriate source manager"""
        context = self.active_sources.get(pipeline_id)
        if not context:
            raise ValueError(f"No active source context for pipeline: {pipeline_id}")

        source_manager = self.source_managers.get(context.source_type)
        if not source_manager:
            raise ValueError(f"No manager found for source type: {context.source_type}")

        # Update operation in context
        context.operation = operation

        # Route operation to manager
        operation_map = {
            SourceOperation.CONNECT: source_manager.connect,
            SourceOperation.READ: source_manager.read_data,
            SourceOperation.VALIDATE: source_manager.validate_source,
            SourceOperation.EXTRACT: source_manager.extract_data,
            SourceOperation.DISCONNECT: source_manager.disconnect
        }

        operation_func = operation_map.get(operation)
        if operation_func:
            operation_func(pipeline_id, data)
        else:
            raise ValueError(f"Unsupported operation: {operation}")

    def handle_manager_response(self, message: ProcessingMessage) -> None:
        """Handle response from source manager"""
        pipeline_id = message.content['pipeline_id']
        response = message.content['response']

        try:
            context = self.active_sources.get(pipeline_id)
            if not context:
                raise ValueError(f"No active source context for pipeline: {pipeline_id}")

            # Forward response to pipeline manager
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.SOURCE_SUCCESS,
                content={
                    'pipeline_id': pipeline_id,
                    'operation': context.operation.value,
                    'result': response
                }
            )

            # If extract operation completed, cleanup
            if context.operation == SourceOperation.EXTRACT:
                self._cleanup_source(pipeline_id)

        except Exception as e:
            self._handle_source_error(pipeline_id, str(e))

    def _handle_source_error(self, pipeline_id: str, error_message: str) -> None:
        """Handle source operation errors"""
        context = self.active_sources.get(pipeline_id)
        if context:
            # Notify pipeline manager of error
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.SOURCE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'operation': context.operation.value,
                    'error': error_message
                }
            )

            # Cleanup failed source
            self._cleanup_source(pipeline_id)

    def _cleanup_source(self, pipeline_id: str) -> None:
        """Clean up source resources"""
        if pipeline_id in self.active_sources:
            context = self.active_sources[pipeline_id]

            # Use source manager for cleanup
            source_manager = self.source_managers.get(context.source_type)
            if source_manager:
                try:
                    source_manager.cleanup(pipeline_id)
                except Exception as e:
                    self.logger.error(f"Error during source cleanup: {str(e)}")

            del self.active_sources[pipeline_id]

    def __del__(self):
        """Cleanup handler resources"""
        for pipeline_id in list(self.active_sources.keys()):
            self._cleanup_source(pipeline_id)
        super().__del__()
