import pytest
import requests_mock
import requests
from backend.data_pipeline.source.api.api_models import APIConfig, DataFormat
from backend.data_pipeline.source.api.api_client import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.parametrize("use_adapter", [True])
def test_fetch_data_success(client, use_adapter):
    with requests_mock.Mocker() as m:
        config = APIConfig(
            url="https://example.com/api",
            headers={"Authorization": "Bearer token"},
            params={"limit": 10},
            max_retries=3,
            retry_delay=1,
            timeout=30,
            verify_ssl=True
        )

        expected_response = {"data": [{"id": 1}, {"id": 2}]}
        m.get(
            "https://example.com/api",
            json=expected_response,
            headers={"Content-Type": "application/json"},
            status_code=200
        )

        response = client.fetch_data(config)

        assert response.success is True
        assert response.data == expected_response
        assert response.metadata["status_code"] == 200
        assert response.metadata["content_type"] == "application/json"
        assert isinstance(response.metadata["response_time"], float)
        assert response.metadata["url"] == "https://example.com/api"
        assert response.metadata["attempt"] == 1


@pytest.mark.parametrize("use_adapter", [True])
def test_fetch_data_format_validation_failure(client, use_adapter):
    with requests_mock.Mocker() as m:
        config = APIConfig(
            url="https://example.com/api",
            headers={"Authorization": "Bearer token"},
            params={"limit": 10},
            max_retries=3,
            retry_delay=1,
            timeout=30,
            verify_ssl=True
        )

        m.get(
            "https://example.com/api",
            json={"invalid": "data"},
            status_code=200
        )

        data_format = DataFormat(
            type="json",
            required_fields=["id", "name"]
        )

        response = client.fetch_data(config, data_format)
        assert response.success is False
        assert "Response format validation failed" in response.error
        assert "Missing required fields" in response.error


@pytest.mark.parametrize("use_adapter", [True])
def test_fetch_data_request_exception(client, use_adapter):
    with requests_mock.Mocker() as m:
        config = APIConfig(
            url="https://example.com/api",
            headers={"Authorization": "Bearer token"},
            params={"limit": 10},
            max_retries=2,
            retry_delay=0,  # Set to 0 for faster tests
            timeout=30,
            verify_ssl=True
        )

        m.get(
            "https://example.com/api",
            exc=requests.exceptions.Timeout
        )

        response = client.fetch_data(config)
        assert response.success is False
        assert "Failed after 3 attempts" in response.error
        assert "Last error: " in response.error


@pytest.mark.parametrize("use_adapter", [True])
def test_fetch_data_unexpected_exception(client, use_adapter):
    with requests_mock.Mocker() as m:
        config = APIConfig(
            url="https://example.com/api",
            headers={"Authorization": "Bearer token"},
            params={"limit": 10},
            max_retries=3,
            retry_delay=1,
            timeout=30,
            verify_ssl=True
        )

        m.get(
            "https://example.com/api",
            exc=ValueError("Unexpected error")
        )

        response = client.fetch_data(config)
        assert response.success is False
        assert "Unexpected error: Unexpected error" in response.error