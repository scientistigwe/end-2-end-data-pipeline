# Standard library imports
from datetime import datetime
import uuid
from typing import Dict, List, Any, Optional, Callable
from enum import Enum

# Third-party imports
from pydantic import BaseModel  # For data validation
import logging
from concurrent.futures import ThreadPoolExecutor  # For parallel processing

# Local imports - assuming these are defined in other modules
from backend.backend.core.messaging.broker import MessageBroker
from backend.backend.core.messaging.types import (
    ProcessingMessage,
    MessageType,
    ProcessingStatus,
    ModuleIdentifier,
)

from backend.backend.core.orchestration.conductor import DataConductor
from backend.backend.core.staging.staging_area import EnhancedStagingArea

# Source manager imports
from backend.backend.data_pipeline.source.file.file_manager import FileManager
from backend.backend.data_pipeline.source.api.api_manager import ApiManager
from backend.backend.data_pipeline.source.cloud.s3_data_manager import S3DataManager
from backend.backend.data_pipeline.source.database.db_data_manager import DBDataManager
from backend.backend.data_pipeline.source.stream.stream_manager import StreamManager

# Output handler imports
from backend.backend.core.output.handlers import (
    DatabaseOutputHandler,
    FileOutputHandler,
    APIOutputHandler,
    StreamOutputHandler
)


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
        # Initialize logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

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

    def register_source_manager(self, source_type: str, manager: ManagerType) -> None:
        """Register a data source manager"""
        if source_type not in self.source_managers:
            raise SourceManagerError(f"Unknown source type: {source_type}")

        self.source_managers[source_type] = manager

        # Subscribe to data messages from this source
        self.message_broker.subscribe_to_module(
            manager.module_id.get_tag(),
            self.handle_source_data
        )

        self.logger.info(f"Registered source manager for: {source_type}")

    def register_output_handler(self, destination: str, handler: HandlerFunction) -> None:
        """Register handler for pipeline outputs"""
        self.output_handlers[destination] = handler
        self.logger.info(f"Registered output handler for: {destination}")

    def initialize_pipeline(self) -> None:
        """Initialize pipeline with all available modules and transitions"""
        # Register core pipeline stages
        stages = [
            (ModuleIdentifier("DataIngestion", "ingest"), ["raw_data"]),
            (ModuleIdentifier("DataQuality", "check"), ["quality_report"]),
            (ModuleIdentifier("EDA", "analyze"), ["analysis_report"]),
            (ModuleIdentifier("DataCleaning", "clean"), ["cleaned_data"]),
            (ModuleIdentifier("DataTransform", "transform"), ["transformed_data"]),
            (ModuleIdentifier("DataOutput", "output"), ["output_data"])
        ]

        # Register module flows
        for i, (module, outputs) in enumerate(stages[:-1]):
            next_module = stages[i + 1][0]
            self.conductor.register_module_flow(
                module,
                [next_module],
                {"status": "success", "outputs": outputs}
            )

        self.logger.info("Pipeline initialized with all stages")

    def handle_source_data(self, message: ProcessingMessage) -> str:
        """Handle incoming data from source managers"""
        source_type = message.source_identifier.module_name.lower()

        try:
            # Create new pipeline for this data
            pipeline_id = self.start_pipeline({
                "source_type": source_type,
                "data": message.content.get("data"),
                "metadata": message.content.get("metadata", {})
            })

            # Track source in pipeline state
            self.active_pipelines[pipeline_id]["source_type"] = source_type

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