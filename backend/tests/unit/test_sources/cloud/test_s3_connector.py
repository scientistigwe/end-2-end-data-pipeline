import pytest
from unittest.mock import patch, MagicMock, call
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config
from backend.backend.data_pipeline.exceptions import CloudConnectionError
from backend.backend.data_pipeline.source.cloud.s3_connector import S3Connector


@pytest.fixture
def mock_boto3_session():
    with patch('boto3.Session') as mock_session:
        # Create mock client and resource
        mock_client = MagicMock()
        mock_resource = MagicMock()

        # Configure list_buckets for successful initialization
        mock_client.list_buckets.return_value = {'Buckets': []}

        # Set up the session to return our mock client and resource
        mock_session.return_value.client.return_value = mock_client
        mock_session.return_value.resource.return_value = mock_resource

        yield mock_session, mock_client, mock_resource


@pytest.fixture
def mock_existing_session():
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_resource = MagicMock()

    # Configure list_buckets for successful initialization
    mock_client.list_buckets.return_value = {'Buckets': []}

    mock_session.client.return_value = mock_client
    mock_session.resource.return_value = mock_resource

    return mock_session, mock_client, mock_resource


@pytest.fixture
def s3_connector(mock_boto3_session):
    _, mock_client, _ = mock_boto3_session
    return S3Connector(
        aws_access_key='test_key',
        aws_secret_key='test_secret',
        region_name='us-east-1'
    )


def test_init_with_missing_credentials():
    """Test initialization with missing credentials."""
    with pytest.raises(CloudConnectionError) as exc_info:
        S3Connector(
            aws_access_key='',
            aws_secret_key='test_secret',
            region_name='us-east-1'
        )
    assert "Failed to establish S3 connection" in str(exc_info.value)


def test_connect_success(mock_boto3_session):
    """Test successful connection initialization."""
    mock_session, mock_client, mock_resource = mock_boto3_session

    connector = S3Connector(
        aws_access_key='test_key',
        aws_secret_key='test_secret',
        region_name='us-east-1'
    )

    assert connector.s3_client is not None
    assert connector.s3_resource is not None
    mock_client.list_buckets.assert_called_once()

    # Verify session creation with correct credentials
    mock_session.assert_called_once_with(
        aws_access_key_id='test_key',
        aws_secret_access_key='test_secret',
        region_name='us-east-1'
    )


def test_connect_with_existing_session(mock_existing_session):
    """Test connection with provided session."""
    mock_session, mock_client, mock_resource = mock_existing_session

    connector = S3Connector(
        aws_access_key='test_key',
        aws_secret_key='test_secret',
        region_name='us-east-1',
        session=mock_session
    )

    assert connector.session == mock_session
    assert connector.s3_client is not None
    assert connector.s3_resource is not None
    mock_client.list_buckets.assert_called_once()


def test_connect_with_config(mock_boto3_session):
    """Test connection with custom configuration."""
    mock_session, mock_client, mock_resource = mock_boto3_session

    test_config = Config(
        retries=dict(max_attempts=3),
        connect_timeout=5
    )

    connector = S3Connector(
        aws_access_key='test_key',
        aws_secret_key='test_secret',
        region_name='us-east-1',
        config=test_config
    )

    assert connector.config == test_config
    mock_session.return_value.client.assert_called_with('s3', config=test_config)


def test_connect_failure_client_error(mock_boto3_session):
    """Test connection failure due to ClientError."""
    mock_session, mock_client, mock_resource = mock_boto3_session
    mock_client.list_buckets.side_effect = ClientError(
        {'Error': {'Code': 'InvalidAccessKeyId', 'Message': 'Invalid access key'}},
        'ListBuckets'
    )

    with pytest.raises(CloudConnectionError) as exc_info:
        S3Connector(
            aws_access_key='test_key',
            aws_secret_key='test_secret',
            region_name='us-east-1'
        )
    assert "Invalid access key" in str(exc_info.value)


def test_connect_failure_boto_error(mock_boto3_session):
    """Test connection failure due to BotoCoreError."""
    mock_session, mock_client, mock_resource = mock_boto3_session
    mock_client.list_buckets.side_effect = BotoCoreError()

    with pytest.raises(CloudConnectionError):
        S3Connector(
            aws_access_key='test_key',
            aws_secret_key='test_secret',
            region_name='us-east-1'
        )


def test_close(s3_connector):
    """Test closing connections."""
    s3_connector.close()
    assert s3_connector.s3_client is None
    assert s3_connector.s3_resource is None


def test_close_with_resource(mock_boto3_session):
    """Test closing connections with resource cleanup."""
    mock_session, mock_client, mock_resource = mock_boto3_session

    connector = S3Connector(
        aws_access_key='test_key',
        aws_secret_key='test_secret',
        region_name='us-east-1'
    )

    connector.close()
    assert connector.s3_client is None
    assert connector.s3_resource is None
    mock_client.close.assert_called_once()
    mock_resource.meta.client.close.assert_called_once()


def test_upload_file_success(s3_connector, mock_boto3_session):
    """Test successful file upload."""
    _, mock_client, _ = mock_boto3_session
    test_data = b"test data"

    s3_connector.upload_file("test-bucket", "test-key", test_data)

    mock_client.put_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="test-key",
        Body=test_data
    )


def test_upload_file_failure(s3_connector, mock_boto3_session):
    """Test file upload failure."""
    _, mock_client, _ = mock_boto3_session
    mock_client.put_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchBucket', 'Message': 'The bucket does not exist'}},
        'PutObject'
    )

    with pytest.raises(CloudConnectionError) as exc_info:
        s3_connector.upload_file("test-bucket", "test-key", b"test data")
    assert "Failed to upload to S3" in str(exc_info.value)


def test_download_file_success(s3_connector, mock_boto3_session):
    """Test successful file download."""
    _, mock_client, _ = mock_boto3_session
    test_data = b"test data"
    mock_body = MagicMock()
    mock_body.read.return_value = test_data
    mock_client.get_object.return_value = {'Body': mock_body}

    result = s3_connector.download_file("test-bucket", "test-key")

    assert result == test_data
    mock_client.get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="test-key"
    )


def test_download_file_failure(s3_connector, mock_boto3_session):
    """Test file download failure."""
    _, mock_client, _ = mock_boto3_session
    mock_client.get_object.side_effect = ClientError(
        {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist'}},
        'GetObject'
    )

    with pytest.raises(CloudConnectionError) as exc_info:
        s3_connector.download_file("test-bucket", "test-key")
    assert "Failed to download from S3" in str(exc_info.value)


def test_upload_file_invalid_data(s3_connector):
    """Test upload with invalid data type."""
    with pytest.raises(AttributeError):
        s3_connector.upload_file("test-bucket", "test-key", "not bytes")