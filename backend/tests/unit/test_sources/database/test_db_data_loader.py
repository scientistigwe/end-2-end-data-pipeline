import pandas as pd
import pytest
from unittest import mock
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_data_loader import DatabaseLoader
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_connector import DatabaseConnector
from backend.src.end_2_end_data_pipeline.data_pipeline.source.database.db_config import DatabaseConfig
from backend.src.end_2_end_data_pipeline.data_pipeline.exceptions import DatabaseQueryError


# Mock for cursor method to simulate DB interactions
def mock_cursor(self):
    cursor = mock.MagicMock()
    cursor.execute = mock.MagicMock()
    cursor.fetchall = mock.MagicMock(return_value=[{'id': 1, 'name': 'John Doe', 'email': 'johndoe@example.com'}])
    return cursor


@pytest.fixture
def db_config():
    # Mock DatabaseConfig
    config = mock.MagicMock(DatabaseConfig)
    config.from_dict.return_value = config
    config.db_type = 'postgresql'
    config.host = 'localhost'
    config.port = 5432
    config.database = 'test_db'
    config.username = 'test_user'
    config.password = 'test_password'
    return config


@pytest.fixture
def db_connector(db_config):
    # Mock DatabaseConnector
    connector = mock.MagicMock(DatabaseConnector)
    connector.config = db_config
    connector.get_connection = mock.MagicMock()
    connector.get_connection.return_value.__enter__.return_value = mock.MagicMock()
    connector.get_connection.return_value.__enter__.return_value.cursor = mock_cursor
    return connector


@pytest.fixture
def db_loader(db_connector):
    # Mock DatabaseLoader
    loader = mock.MagicMock(DatabaseLoader)
    loader.connector = db_connector
    return loader


# Test for load_data method with MagicMock
def test_load_data(db_loader):
    # Mock the load_data method to return a DataFrame
    db_loader.load_data = mock.MagicMock(return_value=pd.DataFrame([{
        'id': 1, 'name': 'John Doe', 'email': 'johndoe@example.com'
    }]))

    try:
        # Test that load_data returns the correct DataFrame
        result = db_loader.load_data("SELECT * FROM users LIMIT 5")
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0
        assert all(col in result.columns for col in ['id', 'name', 'email'])

        # Check if the correct query was executed
        db_loader.load_data.assert_called_once_with("SELECT * FROM users LIMIT 5")

    except DatabaseQueryError as e:
        pytest.fail(f"Database query failed: {str(e)}")


# Example of a placeholder for MongoDB-specific test (yet to be implemented)
def test_load_mongodb_data(db_loader):
    # Implement MongoDB-specific test
    pass
