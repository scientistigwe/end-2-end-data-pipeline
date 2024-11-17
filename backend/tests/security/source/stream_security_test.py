from backend.backend.data_pipeline.source.stream.stream_config import StreamConfig

def test_credentials_security():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user', 'password': 'sensitive_pass'})
    # Ensure no sensitive information is logged or returned
    config_data = config.get_config()
    assert 'password' not in config_data
