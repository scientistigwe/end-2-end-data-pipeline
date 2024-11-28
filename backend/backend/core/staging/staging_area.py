from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import logging
from backend.core.metrics.metrics_manager import MetricsManager
from backend.core.messaging.broker import MessageBroker
from backend.core.registry.component_registry import ComponentRegistry
from backend.core.messaging.types import (
    ModuleIdentifier,
    ProcessingMessage,
    MessageType,
    ProcessingStatus
)

logger = logging.getLogger(__name__)

@dataclass
class QualityCheckResult:
    passed: bool
    score: float
    message: str


@dataclass
class StagingMetadata:
    """Enhanced metadata for staged data"""
    source_module: ModuleIdentifier
    stage_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data_type: str = ""
    file_format: str = ""
    size_bytes: int = 0
    row_count: Optional[int] = None
    columns: Optional[List[str]] = None
    quality_score: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    retention_period: timedelta = field(default_factory=lambda: timedelta(days=7))


class EnhancedStagingArea:
    """Advanced staging area with data management and quality tracking"""

    def __init__(self, message_broker: MessageBroker):
        self.staging_area: Dict[str, Dict[str, Any]] = {}
        self.message_broker = message_broker
        self.registry = ComponentRegistry()
        self.metrics = {
            'total_staged_data': 0,
            'quality_check_failures': 0,
            'data_quality_avg_score': 1.0
        }
        self.logger = logging.getLogger(__name__)
        self._initialize_messaging()

    def _initialize_messaging(self):
        """Initialize messaging components"""
        self.module_id = ModuleIdentifier(
            "StagingArea",
            "manage_data",
            self.registry.get_component_uuid("StagingArea")
        )
        self.data_staged_module = ModuleIdentifier(
            "StagingArea",
            "data_staged",
            self.registry.get_component_uuid("StagingArea")
        )

        # Register modules
        self.message_broker.register_module(self.module_id)
        self.message_broker.register_module(self.data_staged_module)

        # Set up subscriptions
        self.message_broker.subscribe_to_module(
            self.data_staged_module.get_tag(),
            self._handle_data_staged
        )

        self.logger.info("Staging Area messaging initialized")

    def stage_data(self, data: Any, metadata: Dict) -> str:
        try:
            staging_metadata = StagingMetadata(
                source_module=metadata.get('source_module'),
                data_type=metadata.get('file_type', 'unknown'),
                file_format=metadata.get('format', 'unknown'),
                size_bytes=metadata.get('size_bytes', 0),
                row_count=metadata.get('row_count'),
                columns=metadata.get('columns')
            )

            staging_id = staging_metadata.stage_id
            self.staging_area[staging_id] = {
                "data": data,
                "metadata": staging_metadata,
                "status": ProcessingStatus.PENDING  # Using enum
            }

            self._publish_staged_message(staging_id, staging_metadata)
            self.logger.info(f"Data staged successfully with ID: {staging_id}")
            return staging_id

        except Exception as e:
            self.logger.error(f"Error staging data: {str(e)}")
            raise ValueError(f"Failed to stage data: {str(e)}")

    def _publish_staged_message(self, staging_id: str, metadata: StagingMetadata):
        message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=self.data_staged_module,
            message_type=MessageType.STATUS_UPDATE,
            status=ProcessingStatus.PENDING,  # Using enum
            content={
                'staging_id': staging_id,
                'status': ProcessingStatus.PENDING.value,  # Using enum value
                'metadata': {
                    'data_type': metadata.data_type,
                    'file_format': metadata.file_format,
                    'size_bytes': metadata.size_bytes,
                    'row_count': metadata.row_count,
                    'columns': metadata.columns,
                    'quality_score': metadata.quality_score,
                    'created_at': metadata.created_at.isoformat()
                }
            }
        )
        self.message_broker.publish(message)

    def get_staged_data(self, staging_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve staged data and metadata by ID"""
        staged_data = self.staging_area.get(staging_id)
        if staged_data:
            self.logger.info(f"Retrieved staged data for ID: {staging_id}")
            return staged_data
        self.logger.warning(f"No staged data found for ID: {staging_id}")
        return None

    def update_staging_status(self, staging_id: str, status: ProcessingStatus,
                              additional_metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update status and metadata of staged data"""
        if staging_id not in self.staging_area:
            self.logger.error(f"Staging ID {staging_id} not found")
            return

        staged_data = self.staging_area[staging_id]

        # Check if status actually changed
        if staged_data['status'] == status:
            return

        staged_data['status'] = status

        if additional_metadata:
            staged_data['metadata'].updated_at = datetime.now()
            for key, value in additional_metadata.items():
                setattr(staged_data['metadata'], key, value)

        # Only publish update if status changed
        self._publish_status_update(staging_id, status, staged_data['metadata'])
        self.logger.info(f"Updated staging status to {status.value} for ID: {staging_id}")

    def _publish_status_update(self, staging_id: str, status: ProcessingStatus, metadata: StagingMetadata):
        """Publish status update message"""
        message = ProcessingMessage(
            source_identifier=self.module_id,
            target_identifier=self.data_staged_module,
            message_type=MessageType.STATUS_UPDATE,
            content={
                'staging_id': staging_id,
                'status': status,
                'metadata': metadata.__dict__
            }
        )
        self.message_broker.publish(message)

    def _handle_data_staged(self, message: ProcessingMessage) -> None:
        """Handle data staged events"""
        try:
            content = message.content
            if 'staging_id' not in content:
                raise ValueError("Missing staging_id in message")

            staging_id = content['staging_id']
            if staging_id in self.staging_area:
                current_status = self.staging_area[staging_id]['status']
                # Only update if not already completed
                if current_status != ProcessingStatus.COMPLETED:
                    self.update_staging_status(
                        staging_id=staging_id,
                        status=ProcessingStatus.COMPLETED
                    )
                    self.logger.info(f"Updated status for staged data: {staging_id}")
            else:
                self.logger.warning(f"No staged data found for ID: {staging_id}")

        except Exception as e:
            self.logger.error(f"Error handling staged data: {str(e)}")

    def cleanup_expired_data(self) -> None:
        """Remove expired staged data"""
        current_time = datetime.now()
        expired_ids = [
            sid for sid, entry in self.staging_area.items()
            if current_time - entry['metadata'].created_at > entry['metadata'].retention_period
        ]

        for staging_id in expired_ids:
            del self.staging_area[staging_id]
            self.metrics['total_staged_data'] -= 1
            self.logger.info(f"Removed expired staging data: {staging_id}")

    def _run_quality_checks(self, data: Any, metadata: StagingMetadata) -> float:
        """Run basic quality checks and return quality score"""
        checks = [
            self._check_data_presence(data),
            self._check_size(data, metadata),
            self._check_format(metadata)
        ]

        score = sum(check.score for check in checks) / len(checks)
        metadata.quality_score = score

        if any(not check.passed for check in checks):
            self.metrics['quality_check_failures'] += 1

        return score

    def _check_data_presence(self, data: Any) -> QualityCheckResult:
        if data is None:
            return QualityCheckResult(False, 0.0, "Data is missing")
        return QualityCheckResult(True, 1.0, "Data present")

    def _check_size(self, data: Any, metadata: StagingMetadata) -> QualityCheckResult:
        if metadata.size_bytes == 0:
            return QualityCheckResult(False, 0.0, "Empty data")
        return QualityCheckResult(True, 1.0, "Valid size")

    def _check_format(self, metadata: StagingMetadata) -> QualityCheckResult:
        if not metadata.file_format:
            return QualityCheckResult(False, 0.5, "Unknown format")
        return QualityCheckResult(True, 1.0, "Valid format")