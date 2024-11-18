import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
from backend.data_pipeline.source.cloud.s3_data_loader import S3DataLoader
from backend.data_pipeline.exceptions import CloudQueryError


@pytest.fixture
def s3_loader():
    connector_mock = MagicMock()
    return S3DataLoader(connector_mock)


@patch('backend.data_pipeline.source.cloud.s3_data_loader.pd.read_csv')
def test_load_data_csv_success(mock_read_csv, s3_loader):
    mock_read_csv.return_value = pd.DataFrame({'col1': [1, 2]})
    s3_loader.s3_connector.s3.Object().get.return_value = {'Body': MagicMock(read=MagicMock(return_value=b'data'))}

    df = s3_loader.load_data('mock_bucket', 'mock_key')
    assert not df.empty
    mock_read_csv.assert_called_once()


@patch('backend.data_pipeline.source.cloud.s3_data_loader.pd.read_parquet')
def test_load_data_parquet_success(mock_read_parquet, s3_loader):
    mock_read_parquet.return_value = pd.DataFrame({'col1': [1, 2]})
    s3_loader.s3_connector.s3.Object().get.return_value = {'Body': MagicMock(read=MagicMock(return_value=b'data'))}

    df = s3_loader.load_data('mock_bucket', 'mock_key', data_format='parquet')
    assert not df.empty
    mock_read_parquet.assert_called_once()


def test_load_data_failure(s3_loader):
    s3_loader.s3_connector.connect.side_effect = Exception("Loading error")
    with pytest.raises(CloudQueryError):
        s3_loader.load_data('mock_bucket', 'mock_key')
