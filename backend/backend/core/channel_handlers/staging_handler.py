# backend/core/channel_handlers/staging_handler.py

from typing import Dict, Any, Optional
from datetime import datetime

from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ComponentType
)
from backend.core.channel_handlers.base_channel_handler import BaseChannelHandler


class StagingChannelHandler(BaseChannelHandler):
    """Handles communication between orchestrator and staging area"""

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "staging_handler")
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers"""
        self.register_callback(MessageType.STAGE_REQUEST, self._handle_stage_request)
        self.register_callback(MessageType.GET_STAGE_STATUS, self._handle_status_request)
        self.register_callback(MessageType.RETRIEVE_REQUEST, self._handle_retrieve_request)
        self.register_callback(MessageType.UPDATE_REQUEST, self._handle_update_request)
        self.register_callback(MessageType.DELETE_REQUEST, self._handle_delete_request)

    def handle_staging_request(self, pipeline_id: str, operation: str, content: Dict[str, Any]) -> None:
        """Route staging request to appropriate handler"""
        try:
            self.send_message(
                MessageType.STAGE_REQUEST,
                {
                    'pipeline_id': pipeline_id,
                    'operation': operation,
                    **content
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to handle staging request: {str(e)}")
            raise

    def notify_staging_complete(self, pipeline_id: str, result: Dict[str, Any]) -> None:
        """Notify staging completion"""
        try:
            self.send_message(
                MessageType.STAGE_COMPLETE,
                {
                    'pipeline_id': pipeline_id,
                    'result': result
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to notify staging complete: {str(e)}")
            raise

    def notify_staging_error(self, pipeline_id: str, error: Dict[str, Any]) -> None:
        """Notify staging error"""
        try:
            self.send_message(
                MessageType.STAGE_ERROR,
                {
                    'pipeline_id': pipeline_id,
                    'error': error
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to notify staging error: {str(e)}")
            raise

    def _handle_stage_request(self, message: ProcessingMessage) -> None:
        """Handle incoming stage request"""
        try:
            self.send_response(
                target_id=message.source_identifier,
                message_type=MessageType.STAGE_REQUEST_RECEIVED,
                content={
                    'pipeline_id': message.content['pipeline_id'],
                    'timestamp': datetime.now().isoformat()
                }
            )
        except Exception as e:
            self._handle_error(message, str(e))

    def _handle_status_request(self, message: ProcessingMessage) -> None:
        """Forward status request"""
        try:
            self.send_message(
                MessageType.GET_STAGE_STATUS,
                {
                    'pipeline_id': message.content['pipeline_id'],
                    'request_id': message.content.get('request_id'),
                    'source_id': message.source_identifier
                }
            )
        except Exception as e:
            self._handle_error(message, str(e))

    def _handle_retrieve_request(self, message: ProcessingMessage) -> None:
        """Forward retrieve request"""
        try:
            self.send_message(
                MessageType.RETRIEVE_DATA,
                {
                    'staging_id': message.content['staging_id'],
                    'request_id': message.content.get('request_id'),
                    'source_id': message.source_identifier
                }
            )
        except Exception as e:
            self._handle_error(message, str(e))

    def _handle_update_request(self, message: ProcessingMessage) -> None:
        """Forward update request"""
        try:
            self.send_message(
                MessageType.UPDATE_DATA,
                {
                    'staging_id': message.content['staging_id'],
                    'data': message.content.get('data'),
                    'metadata_updates': message.content.get('metadata_updates'),
                    'source_id': message.source_identifier
                }
            )
        except Exception as e:
            self._handle_error(message, str(e))

    def _handle_delete_request(self, message: ProcessingMessage) -> None:
        """Forward delete request"""
        try:
            self.send_message(
                MessageType.DELETE_DATA,
                {
                    'staging_id': message.content['staging_id'],
                    'source_id': message.source_identifier
                }
            )
        except Exception as e:
            self._handle_error(message, str(e))

    def _handle_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle and forward errors"""
        self.send_response(
            target_id=message.source_identifier,
            message_type=MessageType.STAGE_ERROR,
            content={
                'pipeline_id': message.content.get('pipeline_id'),
                'staging_id': message.content.get('staging_id'),
                'error': error,
                'timestamp': datetime.now().isoformat()
            }
        )

    def cleanup_pipeline(self, pipeline_id: str) -> None:
        """Request pipeline cleanup"""
        try:
            self.send_message(
                MessageType.CLEANUP_REQUEST,
                {'pipeline_id': pipeline_id}
            )
        except Exception as e:
            self.logger.error(f"Failed to request pipeline cleanup: {str(e)}")