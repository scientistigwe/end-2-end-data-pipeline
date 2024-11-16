import pytest
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_config import StreamConfig
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_connector import StreamConnector

def test_kafka_connection():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user'})
    connector = StreamConnector(config)
    connection = connector.connect()
    assert connection == 'Kafka connection'

def test_kinesis_connection():
    config = StreamConfig(source_type='Kinesis', endpoint='localhost:8080', credentials={'username': 'user'})
    connector = StreamConnector(config)
    connection = connector.connect()
    assert connection == 'Kinesis connection'

def test_http_connection():
    config = StreamConfig(source_type='HTTP', endpoint='http://localhost:8080', credentials={'username': 'user'})
    connector = StreamConnector(config)
    connection = connector.connect()
    assert connection == 'HTTP connection'

def test_invalid_connection():
    config = StreamConfig(source_type='Invalid', endpoint='localhost', credentials={'username': 'user'})
    connector = StreamConnector(config)
    with pytest.raises(ValueError):
        connector.connect()
