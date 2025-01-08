# backend/data_pipeline/source/file/file_service.py
from datetime import datetime
from typing import Dict, Any
import logging
from .file_manager import FileManager
from backend.core.messaging.broker import MessageBroker
from backend.core.orchestration.data_conductor import DataConductor
from backend.core.orchestration.staging_manager import StagingManager
from backend.core.orchestration.pipeline_manager import PipelineManager
import pandas as pd

logger = logging.getLogger(__name__)


class FileService:
    """Service layer for managing file operations"""

    def __init__(self, message_broker=None, pipeline_manager=None):
        """Initialize FileService with dependency injection"""
        self.message_broker = message_broker or MessageBroker()
        self.file_manager = FileManager(self.message_broker)
        self.pipeline_manager = pipeline_manager or self._initialize_pipeline_manager()
        logger.info("FileService initialized with MessageBroker")

    def _initialize_pipeline_manager(self):
        """Initialize PipelineManager with required dependencies"""
        try:
            # Create data conductor for routing
            data_conductor = DataConductor(self.message_broker)

            # Create staging manager for data storage
            staging_manager = StagingManager(self.message_broker)

            # Initialize pipeline manager
            pipeline_manager = PipelineManager(
                message_broker=self.message_broker,
                db_session=None  # Add if needed
            )

            logger.info("Initialized PipelineManager with dependencies")
            return pipeline_manager

        except Exception as e:
            logger.error(f"Failed to initialize PipelineManager: {str(e)}", exc_info=True)
            raise

    def _create_pipeline_entry(self, filename: str, upload_result: Dict) -> str:
        """Create a pipeline entry for tracking"""
        # Create pipeline config
        config = {
            'filename': filename,
            'source_type': 'file',
            'metadata': upload_result.get('metadata', {}),
            'start_time': datetime.now().isoformat()
        }

        # Start pipeline using pipeline manager
        pipeline_id = self.pipeline_manager.start_pipeline(config)
        logger.info(f"Created pipeline {pipeline_id} for file {filename}")
        return pipeline_id

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

            if result.get('status') == 'success':
                # Create pipeline entry when file is successfully uploaded
                pipeline_id = self._create_pipeline_entry(filename, result)

                # Add pipeline_id to result
                result['pipeline_id'] = pipeline_id

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

    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get pipeline status"""
        try:
            return self.pipeline_manager.get_pipeline_status(pipeline_id)
        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'message': f"Failed to get pipeline status: {str(e)}"
            }