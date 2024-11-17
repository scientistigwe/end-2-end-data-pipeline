import pytest
from backend.backend.data_pipeline.source.stream.stream_connector import StreamConnector
from backend.backend.data_pipeline.source.stream.data_fetcher import DataLoader
from backend.backend.data_pipeline.source.stream.stream_config import StreamConfig
import pandas as pd
import os

def test_fetch_data_dataframe():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user'})
    connector = StreamConnector(config)
    loader = DataLoader(connector)
    
    data = loader.fetch_data()
    assert isinstance(data, pd.DataFrame)
    assert not data.empty

def test_fetch_data_parquet():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user'})
    connector = StreamConnector(config)
    loader = DataLoader(connector)
    
    # Simulate large data by creating a large DataFrame
    large_data = pd.DataFrame({'timestamp': ['2024-11-16T12:00:00Z']*1000000, 'value': range(1000000)})
    loader.fetch_data = lambda: large_data  # Override the fetch to simulate large data
    
    result = loader.fetch_data()
    assert result is None  # Data should be saved as Parquet, not returned
    assert os.path.exists('staging_area/stream_data.parquet')

def test_fetch_data_error():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user'})
    connector = StreamConnector(config)
    loader = DataLoader(connector)
    
    # Simulate an error scenario (e.g., invalid stream source)
    with pytest.raises(ValueError):
        loader.fetch_data()
