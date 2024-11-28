from typing import Dict, Any
import logging
from .file_manager import FileManager
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea
from backend.core.orchestration.orchestrator import DataOrchestrator
import pandas as pd

logger = logging.getLogger(__name__)


class FileService:
    """Service layer for managing file operations"""

    def __init__(self, message_broker=None, orchestrator=None):
        """
        Initialize FileService with dependency injection

        Args:
            message_broker: MessageBroker instance
            orchestrator: DataOrchestrator instance
        """
        # Allow injection of dependencies
        self.message_broker = message_broker or MessageBroker()

        # Initialize the FileManager with the message broker
        self.file_manager = FileManager(self.message_broker)

        # Store orchestrator reference if provided
        self.orchestrator = orchestrator

        logger.info("FileService initialized with MessageBroker")

    def _initialize_data_orchestrator(self):
        """
        Initialize the DataOrchestrator to ensure all required modules are registered
        """
        try:
            # Create necessary dependencies
            data_conductor = DataConductor(self.message_broker)
            staging_area = EnhancedStagingArea(self.message_broker)

            # Directly instantiate the DataOrchestrator
            data_orchestrator = DataOrchestrator(
                message_broker=self.message_broker,
                data_conductor=data_conductor,
                staging_area=staging_area
            )

        except Exception as e:
            logger.error(f"Failed to initialize DataOrchestrator: {str(e)}", exc_info=True)
            raise

    logger.info("FileService initialized with MessageBroker")

    def handle_file_upload(self, file_obj: Any) -> Dict[str, Any]:
        """
        Service layer method to handle file uploads using FileManager.

        Args:
            file_obj: File object to be processed

        Returns:
            dict: Processing result containing status and relevant data
        """
        filename = getattr(file_obj, 'filename', 'unknown')
        logger.info(f"Handling file upload: {filename}")

        try:
            # Delegate to FileManager for processing
            result = self.file_manager.process_file(file_obj)

            # Replace NaN values with None
            def replace_nan(obj):
                if isinstance(obj, dict):
                    return {k: replace_nan(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [replace_nan(v) for v in obj]
                elif pd.isna(obj):
                    return None
                return obj

            result = replace_nan(result)

            # Log the result
            logger.info(f"File upload result for {filename}: {result.get('status')}")

            return result

        except Exception as e:
            logger.error(f"Unexpected error during file upload for {filename}", exc_info=True)

            return {
                'status': 'error',
                'message': f"File upload failed: {str(e)}",
                'filename': filename
            }

    def get_metadata(self) -> Dict[str, Any]:
        """
        Retrieves metadata from the last processed file.
        Delegates to FileManager while handling errors.

        Returns:
            dict: File metadata or error information
        """
        try:
            return self.file_manager.get_file_metadata()
        except Exception as e:
            logger.error(f"Error retrieving metadata: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to retrieve metadata: {str(e)}"
            }