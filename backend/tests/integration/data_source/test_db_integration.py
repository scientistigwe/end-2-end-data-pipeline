from unittest.mock import MagicMock, patch
import pytest
import pandas as pd
from datetime import datetime
from backend.data_pipeline.source.database.db_config import DatabaseConfig
from backend.data_pipeline.source.database.db_connector import DatabaseConnector
from backend.data_pipeline.source.database.db_data_manager import DBDataManager, DBData
from backend.data_pipeline.source.database.db_security import DataSecurityManager
from backend.data_pipeline.source.database.db_validator import DatabaseValidator
from backend.data_pipeline.source.database.db_types import DatabaseType


@pytest.fixture(scope="module")
def db_config():
    """Create a mock database configuration"""
    config = MagicMock(spec=DatabaseConfig)
    config.get_connection_params.return_value = {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'username': 'test_user',
        'password': 'test_password'
    }
    return config

@pytest.fixture(scope="module")
def db_connector(db_config):
    """Create a mock database connector"""
    connector = MagicMock(spec=DatabaseConnector)
    connector.config = db_config
    connector.connect.return_value = None  # Simulate a successful connection
    return connector

@pytest.fixture(scope="module")
def db_data_manager(db_connector):
    """Create a mock data manager"""
    manager = DBDataManager(db_connector)
    manager.loader = MagicMock()  # Mock the loader to avoid real DB calls
    return manager

@pytest.fixture(scope="module")
def data_security_manager():
    """Create a mock data security manager"""
    return MagicMock(spec=DataSecurityManager)

@pytest.fixture(scope="module")
def validator(db_connector, data_security_manager):
    """Create a mock validator"""
    validator = DatabaseValidator(db_connector, data_security_manager)
    validator._validate_db_type = MagicMock(return_value=True)
    validator._validate_connection_params = MagicMock()
    validator._validate_query_structure = MagicMock()
    return validator

@pytest.fixture(scope="module")
def mock_db_data():
    """Create mock database data"""
    return [
        DBData(
            id=1,
            table_name='users',
            data_type=DatabaseType.POSTGRESQL,
            last_updated=datetime(2023, 1, 1, 12, 0, 0)
        )
    ]

@pytest.fixture(scope="module")
def mock_dataframe():
    """Create a mock DataFrame for testing"""
    return pd.DataFrame({
        'id': [1],
        'name': ['Test User'],
        'email': ['test@example.com'],
        'last_updated': [datetime(2023, 1, 1, 12, 0, 0)]
    })

def test_full_workflow(db_data_manager, mock_db_data, mock_dataframe, monkeypatch):
    """Test the full workflow from encryption to decryption"""
    # Mock the loader's load_data method
    db_data_manager.loader.load_data = MagicMock(return_value=mock_dataframe)

    # Test encryption
    encrypted_data = db_data_manager.encrypt_data(mock_db_data)
    assert isinstance(encrypted_data, list)
    assert len(encrypted_data) == 1

    # Test decryption
    decrypted_data = db_data_manager.decrypt_data(encrypted_data)
    assert isinstance(decrypted_data, list)
    assert len(decrypted_data) == 1
    assert decrypted_data[0].id == mock_db_data[0].id
    assert decrypted_data[0].table_name == mock_db_data[0].table_name

    # Test validation
    db_data_manager.validate_data = MagicMock(return_value=None)
    db_data_manager.validate_data(decrypted_data)



# Test the database type validation
@patch.object(DatabaseValidator, '_validate_db_type')  # Mock the _validate_db_type method of the Validator class
def test_db_type_validation(mock_validate_db_type, validator):
    """Test database type validation"""
    # Call the method you're testing, passing DatabaseType.POSTGRESQL
    DatabaseValidator._validate_db_type(DatabaseType.POSTGRESQL)

    # Assert that _validate_db_type was called with DatabaseType.POSTGRESQL
    mock_validate_db_type.assert_called_with(DatabaseType.POSTGRESQL)


# Test the SQL query structure validation
@patch.object(DatabaseValidator, '_validate_query_structure')  # Mock the _validate_query_structure method
def test_query_structure_validation(mock_validate_query_structure, validator):
    """Test SQL query structure validation"""
    # Call the method you're testing
    DatabaseValidator._validate_query_structure("SELECT * FROM users")

    # Assert that _validate_query_structure was called with the expected SQL query
    mock_validate_query_structure.assert_called_with("SELECT * FROM users")

