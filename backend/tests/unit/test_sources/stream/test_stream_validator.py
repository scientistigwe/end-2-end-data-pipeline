import pytest
from backend.backend.data_pipeline.source.stream.stream_config import StreamConfig
from backend.backend.data_pipeline.source.stream.stream_validator import StreamValidator

def test_validate_source_valid():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user', 'password': 'pass'})
    validator = StreamValidator(config)
    assert validator.validate_source() is True

def test_validate_source_missing_field():
    config = StreamConfig(source_type='Kafka', endpoint=None, credentials={'username': 'user'})
    validator = StreamValidator(config)
    with pytest.raises(ValueError):
        validator.validate_source()
