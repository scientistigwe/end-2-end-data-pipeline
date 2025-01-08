# backend/core/channel_handlers/processing_handler.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.channel_handlers.base_channel_handler import BaseChannelHandler
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage

from backend.data_pipeline.quality_analysis.data_quality_processor import (
    DataQualityProcessor,
    QualityPhase
)

logger = logging.getLogger(__name__)


@dataclass
class ProcessingContext:
    """Context for processing operations"""
    pipeline_id: str
    current_phase: QualityPhase
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"


class ProcessingChannelHandler(BaseChannelHandler):
    """
    Handles communication between orchestrator and quality module manager
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "processing_handler")

        # Initialize quality module manager
        self.quality_manager = QualityManager(message_broker)

        # Track active processing
        self.active_processing: Dict[str, ProcessingContext] = {}

        # Register message handlers
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Register message handlers"""
        self.register_callback(
            MessageType.START_QUALITY_CHECK,
            self._handle_quality_start
        )
        self.register_callback(
            MessageType.QUALITY_UPDATE,
            self._handle_quality_update
        )
        self.register_callback(
            MessageType.QUALITY_COMPLETE,
            self._handle_quality_complete
        )
        self.register_callback(
            MessageType.QUALITY_ERROR,
            self._handle_quality_error
        )

    def initiate_quality_check(self, pipeline_id: str, data: Any,
                               context: Dict[str, Any]) -> None:
        """Entry point for quality checking process"""
        try:
            # Create processing context
            proc_context = ProcessingContext(
                pipeline_id=pipeline_id,
                current_phase=QualityPhase.DETECTION,
                metadata=context
            )

            self.active_processing[pipeline_id] = proc_context

            # Start quality process
            self.quality_manager.start_quality_process(
                pipeline_id,
                data,
                context
            )

        except Exception as e:
            self.logger.error(f"Failed to initiate quality check: {str(e)}")
            self._handle_processing_error(pipeline_id, str(e))

    def _handle_quality_start(self, message: ProcessingMessage) -> None:
        """Handle quality process start request"""
        pipeline_id = message.content['pipeline_id']
        data = message.content.get('data')
        context = message.content.get('context', {})

        self.initiate_quality_check(pipeline_id, data, context)

    def _handle_quality_update(self, message: ProcessingMessage) -> None:
        """Handle quality process updates"""
        pipeline_id = message.content['pipeline_id']
        phase = message.content.get('phase')
        status = message.content.get('status')

        context = self.active_processing.get(pipeline_id)
        if context:
            context.current_phase = QualityPhase(phase)
            context.status = status

            # Forward update to orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.QUALITY_STATUS_UPDATE,
                content=message.content
            )

    def _handle_quality_complete(self, message: ProcessingMessage) -> None:
        """Handle quality process completion"""
        pipeline_id = message.content['pipeline_id']
        context = self.active_processing.get(pipeline_id)

        if context:
            # Forward completion to orchestrator
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.QUALITY_COMPLETE,
                content={
                    'pipeline_id': pipeline_id,
                    'results': message.content,
                    'metadata': context.metadata
                }
            )

            # Cleanup
            self._cleanup_processing(pipeline_id)

    def _handle_quality_error(self, message: ProcessingMessage) -> None:
        """Handle quality process errors"""
        pipeline_id = message.content['pipeline_id']
        error = message.content.get('error')
        phase = message.content.get('phase')

        # Forward error to orchestrator
        self.send_response(
            target_id=f"pipeline_manager_{pipeline_id}",
            message_type=MessageType.QUALITY_ERROR,
            content={
                'pipeline_id': pipeline_id,
                'phase': phase,
                'error': error
            }
        )

        # Cleanup
        self._cleanup_processing(pipeline_id)

    def _handle_processing_error(self, pipeline_id: str, error: str) -> None:
        """Handle processing errors"""
        context = self.active_processing.get(pipeline_id)
        if context:
            # Send error notification
            self.send_response(
                target_id=f"pipeline_manager_{pipeline_id}",
                message_type=MessageType.PROCESSING_ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'phase': context.current_phase.value,
                    'error': error
                }
            )

            # Cleanup
            self._cleanup_processing(pipeline_id)

    def get_processing_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current processing status"""
        context = self.active_processing.get(pipeline_id)
        if not context:
            return None

        # Get status from both handler and quality manager
        handler_status = {
            'pipeline_id': pipeline_id,
            'phase': context.current_phase.value,
            'status': context.status,
            'created_at': context.created_at.isoformat()
        }

        # Get detailed quality status
        quality_status = self.quality_manager.get_process_status(pipeline_id)

        return {
            **handler_status,
            'quality_details': quality_status
        }


    def pause_processing(self, pipeline_id: str) -> None:
        """Pause quality processing"""
        context = self.active_processing.get(pipeline_id)
        if not context:
            return

        context.status = "paused"

        # Notify orchestrator
        self.send_response(
            target_id=f"pipeline_manager_{pipeline_id}",
            message_type=MessageType.PROCESSING_PAUSED,
            content={
                'pipeline_id': pipeline_id,
                'phase': context.current_phase.value
            }
        )


    def resume_processing(self, pipeline_id: str) -> None:
        """Resume quality processing"""
        context = self.active_processing.get(pipeline_id)
        if not context:
            return

        context.status = "running"

        # Notify orchestrator
        self.send_response(
            target_id=f"pipeline_manager_{pipeline_id}",
            message_type=MessageType.PROCESSING_RESUMED,
            content={
                'pipeline_id': pipeline_id,
                'phase': context.current_phase.value
            }
        )


    def cancel_processing(self, pipeline_id: str) -> None:
        """Cancel quality processing"""
        context = self.active_processing.get(pipeline_id)
        if not context:
            return

        # Notify orchestrator
        self.send_response(
            target_id=f"pipeline_manager_{pipeline_id}",
            message_type=MessageType.PROCESSING_CANCELLED,
            content={
                'pipeline_id': pipeline_id,
                'phase': context.current_phase.value
            }
        )

        # Cleanup
        self._cleanup_processing(pipeline_id)


    def _cleanup_processing(self, pipeline_id: str) -> None:
        """Clean up processing resources"""
        if pipeline_id in self.active_processing:
            del self.active_processing[pipeline_id]


    def __del__(self):
        """Cleanup handler resources"""
        self.active_processing.clear()
        super().__del__()
