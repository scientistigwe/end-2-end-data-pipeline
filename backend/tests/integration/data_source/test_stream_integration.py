import pytest
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_config import StreamConfig
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_validator import StreamValidator
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.stream_connector import StreamConnector
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.data_loader import DataLoader
from backend.src.end_2_end_data_pipeline.data_pipeline.source.stream.data_manager import DataManager
import os
import pandas as pd

def test_full_stream_pipeline():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user'})
    validator = StreamValidator(config)
    assert validator.validate_source() is True

    connector = StreamConnector(config)
    connection = connector.connect()
    assert connection == 'Kafka connection'

    loader = DataLoader(connector)
    data = loader.fetch_data()
    assert isinstance(data, pd.DataFrame)

    manager = DataManager(loader)
    result = manager.manage_data()
    assert result == "DataFrame sent to orchestrator"


def test_full_stream_pipeline_parquet():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user'})
    validator = StreamValidator(config)
    assert validator.validate_source() is True

    connector = StreamConnector(config)
    connection = connector.connect()
    assert connection == 'Kafka connection'

    loader = DataLoader(connector)
    large_data = pd.DataFrame({'timestamp': ['2024-11-16T12:00:00Z'] * 1000000, 'value': range(1000000)})
    loader.fetch_data = lambda: large_data  # Override fetch to simulate large data

    result = loader.fetch_data()
    assert result is None  # Data should be saved as Parquet

    manager = DataManager(loader)
    result = manager.manage_data()
    assert result == "Parquet staged"
    assert os.path.exists('staging_area/stream_data.parquet')
