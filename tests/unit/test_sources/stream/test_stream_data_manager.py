"""Unit tests for stream data manager. tests/test_stream_data_manager.py"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch
from data_pipeline.source.stream.stream_config import StreamConfig
from data_pipeline.exceptions import StreamingDataValidationError
from data_pipeline.source.stream.stream_types import StreamConfig, StreamData
from data_pipeline.source.stream.data_manager import StreamDataManager


class TestStreamDataManager:
    def setup_method(self):
        self.config = StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic',
            validation_config={'source_health_threshold': 0.9}
        )
        self.data_manager = StreamDataManager(self.config)

    @pytest.fixture
    def config(self):
        return StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic',
            validation_config={'source_health_threshold': 0.9}
        )

    @pytest.fixture
    def mock_loader(self):
        loader = Mock()
        loader.load_data.return_value = pd.DataFrame({
            'id': [1, 2],
            'value': ['test1', 'test2']
        })
        loader.get_metrics.return_value = {
            'messages_per_second': 100,
            'connection_drops': 0
        }
        return loader

    @pytest.fixture
    def mock_validator(self):
        validator = Mock()
        validator.validate_source.return_value = True
        return validator

    @pytest.fixture
    def manager(self, config, mock_loader, mock_validator):
        with patch('data_pipeline.source.stream.data_loader.StreamDataLoader', return_value=mock_loader), \
                patch('data_pipeline.source.cloud.stream_validator.StreamDataValidator',
                      return_value=mock_validator):
            return StreamDataManager(config)

    def test_process_stream(self, manager):
        # Act: Call the method to process the stream
        data = manager.get_data()

        # Assert: Check that the returned data is as expected
        assert not data.empty
        assert len(data) == 2
        assert 'id' in data.columns
        assert 'value' in data.columns

        # Assert: Check if metrics were updated correctly
        metrics = manager.get_metrics()
        assert metrics['manager_metrics']['total_batches'] == 1
        assert metrics['manager_metrics']['failed_validations'] == 0
        assert metrics['manager_metrics']['last_success'] is not None

    def test_get_data_success(self, manager):
        data = manager.get_data()
        assert isinstance(data, pd.DataFrame)
        assert len(data) == 2

    def test_get_data_validation_failure(self, manager, mock_validator):
        mock_validator.validate_source.return_value = False
        with pytest.raises(StreamingDataValidationError):
            manager.get_data()

    def test_get_data_empty(self, manager, mock_loader):
        mock_loader.load_data.return_value = pd.DataFrame()
        data = manager.get_data()
        assert data.empty

    def test_metrics_tracking(self, manager):
        manager.get_data()
        metrics = manager.get_metrics()

        assert metrics['manager_metrics']['total_batches'] == 1
        assert metrics['manager_metrics']['failed_validations'] == 0
        assert metrics['manager_metrics']['last_success'] is not None

