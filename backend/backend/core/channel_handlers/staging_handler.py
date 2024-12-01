# backend/core/channel_handlers/staging_handler.py

from typing import Dict, Any, Optional
from datetime import datetime

from backend.core.channel_handlers.base_handler import BaseHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    MessageType,
    ProcessingMessage,
    ProcessingStatus,
    ComponentType
)
from backend.core.staging.staging_area import StagingArea


class StagingHandler(BaseHandler):
    """Handles communication between orchestrator and staging area"""

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "staging_handler")

        # Initialize staging area
        self.staging_area = StagingArea()

        # Register handlers
        self._register_handlers()

    def _handle_retrieve_request(self, message: ProcessingMessage) -> None:
        """Handle data retrieval request"""
        try:
            staging_id = message.content['staging_id']
            staged_item = self.staging_area.retrieve_data(staging_id)

            if staged_item:
                self.send_response(
                    target_id=message.source_identifier,
                    message_type=MessageType.STAGED_DATA,
                    content={
                        'staging_id': staging_id,
                        'data': staged_item['data'],
                        'metadata': staged_item['metadata'].__dict__
                    }
                )
            else:
                raise ValueError(f"No data found for staging ID: {staging_id}")

        except Exception as e:
            self._handle_staging_error(message, str(e))

    def _handle_update_request(self, message: ProcessingMessage) -> None:
        """Handle data update request"""
        try:
            staging_id = message.content['staging_id']
            data = message.content.get('data')
            metadata_updates = message.content.get('metadata_updates')

            success = self.staging_area.update_data(
                staging_id,
                data,
                metadata_updates
            )

            if success:
                self.send_response(
                    target_id=message.source_identifier,
                    message_type=MessageType.STAGE_SUCCESS,
                    content={
                        'staging_id': staging_id,
                        'message': 'Data updated successfully'
                    }
                )
            else:
                raise ValueError(f"Failed to update staging ID: {staging_id}")

        except Exception as e:
            self._handle_staging_error(message, str(e))

    def _handle_delete_request(self, message: ProcessingMessage) -> None:
        """Handle data deletion request"""
        try:
            staging_id = message.content['staging_id']
            success = self.staging_area.delete_data(staging_id)

            if success:
                self.send_response(
                    target_id=message.source_identifier,
                    message_type=MessageType.STAGE_SUCCESS,
                    content={
                        'staging_id': staging_id,
                        'message': 'Data deleted successfully'
                    }
                )
            else:
                raise ValueError(f"Failed to delete staging ID: {staging_id}")

        except Exception as e:
            self._handle_staging_error(message, str(e))

    def _handle_staging_error(self, message: ProcessingMessage, error: str) -> None:
        """Handle staging errors"""
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
        """Clean up all staged data for a pipeline"""
        staged_items = self.staging_area.get_pipeline_data(pipeline_id)
        for item in staged_items:
            self.staging_area.delete_data(item['staging_id'])

    def notify_staging_success(self, pipeline_id: str, staging_id: str,
                             operation: str, details: Dict[str, Any]) -> None:
        """Notify successful staging operation"""
        try:
            # Get current status
            status = self.staging_area.get_staging_status(staging_id)
            if not status:
                raise ValueError(f"No staging found for ID: {staging_id}")

            # Send success notification
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.STAGE_SUCCESS,
                content={
                    'pipeline_id': pipeline_id,
                    'staging_id': staging_id,
                    'operation': operation,
                    'details': details,
                    'status': status,
                    'timestamp': datetime.now().isoformat()
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to notify staging success: {str(e)}")
            self._handle_staging_error(
                ProcessingMessage(
                    content={
                        'pipeline_id': pipeline_id,
                        'staging_id': staging_id
                    }
                ),
                str(e)
            )

    def retrieve_staging_status(self, message: ProcessingMessage) -> None:
        """Handle staging status request"""
        try:
            staging_id = message.content['staging_id']
            status = self.staging_area.get_staging_status(staging_id)

            if status:
                self.send_response(
                    target_id=message.source_identifier,
                    message_type=MessageType.STAGE_STATUS,
                    content={
                        'staging_id': staging_id,
                        'status': status,
                        'metrics': self.staging_area.get_metrics()
                    }
                )
            else:
                raise ValueError(f"No staging found for ID: {staging_id}")

        except Exception as e:
            self._handle_staging_error(message, str(e))

    def _register_handlers(self) -> None:
        """Register message handlers"""
        # ... existing handlers ...
        self.register_callback(
            MessageType.GET_STAGE_STATUS,
            self.get_staging_status
        )

    def _handle_stage_request(self, message: ProcessingMessage) -> None:
        """Handle data staging request"""
        try:
            pipeline_id = message.content['pipeline_id']
            data = message.content.get('data')
            metadata = message.content.get('metadata', {})

            staging_id = self.staging_area.store_data(
                pipeline_id,
                data,
                metadata
            )

            # Notify success with operation details
            self.notify_staging_success(
                pipeline_id,
                staging_id,
                'store',
                {
                    'data_type': metadata.get('data_type', 'unknown'),
                    'size_bytes': len(str(data)),
                    'stage': metadata.get('stage', 'initial')
                }
            )

        except Exception as e:
            self._handle_staging_error(message, str(e))

    def __del__(self):
        """Cleanup handler resources"""
        # Clean up all staged data
        for staging_id in list(self.active_operations.keys()):
            self.cleanup_staged_data(staging_id)
        super().__del__()
