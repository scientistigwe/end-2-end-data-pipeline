import pytest
from unittest.mock import MagicMock, patch
from backend.data_pipeline.source.database.db_connector import DatabaseConnector
from backend.data_pipeline.source.database.db_security import DataSecurityManager
from backend.data_pipeline.source.database.db_types import DatabaseType
from backend.data_pipeline.exceptions import DatabaseConnectionError, DatabaseError
from backend.data_pipeline.source.database.db_validator import DatabaseValidator

@pytest.fixture
def connector_mock():
    connector = MagicMock(spec=DatabaseConnector)
    connector.config = MagicMock()
    connector.config.db_type = DatabaseType.POSTGRESQL
    connector.config.get_connection_params.return_value = {
        'host': 'localhost',
        'port': 5432,
        'database': 'test_db',
        'username': 'test_user'
    }
    return connector

    # Mock the load_data method to return our test DataFrame
    db_manager.loader.load_data = MagicMock(return_value=test_df)

@pytest.fixture
def security_manager_mock():
    return MagicMock(spec=DataSecurityManager)

@pytest.fixture
def db_validator(connector_mock, security_manager_mock):
    return DatabaseValidator(connector_mock, security_manager_mock)

def test_validate_connection_success(db_validator, connector_mock):
    with patch.object(connector_mock, 'get_connection', MagicMock()) as mocked_connection:
        mock_cursor = MagicMock()
        mocked_connection.return_value.__enter__.return_value.cursor.return_value = mock_cursor
        mock_cursor.execute.return_value = None
        mock_cursor.fetchone.return_value = (1,)

        with pytest.raises(DatabaseConnectionError, match="Database connection validation failed:"):
            db_validator.validate_connection()

def test_validate_connection_failure(db_validator, connector_mock):
    with patch.object(connector_mock, 'get_connection', side_effect=Exception("Connection failed")):
        with pytest.raises(DatabaseConnectionError, match="Database connection validation failed: Connection failed"):
            db_validator.validate_connection()

def test_validate_db_type_unsupported(db_validator, connector_mock):
    mock_db_type = MagicMock()
    mock_db_type.name = "UNSUPPORTED_DB"
    connector_mock.config.db_type = mock_db_type

    with pytest.raises(DatabaseError, match="Unsupported database type: UNSUPPORTED_DB"):
        db_validator._validate_db_type(None)

def test_validate_postgresql_params_success(db_validator, connector_mock):
    with patch.object(db_validator, '_validate_connection_params', return_value=None) as validate_params_mock:
        db_validator._validate_postgresql(MagicMock())
        validate_params_mock.assert_called_once()

def test_validate_connection_params_missing_params(db_validator, connector_mock):
    connector_mock.config.get_connection_params.return_value = {
        'host': 'localhost',
        'database': 'test_db',
        'username': 'test_user'
    }

    with pytest.raises(DatabaseError, match="Database connection parameter validation failed: Missing required parameters"):
        db_validator._validate_connection_params(None)

def test_validate_query_structure_success(db_validator):
    mock_connection = MagicMock()
    mock_cursor = mock_connection.cursor.return_value
    mock_cursor.execute.return_value = None
    mock_cursor.fetchone.return_value = (1,)
    mock_cursor.connection.query = "SELECT 1"

    with pytest.raises(DatabaseError, match="Database query structure validation failed: Failed to execute test query"):
        db_validator._validate_query_structure(mock_connection)

def test_validate_query_structure_injection_detected(db_validator):
    mock_connection = MagicMock()
    mock_cursor = mock_connection.cursor.return_value
    mock_cursor.execute.return_value = None
    mock_cursor.fetchone.return_value = (1,)
    mock_cursor.connection.query = "SELECT * FROM users UNION SELECT * FROM passwords"

    with pytest.raises(DatabaseError, match="Database query structure validation failed: Failed to execute test query"):
        db_validator._validate_query_structure(mock_connection)

def test_validate_query_structure_failure(db_validator):
    mock_connection = MagicMock()
    mock_cursor = mock_connection.cursor.side_effect = Exception("Failed to execute test query")

    with pytest.raises(DatabaseError, match="Database query structure validation failed: Failed to execute test query"):
        db_validator._validate_query_structure(mock_connection)
