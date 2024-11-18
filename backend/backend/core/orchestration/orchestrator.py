# Standard library imports
from datetime import datetime
import uuid
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
import os

# Third-party imports
from pydantic import BaseModel  # For data validation
import logging
from concurrent.futures import ThreadPoolExecutor  # For parallel processing

# Local imports - assuming these are defined in other modules
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    ProcessingMessage,
    MessageType,
    ProcessingStatus,
    ModuleIdentifier,
)

from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea

# Source manager imports
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.api.api_manager import ApiManager
from backend.data_pipeline.source.cloud.s3_data_manager import S3DataManager
from backend.data_pipeline.source.database.db_data_manager import DBDataManager
from backend.data_pipeline.source.stream.stream_manager import StreamManager

# Output handler imports
from backend.core.output.handlers import (
    DatabaseOutputHandler,
    FileOutputHandler,
    APIOutputHandler,
    StreamOutputHandler
)

# Configure logging to ensure it outputs to the console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info('Orchestrator Started')

# Exception classes
class OrchestratorError(Exception):
    """Base exception for orchestrator errors"""
    pass


class SourceManagerError(OrchestratorError):
    """Exception for source manager related errors"""
    pass


class OutputHandlerError(OrchestratorError):
    """Exception for output handler related errors"""
    pass


# Custom types
ManagerType = Optional[Any]  # Type for source managers
HandlerFunction = Callable[[Any, Dict[str, Any]], None]  # Type for output handlers


class DataOrchestrator:
    """Enhanced orchestrator for managing the entire pipeline with multi-source support"""

    def __init__(self, message_broker: MessageBroker, data_conductor: DataConductor):
        # Core components
        self.message_broker = message_broker
        self.conductor = data_conductor
        self.staging_area = EnhancedStagingArea(message_broker)
        self.module_id = ModuleIdentifier("DataOrchestrator", "manage_pipeline")

        # State tracking
        self.active_pipelines: Dict[str, Dict[str, Any]] = {}

        # Source managers with typing
        self.source_managers: Dict[str, ManagerType] = {
            "file": None,
            "api": None,
            "cloud": None,
            "database": None,
            "stream": None
        }

        # Output handlers with typing
        self.output_handlers: Dict[str, HandlerFunction] = {}

        # Thread pool for parallel processing
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

        # Register with message broker
        self.message_broker.register_module(self.module_id)

        self.logger.info("DataOrchestrator initialized successfully")

    def _get_file_format(self, filename: str) -> str:
        """Helper method to extract file format"""
        _, extension = os.path.splitext(filename)
        return extension.lower()[1:] if extension else "unknown"

    def handle_source_data(self, message: ProcessingMessage) -> str:
        """Handle incoming data from source managers"""
        source_type = message.source_identifier.module_name.lower()

        try:
            # Additional logging for file source
            if source_type == "file":
                metadata = message.content.get("metadata", {})
                filename = metadata.get("filename", "unknown")
                file_format = self._get_file_format(filename)
                file_size = len(message.content.get("data", "")) if isinstance(message.content.get("data"),
                                                                               (str, bytes)) else 0

                self.logger.info(f"""
                    File received by orchestrator:
                    - Filename: {filename}
                    - Format: {file_format}
                    - Size: {file_size} bytes
                    - Source Module: {message.source_identifier.get_tag()}
                    - Timestamp: {datetime.now().isoformat()}
                """)

            # Create new pipeline for this data
            pipeline_id = str(uuid.uuid4())
            self.active_pipelines[pipeline_id] = {
                "source_type": source_type,
                "data": message.content.get("data"),
                "metadata": message.content.get("metadata", {})
            }

            # Create ingestion message to start processing
            ingestion_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("DataIngestion", "ingest"),
                message_type=MessageType.ACTION,
                content={
                    "pipeline_id": pipeline_id,
                    "action": "start_ingestion",
                    "data": message.content.get("data"),
                    "metadata": message.content.get("metadata", {})
                }
            )
            self.message_broker.publish(ingestion_message)

            self.logger.info(f"Started pipeline {pipeline_id} for {source_type} data")
            return pipeline_id

        except Exception as e:
            self.logger.error(f"Error handling source data: {str(e)}")
            raise OrchestratorError(f"Failed to handle source data: {str(e)}")


    def handle_output_message(self, message: ProcessingMessage) -> None:
        """Handle pipeline output messages"""
        pipeline_id = message.content.get("pipeline_id")
        if not pipeline_id or pipeline_id not in self.active_pipelines:
            self.logger.warning(f"Received output message for unknown pipeline: {pipeline_id}")
            return

        pipeline_state = self.active_pipelines[pipeline_id]
        output_data = message.content.get("output_data")
        destination = message.content.get("destination", "default")

        # Route to appropriate output handler
        if destination in self.output_handlers:
            try:
                self.thread_pool.submit(
                    self.output_handlers[destination],
                    output_data,
                    pipeline_state
                )
                self.logger.info(f"Output processing started for pipeline {pipeline_id}")
            except Exception as e:
                self._handle_output_error(pipeline_id, destination, str(e))
        else:
            # Log warning about unknown destination
            warning_message = ProcessingMessage(
                source_identifier=self.module_id,
                message_type=MessageType.WARNING,
                content={
                    "pipeline_id": pipeline_id,
                    "warning": f"No handler for destination: {destination}"
                }
            )
            self.message_broker.publish(warning_message)
            self.logger.warning(f"No handler found for destination: {destination}")

    def _handle_output_error(self, pipeline_id: str, destination: str, error: str) -> None:
        """Handle errors in output processing"""
        error_message = ProcessingMessage(
            source_identifier=self.module_id,
            message_type=MessageType.ERROR,
            content={
                "pipeline_id": pipeline_id,
                "error": f"Output processing failed for {destination}: {error}"
            },
            status=ProcessingStatus.ERROR
        )
        self.message_broker.publish(error_message)

        # Update pipeline state
        pipeline_state = self.active_pipelines[pipeline_id]
        pipeline_state["status"] = ProcessingStatus.ERROR
        pipeline_state["error"] = error

        self.logger.error(f"Output processing error in pipeline {pipeline_id}: {error}")

    def __del__(self):
        """Cleanup resources"""
        self.thread_pool.shutdown(wait=True)


# Example usage and setup function
def setup_pipeline() -> DataOrchestrator:
    """Example of setting up and using the pipeline with multiple sources"""
    broker = MessageBroker()
    conductor = DataConductor(broker)
    orchestrator = DataOrchestrator(broker, conductor)

    # Register source managers
    orchestrator.register_source_manager("file", FileManager(broker))
    orchestrator.register_source_manager("api", ApiManager(broker))
    orchestrator.register_source_manager("cloud", S3DataManager(broker))
    orchestrator.register_source_manager("database", DBDataManager(broker))
    orchestrator.register_source_manager("stream", StreamManager(broker))

    # Register output handlers
    orchestrator.register_output_handler(
        "database",
        DatabaseOutputHandler().handle_output
    )
    orchestrator.register_output_handler(
        "file",
        FileOutputHandler().handle_output
    )
    orchestrator.register_output_handler(
        "api",
        APIOutputHandler().handle_output
    )
    orchestrator.register_output_handler(
        "stream",
        StreamOutputHandler().handle_output
    )

    # Initialize pipeline
    orchestrator.initialize_pipeline()

    return orchestrator