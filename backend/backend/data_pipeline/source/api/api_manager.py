# api_manager.py
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from backend.core.messaging.types import ComponentType
from backend.core.registry.component_registry import ComponentRegistry
from backend.core.messaging.types import ProcessingMessage, MessageType, ModuleIdentifier
from .api_validator import APIValidator
from .api_fetcher import APIFetcher

logger = logging.getLogger(__name__)


class APIManager:
    """Enhanced API management system with messaging integration"""

    def __init__(self, message_broker):
        """Initialize APIManager with component registration"""
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.validator = APIValidator()

        # Initialize with consistent UUID and proper ComponentType
        component_uuid = self.registry.get_component_uuid("APIManager")
        self.module_id = ModuleIdentifier(
            component_name="APIManager",
            component_type=ComponentType.MODULE,  # Add proper component type
            method_name="process_api",
            instance_id=component_uuid
        )

        # Track processing state
        self.pending_requests: Dict[str, Dict[str, Any]] = {}

        # Register and subscribe
        self._initialize_messaging()
        logger.info(f"APIManager initialized with ID: {self.module_id.get_tag()}")

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

            # For APIManager
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

    def process_api_request(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point for API data processing"""
        try:
            request_id = str(uuid.uuid4())
            endpoint = config.get('endpoint')

            # Store request info immediately
            self.pending_requests[request_id] = {
                'endpoint': endpoint,
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            }

            logger.info(f"Starting API request processing: {endpoint} (ID: {request_id})")

            # Step 1: Initialize API fetcher
            api_fetcher = APIFetcher(config)

            # Step 2: Validate endpoint and credentials
            self._validate_api_config(api_fetcher, config)

            # Step 3: Process API data
            processed_data = self._process_api_data(api_fetcher, endpoint)

            # Step 4: Update pending request status
            self.pending_requests[request_id]['status'] = 'processed'
            self.pending_requests[request_id]['processed_data'] = processed_data

            # Step 5: Send processed data to orchestrator
            self._send_to_orchestrator(request_id, processed_data)

            return processed_data

        except Exception as e:
            logger.error(f"Error processing API request: {str(e)}")
            raise

    def _validate_api_config(self, api_fetcher: APIFetcher, config: Dict[str, Any]) -> None:
        """Validate API configuration and credentials"""
        try:
            # Validate endpoint
            endpoint_valid, endpoint_msg = self.validator.validate_endpoint(config['endpoint'])
            if not endpoint_valid:
                raise ValueError(endpoint_msg)

            # Validate credentials if present
            if 'credentials' in config:
                creds_valid, creds_msg = self.validator.validate_credentials(
                    config['credentials'],
                    config['endpoint']
                )
                if not creds_valid:
                    raise ValueError(creds_msg)

            logger.info("API configuration validation successful")

        except Exception as e:
            logger.error(f"API validation error: {str(e)}")
            raise

    def _process_api_data(self, api_fetcher: APIFetcher, endpoint: str) -> Dict[str, Any]:
        """Process API data with error handling"""
        try:
            # Fetch data from API
            response = api_fetcher.fetch_data(endpoint)

            # Validate response format
            format_valid, format_msg = self.validator.validate_response_format(response)
            if not format_valid:
                raise ValueError(format_msg)

            # Check rate limits
            rate_limits = self.validator.validate_rate_limits(response)

            return {
                "endpoint": endpoint,
                "status": "success",
                "data": response['data'],
                "metadata": {
                    "rate_limits": rate_limits,
                    "headers": response['headers'],
                    "timestamp": datetime.now().isoformat()
                }
            }
        except Exception as e:
            raise ValueError(str(e))

    def _send_to_orchestrator(self, request_id: str, processed_data: Dict[str, Any]) -> None:
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
                    'request_id': request_id,
                    'action': 'process_api_data',
                    'data': processed_data['data'],
                    'metadata': processed_data['metadata'],
                    'source_type': 'api',
                    'endpoint': processed_data['endpoint']
                }
            )

            logger.info(f"Sending data to orchestrator: {orchestrator_id.get_tag()}")
            self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error sending to orchestrator: {str(e)}")
            raise

    def _handle_orchestrator_error(self, request_id: str, error_message: str) -> None:
        """Handle orchestrator-reported errors"""
        try:
            if request_id in self.pending_requests:
                request_data = self.pending_requests[request_id]
                logger.error(f"Processing failed for API request to {request_data['endpoint']}: {error_message}")

                # Update request status
                request_data['status'] = 'error'
                request_data['error_message'] = error_message
                request_data['error_timestamp'] = datetime.now().isoformat()

                # Cleanup
                self._cleanup_pending_request(request_id)
            else:
                logger.warning(f"Received error for unknown request ID: {request_id}")
        except Exception as e:
            logger.error(f"Error handling orchestrator error: {str(e)}")

    def _handle_orchestrator_response(self, message: ProcessingMessage) -> None:
        """Handle responses from orchestrator"""
        try:
            request_id = message.content.get('request_id')
            if not request_id or request_id not in self.pending_requests:
                logger.warning(f"Received response for unknown request ID: {request_id}")
                return

            request_data = self.pending_requests[request_id]

            if message.message_type == MessageType.SOURCE_SUCCESS:
                logger.info(f"API request {request_id} processed successfully")
                self._cleanup_pending_request(request_id)
            elif message.message_type == MessageType.SOURCE_ERROR:
                logger.error(f"Error processing API request {request_id}")
                self._handle_orchestrator_error(request_id, message.content.get('error'))
            elif message.message_type == MessageType.SOURCE_VALIDATE:
                logger.info(f"Validation in progress for request {request_id}")
                request_data['status'] = 'validating'

        except Exception as e:
            logger.error(f"Error handling orchestrator response: {str(e)}")

    def _cleanup_pending_request(self, request_id: str) -> None:
        """Clean up processed request data"""
        if request_id in self.pending_requests:
            del self.pending_requests[request_id]
            logger.info(f"Cleaned up pending request: {request_id}")

