import pytest
from unittest import mock
from datetime import datetime
import pandas as pd
from backend.data_pipeline.source.database.db_connector import DatabaseConnector
from backend.data_pipeline.source.database.db_data_loader import DatabaseLoader
from backend.data_pipeline.source.database.db_data_manager import DBDataManager, DBData
from backend.data_pipeline.exceptions import DatabaseConnectionError, DatabaseError
from backend.data_pipeline.source.database.db_types import DatabaseType


# Mock Connection Class using MagicMock
class MockConnection:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.closed = False

    def cursor(self):
        if self.should_fail:
            raise Exception("Cursor operation failed")
        cursor = mock.MagicMock()
        cursor.execute = mock.MagicMock()
        cursor.fetchall = mock.MagicMock(return_value=[])
        return cursor

    def close(self):
        self.closed = True


@pytest.fixture
def mock_config():
    """Fixture to mock the database config"""
    config = mock.MagicMock()
    config.db_type = DatabaseType.POSTGRESQL
    config.host = "localhost"
    config.port = 5432
    config.database = "test_db"
    config.user = "test_user"
    config.password = "test_password"
    config.get_connection_params = mock.MagicMock(return_value={
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'user': 'test_user',
        'password': 'test_password'
    })
    return config


@pytest.fixture
def db_connector(mock_config):
    """Fixture to mock the DatabaseConnector"""
    return DatabaseConnector(mock_config)


@pytest.fixture
def mock_db_data():
    """Fixture to mock DBData"""
    return [
        DBData(
            id=1,
            table_name='users',
            data_type=DatabaseType.POSTGRESQL,
            last_updated=datetime.now()
        )
    ]


@pytest.fixture
def db_manager(db_connector):
    """Fixture to create DBDataManager with mocked connection and loader"""
    manager = DBDataManager(db_connector)
    # Create a mock loader and attach it to the manager
    manager.loader = mock.MagicMock()
    manager.loader.load_data = mock.MagicMock()
    manager.security_manager = mock.MagicMock()
    manager.security_manager.encrypt = mock.MagicMock(side_effect=lambda x: x)
    manager.security_manager.decrypt = mock.MagicMock(side_effect=lambda x: x)
    return manager


def test_validate_data(db_manager, mock_db_data):
    """Test data validation with proper mocking"""
    # Create a DataFrame that matches the expected structure
    test_df = pd.DataFrame({
        'id': [1],
        'name': ['Test User']
    })

    # Set up the mock to return our test DataFrame
    db_manager.loader.load_data.return_value = test_df

    # Mock the get_connection() context manager
    with mock.patch.object(db_manager.connector, 'get_connection') as mock_get_connection:
        mock_conn = MockConnection()
        mock_get_connection.return_value.__enter__.return_value = mock_conn

        # Call validate_data
        db_manager.validate_data(mock_db_data)

        # Verify load_data was called exactly once
        assert db_manager.loader.load_data.call_count == 1

        # Verify the query contains the expected table name
        call_args = db_manager.loader.load_data.call_args[0][0]
        assert "SELECT * FROM users" in call_args


def test_load_data_call(db_manager, mock_db_data):
    """Test that load_data is called with correct arguments"""
    # Create a DataFrame that matches the expected structure
    test_df = pd.DataFrame({
        'id': [1],
        'name': ['Test User']
    })

    # Set up the mock to return our test DataFrame
    db_manager.loader.load_data.return_value = test_df

    # Mock the get_connection() context manager
    with mock.patch.object(db_manager.connector, 'get_connection') as mock_get_connection:
        mock_conn = MockConnection()
        mock_get_connection.return_value.__enter__.return_value = mock_conn

        # Call validate_data which should trigger load_data
        db_manager.validate_data(mock_db_data)

        # Verify load_data was called exactly once
        assert db_manager.loader.load_data.call_count == 1

        # Verify the query
        call_args = db_manager.loader.load_data.call_args[0][0]
        assert "SELECT * FROM users" in call_args


def test_connection_error(mock_config):
    """Test database connection error handling"""
    connector = DatabaseConnector(mock_config)

    # Mock _create_connection to raise an exception
    with mock.patch.object(connector, '_create_connection') as mock_create:
        mock_create.side_effect = Exception("Connection failed")

        # Test that connect() raises DatabaseConnectionError
        with pytest.raises(DatabaseConnectionError) as exc_info:
            connector.connect()

        assert "Connection failed" in str(exc_info.value)

        # Test that get_connection() also raises DatabaseConnectionError
        with pytest.raises(DatabaseConnectionError) as exc_info:
            with connector.get_connection():
                pass

        assert "Connection failed" in str(exc_info.value)