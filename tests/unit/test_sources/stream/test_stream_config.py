# tests/unit/test_sources/stream/test_stream_config.py
import pytest
from data_pipeline.source.stream.stream_config import StreamConfig


class TestStreamConfig:
    @pytest.fixture
    def basic_config(self):
        return StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic'
        )

    @pytest.fixture
    def auth_config(self):
        return StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic',
            auth_config={
                'security.protocol': 'SASL_SSL',
                'sasl.mechanism': 'PLAIN',
                'sasl.username': 'test-user',
                'sasl.password': 'test-pass'
            }
        )

    def test_basic_config_creation(self, basic_config):
        """Test basic configuration creation and default values"""
        assert basic_config.bootstrap_servers == 'localhost:9092'
        assert basic_config.group_id == 'test-group'
        assert basic_config.topic == 'test-topic'
        assert basic_config.batch_size == 1000
        assert basic_config.poll_timeout == 1.0
        assert basic_config.max_poll_records == 500

    def test_auth_config_creation(self, auth_config):
        """Test configuration creation with authentication"""
        assert auth_config.auth_config['security.protocol'] == 'SASL_SSL'
        assert auth_config.auth_config['sasl.username'] == 'test-user'
        assert auth_config.auth_config['sasl.password'] == 'test-pass'

    def test_get_consumer_config(self, basic_config):
        """Test consumer configuration generation for basic setup"""
        consumer_config = basic_config.get_consumer_config()
        assert consumer_config['bootstrap.servers'] == 'localhost:9092'
        assert consumer_config['group.id'] == 'test-group'
        assert consumer_config['enable.auto.commit'] is False
        assert consumer_config['max.poll.records'] == 500
        assert consumer_config['auto.offset.reset'] == 'earliest'

    def test_get_consumer_config_with_auth(self, auth_config):
        """Test consumer configuration generation with authentication"""
        consumer_config = auth_config.get_consumer_config()
        assert consumer_config['bootstrap.servers'] == 'localhost:9092'
        assert consumer_config['group.id'] == 'test-group'
        assert consumer_config['security.protocol'] == 'SASL_SSL'
        assert consumer_config['sasl.mechanism'] == 'PLAIN'
        assert consumer_config['sasl.username'] == 'test-user'
        assert consumer_config['sasl.password'] == 'test-pass'
        assert consumer_config['enable.auto.commit'] is False

    def test_custom_batch_settings(self):
        """Test configuration with custom batch settings"""
        config = StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic',
            batch_size=2000,
            max_poll_records=1000
        )
        consumer_config = config.get_consumer_config()
        assert consumer_config['max.poll.records'] == 1000

    def test_default_values(self):
        """Test default values in configuration"""
        config = StreamConfig(
            bootstrap_servers='localhost:9092',
            group_id='test-group',
            topic='test-topic'
        )
        assert config.auth_config is None
        assert config.batch_size == 1000
        assert config.poll_timeout == 1.0
        assert config.max_poll_records == 500