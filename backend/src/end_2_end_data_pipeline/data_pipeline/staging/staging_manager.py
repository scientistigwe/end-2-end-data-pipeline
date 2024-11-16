# staging/staging_manager.py

from typing import Any, Dict, Optional, Union
from datetime import datetime
import pandas as pd
import pyarrow as pa
import uuid
from enum import Enum
from dataclasses import dataclass
import json


class DataFormat(Enum):
    PARQUET = "parquet"
    DATAFRAME = "dataframe"
    JSON = "json"
    BYTES = "bytes"


class StageStatus(Enum):
    RECEIVED = "received"
    VALIDATED = "validated"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class StagingMetadata:
    source_type: str
    source_id: str
    format: DataFormat
    size_bytes: int
    row_count: Optional[int]
    columns: Optional[list]
    tags: Dict[str, str]
    quality_score: float
    validation_results: Dict[str, Any]


class StagingManager:
    def __init__(self, base_storage_path: str = "./staging"):
        self._staging_area: Dict[str, Dict[str, Any]] = {}
        self.base_storage_path = base_storage_path
        self._initialize_storage()

    def _initialize_storage(self):
        """Initialize storage directory structure."""
        import os
        os.makedirs(self.base_storage_path, exist_ok=True)
        for status in StageStatus:
            os.makedirs(os.path.join(self.base_storage_path, status.value), exist_ok=True)

    def _generate_staging_id(self) -> str:
        """Generate unique staging ID."""
        return str(uuid.uuid4())

    def _calculate_metadata(self, data: Any, format: DataFormat) -> Dict[str, Any]:
        """Calculate basic metadata about the staged data."""
        size_bytes = 0
        row_count = None
        columns = None

        if format == DataFormat.DATAFRAME:
            if isinstance(data, pd.DataFrame):
                size_bytes = data.memory_usage(deep=True).sum()
                row_count = len(data)
                columns = list(data.columns)
        elif format == DataFormat.PARQUET:
            if isinstance(data, pa.Table):
                size_bytes = data.nbytes
                row_count = data.num_rows
                columns = data.column_names

        return {
            "size_bytes": size_bytes,
            "row_count": row_count,
            "columns": columns
        }

    def stage_data(
            self,
            data: Any,
            source_type: str,
            source_id: str,
            format: DataFormat,
            metadata: StagingMetadata
    ) -> str:
        """Stage data with metadata and return staging ID."""
        staging_id = self._generate_staging_id()
        timestamp = datetime.now()

        # Calculate additional metadata
        calc_metadata = self._calculate_metadata(data, format)

        staging_info = {
            'data': data,
            'source_type': source_type,
            'source_id': source_id,
            'format': format,
            'timestamp': timestamp,
            'status': StageStatus.RECEIVED,
            'metadata': metadata,
            'calc_metadata': calc_metadata,
            'history': [{
                'timestamp': timestamp,
                'status': StageStatus.RECEIVED,
                'details': 'Initial staging'
            }]
        }

        self._staging_area[staging_id] = staging_info
        return staging_id

    def get_data(self, staging_id: str) -> Optional[Any]:
        """Retrieve staged data."""
        return self._staging_area.get(staging_id, {}).get('data')

    def get_metadata(self, staging_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for staged data."""
        staged_item = self._staging_area.get(staging_id)
        if staged_item:
            return {
                'metadata': staged_item['metadata'],
                'calc_metadata': staged_item['calc_metadata'],
                'history': staged_item['history']
            }
        return None

    def update_status(
            self,
            staging_id: str,
            status: StageStatus,
            details: Optional[str] = None
    ) -> None:
        """Update status of staged data."""
        if staging_id in self._staging_area:
            self._staging_area[staging_id]['status'] = status
            self._staging_area[staging_id]['history'].append({
                'timestamp': datetime.now(),
                'status': status,
                'details': details or ''
            })

    def cleanup(self, staging_id: str) -> None:
        """Archive staged data."""
        if staging_id in self._staging_area:
            self.update_status(staging_id, StageStatus.ARCHIVED, "Data archived")
            del self._staging_area[staging_id]


