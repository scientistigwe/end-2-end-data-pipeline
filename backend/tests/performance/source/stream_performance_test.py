import pytest
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_connector import StreamConnector
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_config import StreamConfig

@pytest.mark.benchmark(group="stream-connector")
def test_kafka_connection_performance(benchmark):
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user'})
    connector = StreamConnector(config)
    benchmark(connector.connect)
