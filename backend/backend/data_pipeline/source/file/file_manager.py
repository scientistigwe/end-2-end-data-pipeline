import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from backend.core.registry.component_registry import ComponentRegistry
from backend.core.messaging.types import ProcessingMessage, MessageType, ModuleIdentifier
from .file_validator import FileValidator
from .file_fetcher import FileFetcher

logger = logging.getLogger(__name__)

class FileManager:
    """Enhanced file management system with consistent messaging integration"""

    def __init__(self, message_broker):
        """Initialize FileManager with enhanced component registration"""
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.validator = FileValidator()

        # Initialize with consistent UUID
        component_uuid = self.registry.get_component_uuid("FileManager")
        self.module_id = ModuleIdentifier("FileManager", "process_file", component_uuid)

        # Track processing state
        self.pending_files: Dict[str, Dict[str, Any]] = {}

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

    def process_file(self, file: Any) -> Dict[str, Any]:
        """Main entry point for file processing"""
        try:
            filename = self._get_filename(file)
            file_id = str(uuid.uuid4())

            # Store file info immediately
            self.pending_files[file_id] = {
                'filename': filename,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }

            logger.info(f"Starting processing for file: {filename} (ID: {file_id})")

            # Step 1: Initialize file fetcher
            file_fetcher = FileFetcher(file)

            # Step 2: Validate file
            self._validate_file(file_fetcher)

            # Step 3: Process file data
            processed_data = self._process_file_data(file_fetcher, filename)

            # Step 4: Update pending file status
            self.pending_files[file_id]['status'] = 'processed'
            self.pending_files[file_id]['processed_data'] = processed_data

            # Step 5: Send processed data to orchestrator
            self._send_to_orchestrator(file_id, processed_data)

            return processed_data, file_id

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise

    def _process_file_data(self, file_fetcher: FileFetcher, filename: str) -> Dict[str, Any]:
        """Process file data with comprehensive error handling"""
        try:
            # Convert to DataFrame
            data, conversion_message = file_fetcher.convert_to_dataframe()
            if data is None:
                raise ValueError(conversion_message)

            # Extract metadata
            metadata = file_fetcher.extract_metadata()
            if 'error' in metadata:
                raise ValueError(metadata['error'])

            return {
                "filename": filename,
                "status": "success",
                "metadata": metadata,
                "data": data.to_dict(orient="records")
            }
        except Exception as e:
            raise ValueError(str(e))

    def _validate_file(self, file_fetcher: FileFetcher) -> None:
        """Perform file validations using FileFetcher and FileValidator"""
        try:
            # Reset file pointer at the start of validation
            file_fetcher.file.seek(0)

            # First, validate security (do this first as it reads raw bytes)
            security_valid, security_message = self.validator.validate_security(file_fetcher.file.read())
            if not security_valid:
                raise ValueError(security_message)

            # Reset file pointer after security check
            file_fetcher.file.seek(0)

            # Get metadata
            metadata = file_fetcher.extract_metadata()
            if "error" in metadata:
                raise ValueError(metadata["error"])

            # Validate format
            format_valid, format_message = self.validator.validate_file_format(metadata)
            if not format_valid:
                raise ValueError(format_message)

            # Validate size
            size_valid, size_message = self.validator.validate_file_size(metadata)
            if not size_valid:
                raise ValueError(size_message)

            # Reset file pointer before loading data
            file_fetcher.file.seek(0)

            # Get and validate data
            data, message = file_fetcher.load_file()
            if data is None:
                raise ValueError(message)

            # Validate integrity
            integrity_valid, integrity_message = self.validator.validate_file_integrity(data)
            if not integrity_valid:
                raise ValueError(integrity_message)

            logger.info("File validation successful")

        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            raise

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
                    'file_id': file_id,
                    'action': 'process_file_data',
                    'data': processed_data['data'],
                    'metadata': processed_data['metadata'],
                    'source_type': 'file',
                    'filename': processed_data['filename']
                }
            )

            logger.info(f"Sending data to orchestrator: {orchestrator_id.get_tag()}")
            self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error sending to orchestrator: {str(e)}")
            raise

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

    def _handle_orchestrator_error(self, file_id: str, error_message: str) -> None:
        """Handle orchestrator-reported errors"""
        try:
            if file_id in self.pending_files:
                file_data = self.pending_files[file_id]
                logger.error(f"Processing failed for file {file_data['filename']}: {error_message}")
                self._cleanup_pending_file(file_id)
        except Exception as e:
            logger.error(f"Error handling orchestrator error: {str(e)}")

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
        else:
            return 'unknown'

    def _cleanup_pending_file(self, file_id: str) -> None:
        """Clean up processed file data"""
        if file_id in self.pending_files:
            del self.pending_files[file_id]
            logger.info(f"Cleaned up pending file: {file_id}")





