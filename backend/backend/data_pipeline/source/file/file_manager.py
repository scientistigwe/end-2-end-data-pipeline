import logging
import uuid
from io import BytesIO
import pandas as pd
from typing import Dict, Tuple, Any, Optional
import traceback

from backend.core.registry.component_registry import ComponentRegistry
from backend.core.messaging.types import (
    ProcessingMessage,
    MessageType,
    ModuleIdentifier,
    ProcessingStatus
)
from .file_validator import FileValidator
from .file_fetcher import FileFetcher

logger = logging.getLogger(__name__)


class FileManager:
    """Enhanced file management system with consistent messaging integration"""

    # ----------------
    # Initialization
    # ----------------

    def __init__(self, message_broker):
        """Initialize FileManager with enhanced component registration"""
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.validator = FileValidator()

        # Initialize with consistent UUID
        component_uuid = self.registry.get_component_uuid("FileManager")
        self.module_id = ModuleIdentifier(
            "FileManager",
            "process_file",
            component_uuid
        )

        # Track processing state
        self.pending_files: Dict[str, Dict[str, Any]] = {}
        self.processed_data: Optional[Dict[str, Any]] = None

        # Register and subscribe
        self._initialize_messaging()
        logger.info(f"FileManager initialized with ID: {self.module_id.get_tag()}")

    def _initialize_messaging(self) -> None:
        """Set up message broker registration and subscriptions"""
        try:
            # Register with message broker
            self.message_broker.register_module(self.module_id)

            # Get orchestrator ID with consistent UUID
            orchestrator_id = ModuleIdentifier(
                "DataOrchestrator",
                "manage_pipeline",
                self.registry.get_component_uuid("DataOrchestrator")
            )

            # Subscribe to orchestrator responses
            self.message_broker.subscribe_to_module(
                orchestrator_id.get_tag(),
                self._handle_orchestrator_response
            )
            logger.info("FileManager messaging initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing messaging: {str(e)}")
            raise

    # ----------------
    # Main Processing Flow
    # ----------------
    def process_file(self, file: Any) -> Dict[str, Any]:
        """Main entry point for file processing"""
        filename = self._get_filename(file)
        file_id = str(uuid.uuid4())

        logger.info(f"Starting processing for file: {filename} (ID: {file_id})")

        try:
            # Step 1: Initialize file fetcher
            file_fetcher = FileFetcher(file)

            # Step 2: Validate file
            is_valid, validation_message = self._validate_file(file_fetcher)
            if not is_valid:
                return self._handle_error(filename, validation_message)

            # Step 3: Process file data
            processed_data = self._process_file_data(file_fetcher, filename)
            if processed_data["status"] == "error":
                return processed_data

            # Step 4: Track pending file
            self.pending_files[file_id] = {
                "filename": filename,
                "processed_data": processed_data,
                "status": "pending"
            }

            # Step 5: Send to orchestrator
            self._send_to_orchestrator(file_id, processed_data)
            return processed_data

        except Exception as e:
            error_msg = f"Unexpected error processing file: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return self._handle_error(filename, error_msg)

    # ----------------
    # File Processing Helpers
    # ----------------
    def _process_file_data(self, file_fetcher: FileFetcher, filename: str) -> Dict[str, Any]:
        """Process file data with comprehensive error handling"""
        try:
            # Convert to DataFrame
            data, conversion_message = file_fetcher.convert_to_dataframe()
            if data is None:
                return self._handle_error(filename, conversion_message)

            # Extract metadata
            metadata = file_fetcher.extract_metadata()
            if 'error' in metadata:
                return self._handle_error(filename, metadata['error'])

            return {
                "filename": filename,
                "status": "success",
                "metadata": metadata,
                "data": data.to_dict(orient="records")
            }
        except Exception as e:
            return self._handle_error(filename, str(e))

    def _validate_file(self, file_fetcher: FileFetcher) -> Tuple[bool, str]:
        """
        Perform file validations using FileFetcher and FileValidator.
        """
        try:
            # Reset file pointer at the start of validation
            file_fetcher.file.seek(0)

            # First, validate security (do this first as it reads raw bytes)
            security_valid, security_message = self.validator.validate_security(file_fetcher.file.read())
            if not security_valid:
                logger.warning(f"Security validation failed: {security_message}")
                return False, security_message

            # Reset file pointer after security check
            file_fetcher.file.seek(0)

            # Get metadata
            metadata = file_fetcher.extract_metadata()
            if "error" in metadata:
                logger.warning(f"File validation failed: {metadata['error']}")
                return False, metadata["error"]

            # Validate format
            format_valid, format_message = self.validator.validate_file_format(metadata)
            if not format_valid:
                logger.warning(f"File format validation failed: {format_message}")
                return False, format_message

            # Validate size
            size_valid, size_message = self.validator.validate_file_size(metadata)
            if not size_valid:
                logger.warning(f"File size validation failed: {size_message}")
                return False, size_message

            # Reset file pointer before loading data
            file_fetcher.file.seek(0)

            # Get and validate data
            data, message = file_fetcher.load_file()
            if data is None:
                logger.warning(f"File loading failed: {message}")
                return False, message

            # Validate integrity
            integrity_valid, integrity_message = self.validator.validate_file_integrity(data)
            if not integrity_valid:
                logger.warning(f"File integrity validation failed: {integrity_message}")
                return False, integrity_message

            logger.info("File validation successful")
            return True, "Validation successful"

        except Exception as e:
            logger.error(f"File validation error: {str(e)}", exc_info=True)
            return False, f"Validation error: {str(e)}"

    # ----------------
    # Orchestrator Communication
    # ----------------
    def _send_to_orchestrator(self, file_id: str, processed_data: Dict[str, Any]) -> None:
        """Send processed data to orchestrator"""
        try:
            orchestrator_id = ModuleIdentifier(
                "DataOrchestrator",
                "manage_pipeline",
                self.registry.get_component_uuid("DataOrchestrator")
            )

            message = ProcessingMessage(
                source_identifier=self.module_id,
                target_identifier=orchestrator_id,
                message_type=MessageType.ACTION,
                content={
                    'file_id': file_id,  # This file_id needs to match what's in pending_files
                    'action': 'process_file_data',
                    'data': processed_data['data'],
                    'metadata': processed_data['metadata'],
                    'source_type': 'file',
                    'filename': processed_data['filename']
                }
            )

            # Store in pending files before sending
            if file_id not in self.pending_files:
                self.pending_files[file_id] = {
                    "filename": processed_data['filename'],
                    "status": "pending"
                }

            logger.info(f"Sending data to orchestrator: {orchestrator_id.get_tag()}")
            self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error sending to orchestrator: {str(e)}")
            self._handle_error(processed_data['filename'], str(e))

    def _handle_orchestrator_response(self, message: ProcessingMessage) -> None:
        """Handle responses from orchestrator"""
        try:
            file_id = message.content.get('file_id')
            if not file_id or file_id not in self.pending_files:
                logger.warning(f"Received response for unknown file ID: {file_id}")
                return

            file_data = self.pending_files[file_id]

            if message.message_type == MessageType.ACTION:
                logger.info(f"File {file_data['filename']} processed successfully")
                self._cleanup_pending_file(file_id)
            elif message.message_type == MessageType.ERROR:
                logger.error(f"Error processing file {file_data['filename']}")
                self._handle_orchestrator_error(file_id, message.content.get('error'))

        except Exception as e:
            logger.error(f"Error handling orchestrator response: {str(e)}")

    # ----------------
    # Error Handling
    # ----------------
    def _handle_error(self, filename: str, error_message: str) -> Dict[str, Any]:
        """Centralized error handling"""
        error_data = {
            'filename': filename,
            'status': 'error',
            'message': error_message,
            'traceback': traceback.format_exc()
        }
        logger.error(f"Error processing {filename}: {error_message}")
        return error_data

    def _handle_orchestrator_error(self, file_id: str, error_message: str) -> None:
        """Handle orchestrator-reported errors"""
        if file_id in self.pending_files:
            file_data = self.pending_files[file_id]
            logger.error(f"Processing failed for file {file_data['filename']}: {error_message}")
            self._cleanup_pending_file(file_id)

    # ----------------
    # Utility Methods
    # ----------------
    def get_file_metadata(self, file_obj: Any) -> Dict[str, Any]:
        """Public method to generate file metadata"""
        try:
            file_fetcher = FileFetcher(file_obj)
            metadata = file_fetcher.extract_metadata()
            logger.info(f'Metadata: {metadata}')
            return {'status': 'success', 'metadata': metadata}
        except Exception as e:
            logger.error(f"Metadata generation error: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    def _get_filename(self, file: Any) -> str:
        """Extract filename from various file object types"""
        if hasattr(file, 'filename'):
            return file.filename
        elif hasattr(file, 'name'):
            return file.name
        elif isinstance(file, str):
            return file.split('/')[-1]
        elif isinstance(file, pd.DataFrame):
            return 'DataFrame'
        elif isinstance(file, BytesIO):
            return 'BytesIO'
        return 'unknown'

    def _cleanup_pending_file(self, file_id: str) -> None:
        """Clean up processed file data"""
        if file_id in self.pending_files:
            del self.pending_files[file_id]



