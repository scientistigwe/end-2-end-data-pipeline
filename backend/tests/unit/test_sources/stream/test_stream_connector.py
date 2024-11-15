"""Unit tests for stream connector. tests/test_stream_connector.py"""

import pytest
import confluent_kafka
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_connector import StreamConnector
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import StreamingDataLoadingError
from unittest.mock import Mock, patch
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_types import StreamConfig


class TestStreamConnector:
    def setup_method(self):
        self.config: StreamConfig = {
            'stream_name': 'test_stream',
            'batch_size': 100,
            'max_retries': 3
        }
        self.connector = StreamConnector(self.config)

    def test_connect(self):
        # Add your test implementation here
        pass
    @pytest.fixture
    def mock_consumer(self):
        return Mock(spec=confluent_kafka.Consumer)

    @pytest.fixture
    def config(self):
        return StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic'
        )

    @pytest.fixture
    def connector(self, config, mock_consumer):
        with patch('confluent_kafka.Consumer', return_value=mock_consumer):
            connector = StreamConnector(config)
            return connector

    def test_initialization(self, connector, mock_consumer):
        assert connector.consumer is not None
        mock_consumer.subscribe.assert_called_once_with(['test-topic'])

    def test_connection_retry(self, config):
        with patch('confluent_kafka.Consumer') as mock_consumer_class:
            mock_consumer_class.side_effect = [
                confluent_kafka.KafkaException("Connection failed"),
                Mock(spec=confluent_kafka.Consumer)
            ]
            connector = StreamConnector(config)
            assert connector.metrics['connection_attempts'] == 1

    def test_read_messages_success(self, connector, mock_consumer):
        mock_message = Mock()
        mock_message.error.return_value = None
        mock_message.value.return_value = b'{"test": "data"}'
        mock_consumer.poll.side_effect = [mock_message, None]

        messages = connector.read_messages(batch_size=1)
        assert len(messages) == 1
        assert messages[0] == '{"test": "data"}'

    def test_read_messages_error(self, connector, mock_consumer):
        mock_message = Mock()
        mock_message.error.return_value = confluent_kafka.KafkaError("Test error")
        mock_consumer.poll.return_value = mock_message

        with pytest.raises(StreamingDataLoadingError):
            connector.read_messages()

    def test_metrics_tracking(self, connector, mock_consumer):
        mock_message = Mock()
        mock_message.error.return_value = None
        mock_message.value.return_value = b'{"test": "data"}'
        mock_consumer.poll.side_effect = [mock_message, None]

        connector.read_messages()
        metrics = connector.get_metrics()

        assert metrics['messages_processed'] == 1
        assert metrics['last_poll_timestamp'] is not None
        assert len(metrics['batch_sizes']) == 1

