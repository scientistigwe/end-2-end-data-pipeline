"""Unit tests for stream data loader. tests/test_stream_data_loader.py"""

import pytest
import pandas as pd
from data_pipeline.source.stream.data_loader import StreamDataLoader
from data_pipeline.source.stream.stream_config import StreamConfig
from data_pipeline.exceptions import StreamingDataLoadingError
from typing import Dict, List, Any
from unittest.mock import Mock, patch
from data_pipeline.source.stream.stream_types import StreamConfig, StreamData


class TestStreamDataLoader:
    def setup_method(self):
        self.config: StreamConfig = {
            'stream_name': 'test_stream',
            'batch_size': 100,
            'max_retries': 3
        }
        self.data_loader = StreamDataLoader(self.config)

    def test_load_data(self):
        # Add your test implementation here
        pass
    @pytest.fixture
    def config(self):
        return StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic'
        )

    @pytest.fixture
    def mock_connector(self):
        connector = Mock()
        connector.read_messages.return_value = [
            '{"id": 1, "value": "test1"}',
            '{"id": 2, "value": "test2"}'
        ]
        return connector

    @pytest.fixture
    def loader(self, config, mock_connector):
        with patch('data_pipeline.source.cloud.stream_data_loader.StreamConnector', return_value=mock_connector):
            return StreamDataLoader(config)

    def test_load_data_success(self, loader):
        df = loader.load_data()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert 'id' in df.columns
        assert 'value' in df.columns

    def test_load_data_empty(self, loader, mock_connector):
        mock_connector.read_messages.return_value = []
        df = loader.load_data()
        assert df.empty

    def test_load_data_invalid_json(self, loader, mock_connector):
        mock_connector.read_messages.return_value = [
            '{"id": 1}',
            'invalid json',
            '{"id": 2}'
        ]
        df = loader.load_data()
        assert len(df) == 2  # Only valid JSON should be included

    def test_metrics_tracking(self, loader):
        loader.load_data()
        metrics = loader.get_metrics()

        assert metrics['batches_processed'] == 1
        assert metrics['total_records'] == 2
        assert metrics['last_load_timestamp'] is not None
