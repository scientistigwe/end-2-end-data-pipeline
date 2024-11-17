# test_s3_validator.py
import pytest
from unittest.mock import MagicMock, patch
from botocore.exceptions import ClientError
from backend.backend.data_pipeline.exceptions import CloudConnectionError
from backend.backend.data_pipeline.source.cloud.s3_validator import S3Validator


@pytest.fixture
def mock_s3_connector():
    connector = MagicMock()
    connector.s3_client = MagicMock()
    return connector


@pytest.fixture
def s3_validator(mock_s3_connector):
    return S3Validator(mock_s3_connector)


def test_validate_connection_success(s3_validator):
    # Arrange
    s3_validator.s3_connector.s3_client.list_buckets.return_value = {'Buckets': []}

    # Act
    result, error_message = s3_validator.validate_connection()

    # Assert
    assert result is True
    assert error_message is None
    s3_validator.s3_connector.s3_client.list_buckets.assert_called_once()


def test_validate_connection_failure_client_error(s3_validator):
    # Arrange
    s3_validator.s3_connector.s3_client.list_buckets.side_effect = ClientError(
        error_response={'Error': {'Code': 'InvalidAccessKeyId', 'Message': 'Invalid access key'}},
        operation_name='ListBuckets'
    )

    # Act
    result, error_message = s3_validator.validate_connection()

    # Assert
    assert result is False
    assert "Invalid access key" in str(error_message)
    s3_validator.s3_connector.s3_client.list_buckets.assert_called_once()


def test_validate_connection_failure_cloud_connection_error(s3_validator):
    # Arrange
    s3_validator.s3_connector.s3_client.list_buckets.side_effect = CloudConnectionError(
        "Failed to connect to S3"
    )

    # Act
    result, error_message = s3_validator.validate_connection()

    # Assert
    assert result is False
    assert "Failed to connect to S3" in str(error_message)
    s3_validator.s3_connector.s3_client.list_buckets.assert_called_once()


def test_validate_connection_with_empty_buckets(s3_validator):
    # Arrange
    s3_validator.s3_connector.s3_client.list_buckets.return_value = {'Buckets': []}

    # Act
    result, error_message = s3_validator.validate_connection()

    # Assert
    assert result is True
    assert error_message is None
    s3_validator.s3_connector.s3_client.list_buckets.assert_called_once()


def test_validate_connection_with_buckets(s3_validator):
    # Arrange
    s3_validator.s3_connector.s3_client.list_buckets.return_value = {
        'Buckets': [{'Name': 'test-bucket'}]
    }

    # Act
    result, error_message = s3_validator.validate_connection()

    # Assert
    assert result is True
    assert error_message is None
    s3_validator.s3_connector.s3_client.list_buckets.assert_called_once()