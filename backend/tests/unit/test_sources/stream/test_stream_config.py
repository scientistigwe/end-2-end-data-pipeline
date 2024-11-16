import pytest
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_config import StreamConfig

def test_stream_config_init():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user', 'password': 'pass'})
    assert config.source_type == 'Kafka'
    assert config.endpoint == 'localhost:9092'
    assert config.credentials == {'username': 'user', 'password': 'pass'}

def test_missing_credentials():
    with pytest.raises(ValueError):
        StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials=None)

def test_get_config():
    config = StreamConfig(source_type='Kinesis', endpoint='localhost:8080', credentials={'username': 'user'})
    config_data = config.get_config()
    assert config_data['source_type'] == 'Kinesis'
    assert 'username' in config_data['credentials']
