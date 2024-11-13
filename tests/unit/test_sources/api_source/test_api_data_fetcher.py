import pytest
from unittest.mock import patch
from data_pipeline.source.api_source.data_fetcher import APIDataFetcher
from data_pipeline.source.api_source.models import APIResponse, APIConfig

@pytest.fixture
def fetcher():
    return APIDataFetcher()

def test_test_connection_success(fetcher):
    with patch('data_pipeline.source.api_source.validator.APIValidator.validate_url') as mock_validate_url:
        mock_validate_url.return_value = (True, None)
        with patch('data_pipeline.source.api_source.api_client.APIClient.fetch_data') as mock_fetch_data:
            mock_fetch_data.return_value = APIResponse(success=True, data={})
            response = fetcher.test_connection('https://example.com')
            assert response.success is True

def test_test_connection_failure(fetcher):
    with patch('data_pipeline.source.api_source.validator.APIValidator.validate_url') as mock_validate_url:
        mock_validate_url.return_value = (False, "Invalid URL")
        response = fetcher.test_connection('invalid_url')
        assert response.success is False
        assert response.error == "Invalid URL"

def test_fetch_data_success(fetcher):
    with patch('data_pipeline.source.api_source.validator.APIValidator.validate_url') as mock_validate_url:
        mock_validate_url.return_value = (True, None)
        with patch('data_pipeline.source.api_source.validator.APIValidator.validate_headers') as mock_validate_headers:
            mock_validate_headers.return_value = (True, None)
            with patch('data_pipeline.source.api_source.api_client.APIClient.fetch_data') as mock_fetch_data:
                mock_fetch_data.return_value = APIResponse(success=True, data={'key': 'value'})
                response = fetcher.fetch_data('https://example.com', headers={'Authorization': 'Bearer token'})
                assert response.success is True
                assert response.data == {'key': 'value'}

def test_fetch_data_url_failure(fetcher):
    with patch('data_pipeline.source.api_source.validator.APIValidator.validate_url') as mock_validate_url:
        mock_validate_url.return_value = (False, "Invalid URL")
        response = fetcher.fetch_data('invalid_url')
        assert response.success is False
        assert response.error == "Invalid URL"

def test_fetch_data_headers_failure(fetcher):
    with patch('data_pipeline.source.api_source.validator.APIValidator.validate_url') as mock_validate_url:
        mock_validate_url.return_value = (True, None)
        with patch('data_pipeline.source.api_source.validator.APIValidator.validate_headers') as mock_validate_headers:
            mock_validate_headers.return_value = (False, "Invalid headers")
            response = fetcher.fetch_data('https://example.com', headers={'invalid header': 'value'})
            assert response.success is False
            assert response.error == "Invalid headers"