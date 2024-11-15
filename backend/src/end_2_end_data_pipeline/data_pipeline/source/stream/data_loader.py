# data_pipeline/source/cloud/stream_data_loader.py
import json
import pandas as pd
from typing import Optional, Dict, Any, List
import logging
from datetime import datetime
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_connector import StreamConnector
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_config import StreamConfig
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import StreamingDataLoadingError


class StreamDataLoader:
    """Manages data loading and transformation from stream sources"""

    def __init__(self, config: StreamConfig):
        self.config = config
        self.connector = StreamConnector(config)
        self.metrics = {
            'batches_processed': 0,
            'total_records': 0,
            'failed_loads': 0,
            'last_load_timestamp': None,
            'processing_times': []
        }

    def load_data(self, batch_size: Optional[int] = None) -> pd.DataFrame:
        """Load and transform data from the stream"""
        start_time = datetime.now()

        try:
            # Read messages from stream
            messages = self.connector.read_messages(batch_size)

            if not messages:
                logging.warning("No messages received from stream")
                return pd.DataFrame()

            # Parse messages to DataFrame
            df = self._messages_to_dataframe(messages)

            # Update metrics
            self._update_metrics(len(df), start_time)

            return df

        except Exception as e:
            self.metrics['failed_loads'] += 1
            raise StreamingDataLoadingError(f"Error loading data: {str(e)}")

    def _messages_to_dataframe(self, messages: List[str]) -> pd.DataFrame:
        """Convert messages to DataFrame with error handling"""
        parsed_messages = []

        for msg in messages:
            try:
                parsed_messages.append(json.loads(msg))
            except json.JSONDecodeError as e:
                logging.error(f"Failed to parse message: {e}")
                continue

        return pd.DataFrame(parsed_messages)

    def _update_metrics(self, record_count: int, start_time: datetime):
        """Update loader metrics"""
        self.metrics['batches_processed'] += 1
        self.metrics['total_records'] += record_count
        self.metrics['last_load_timestamp'] = datetime.now()
        self.metrics['processing_times'].append(
            (datetime.now() - start_time).total_seconds()
        )

    def get_metrics(self) -> Dict[str, Any]:
        """Get current loader metrics"""
        connector_metrics = self.connector.get_metrics()
        return {
            **self.metrics,
            'average_processing_time': sum(self.metrics['processing_times']) / len(self.metrics['processing_times'])
            if self.metrics['processing_times'] else 0,
            'connector_metrics': connector_metrics
        }

    def close(self):
        """Clean up resources"""
        self.connector.close()

