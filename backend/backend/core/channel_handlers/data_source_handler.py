import logging
from typing import Dict, Any
from backend.core.base.base_manager import BaseManager
from backend.core.messaging.types import ProcessingMessage, MessageType, ModuleIdentifier
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.api.api_manager import APIManager
from backend.data_pipeline.source.cloud.s3_data_manager import S3DataManager
from backend.data_pipeline.source.stream.stream_manager import StreamManager
from backend.data_pipeline.source.database.db_data_manager import DBDataManager

logger = logging.getLogger(__name__)

class DataSourceChannelHandler(BaseManager):
    def __init__(self, message_broker):
        super().__init__(message_broker, "DataSourceChannelHandler")
        self.file_manager = FileManager(message_broker)
        self.api_manager = APIManager(message_broker)
        self.s3_manager = S3DataManager(message_broker)
        self.stream_manager = StreamManager(message_broker)
        self.db_manager = DBDataManager(message_broker)
        self.user_messages: Dict[str, ProcessingMessage] = {}

    # ==========================================
    # User Data Ingestion
    # ==========================================

    def _handle_data_ingestion(self, message: ProcessingMessage) -> None:
        """Handle data ingestion request from the user"""
        try:
            user_id = message.content.get('user_id')
            data_payload = message.content.get('data_payload')

            # Store the user message for later feedback
            self.user_messages[user_id] = message

            # Send the data to the orchestrator for processing
            self.send_to_orchestrator(MessageType.ACTION, {
                'action': 'process_user_data',
                'user_id': user_id,
                'data_payload': data_payload
            })

        except Exception as e:
            self.handle_error(e, message.content)
            self._send_error_response(message, str(e))

    # ==========================================
    # Orchestrator Feedback Handling
    # ==========================================

    def _handle_orchestrator_feedback(self, message: ProcessingMessage) -> None:
        """Handle feedback from the orchestrator"""
        try:
            user_id = message.content.get('user_id')
            feedback = message.content.get('feedback')

            # Retrieve the original user message
            user_message = self.user_messages.get(user_id)

            if user_message:
                # Send the feedback to the user
                self._send_user_feedback(user_message, feedback)
            else:
                self.logger.warning(f"User message not found for user ID: {user_id}")

        except Exception as e:
            self.handle_error(e, message.content)

    # ==========================================
    # User Feedback and Error Responses
    # ==========================================

    def _send_user_feedback(self, user_message: ProcessingMessage, feedback: str) -> None:
        """Send feedback to the user"""
        try:
            response_content = {
                'user_id': user_message.content.get('user_id'),
                'feedback': feedback
            }
            self.publish_message(user_message.source_identifier, MessageType.RESPONSE, response_content)
        except Exception as e:
            self.handle_error(e, user_message.content)

    def _send_error_response(self, original_message: ProcessingMessage, error_message: str) -> None:
        """Send error response to the user"""
        error_content = {
            'user_id': original_message.content.get('user_id'),
            'error_message': error_message
        }
        self.publish_message(original_message.source_identifier, MessageType.ERROR, error_content)

    # ==========================================
    # Source-Specific Data Processing
    # ==========================================

    def _process_file_data(self, data_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process file data using the FileManager"""
        file_data = data_payload.get('file_data')
        processed_data, file_id = self.file_manager.process_file(file_data)
        return {
            'source_type': 'file',
            'data_id': file_id,
            'processed_data': processed_data
        }

    def _process_api_data(self, data_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process API data using the APIManager"""
        api_request = data_payload.get('api_request')
        processed_data, request_id = self.api_manager.process_api_request(api_request)
        return {
            'source_type': 'api',
            'data_id': request_id,
            'processed_data': processed_data
        }

    def _process_s3_data(self, data_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process S3 data using the S3DataManager"""
        s3_resource = data_payload.get('s3_resource')
        processed_data, resource_id = self.s3_manager.process_s3_data(s3_resource)
        return {
            'source_type': 's3',
            'data_id': resource_id,
            'processed_data': processed_data
        }

    def _process_stream_data(self, data_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process stream data using the StreamManager"""
        stream_data = data_payload.get('stream_data')
        processed_data, stream_id = self.stream_manager.process_stream_data(stream_data)
        return {
            'source_type': 'stream',
            'data_id': stream_id,
            'processed_data': processed_data
        }

    def _process_db_data(self, data_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Process database data using the DBDataManager"""
        query = data_payload.get('query')
        processed_data, query_id = self.db_manager.process_db_query(query)
        return {
            'source_type': 'db',
            'data_id': query_id,
            'processed_data': processed_data
        }