from backend.data_pipeline.source.stream.data_fetcher import DataLoader
from backend.data_pipeline.source.stream.stream_manager import DataManager
from backend.data_pipeline.source.stream.stream_connector import StreamConnector
from backend.data_pipeline.source.stream.stream_config import StreamConfig
import pandas as pd
import os

def test_manage_data_dataframe():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user'})
    connector = StreamConnector(config)
    loader = DataLoader(connector)
    manager = DataManager(loader)
    
    data = pd.DataFrame({'timestamp': ['2024-11-16T12:00:00Z'], 'value': [42]})
    loader.fetch_data = lambda: data  # Override fetch to simulate small data
    
    result = manager.manage_data()
    assert result == "DataFrame sent to orchestrator"

def test_manage_data_parquet():
    config = StreamConfig(source_type='Kafka', endpoint='localhost:9092', credentials={'username': 'user'})
    connector = StreamConnector(config)
    loader = DataLoader(connector)
    manager = DataManager(loader)
    
    # Simulate large data
    large_data = pd.DataFrame({'timestamp': ['2024-11-16T12:00:00Z']*1000000, 'value': range(1000000)})
    loader.fetch_data = lambda: large_data  # Override fetch to simulate large data
    
    result = manager.manage_data()
    assert result == "Parquet staged"
    assert os.path.exists('staging_area/stream_data.parquet')
