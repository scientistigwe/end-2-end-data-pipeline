# backend/core/staging/staging_manager.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import uuid

from backend.core.orchestration.base_manager import BaseManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus
from backend.core.channel_handlers.staging_handler import StagingChannelHandler

logger = logging.getLogger(__name__)


@dataclass
class StagingMetadata:
    """Enhanced metadata for staged data"""
    pipeline_id: str
    data_type: str
    file_format: str
    source_type: str
    stage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    size_bytes: int = 0
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    retention_period: timedelta = field(default_factory=lambda: timedelta(days=7))
    processing_stage: str = "initial"


@dataclass
class QualityCheckResult:
    """Data quality check results"""
    passed: bool
    score: float
    message: str


@dataclass
class StagingState:
    """Tracks staging operation state"""
    pipeline_id: str
    operation: 'StagingOperation'
    status: ProcessingStatus
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None


class StagingOperation(Enum):
    """Types of staging operations"""
    STORE = "store"
    RETRIEVE = "retrieve"
    UPDATE = "update"
    DELETE = "delete"


class StagingManager(BaseManager):
    """
    Unified manager for data staging operations and storage.
    Combines messaging and data storage capabilities.
    """

    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker, "StagingManager")
        self.staging_handler = StagingChannelHandler(message_broker)
        self.active_operations: Dict[str, StagingState] = {}
        self.staging_area: Dict[str, Dict[str, Any]] = {}
        self.metrics = {
            'total_staged_data': 0,
            'quality_check_failures': 0,
            'data_quality_avg_score': 1.0
        }

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

    def store_data(self, pipeline_id: str, data: Any, metadata: Dict[str, Any]) -> str:
        """Store data in staging area"""
        try:
            staging_metadata = StagingMetadata(
                pipeline_id=pipeline_id,
                data_type=metadata.get('data_type', 'unknown'),
                file_format=metadata.get('format', 'unknown'),
                source_type=metadata.get('source_type', 'unknown'),
                size_bytes=len(str(data)),
                row_count=metadata.get('row_count'),
                columns=metadata.get('columns'),
                processing_stage=metadata.get('stage', 'initial')
            )

            staging_id = staging_metadata.stage_id
            self.staging_area[staging_id] = {
                "data": data,
                "metadata": staging_metadata
            }

            self.metrics['total_staged_data'] += 1
            self.logger.info(f"Data stored with staging ID: {staging_id}")

            # Create and track store operation
            state = StagingState(
                pipeline_id=pipeline_id,
                operation=StagingOperation.STORE,
                status=ProcessingStatus.COMPLETED
            )
            self.active_operations[pipeline_id] = state

            return staging_id

        except Exception as e:
            self.logger.error(f"Failed to store data: {str(e)}")
            self.handle_error(e, {"pipeline_id": pipeline_id})
            raise

    def retrieve_data(self, staging_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve staged data"""
        if staging_id not in self.staging_area:
            self.logger.warning(f"No data found for staging ID: {staging_id}")
            return None

        staged_item = self.staging_area[staging_id]
        staged_item['metadata'].updated_at = datetime.now()
        return staged_item

    def update_data(self, staging_id: str, data: Any,
                    metadata_updates: Optional[Dict[str, Any]] = None) -> bool:
        """Update staged data"""
        try:
            if staging_id not in self.staging_area:
                return False

            staged_item = self.staging_area[staging_id]
            staged_item['data'] = data

            if metadata_updates:
                for key, value in metadata_updates.items():
                    if hasattr(staged_item['metadata'], key):
                        setattr(staged_item['metadata'], key, value)

            staged_item['metadata'].updated_at = datetime.now()
            return True

        except Exception as e:
            self.logger.error(f"Failed to update staged data: {str(e)}")
            return False

    def delete_data(self, staging_id: str) -> bool:
        """Delete staged data"""
        try:
            if staging_id in self.staging_area:
                pipeline_id = self.staging_area[staging_id]['metadata'].pipeline_id
                del self.staging_area[staging_id]
                self.metrics['total_staged_data'] -= 1

                # Track delete operation
                state = StagingState(
                    pipeline_id=pipeline_id,
                    operation=StagingOperation.DELETE,
                    status=ProcessingStatus.COMPLETED
                )
                self.active_operations[pipeline_id] = state
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete staged data: {str(e)}")
            return False

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

    def get_pipeline_data(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Get all staged data for a pipeline"""
        return [
            {'staging_id': sid, **item}
            for sid, item in self.staging_area.items()
            if item['metadata'].pipeline_id == pipeline_id
        ]

    def get_metrics(self) -> Dict[str, Any]:
        """Get staging metrics"""
        return {
            **self.metrics,
            'active_staging_count': len(self.staging_area),
            'active_operations_count': len(self.active_operations)
        }

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

    def cleanup_expired(self) -> None:
        """Clean up expired data"""
        current_time = datetime.now()
        expired_ids = [
            sid for sid, item in self.staging_area.items()
            if (current_time - item['metadata'].created_at) > item['metadata'].retention_period
        ]

        for sid in expired_ids:
            self.delete_data(sid)

    def _cleanup_operation(self, pipeline_id: str) -> None:
        """Clean up completed/failed operation"""
        if pipeline_id in self.active_operations:
            del self.active_operations[pipeline_id]

    def __del__(self):
        """Cleanup manager resources"""
        self.active_operations.clear()
        self.staging_area.clear()
        super().__del__()