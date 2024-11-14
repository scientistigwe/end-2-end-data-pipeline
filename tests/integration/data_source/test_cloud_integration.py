import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from data_pipeline.source.cloud.s3_connector import S3Connector
from data_pipeline.source.cloud.s3_data_loader import S3DataLoader
from data_pipeline.source.cloud.s3_data_manager import S3DataManager
from data_pipeline.source.cloud.s3_security import DataSecurityManager
from data_pipeline.source.cloud.s3_validator import S3Validator
from data_pipeline.exceptions import CloudConnectionError, CloudQueryError, DataEncodingError


@pytest.fixture
def s3_connector():
    return S3Connector('mock_access_key', 'mock_secret_key', 'mock_region')


@pytest.fixture
def s3_data_loader(s3_connector):
    s3_connector.connect = MagicMock()  # Mock the connection to avoid actual AWS interaction
    s3_connector.s3 = MagicMock()
    return S3DataLoader(s3_connector)


@pytest.fixture
def s3_manager(s3_connector):
    return S3DataManager('mock_access_key', 'mock_secret_key', 'mock_region')


@pytest.fixture
def security_manager():
    with patch('data_pipeline.source.cloud.s3_security.os.environ', {'ENCRYPTION_KEY': 'mock_key'}):
        return DataSecurityManager()


@pytest.fixture
def s3_validator(s3_connector):
    return S3Validator(s3_connector)


@patch('data_pipeline.source.cloud.s3_data_loader.pd.read_csv')
def test_end_to_end_data_loading(mock_read_csv, s3_manager, s3_data_loader):
    # Arrange
    mock_read_csv.return_value = pd.DataFrame({'col1': [1, 2]})
    s3_manager.s3_data_loader = s3_data_loader
    mock_validator = MagicMock()
    mock_validator.validate_connection.return_value = (True, '')
    s3_manager.s3_validator = mock_validator

    # Act
    df = s3_manager.validate_and_load('mock_bucket', 'mock_key')

    # Assert
    assert not df.empty
    assert 'col1' in df.columns
    mock_read_csv.assert_called_once()
    mock_validator.validate_connection.assert_called_once()

@patch('data_pipeline.source.cloud.s3_security.Fernet.encrypt')
@patch('data_pipeline.source.cloud.s3_security.Fernet.decrypt')
def test_end_to_end_data_encryption_decryption(mock_decrypt, mock_encrypt, security_manager):
    # Arrange
    mock_encrypt.return_value = b'encrypted_data'
    mock_decrypt.return_value = b'test data'

    # Act
    encrypted_data = security_manager.encrypt_data('test data')
    decrypted_data = security_manager.decrypt_data(encrypted_data)

    # Assert
    assert encrypted_data == b'string:encrypted_data'
    assert decrypted_data == 'test data'
    mock_encrypt.assert_called_once()
    mock_decrypt.assert_called_once()

@pytest.mark.usefixtures("s3_connector", "s3_validator")
def test_end_to_end_validation(s3_validator):
    # Arrange
    s3_validator.s3_connector.s3.buckets.all.return_value = []  # Simulate a successful connection

    # Act
    result, message = s3_validator.validate_connection()

    # Assert
    assert result is True
    assert message == ''
