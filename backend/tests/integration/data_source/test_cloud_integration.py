# test_cloud_integration.py

import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from backend.data_pipeline.source.cloud.s3_connector import S3Connector
from backend.data_pipeline.source.cloud.s3_data_loader import S3DataLoader
from backend.data_pipeline.source.cloud.s3_data_manager import S3DataManager
from backend.data_pipeline.source.cloud.s3_security import DataSecurityManager
from backend.data_pipeline.source.cloud.s3_validator import S3Validator

@pytest.fixture
def mock_boto3_session():
    with patch('boto3.Session') as mock_session:
        mock_client = MagicMock()
        mock_resource = MagicMock()

        # Configure list_buckets for successful initialization
        mock_client.list_buckets.return_value = {'Buckets': []}

        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.resource.return_value = mock_resource

        yield mock_session, mock_client, mock_resource

@pytest.fixture
def s3_connector(mock_boto3_session):
    _, mock_client, mock_resource = mock_boto3_session
    connector = S3Connector(
        aws_access_key='mock_access_key',
        aws_secret_key='mock_secret_key',
        region_name='us-east-1'
    )
    connector.s3_client = mock_client
    connector.s3_resource = mock_resource
    return connector

@pytest.fixture
def s3_data_loader(s3_connector):
    return S3DataLoader(s3_connector)

@pytest.fixture
def s3_manager(mock_boto3_session):
    return S3DataManager(
        aws_access_key='mock_access_key',
        aws_secret_key='mock_secret_key',
        region_name='us-east-1'  # Use valid region name for tests
    )

@pytest.fixture
def security_manager():
    with patch('backend.data_pipeline.source.cloud.s3_security.os.environ',
               {'ENCRYPTION_KEY': 'mock_key'}):
        return DataSecurityManager()

@pytest.fixture
def s3_validator(s3_connector):
    return S3Validator(s3_connector)

@patch('backend.data_pipeline.source.cloud.s3_data_loader.pd.read_csv')
def test_end_to_end_data_loading(mock_read_csv, s3_manager, mock_boto3_session):
    # Arrange
    mock_df = pd.DataFrame({'col1': [1, 2]})
    mock_read_csv.return_value = mock_df

    # Mock the S3 response
    mock_session, mock_client, _ = mock_boto3_session
    mock_body = MagicMock()
    mock_body.read.return_value = b"col1\n1\n2"
    mock_client.get_object.return_value = {'Body': mock_body}

    # Act
    df = s3_manager.validate_and_load('mock_bucket', 'mock_key')

    # Assert
    assert not df.empty
    assert 'col1' in df.columns
    pd.testing.assert_frame_equal(df, mock_df)
    mock_client.get_object.assert_called_once_with(
        Bucket='mock_bucket',
        Key='mock_key'
    )

@patch('backend.data_pipeline.source.cloud.s3_security.Fernet.encrypt')
@patch('backend.data_pipeline.source.cloud.s3_security.Fernet.decrypt')
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


def test_end_to_end_validation(s3_validator, mock_boto3_session):
    # Arrange
    _, mock_client, _ = mock_boto3_session
    mock_client.list_buckets.return_value = {'Buckets': []}

    # Act
    result, error_message = s3_validator.validate_connection()

    # Assert
    assert result is True
    assert error_message is None

    # Assert that list_buckets was called exactly twice
    assert mock_client.list_buckets.call_count == 2  # Check for two calls

