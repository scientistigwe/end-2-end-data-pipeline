"""Unit tests for stream data loader. tests/test_stream_data_loader.py"""

import pytest
import pandas as pd
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.data_loader import StreamDataLoader
from unittest.mock import Mock, patch
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_types import StreamConfig

class TestStreamDataLoader:
    @pytest.fixture
    def config(self):
        return StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic',
            validation_config={'source_health_threshold': 0.9},
            batch_size=1000
        )

    @pytest.fixture
    def mock_connector(self):
        connector = Mock()
        connector.read_messages.return_value = [
            b'{"id": 1, "value": "test1"}',
            b'{"id": 2, "value": "test2"}'
        ]
        connector.get_metrics.return_value = {
            'messages_read': 2,
            'connection_retries': 0
        }
        return connector

    @pytest.fixture
    def loader(self, config, mock_connector):
        with patch('backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_connector.StreamConnector',
                   return_value=mock_connector):
            return StreamDataLoader(config)

    def test_load_data_success(self, loader):
        data = loader.load_data()
        assert not data.empty
        assert len(data) == 2
        assert 'id' in data.columns
        assert 'value' in data.columns

    def test_load_data_empty(self, loader, mock_connector):
        mock_connector.read_messages.return_value = []
        data = loader.load_data()
        assert data.empty

    def test_load_data_invalid_json(self, loader, mock_connector):
        mock_connector.read_messages.return_value = [b'invalid json']
        data = loader.load_data()
        assert data.empty

    def test_metrics_tracking(self, loader):
        loader.load_data()
        metrics = loader.get_metrics()
        assert isinstance(metrics, dict)
        assert 'total_records' in metrics
        assert 'invalid_records' in metrics
        assert 'last_batch_size' in metrics