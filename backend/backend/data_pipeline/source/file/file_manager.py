import logging
import io
import uuid
from io import BytesIO
import pandas as pd
from typing import Dict, Tuple, Any, Optional

from torch.utils.hipify.hipify_python import meta_data

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

    def get_file_metadata(self, file_obj: Any) -> Dict[str, Any]:
        """Generate metadata for a given file object using FileFetcher."""
        try:
            file_fetcher = FileFetcher(file_obj)
            metadata = file_fetcher.extract_metadata()
            logger.info(f'Metadata: {metadata}')
            return {'status': 'success', 'metadata': metadata}
        except Exception as e:
            logger.error(f"Metadata generation error: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _validate_file(self, file_fetcher: FileFetcher) -> Tuple[bool, str]:
        """
        Perform file validations using FileFetcher and its extracted metadata.
        """
        try:
            # Retrieve metadata from FileFetcher
            metadata = file_fetcher.get_metadata()
            if "error" in metadata:
                logger.warning(f"File validation failed: {metadata['error']}")
                return False, metadata["error"]

            # Validate file format and size using metadata
            format_valid, format_message = self.validator.validate_file_format(metadata)
            if not format_valid:
                logger.warning(f"File format validation failed: {format_message}")
                return False, format_message

            size_valid, size_message = self.validator.validate_file_size(metadata)
            if not size_valid:
                logger.warning(f"File size validation failed: {size_message}")
                return False, size_message

            # Validate file integrity using the preloaded file content
            data = file_fetcher.load_file()
            integrity_valid, integrity_message = self.validator.validate_file_integrity(data)
            if not integrity_valid:
                logger.warning(f"File integrity validation failed: {integrity_message}")
                return False, integrity_message

            # Additional file-specific checks
            if metadata["file_type"] not in ["csv", "json", "parquet", "xlsx"]:
                return False, "File type not allowed. Expected file types are 'csv', 'json', 'parquet', and 'xlsx'"

            logger.info("File validation successful")
            return True, "Validation successful"

        except Exception as e:
            logger.error(f"File validation error: {str(e)}", exc_info=True)
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
        logger.info(f"Processing file: {filename}")

        try:
            # Create FileFetcher instance
            file_fetcher = FileFetcher(file)

            # Load file, extract and validate metadata
            data, message = file_fetcher.load_file()
            metadata = file_fetcher.extract_metadata()
            if not meta_data:
                return {"status": "error", "message": message}

            # Validate file integrity
            valid, message = FileValidator.validate_file_integrity(data)
            if not valid:
                return {"status": "error", "message": message}

            # Store metadata and data for processing
            self.processed_data = {
                "filename": filename,
                "status": "success",
                "metadata": metadata,
                "data": data.to_dict(orient="records")
            }

            return self.processed_data

        except Exception as e:
            logger.error(f"Processing failed for file {filename}: {str(e)}")
            return {"status": "error", "message": str(e)}

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
