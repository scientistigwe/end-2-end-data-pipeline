import pytest
import pandas as pd
from unittest.mock import patch, MagicMock, call
from datetime import datetime
from io import BytesIO
from botocore.config import Config
from backend.backend.data_pipeline.source.cloud.s3_data_manager import S3DataManager, TimeSync
from backend.backend.data_pipeline.exceptions import CloudConnectionError, CloudQueryError, \
    DataValidationError


@pytest.fixture
def mock_ntp():
    with patch('ntplib.NTPClient') as mock:
        client = MagicMock()
        response = MagicMock()
        response.tx_time = datetime.utcnow().timestamp()
        client.request.return_value = response
        mock.return_value = client
        yield client


@pytest.fixture
def mock_s3_connector():
    with patch('backend.backend.data_pipeline.source.cloud.s3_data_manager.S3Connector') as mock:
        connector = MagicMock()
        mock.return_value = connector
        yield connector


@pytest.fixture
def s3_data_manager(mock_s3_connector, mock_ntp):
    return S3DataManager(
        aws_access_key='test_key',
        aws_secret_key='test_secret',
        region_name='us-east-1'
    )


def test_validate_and_load_success(s3_data_manager):
    """Test successful data validation and loading."""
    # Create test DataFrame and convert to CSV bytes
    test_df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
    csv_buffer = BytesIO()
    test_df.to_csv(csv_buffer, index=False)
    test_bytes = csv_buffer.getvalue()

    # Configure mock to return our test bytes
    s3_data_manager.s3_connector.download_file.return_value = test_bytes

    # Execute test
    result = s3_data_manager.validate_and_load('test-bucket', 'test-key.csv')

    # Verify the result matches our test DataFrame
    pd.testing.assert_frame_equal(result, test_df)
    s3_data_manager.s3_connector.download_file.assert_called_once_with(
        'test-bucket', 'test-key.csv'
    )


def test_validate_and_load_connection_failure(s3_data_manager):
    """Test handling of connection failure during load."""
    # Configure mock to raise CloudConnectionError
    s3_data_manager.s3_connector.download_file.side_effect = CloudConnectionError("Connection failed")

    # Verify that CloudQueryError is raised
    with pytest.raises(CloudQueryError) as exc_info:
        s3_data_manager.validate_and_load('test-bucket', 'test-key.csv')

    assert "Connection failed" in str(exc_info.value)


def test_upload_dataframe_success(s3_data_manager):
    """Test successful DataFrame upload."""
    # Create test DataFrame
    test_df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})

    # Upload DataFrame
    s3_data_manager.upload_dataframe('test-bucket', 'test-key.csv', test_df)

    # Verify upload_file was called with correct arguments
    s3_data_manager.s3_connector.upload_file.assert_called_once()

    # Get the arguments passed to upload_file
    call_args = s3_data_manager.s3_connector.upload_file.call_args[0]
    bucket_name, key, data = call_args

    # Verify the arguments
    assert bucket_name == 'test-bucket'
    assert key == 'test-key.csv'
    assert isinstance(data, bytes)

    # Verify the uploaded data can be converted back to a DataFrame
    uploaded_df = pd.read_csv(BytesIO(data))
    pd.testing.assert_frame_equal(uploaded_df, test_df)


def test_validate_and_load_empty_data(s3_data_manager):
    """Test validation of empty DataFrame."""
    # Create empty DataFrame bytes
    empty_df = pd.DataFrame()
    csv_buffer = BytesIO()
    empty_df.to_csv(csv_buffer, index=False)
    test_bytes = csv_buffer.getvalue()

    s3_data_manager.s3_connector.download_file.return_value = test_bytes

    with pytest.raises(DataValidationError) as exc_info:
        s3_data_manager.validate_and_load('test-bucket', 'test-key.csv')

    assert "Empty DataFrame received" in str(exc_info.value)


def test_upload_dataframe_invalid_format(s3_data_manager):
    """Test upload with invalid format."""
    test_df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})

    with pytest.raises(ValueError) as exc_info:
        s3_data_manager.upload_dataframe('test-bucket', 'test-key', test_df, data_format='invalid')

    assert "Unsupported format: invalid" in str(exc_info.value)


def test_validate_and_load_json_format(s3_data_manager):
    """Test loading JSON format data."""
    test_df = pd.DataFrame({'col1': [1, 2], 'col2': ['a', 'b']})
    json_buffer = BytesIO()
    test_df.to_json(json_buffer)
    test_bytes = json_buffer.getvalue()

    s3_data_manager.s3_connector.download_file.return_value = test_bytes

    result = s3_data_manager.validate_and_load('test-bucket', 'test-key.json', data_format='json')

    pd.testing.assert_frame_equal(result, test_df)