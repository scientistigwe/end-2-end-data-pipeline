# core/staging/staging_area.py
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from backend.core.messaging.types import ModuleIdentifier, ProcessingMessage, MessageType, ProcessingStatus


@dataclass
class StagingMetadata:
    """Enhanced metadata for staged data"""
    source_module: ModuleIdentifier
    stage_id: str
    data_type: str
    format: str
    size_bytes: int
    row_count: Optional[int]
    columns: Optional[List[str]]
    tags: Dict[str, str]
    quality_score: float
    processing_chain: List[str]  # List of message IDs in processing chain
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


class EnhancedStagingArea:
    """Enhanced staging area with message tracking and quality checks"""

    def __init__(self, message_broker):
        self.staging_area: Dict[str, Dict] = {}
        self.message_broker = message_broker
        self.module_id = ModuleIdentifier("StagingArea", "manage_data")
        self.message_broker.register_module(self.module_id)

    def stage_data(self, data: Any, metadata: StagingMetadata) -> str:
        """Stage data with enhanced tracking and messaging"""
        staging_id = str(uuid.uuid4())

        # Create staging message
        stage_message = ProcessingMessage(
            source_identifier=self.module_id,
            message_type=MessageType.INFO,
            content={
                "action": "data_staged",
                "staging_id": staging_id,
                "metadata": {
                    "data_type": metadata.data_type,
                    "format": metadata.format,
                    "size": metadata.size_bytes,
                    "row_count": metadata.row_count
                }
            },
            status=ProcessingStatus.COMPLETED
        )

        # Publish staging message
        message_id = self.message_broker.publish(stage_message)
        metadata.processing_chain.append(message_id)

        # Store data with metadata
        self.staging_area[staging_id] = {
            "data": data,
            "metadata": metadata,
            "status": ProcessingStatus.PENDING
        }

        return staging_id

    def update_status(self, staging_id: str, status: ProcessingStatus,
                      details: Dict[str, Any] = None):
        """Update staging status with message broadcast"""
        if staging_id not in self.staging_area:
            raise ValueError(f"No data found for staging_id: {staging_id}")

        self.staging_area[staging_id]["status"] = status
        self.staging_area[staging_id]["metadata"].updated_at = datetime.now()

        # Broadcast status update
        status_message = ProcessingMessage(
            source_identifier=self.module_id,
            message_type=MessageType.STATUS_UPDATE,
            content={
                "staging_id": staging_id,
                "status": status,
                **(details or {})
            },
            status=status
        )
        self.message_broker.publish(status_message)

    def get_data(self, staging_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve staged data and metadata"""
        if staging_id not in self.staging_area:
            return None
        return self.staging_area[staging_id]

    def cleanup(self, staging_id: str):
        """Remove staged data with notification"""
        if staging_id in self.staging_area:
            cleanup_message = ProcessingMessage(
                source_identifier=self.module_id,
                message_type=MessageType.INFO,
                content={"action": "cleanup", "staging_id": staging_id},
                status=ProcessingStatus.COMPLETED
            )
            self.message_broker.publish(cleanup_message)
            del self.staging_area[staging_id]


