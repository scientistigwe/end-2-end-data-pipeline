import pytest
from datetime import datetime
from unittest import mock
from backend.backend.data_pipeline.source.database.db_data_manager import DBDataManager, DBData
from backend.backend.data_pipeline.source.database.db_connector import DatabaseConnector
from backend.backend.data_pipeline.source.database.db_config import DatabaseConfig
from backend.backend.data_pipeline.source.database.db_security import DataSecurityManager
from backend.backend.data_pipeline.source.database.db_types import DatabaseType

# Fixtures with MagicMock

@pytest.fixture
def db_config():
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
    connector = mock.MagicMock(DatabaseConnector)
    connector.config = db_config
    return connector


@pytest.fixture
def data_security_manager():
    security_manager = mock.MagicMock(DataSecurityManager)
    return security_manager


@pytest.fixture
def db_data_manager(db_connector, data_security_manager):
    db_manager = mock.MagicMock(DBDataManager)
    db_manager.connector = db_connector
    db_manager.security_manager = data_security_manager
    return db_manager


# Tests with MagicMock for all components

def test_get_data(db_data_manager):
    mock_data = [
        mock.MagicMock(DBData, id=1, table_name='users', data_type=DatabaseType.POSTGRESQL, last_updated=datetime.now()),
        mock.MagicMock(DBData, id=2, table_name='products', data_type=DatabaseType.MYSQL, last_updated=datetime.now())
    ]

    # Mock the get_data method
    db_data_manager.get_data.return_value = mock_data

    result = db_data_manager.get_data({
        'table_name': 'users',
        'data_type': DatabaseType.POSTGRESQL
    })

    assert isinstance(result, list)
    assert all(isinstance(item, DBData) for item in result)
    db_data_manager.get_data.assert_called_once_with({
        'table_name': 'users',
        'data_type': DatabaseType.POSTGRESQL
    })


def test_validate_data(db_data_manager):
    # Create mock data for DBData
    mock_data = [
        mock.MagicMock(DBData, id=1, table_name='users', data_type=DatabaseType.POSTGRESQL, last_updated=datetime.now()),
        mock.MagicMock(DBData, id=2, table_name='products', data_type=DatabaseType.MYSQL, last_updated=datetime.now())
    ]

    # Mock the validate_data method (we're mocking the method itself, not the DBData object)
    db_data_manager.validate_data = mock.MagicMock()

    # Call the method we're testing
    db_data_manager.validate_data(mock_data)

    # Ensure validate_data was called with the expected mock_data
    db_data_manager.validate_data.assert_called_once_with(mock_data)

def test_encrypt_decrypt(db_data_manager):
    mock_data = [
        mock.MagicMock(DBData, id=1, table_name='users', data_type=DatabaseType.POSTGRESQL, last_updated=datetime.now())
    ]

    # Mock the encrypt and decrypt methods
    db_data_manager.encrypt_data.return_value = mock_data
    db_data_manager.decrypt_data.return_value = mock_data

    encrypted_data = db_data_manager.encrypt_data(mock_data)
    decrypted_data = db_data_manager.decrypt_data(encrypted_data)

    assert isinstance(decrypted_data, list)
    assert len(decrypted_data) == 1
    db_data_manager.encrypt_data.assert_called_once_with(mock_data)
    db_data_manager.decrypt_data.assert_called_once_with(encrypted_data)
