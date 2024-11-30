# backend/core/managers/staging_manager.py

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from backend.core.base.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus

# Channel Handler
from backend.core.channel_handlers.staging_handler import StagingChannelHandler

logger = logging.getLogger(__name__)


class StagingOperation(Enum):
    """Types of staging operations"""
    STORE = "store"
    RETRIEVE = "retrieve"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class StagingState:
    """Tracks staging operation state"""
    pipeline_id: str
    operation: StagingOperation
    status: ProcessingStatus
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class StagingManager(BaseManager):
    """
    Orchestrates data staging operations between pipeline components
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "StagingManager")
        self.staging_handler = StagingChannelHandler(message_broker)
        self.active_operations: Dict[str, StagingState] = {}

    def initiate_staging(self, message: ProcessingMessage) -> None:
        """Entry point for staging operations"""
        try:
            pipeline_id = message.content['pipeline_id']
            operation = StagingOperation(message.content['operation'])

            # Track operation state
            state = StagingState(
                pipeline_id=pipeline_id,
                operation=operation,
                status=ProcessingStatus.PENDING
            )
            self.active_operations[pipeline_id] = state

            # Route to staging handler
            self.staging_handler.handle_staging_request(
                pipeline_id,
                operation,
                message.content
            )

        except Exception as e:
            self.logger.error(f"Failed to initiate staging: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def handle_staging_result(self, message: ProcessingMessage) -> None:
        """Handle staging operation result"""
        try:
            pipeline_id = message.content['pipeline_id']
            result = message.content['result']
            state = self.active_operations.get(pipeline_id)

            if not state:
                raise ValueError(f"No active staging operation for pipeline: {pipeline_id}")

            # Update state
            state.status = ProcessingStatus.COMPLETED
            state.completed_at = datetime.now()

            # Route result
            if result['status'] == 'success':
                self.staging_handler.notify_staging_complete(pipeline_id, result)
            else:
                self.staging_handler.notify_staging_error(pipeline_id, result)

            # Cleanup completed operation
            self._cleanup_operation(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to handle staging result: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def handle_staging_error(self, message: ProcessingMessage) -> None:
        """Handle staging operation errors"""
        try:
            pipeline_id = message.content['pipeline_id']
            error = message.content['error']

            state = self.active_operations.get(pipeline_id)
            if state:
                state.status = ProcessingStatus.ERROR
                state.completed_at = datetime.now()

            # Route error notification
            self.staging_handler.notify_staging_error(
                pipeline_id,
                {'error': error, 'operation': state.operation if state else 'unknown'}
            )

            # Cleanup failed operation
            self._cleanup_operation(pipeline_id)

        except Exception as e:
            self.logger.error(f"Failed to handle staging error: {str(e)}")
            self.handle_error(e, {"message": message.content})
            raise

    def get_staging_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current staging operation status"""
        state = self.active_operations.get(pipeline_id)
        if not state:
            return None

        return {
            'pipeline_id': pipeline_id,
            'operation': state.operation.value,
            'status': state.status.value,
            'created_at': state.created_at.isoformat(),
            'completed_at': state.completed_at.isoformat() if state.completed_at else None
        }

    def _cleanup_operation(self, pipeline_id: str) -> None:
        """Clean up completed/failed operation"""
        if pipeline_id in self.active_operations:
            del self.active_operations[pipeline_id]

    def __del__(self):
        """Cleanup manager resources"""
        self.active_operations.clear()
        super().__del__()
