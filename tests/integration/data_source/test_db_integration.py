import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from data_pipeline.source.database.db_connector import DBConnector
from data_pipeline.source.database.db_data_loader import DBDataLoader
from data_pipeline.source.database.db_data_manager import DBDataManager
from data_pipeline.source.database.db_validator import DBValidator
from data_pipeline.source.database.db_security import DataSecurityManager

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from data_pipeline.source.database.db_connector import DBConnector
from data_pipeline.source.database.db_data_loader import DBDataLoader
from data_pipeline.source.database.db_data_manager import DBDataManager
from data_pipeline.source.database.db_validator import DBValidator
from data_pipeline.source.database.db_security import DataSecurityManager

@pytest.fixture
def db_connector():
    connector = DBConnector(db_type='postgresql', host='localhost', user='user', password='password', db_name='test_db')
    with patch('psycopg2.connect') as mock_connect:
        mock_connect.return_value = MagicMock()
        yield connector

@pytest.fixture
def db_validator(db_connector):
    validator = DBValidator(db_connector)
    # Mock the validate_encryption_key method to return success
    with patch.object(validator, 'validate_encryption_key', return_value=(True, "")):
        yield validator

@pytest.fixture
def security_manager(db_validator):
    with patch.dict('os.environ', {'ENCRYPTION_KEY': 'test_encryption_key'}):
        return DataSecurityManager(db_validator)

@pytest.fixture
def db_data_loader(db_connector):
    return DBDataLoader(db_connector)

@pytest.fixture
def db_data_manager(db_connector):
    data_loader = DBDataLoader(db_connector)
    validator = DBValidator(db_connector)
    with patch.dict('os.environ', {'ENCRYPTION_KEY': 'test_encryption_key'}):
        security_manager = DataSecurityManager(validator)

    with patch('data_pipeline.source.database.db_data_loader.DBDataLoader',
              return_value=data_loader), \
         patch('data_pipeline.source.database.db_validator.DBValidator',
              return_value=validator), \
         patch('data_pipeline.source.database.db_security.DataSecurityManager',
              return_value=security_manager):
        yield DBDataManager(db_type='postgresql', host='localhost', user='user',
                          password='password', db_name='test_db')

def test_integration_pipeline(db_data_manager, security_manager):
    # Mocking the DB connection and cursor
    with patch.object(db_data_manager.db_connector, 'connect'), \
         patch.object(db_data_manager.db_connector.connection, 'cursor'), \
         patch.object(db_data_manager.db_data_loader, 'load_data') as mock_load_data, \
         patch.object(db_data_manager.db_validator, 'validate_connection',
                     return_value=(True, "")):
        # Sample DataFrame to mock data loading
        mock_data = pd.DataFrame({'col1': [1, 2, 3], 'col2': ['A', 'B', 'C']})
        mock_load_data.return_value = mock_data

        # Run validation and data loading
        loaded_data = db_data_manager.validate_and_load('SELECT * FROM test_table')

        # Assert data was loaded successfully
        assert not loaded_data.empty
        assert 'col1' in loaded_data.columns
        assert 'col2' in loaded_data.columns

        # Test data encryption
        encrypted_data = db_data_manager.encrypt_and_transmit_data(loaded_data)
        assert isinstance(encrypted_data, bytes)

        # Decrypt data to verify
        decrypted_data = security_manager.decrypt_data(encrypted_data)
        assert decrypted_data == loaded_data.to_json(orient='records')

def test_integration_with_mongodb(db_connector):
    # Change the DBConnector to mock MongoDB
    db_connector.db_type = 'mongodb'
    with patch('pymongo.MongoClient') as mock_client:
        mock_client.return_value = MagicMock()
        db_connector.connect()

        # Test connection and ensure MongoDB client was called
        mock_client.assert_called_once()

