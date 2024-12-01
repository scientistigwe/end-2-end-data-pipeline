# backend/core/staging/staging_area.py

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import logging


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
    passed: bool
    score: float
    message: str


class StagingArea:
    """Core staging area functionality"""

    def __init__(self):
        self.staging_area: Dict[str, Dict[str, Any]] = {}
        self.metrics = {
            'total_staged_data': 0,
            'quality_check_failures': 0,
            'data_quality_avg_score': 1.0
        }
        self.logger = logging.getLogger(__name__)

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

            return staging_id

        except Exception as e:
            self.logger.error(f"Failed to store data: {str(e)}")
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
                del self.staging_area[staging_id]
                self.metrics['total_staged_data'] -= 1
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete staged data: {str(e)}")
            return False

    def cleanup_expired(self) -> None:
        """Clean up expired data"""
        current_time = datetime.now()
        expired_ids = [
            sid for sid, item in self.staging_area.items()
            if (current_time - item['metadata'].created_at) > item['metadata'].retention_period
        ]

        for sid in expired_ids:
            self.delete_data(sid)

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
            'active_staging_count': len(self.staging_area)
        }

    def get_staging_status(self, staging_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of staged data"""
        if staging_id not in self.staging_area:
            return None

        staged_item = self.staging_area[staging_id]
        metadata = staged_item['metadata']

        return {
            'staging_id': staging_id,
            'pipeline_id': metadata.pipeline_id,
            'processing_stage': metadata.processing_stage,
            'data_type': metadata.data_type,
            'size_bytes': metadata.size_bytes,
            'row_count': metadata.row_count,
            'created_at': metadata.created_at.isoformat(),
            'updated_at': metadata.updated_at.isoformat(),
            'retention_period': str(metadata.retention_period),
            'active': True
        }