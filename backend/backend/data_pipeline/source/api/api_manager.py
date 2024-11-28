import logging
from typing import Dict, Tuple, Any, Optional
import requests
from datetime import datetime
import traceback

from backend.core.registry.component_registry import ComponentRegistry
from backend.core.messaging.types import (
    ProcessingMessage,
    MessageType,
    ModuleIdentifier,
    ProcessingStatus
)

logger = logging.getLogger(__name__)


class ApiValidator:
    """Validates API responses and data"""

    @staticmethod
    def validate_response(response: requests.Response) -> Tuple[bool, str]:
        """Validate API response status and content"""
        try:
            response.raise_for_status()
            return True, "Response validation successful"
        except requests.exceptions.RequestException as e:
            return False, f"Response validation failed: {str(e)}"

    @staticmethod
    def validate_data_format(data: Dict) -> Tuple[bool, str]:
        """Validate API data structure and format"""
        if not data:
            return False, "Empty data received"
        return True, "Data format validation successful"

    @staticmethod
    def validate_required_fields(data: Dict, required_fields: list) -> Tuple[bool, str]:
        """Validate presence of required fields in API response"""
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"
        return True, "Required fields validation successful"


class ApiManager:
    """Manages API data processing and communication with the orchestrator"""

    def __init__(self, message_broker):
        """Initialize ApiManager with registry integration"""
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.validator = ApiValidator()

        # Initialize with consistent UUID
        component_uuid = self.registry.get_component_uuid("ApiManager")
        self.module_id = ModuleIdentifier(
            "ApiManager",
            "process_api",
            component_uuid
        )

        # Track processing state
        self.pending_requests: Dict[str, Dict[str, Any]] = {}
        self.processed_data: Optional[Dict[str, Any]] = None

        # Register and subscribe
        self._initialize_messaging()
        logger.info(f"ApiManager initialized with ID: {self.module_id.get_tag()}")

    def _initialize_messaging(self) -> None:
        """Set up message broker registration and subscriptions"""
        try:
            # Register with message broker
            self.message_broker.register_module(self.module_id)

            # Get orchestrator ID
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
            logger.info("ApiManager messaging initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing messaging: {str(e)}")
            raise

    def process_api_request(self, request_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process API request and send data to orchestrator"""
        request_id = request_config.get('request_id', str(datetime.now().timestamp()))

        logger.info(f"Processing API request: {request_id}")

        try:
            # Validate request configuration
            if not self._validate_request_config(request_config):
                return self._handle_error(request_id, "Invalid request configuration")

            # Make API request
            response = self._make_api_request(request_config)

            # Validate response
            is_valid, validation_message = self.validator.validate_response(response)
            if not is_valid:
                return self._handle_error(request_id, validation_message)

            # Process response data
            processed_data = self._process_response_data(response, request_config)
            if processed_data["status"] == "error":
                return processed_data

            # Track pending request
            self.pending_requests[request_id] = {
                "request_id": request_id,
                "processed_data": processed_data,
                "status": "pending"
            }

            # Send to orchestrator
            self._send_to_orchestrator(request_id, processed_data)
            return processed_data

        except Exception as e:
            error_msg = f"Unexpected error processing API request: {str(e)}"
            logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return self._handle_error(request_id, error_msg)

    def _validate_request_config(self, config: Dict[str, Any]) -> bool:
        """Validate API request configuration"""
        required_fields = ['url', 'method']
        return all(field in config for field in required_fields)

    def _make_api_request(self, config: Dict[str, Any]) -> requests.Response:
        """Make API request using provided configuration"""
        method = config['method'].upper()
        url = config['url']
        headers = config.get('headers', {})
        params = config.get('params', {})
        data = config.get('data', {})

        return requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data if method in ['POST', 'PUT', 'PATCH'] else None
        )

    def _process_response_data(self, response: requests.Response, config: Dict[str, Any]) -> Dict[str, Any]:
        """Process API response data"""
        try:
            data = response.json()
            metadata = self._extract_metadata(response, config)

            return {
                "request_id": config.get('request_id', str(datetime.now().timestamp())),
                "status": "success",
                "metadata": metadata,
                "data": data
            }
        except Exception as e:
            return self._handle_error(config.get('request_id'), str(e))

    def _extract_metadata(self, response: requests.Response, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from API response"""
        return {
            "url": config['url'],
            "method": config['method'],
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "timestamp": datetime.now().isoformat(),
            "response_time": response.elapsed.total_seconds()
        }

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
                message_type=MessageType.ACTION,
                content={
                    'request_id': request_id,
                    'action': 'process_api_data',
                    'data': processed_data['data'],
                    'metadata': processed_data['metadata'],
                    'source_type': 'api'
                }
            )

            logger.info(f"Sending data to orchestrator: {orchestrator_id.get_tag()}")
            self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error sending to orchestrator: {str(e)}")
            self._handle_error(request_id, str(e))

    def _handle_orchestrator_response(self, message: ProcessingMessage) -> None:
        """Handle responses from orchestrator"""
        try:
            request_id = message.content.get('request_id')
            if not request_id or request_id not in self.pending_requests:
                logger.warning(f"Received response for unknown request ID: {request_id}")
                return

            request_data = self.pending_requests[request_id]

            if message.message_type == MessageType.ACTION:
                logger.info(f"Request {request_data['request_id']} processed successfully")
                self._cleanup_pending_request(request_id)
            elif message.message_type == MessageType.ERROR:
                logger.error(f"Error processing request {request_data['request_id']}")
                self._handle_orchestrator_error(request_id, message.content.get('error'))

        except Exception as e:
            logger.error(f"Error handling orchestrator response: {str(e)}")

    def _handle_error(self, request_id: str, error_message: str) -> Dict[str, Any]:
        """Centralized error handling"""
        error_data = {
            'request_id': request_id,
            'status': 'error',
            'message': error_message,
            'traceback': traceback.format_exc()
        }
        logger.error(f"Error processing request {request_id}: {error_message}")
        return error_data

    def _handle_orchestrator_error(self, request_id: str, error_message: str) -> None:
        """Handle orchestrator-reported errors"""
        if request_id in self.pending_requests:
            request_data = self.pending_requests[request_id]
            logger.error(f"Processing failed for request {request_data['request_id']}: {error_message}")
            self._cleanup_pending_request(request_id)

    def _cleanup_pending_request(self, request_id: str) -> None:
        """Clean up processed request data"""
        if request_id in self.pending_requests:
            del self.pending_requests[request_id]
