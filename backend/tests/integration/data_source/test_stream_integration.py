# tests/test_integration.py
"""Integration tests for stream data source."""
import pytest
import pandas as pd
from unittest.mock import patch, Mock
from confluent_kafka import KafkaException
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import StreamingDataValidationError
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_types import StreamConfig, StreamData
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.data_manager import StreamDataManager

class TestStreamPipelineIntegration:
    def setup_method(self):
        self.config: StreamConfig = {
            'stream_name': 'test_stream',
            'batch_size': 100,
            'max_retries': 3
        }
        self.data_manager = StreamDataManager(self.config)

    def test_stream_data_processing(self):
        test_data: StreamData = {
            'id': '123',
            'value': 'test'
        }

    @pytest.fixture
    def config(self):
        return StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic',
            batch_size=100,
            validation_config={
                'max_latency_seconds': 300,
                'source_health_threshold': 0.9,
                'partition_keys': ['partition_id']
            }
        )

    @pytest.fixture
    def mock_kafka_message(self):
        message = Mock()
        message.error.return_value = None
        message.value.return_value = b'{"partition_id": "p1", "value": "test", "timestamp": "2024-01-01T00:00:00"}'
        return message

    def test_end_to_end_success(self, config, mock_kafka_message):
        """Test successful end-to-end data flow"""
        with patch('confluent_kafka.Consumer') as mock_consumer:
            # Setup mock consumer
            consumer_instance = Mock()
            consumer_instance.poll.side_effect = [mock_kafka_message, None]
            mock_consumer.return_value = consumer_instance

            # Create manager and process data
            manager = StreamDataManager(config)
            data = manager.get_data()

            # Verify results
            assert isinstance(data, pd.DataFrame)
            assert 'partition_id' in data.columns
            assert len(data) == 1

            # Verify metrics
            metrics = manager.get_metrics()
            assert metrics['manager_metrics']['failed_validations'] == 0
            assert metrics['loader_metrics']['failed_loads'] == 0

    def test_end_to_end_connection_failure(self, config):
        """Test handling of connection failures"""
        with patch('confluent_kafka.Consumer') as mock_consumer:
            mock_consumer.side_effect = KafkaException("Connection failed")

            with pytest.raises(Exception) as exc_info:
                manager = StreamDataManager(config)

            assert "Connection failed" in str(exc_info.value)

    def test_end_to_end_validation_failure(self, config, mock_kafka_message):
        """Test handling of validation failures"""
        with patch('confluent_kafka.Consumer') as mock_consumer:
            # Setup mock consumer with invalid data
            consumer_instance = Mock()
            invalid_message = Mock()
            invalid_message.error.return_value = None
            invalid_message.value.return_value = b'{"value": "test"}'  # Missing partition_id
            consumer_instance.poll.side_effect = [invalid_message, None]
            mock_consumer.return_value = consumer_instance

            manager = StreamDataManager(config)
            with pytest.raises(StreamingDataValidationError):
                manager.get_data()

    def test_end_to_end_recovery(self, config, mock_kafka_message):
        """Test pipeline recovery after temporary failures"""
        with patch('confluent_kafka.Consumer') as mock_consumer:
            # Setup mock consumer with failure then success
            consumer_instance = Mock()
            error_message = Mock()
            error_message.error.return_value = KafkaException("Temporary error")
            consumer_instance.poll.side_effect = [
                error_message,  # First attempt fails
                mock_kafka_message,  # Second attempt succeeds
                None
            ]
            mock_consumer.return_value = consumer_instance

            manager = StreamDataManager(config)
            with pytest.raises(Exception):
                manager.get_data()  # First attempt fails

            # Second attempt should succeed
            data = manager.get_data()
            assert isinstance(data, pd.DataFrame)
            assert len(data) == 1

    def test_end_to_end_metrics_aggregation(self, config, mock_kafka_message):
        """Test comprehensive metrics collection through the pipeline"""
        with patch('confluent_kafka.Consumer') as mock_consumer:
            consumer_instance = Mock()
            consumer_instance.poll.side_effect = [mock_kafka_message, None]
            mock_consumer.return_value = consumer_instance

            manager = StreamDataManager(config)
            manager.get_data()

            metrics = manager.get_metrics()
            assert 'manager_metrics' in metrics
            assert 'loader_metrics' in metrics
            assert 'validator_metrics' in metrics

            # Verify metrics at each level
            assert metrics['manager_metrics']['total_batches'] > 0
            assert metrics['loader_metrics']['batches_processed'] > 0
            assert metrics['loader_metrics']['connector_metrics']['messages_processed'] > 0

    @pytest.mark.timeout(10)
    def test_end_to_end_performance(self, config):
        """Test performance characteristics of the pipeline"""
        with patch('confluent_kafka.Consumer') as mock_consumer:
            consumer_instance = Mock()
            # Generate 1000 messages
            messages = [Mock() for _ in range(1000)]
            for msg in messages:
                msg.error.return_value = None
                msg.value.return_value = b'{"partition_id": "p1", "value": "test", "timestamp": "2024-01-01T00:00:00"}'
            messages.append(None)
            consumer_instance.poll.side_effect = messages
            mock_consumer.return_value = consumer_instance

            manager = StreamDataManager(config)
            data = manager.get_data(batch_size=1000)

            assert len(data) == 1000
            metrics = manager.get_metrics()
            assert metrics['loader_metrics']['connector_metrics']['messages_per_second'] > 0