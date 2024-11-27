from typing import Dict, Any
import logging
from .file_manager import FileManager
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea
from backend.core.orchestration.orchestrator import DataOrchestrator

logger = logging.getLogger(__name__)


class FileService:
    """
    Service layer for managing file operations. Acts as a thin wrapper around FileManager
    while providing error handling and logging.
        """

    def __init__(self):
            # Create the message broker
            self.message_broker = MessageBroker()

            # Initialize the DataOrchestrator first
            self._initialize_data_orchestrator()

            # Now create the FileManager
            self.file_manager = FileManager(self.message_broker)
            logger.info("FileService initialized with MessageBroker and DataOrchestrator")

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
        Service layer method to handle file uploads.
        Provides error handling and logging around FileManager operations.

        Args:
            file_obj: File object with read() method and filename attribute

        Returns:
            dict: Processing result containing status and relevant data
        """
        filename = getattr(file_obj, 'filename', 'unknown')

        try:
            # Delegate processing to FileManager
            result = self.file_manager.process_file(file_obj)
            logger.info(f"Successfully processed file: {filename}")
            return result

        except Exception as e:
            logger.error(f"Error processing file {filename}: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
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