import logging
import io
import uuid
from io import BytesIO
import pandas as pd
from typing import Dict, Tuple, Any, Optional
from .file_validator import FileValidator
from .file_fetcher import FileFetcher
from backend.core.messaging.types import ProcessingMessage, MessageType, ModuleIdentifier, ProcessingStatus

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileManager:
    def __init__(self, message_broker):
            self.message_broker = message_broker
            self.module_id = ModuleIdentifier("FileManager", "process_file")
            self.validator = FileValidator()

            # Register with message broker
            self.message_broker.register_module(self.module_id)

            # Subscribe to orchestrator responses using the correct method
            self.message_broker.subscribe_to_module(
                ModuleIdentifier("DataOrchestrator", "manage_pipeline").get_tag(),
                self._handle_orchestrator_response
            )

            logger.info('File Manager Started with Message Broker')
            self.processed_data: Optional[Dict[str, Any]] = None
            self.pending_files: Dict[str, Dict[str, Any]] = {}

    def _extract_metadata_from_content(self, file_obj: Any) -> Dict[str, Any]:
        """Extract comprehensive metadata from file content."""
        try:
            file_content = file_obj.read()
            filename = file_obj.filename

            metadata = {
                'filename': filename,
                'file_size': len(file_content),
                'file_type': filename.split('.')[-1].lower()
            }

            file_metadata_extractors = {
                '.csv': lambda content: pd.read_csv(BytesIO(content), nrows=1),
                '.json': lambda content: pd.read_json(BytesIO(content)),
                '.xlsx': lambda content: pd.read_excel(BytesIO(content), sheet_name=None),
                '.parquet': lambda content: pd.read_parquet(BytesIO(content))
            }

            ext = f".{metadata['file_type']}"
            extractor = file_metadata_extractors.get(ext)

            if extractor:
                df = extractor(file_content)

                if ext == '.xlsx':
                    metadata['sheet_names'] = list(df.keys())
                    metadata['columns'] = list(df[list(df.keys())[0]].columns)
                else:
                    metadata['columns'] = list(df.columns) if hasattr(df, 'columns') else []
                    metadata['row_count'] = len(df) if hasattr(df, '__len__') else 0

            return metadata

        except Exception as e:
            logger.error(f"Metadata extraction error: {str(e)}")
            raise ValueError(f"Failed to extract metadata: {str(e)}")

    def get_file_metadata(self, file_obj: Any) -> Dict[str, Any]:
        """Generate metadata for a given file object."""
        try:
            metadata = self._extract_metadata_from_content(file_obj)
            return {'status': 'success', 'metadata': metadata}
        except Exception as e:
            logger.error(f"Metadata generation error: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _validate_file(self, file_obj: Any) -> Tuple[bool, str]:
        """Perform all file validations."""
        try:
            validation_checks = [
                self.validator.validate_file_format,
                self.validator.validate_file_size,
                self.validator.validate_file_integrity,
                self.validator.validate_security
            ]

            for check in validation_checks:
                valid, message = check(file_obj)
                if not valid:
                    logger.warning(f"File validation failed: {message}")
                    return False, message
            return True, "Validation successful"
        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return False, f"Validation error: {str(e)}"

    def _create_file_obj(self, file_content: bytes, filename: str) -> Any:
            """Create a standardized file object for processing."""

            class FileObj:
                def __init__(self, content: bytes, filename: str):
                    self._content = content
                    self.filename = filename
                    self.content_type = f'application/{filename.split(".")[-1]}'
                    self._position = 0

                def read(self) -> bytes:
                    return self._content

                def seek(self, pos: int) -> None:
                    self._position = pos

                @property
                def stream(self) -> 'StreamWrapper':
                    return self.StreamWrapper(self._content)

                class StreamWrapper:
                    def __init__(self, content: bytes):
                        self._content = content

                    def read(self) -> bytes:
                        return self._content

            return FileObj(file_content, filename)

    def process_file(self, file: Any) -> Dict[str, Any]:
            """Main method to process the file and return structured data."""
            filename = getattr(file, 'filename', 'unknown')
            logger.info(f"Starting to process file: {filename}")

            try:
                # Reset processed data for new file
                self.processed_data = None

                # Read file content
                file_content = file.read()
                if not file_content:
                    return self._send_error_message(filename, "Empty file content")

                # Create file object
                file_obj = self._create_file_obj(file_content, filename)

                # Get metadata
                metadata_result = self.get_file_metadata(file_obj)
                if metadata_result['status'] != 'success':
                    return self._send_error_message(filename, metadata_result['message'])

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

                self.processed_data = {
                    'filename': filename,
                    'status': 'success',
                    'source_type': 'file',
                    'metadata': metadata_result['metadata'],
                    'data': df.to_dict(orient='records')
                }

                # Store in pending files and send to orchestrator
                file_id = str(uuid.uuid4())
                self.pending_files[file_id] = self.processed_data
                self._send_success_message(file_id, self.processed_data)

                return self.processed_data

            except Exception as e:
                logger.error(f"File processing error: {str(e)}", exc_info=True)
                return self._send_error_message(filename, str(e))

    def _send_success_message(self, file_id: str, processed_data: Dict[str, Any]) -> None:
            """Send success message to orchestrator with complete processed data"""
            success_msg = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=ModuleIdentifier("DataOrchestrator", "manage_pipeline"),
                message_type=MessageType.ACTION,
                content={
                    'file_id': file_id,
                    'action': 'process_file_data',
                    'data': processed_data['data'],
                    'metadata': processed_data['metadata'],
                    'source_type': 'file',
                    'filename': processed_data['filename']
                }
            )
            logger.info(f"Sending complete processed data to orchestrator for file: {processed_data['filename']}")
            self.message_broker.publish(success_msg)

    def _send_error_message(self, filename: str, error_message: str) -> Dict[str, Any]:
            """Helper method to send error messages to orchestrator"""
            error_data = {
                'filename': filename,
                'status': 'error',
                'source_type': 'file',
                'message': error_message
            }

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

    def _handle_orchestrator_response(self, message: ProcessingMessage) -> None:
            """Handle responses from the orchestrator"""
            try:
                file_id = message.content.get('file_id')
                if not file_id or file_id not in self.pending_files:
                    logger.warning(f"Received response for unknown file ID: {file_id}")
                    return

                if message.message_type == MessageType.ACTION:
                    logger.info(
                        f"File {self.pending_files[file_id]['filename']} successfully processed by orchestrator")
                    # Clean up pending file
                    del self.pending_files[file_id]
                elif message.message_type == MessageType.ERROR:
                    logger.error(
                        f"Orchestrator reported error for file {self.pending_files[file_id]['filename']}: {message.content.get('error')}")
                    # Handle retry logic or cleanup as needed
                    self._handle_orchestrator_error(file_id, message.content.get('error'))

            except Exception as e:
                logger.error(f"Error handling orchestrator response: {str(e)}")

    def _handle_orchestrator_error(self, file_id: str, error_message: str) -> None:
            """Handle errors reported by the orchestrator"""
            if file_id in self.pending_files:
                file_data = self.pending_files[file_id]
                logger.error(f"Processing failed for file {file_data['filename']}: {error_message}")
                # Implement retry logic or cleanup as needed
                del self.pending_files[file_id]

    def _send_error_message(self, filename: str, error_message: str) -> Dict[str, Any]:
        """Helper method to send error messages to orchestrator"""
        error_data = {
            'filename': filename,
            'status': 'error',
            'source_type': 'file',
            'message': error_message
        }

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

    def get_metadata(self) -> Dict[str, Any]:
        """Extract metadata from processed file."""
        try:
            if not self.processed_data:
                return {"error": "No file has been processed yet"}

            metadata = self.processed_data.get('metadata', {})
            return {
                "file_size_mb": metadata.get('file_size', 0) / (1024 * 1024),
                "file_format": metadata.get('file_type', 'unknown'),
                "columns": metadata.get('columns', []),
                "row_count": metadata.get('row_count', 0)
            }

        except Exception as e:
            logger.error(f"Metadata extraction error: {str(e)}")
            return {"error": str(e)}