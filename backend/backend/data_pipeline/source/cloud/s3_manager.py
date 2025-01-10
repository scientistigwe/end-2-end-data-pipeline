# s3_manager.py
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd

from backend.core.messaging.types import ComponentType
from backend.core.registry.component_registry import ComponentRegistry
from backend.core.messaging.types import ProcessingMessage, MessageType, ModuleIdentifier
from .s3_validator import S3Validator
from .s3_fetcher import S3Fetcher

logger = logging.getLogger(__name__)


class S3Manager:
    """Enhanced S3 management system with messaging integration"""

    def __init__(self, message_broker):
        """Initialize S3Manager with component registration"""
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.validator = S3Validator()

        # Initialize with consistent UUID and proper ComponentType
        component_uuid = self.registry.get_component_uuid("S3Manager")
        self.module_id = ModuleIdentifier(
            component_name="S3Manager",
            component_type=ComponentType.MODULE,  # Add proper component type
            method_name="process_s3",
            instance_id=component_uuid
        )

        # Track active connections and operations
        self.active_connections: Dict[str, S3Fetcher] = {}
        self.pending_operations: Dict[str, Dict[str, Any]] = {}

        # Register and subscribe
        self._initialize_messaging()
        logger.info(f"S3Manager initialized with ID: {self.module_id.get_tag()}")

    def _initialize_messaging(self) -> None:
        """Set up message broker registration and subscriptions"""
        try:
            # Register with message broker
            self.message_broker.register_component(self.module_id)

            # Get orchestrator ID
            orchestrator_id = ModuleIdentifier(
                component_name="DataOrchestrator",
                component_type=ComponentType.ORCHESTRATOR,
                method_name="manage_pipeline",
                instance_id=self.registry.get_component_uuid("DataOrchestrator")
            )

            # Subscribe to relevant patterns based on source type
            patterns = []

            # For S3Manager
            patterns = [
                f"{orchestrator_id.get_tag()}.{MessageType.SOURCE_SUCCESS.value}",
                f"{orchestrator_id.get_tag()}.{MessageType.SOURCE_ERROR.value}"
            ]

            for pattern in patterns:
                self.message_broker.subscribe(
                    component=self.module_id,
                    pattern=pattern,
                    callback=self._handle_orchestrator_response,
                    timeout=10.0
                )
            logger.info(f"{self.__class__.__name__} messaging initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing messaging: {str(e)}")
            raise

    def initialize_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize S3 connection"""
        try:
            connection_id = str(uuid.uuid4())

            # Create and validate connection
            s3_fetcher = S3Fetcher(config)
            is_valid, message = self.validator.validate_credentials(
                config['credentials'],
                config.get('region')
            )

            if not is_valid:
                raise ValueError(message)

            # Store connection
            self.active_connections[connection_id] = s3_fetcher

            return {
                'status': 'success',
                'connection_id': connection_id,
                'message': 'S3 connection established'
            }

        except Exception as e:
            logger.error(f"S3 connection error: {str(e)}")
            raise

    def process_s3_object(self, connection_id: str, bucket: str, key: str) -> Dict[str, Any]:
        """Main entry point for S3 object processing"""
        try:
            if connection_id not in self.active_connections:
                raise ValueError("Invalid connection ID")

            operation_id = str(uuid.uuid4())
            s3_fetcher = self.active_connections[connection_id]

            # Store operation info
            self.pending_operations[operation_id] = {
                'connection_id': connection_id,
                'bucket': bucket,
                'key': key,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }

            logger.info(f"Starting S3 object processing: {bucket}/{key}")

            # Step 1: Validate S3 object
            self._validate_s3_object(s3_fetcher, bucket, key)

            # Step 2: Process S3 data
            processed_data = self._process_s3_data(s3_fetcher, bucket, key)

            # Step 3: Update operation status
            self.pending_operations[operation_id]['status'] = 'processed'
            self.pending_operations[operation_id]['processed_data'] = processed_data

            # Step 4: Send processed data to orchestrator
            self._send_to_orchestrator(operation_id, processed_data)

            return processed_data

        except Exception as e:
            logger.error(f"S3 processing error: {str(e)}")
            raise

    def _validate_s3_object(self, s3_fetcher: S3Fetcher, bucket: str, key: str) -> None:
        """Validate S3 object before processing"""
        try:
            # Validate bucket access
            bucket_valid, bucket_msg = self.validator.validate_bucket_access(
                s3_fetcher.s3_client, bucket
            )
            if not bucket_valid:
                raise ValueError(bucket_msg)

            # Validate object format
            format_valid, format_msg = self.validator.validate_object_format(key)
            if not format_valid:
                raise ValueError(format_msg)

            # Validate object size
            size_valid, size_msg = self.validator.validate_object_size(
                s3_fetcher.s3_client, bucket, key
            )
            if not size_valid:
                raise ValueError(size_msg)

            logger.info("S3 object validation successful")

        except Exception as e:
            logger.error(f"S3 validation error: {str(e)}")
            raise

    def _process_s3_data(self, s3_fetcher: S3Fetcher, bucket: str, key: str) -> Dict[str, Any]:
        """Process S3 object data"""
        try:
            # Fetch and process object
            result = s3_fetcher.fetch_object(bucket, key)

            return {
                "status": "success",
                "source": f"s3://{bucket}/{key}",
                "data": result['data'].to_dict(orient="records"),
                "metadata": {
                    **result['metadata'],
                    "bucket": bucket,
                    "key": key,
                    "processed_at": datetime.now().isoformat()
                }
            }
        except Exception as e:
            raise ValueError(str(e))

    def _send_to_orchestrator(self, operation_id: str, processed_data: Dict[str, Any]) -> None:
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
                message_type=MessageType.SOURCE_SUCCESS,
                content={
                    'operation_id': operation_id,
                    'action': 'process_s3_data',
                    'data': processed_data['data'],
                    'metadata': processed_data['metadata'],
                    'source_type': 's3',
                    'source': processed_data['source']
                }
            )

            logger.info(f"Sending data to orchestrator: {orchestrator_id.get_tag()}")
            self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error sending to orchestrator: {str(e)}")
            raise

    def _handle_orchestrator_error(self, operation_id: str, error_message: str) -> None:
        """Handle orchestrator-reported errors"""
        try:
            if operation_id in self.pending_operations:
                operation_data = self.pending_operations[operation_id]
                logger.error(
                    f"Processing failed for S3 operation (bucket: {operation_data['bucket']}, key: {operation_data['key']}): {error_message}")

                # Update operation status
                operation_data['status'] = 'error'
                operation_data['error_message'] = error_message
                operation_data['error_timestamp'] = datetime.now().isoformat()

                # Cleanup
                self._cleanup_pending_operation(operation_id)
            else:
                logger.warning(f"Received error for unknown operation ID: {operation_id}")
        except Exception as e:
            logger.error(f"Error handling orchestrator error: {str(e)}")

    def _handle_orchestrator_response(self, message: ProcessingMessage) -> None:
        """Handle responses from orchestrator"""
        try:
            operation_id = message.content.get('operation_id')
            if not operation_id or operation_id not in self.pending_operations:
                logger.warning(f"Received response for unknown operation ID: {operation_id}")
                return

            operation_data = self.pending_operations[operation_id]

            if message.message_type == MessageType.SOURCE_SUCCESS:
                logger.info(f"S3 operation {operation_id} processed successfully")
                self._cleanup_pending_operation(operation_id)
            elif message.message_type == MessageType.SOURCE_ERROR:
                logger.error(f"Error processing S3 operation {operation_id}")
                self._handle_orchestrator_error(operation_id, message.content.get('error'))
            elif message.message_type == MessageType.SOURCE_EXTRACT:
                logger.info(f"Data extraction in progress for {operation_id}")
                operation_data['status'] = 'extracting'

        except Exception as e:
            logger.error(f"Error handling orchestrator response: {str(e)}")

    def _cleanup_pending_operation(self, operation_id: str) -> None:
        """Clean up processed operation data"""
        if operation_id in self.pending_operations:
            del self.pending_operations[operation_id]
            logger.info(f"Cleaned up pending operation: {operation_id}")

    def close_connection(self, connection_id: str) -> None:
        """Close S3 connection and cleanup"""
        try:
            if connection_id in self.active_connections:
                self.active_connections[connection_id].close()
                del self.active_connections[connection_id]
                logger.info(f"Closed S3 connection: {connection_id}")
        except Exception as e:
            logger.error(f"Error closing S3 connection: {str(e)}")
            raise

