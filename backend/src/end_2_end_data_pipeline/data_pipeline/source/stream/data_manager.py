# data_pipeline/source/cloud/stream_data_manager.py
from typing import Optional, Dict, Any
import logging
import pandas as pd
from datetime import datetime
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.data_loader import StreamDataLoader
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_validator import StreamDataValidator
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_config import StreamConfig
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import StreamingDataValidationError


class StreamDataManager:
    """Manages the end-to-end stream data pipeline"""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.loader = StreamDataLoader(config)
        self.validator = StreamDataValidator(config.validation_config)
        self.metrics = {
            'total_batches': 0,
            'failed_validations': 0,
            'start_time': datetime.now(),
            'last_success': None
        }

    def get_data(self, batch_size: Optional[int] = None) -> pd.DataFrame:
        """Get validated data from the stream"""
        try:
            # Load data
            data = self.loader.load_data(batch_size)

            if data.empty:
                logging.warning("No data received from loader")
                return data

            # Get loader metrics for validation
            loader_metrics = self.loader.get_metrics()

            # Validate data
            if self.validator.validate_source(data, loader_metrics):
                self._update_metrics(success=True)
                return data
            else:
                self._update_metrics(success=False)
                raise StreamingDataValidationError("Data failed validation checks")

        except Exception as e:
            self._update_metrics(success=False)
            raise type(e)(f"Error in stream data pipeline: {str(e)}")

    def _update_metrics(self, success: bool):
        """Update manager metrics"""
        self.metrics['total_batches'] += 1
        if not success:
            self.metrics['failed_validations'] += 1
        else:
            self.metrics['last_success'] = datetime.now()

    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics from all components"""
        return {
            'manager_metrics': self.metrics,
            'loader_metrics': self.loader.get_metrics(),
            'validator_metrics': self.validator.source_health_metrics
        }

    def close(self):
        """Clean up all resources"""
        self.loader.close()