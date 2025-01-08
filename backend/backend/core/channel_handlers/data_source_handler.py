# backend/core/channel_handlers/source_handler.py
"""
Source Handler Module

This module serves as the central coordination point for all data source operations within
the data pipeline system. It manages communication between the pipeline manager and various
source managers (File, API, Database, S3, Stream), handling source operations lifecycle and
ensuring proper error handling and resource cleanup.

Key Features:
- Unified interface for all data sources
- Operation lifecycle management
- Error handling and recovery
- Resource cleanup
- Message routing and response handling

The handler supports various source types and operations, providing a consistent interface
for the pipeline manager to interact with different data sources while maintaining proper
state management and error recovery.

Source Types Supported:
- File: Local file system operations
- API: REST and GraphQL API connections
- Database: SQL and NoSQL databases
- S3: Cloud storage operations
- Stream: Real-time data streaming

Operations Supported:
- Connect: Establish connection to source
- Read: Read data from source
- Validate: Validate source configuration
- Extract: Extract and transform data
- Disconnect: Clean up source resources
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.channel_handlers.base_channel_handler import BaseChannelHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage

# Source Managers
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.api.api_manager import APIManager
from backend.data_pipeline.source.database.db_manager import DBManager
from backend.data_pipeline.source.cloud.s3_manager import S3Manager
from backend.data_pipeline.source.stream.stream_manager import StreamManager

logger = logging.getLogger(__name__)


class SourceType(Enum):
    """
    Types of data sources supported by the system.

    Each enum value corresponds to a specific source manager implementation.
    """
    FILE = "file"
    API = "api"
    DATABASE = "database"
    STREAM = "stream"
    S3 = "s3"


class SourceOperation(Enum):
    """
    Operations that can be performed on data sources.

    These operations represent the lifecycle of a source interaction.
    """
    CONNECT = "connect"  # Establish connection to source
    READ = "read"  # Read data from source
    VALIDATE = "validate"  # Validate source configuration
    EXTRACT = "extract"  # Extract and transform data
    DISCONNECT = "disconnect"  # Clean up source resources


@dataclass
class SourceContext:
    """
    Context for tracking source operations.

    Attributes:
        pipeline_id: Unique identifier for the pipeline
        source_type: Type of data source
        operation: Current operation being performed
        metadata: Additional context-specific metadata
        created_at: Timestamp of context creation
    """
    pipeline_id: str
    source_type: SourceType
    operation: SourceOperation
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = field(default="initialized")
    error: Optional[str] = field(default=None)


class DataSourceChannelHandler(BaseChannelHandler):
    """
    Handles communication between pipeline manager and source managers.

    This class provides a unified interface for all source operations, managing
    the lifecycle of source interactions and ensuring proper error handling
    and resource cleanup.
    """

    def __init__(self, message_broker: MessageBroker):
        """
        Initialize the source handler.

        Args:
            message_broker: Message broker for component communication
        """
        super().__init__(message_broker, "source_handler")

        # Initialize source managers
        self.source_managers = self._initialize_source_managers(message_broker)

        # Track active source operations
        self.active_sources: Dict[str, SourceContext] = {}

        # Register operation handlers
        self._register_operation_handlers()

        logger.info("SourceHandler initialized with all source managers")

    def _initialize_source_managers(self, message_broker: MessageBroker) -> Dict[SourceType, Any]:
        """
        Initialize all source managers.

        Creates instances of each source manager type with proper dependencies.

        Args:
            message_broker: Message broker for component communication

        Returns:
            Dictionary mapping source types to their managers
        """
        managers = {
            SourceType.FILE: FileManager(message_broker),
            SourceType.API: APIManager(message_broker),
            SourceType.DATABASE: DBManager(message_broker),
            SourceType.STREAM: StreamManager(message_broker),
            SourceType.S3: S3Manager(message_broker)
        }

        # Log initialization of each manager
        for source_type, manager in managers.items():
            logger.info(f"Initialized {source_type.value} source manager")

        return managers

    def _register_operation_handlers(self) -> None:
        """
        Register handlers for different source operations.

        Maps message types to their corresponding handler functions.
        """
        operation_handlers = {
            MessageType.SOURCE_CONNECT: self._handle_source_connect,
            MessageType.SOURCE_READ: self._handle_source_read,
            MessageType.SOURCE_VALIDATE: self._handle_source_validate,
            MessageType.SOURCE_EXTRACT: self._handle_source_extract,
            MessageType.SOURCE_DISCONNECT: self._handle_source_disconnect
        }

        for message_type, handler in operation_handlers.items():
            self.register_callback(message_type, handler)
            logger.debug(f"Registered handler for {message_type.value}")

    def handle_source_request(self, pipeline_id: str, source_type: str,
                              request_data: Dict[str, Any]) -> None:
        """
        Entry point for handling source requests.

        Args:
            pipeline_id: Unique identifier for the pipeline
            source_type: Type of data source
            request_data: Request parameters and configuration
        """
        try:
            source_type_enum = SourceType(source_type)
            source_manager = self.source_managers.get(source_type_enum)

            if not source_manager:
                raise ValueError(f"No manager found for source type: {source_type}")

            # Create and store source context
            context = SourceContext(
                pipeline_id=pipeline_id,
                source_type=source_type_enum,
                operation=SourceOperation.CONNECT,
                metadata=request_data.get('metadata', {}),
                status="processing"
            )

            self.active_sources[pipeline_id] = context
            logger.info(f"Created source context for pipeline {pipeline_id}")

            # Route to appropriate source manager
            source_manager.handle_request(pipeline_id, request_data)

        except Exception as e:
            logger.error(f"Failed to handle source request: {str(e)}", exc_info=True)
            self._handle_source_error(pipeline_id, str(e))

    def route_to_source_manager(self, pipeline_id: str, operation: SourceOperation,
                                data: Dict[str, Any]) -> None:
        """
        Route operation to appropriate source manager.

        Args:
            pipeline_id: Unique identifier for the pipeline
            operation: Operation to perform
            data: Operation parameters and data
        """
        try:
            context = self.active_sources.get(pipeline_id)
            if not context:
                raise ValueError(f"No active source context for pipeline: {pipeline_id}")

            source_manager = self.source_managers.get(context.source_type)
            if not source_manager:
                raise ValueError(f"No manager found for source type: {context.source_type}")

            # Update context
            context.operation = operation
            context.status = "processing"

            # Route operation
            operation_map = {
                SourceOperation.CONNECT: source_manager.connect,
                SourceOperation.READ: source_manager.read_data,
                SourceOperation.VALIDATE: source_manager.validate_source,
                SourceOperation.EXTRACT: source_manager.extract_data,
                SourceOperation.DISCONNECT: source_manager.disconnect
            }

            operation_func = operation_map.get(operation)
            if not operation_func:
                raise ValueError(f"Unsupported operation: {operation}")

            operation_func(pipeline_id, data)
            logger.info(f"Routed {operation.value} operation for pipeline {pipeline_id}")

        except Exception as e:
            logger.error(f"Operation routing error: {str(e)}", exc_info=True)
            self._handle_source_error(pipeline_id, str(e))

    def handle_manager_response(self, message: ProcessingMessage) -> None:
        """
        Handle response from source manager.

        Args:
            message: Response message from source manager
        """
        pipeline_id = message.content['pipeline_id']
        response = message.content['response']

        try:
            context = self.active_sources.get(pipeline_id)
            if not context:
                raise ValueError(f"No active source context for pipeline: {pipeline_id}")

            # Update context status
            context.status = "completed"

            # Forward response to pipeline manager
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.SOURCE_SUCCESS,
                content={
                    'pipeline_id': pipeline_id,
                    'operation': context.operation.value,
                    'result': response,
                    'metadata': context.metadata
                }
            )

            # Cleanup if operation cycle is complete
            if context.operation == SourceOperation.EXTRACT:
                self._cleanup_source(pipeline_id)

            logger.info(f"Processed manager response for pipeline {pipeline_id}")

        except Exception as e:
            logger.error(f"Response handling error: {str(e)}", exc_info=True)
            self._handle_source_error(pipeline_id, str(e))

    def _handle_source_error(self, pipeline_id: str, error_message: str) -> None:
        """
        Handle source operation errors.

        Args:
            pipeline_id: Unique identifier for the pipeline
            error_message: Error details
        """
        context = self.active_sources.get(pipeline_id)
        if context:
            # Update context
            context.status = "error"
            context.error = error_message

            # Notify pipeline manager
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.SOURCE_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'operation': context.operation.value,
                    'error': error_message,
                    'metadata': context.metadata
                }
            )

            # Cleanup failed source
            self._cleanup_source(pipeline_id)
            logger.error(f"Source error handled for pipeline {pipeline_id}: {error_message}")

    def _cleanup_source(self, pipeline_id: str) -> None:
        """
        Clean up source resources.

        Args:
            pipeline_id: Unique identifier for the pipeline
        """
        if pipeline_id in self.active_sources:
            context = self.active_sources[pipeline_id]

            # Use source manager for cleanup
            source_manager = self.source_managers.get(context.source_type)
            if source_manager:
                try:
                    source_manager.cleanup(pipeline_id)
                    logger.info(f"Cleaned up resources for pipeline {pipeline_id}")
                except Exception as e:
                    logger.error(f"Cleanup error for pipeline {pipeline_id}: {str(e)}",
                                 exc_info=True)

            del self.active_sources[pipeline_id]

    def __del__(self):
        """Cleanup handler resources on deletion."""
        for pipeline_id in list(self.active_sources.keys()):
            self._cleanup_source(pipeline_id)
        super().__del__()
