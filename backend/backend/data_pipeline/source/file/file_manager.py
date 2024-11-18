# file_manager.py
import logging
from io import BytesIO
import pandas as pd
from .file_validator import FileValidator
from .file_fetcher import FileFetcher
from backend.core.messaging.types import ProcessingMessage, MessageType, ModuleIdentifier, ProcessingStatus
import pandas as df


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileManager:
    def __init__(self, message_broker):
        self.message_broker = message_broker
        self.module_id = ModuleIdentifier("FileManager", "process_file")
        self.validator = FileValidator()
        # Register with message broker
        self.message_broker.register_module(self.module_id)
        logger.info('File Manager Started with Message Broker')

    def _create_file_obj(self, file_content, filename):
        """Create a standardized file object for processing."""

        class FileObj:
            def __init__(self, content, filename):
                self._content = content
                self.filename = filename
                self.content_type = f'application/{filename.split(".")[-1]}'

            def read(self):
                return self._content

            def seek(self, pos):
                pass

            @property
            def stream(self):
                class StreamWrapper:
                    def __init__(self, content):
                        self._content = content

                    def read(self):
                        return self._content

                return StreamWrapper(self._content)

        return FileObj(file_content, filename)

    def _validate_file(self, file_obj):
        """Perform all file validations."""
        validation_checks = [
            self.validator.validate_file_format,
            self.validator.validate_file_size,
            self.validator.validate_file_integrity,
            self.validator.validate_security
        ]

        for check in validation_checks:
            valid, message = check(file_obj)
            if not valid:
                return False, message
        return True, "Validation successful"

    def process_file(self, file):
        """Main method to process the file and return structured data."""
        filename = getattr(file, 'filename', 'unknown')  # Safe filename access

        try:
            file_content = file.read()

            # Create standardized file object
            file_obj = self._create_file_obj(file_content, filename)

            # Validate file
            is_valid, message = self._validate_file(file_obj)
            if not is_valid:
                return self._send_error_message(filename, message)

            # Process file using FileFetcher
            file_fetcher = FileFetcher(file_obj)
            data, message = file_fetcher.convert_to_dataframe()

            if data is None:
                return self._send_error_message(filename, message)

            # Handle different data types
            if isinstance(data, BytesIO):
                df = pd.read_parquet(data)
            else:
                df = data

            processed_data = {
                'filename': filename,
                'status': 'success',
                'source_type': 'file',
                'metadata': file_fetcher.extract_metadata(df),
                'data': df.to_dict(orient='records')
            }

            # Create message without status first
            orchestrator_message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("DataOrchestrator", "manage_pipeline"),
                message_type=MessageType.ACTION,
                content={
                    'action': 'process_file_data',
                    'data': processed_data
                }
            )

            logger.info(f"Sending message to orchestrator: {orchestrator_message}")
            self.message_broker.publish(orchestrator_message)

            return processed_data

        except Exception as e:
            logger.error(f"File processing error: {str(e)}")
            return self._send_error_message(filename, str(e))

    def _send_error_message(self, filename, error_message):
        """Helper method to send error messages to orchestrator"""
        error_data = {
            'filename': filename,
            'status': 'error',
            'source_type': 'file',
            'message': error_message
        }

        # Create error message without status
        error_msg = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=ModuleIdentifier("DataOrchestrator", "manage_pipeline"),
            message_type=MessageType.ERROR,
            content={
                'action': 'handle_file_error',
                'error_data': error_data
            }
        )

        logger.error(f"Sending error message: {error_msg}")
        self.message_broker.publish(error_msg)
        return error_data

    def prepare_for_orchestration(self):
        """
        Prepare file data for orchestration processing.

        Returns:
            dict: Structured data ready for orchestrator module
        """
        try:
            # Process file if not already processed
            if not self.processed_data:
                result = self.process_file()
                if result.get('status') != 'success':
                    return {"error": result.get('message', 'Unknown error')}

            # Get the data from processed results
            data = self.processed_data.get('data')

            # Log the actual file format
            file_format = self.file.filename.rsplit('.', 1)[-1].lower() if '.' in self.file.filename else 'unknown'
            logger.info(f"Preparing file for orchestration. Detected file format: {file_format}")

            # Convert data to DataFrame for processing
            if isinstance(data, list):  # If data is in records format
                df = pd.DataFrame(data)
            elif isinstance(data, pd.DataFrame):
                df = data
            elif isinstance(data, BytesIO):  # If data is in Parquet format
                # For large datasets, convert to Parquet
                if len(df) > 1000:  # Arbitrary threshold, adjust as needed
                    parquet_buffer = BytesIO()
                    df.to_parquet(parquet_buffer)
                    return {
                        "status": "success",
                        "message": "File converted to in-memory Parquet",
                        "parquet_data": parquet_buffer.getvalue()
                    }
                # For smaller datasets, return preview
                else:
                    return {
                        "status": "success",
                        "message": "File loaded as DataFrame",
                        "data_preview": df.head().to_dict(orient='records')
                    }
            else:
                return {
                    "status": "error",
                    "message": "Empty dataset"
                }

        except Exception as e:
            logger.error(f"Orchestration preparation error: {e}")
            return {"error": str(e)}

    def get_metadata(self):
        """Extract metadata from processed file."""
        try:
            if not self.processed_data:
                self.process_file()

            if self.processed_data.get('status') != 'success':
                return {"error": self.processed_data.get('message', 'Unknown error')}

            metadata = self.processed_data.get('metadata', {})
            return {
                "file_size_mb": metadata.get('file_size', 0),
                "file_format": metadata.get('file_type', 'unknown'),
                "columns": metadata.get('columns', []),
                "row_count": metadata.get('row_count', 0)
            }

        except Exception as e:
            logger.error(f"Metadata extraction error: {e}")
            return {"error": str(e)}
