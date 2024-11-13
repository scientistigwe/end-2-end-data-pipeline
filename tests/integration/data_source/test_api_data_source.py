import pytest
import requests_mock
from datetime import datetime
from typing import Optional, Dict, Any
from data_pipeline.source.api_source.models import APIResponse, APIConfig, DataFormat
from data_pipeline.source.api_source.api_client import APIClient


def test_end_to_end():
    """Test the end-to-end API data fetching flow."""
    # Mock API response with correct data structure
    sample_response = {
        "data": [
            {
                "id": 1,
                "name": "Sample Item",
                "value": 100
            }
        ]
    }

    url = "https://api.example.com/data"
    headers = {"Authorization": "Bearer token"}
    params = {"limit": 10}

    # Create configuration objects
    data_format = DataFormat(
        type="json",
        required_fields=["id", "name", "value"],
        schema=None  # Optional schema validation
    )

    config = APIConfig(
        url=url,
        headers=headers,
        params=params,
        timeout=30,
        verify_ssl=True,
        max_retries=3,
        retry_delay=1
    )

    # Use requests_mock as a context manager
    with requests_mock.Mocker() as m:
        # Register the mock response
        m.get(
            url,
            json=sample_response,
            status_code=200,
            headers={'Content-Type': 'application/json'}
        )

        # Initialize client and make request
        api_client = APIClient()
        response = api_client.fetch_data(config=config, data_format=data_format)

        # Debug information if the request fails
        if not response.success:
            print(f"Response error: {response.error}")
            print(f"Response data: {response.data}")

        # Assertions
        assert response.success is True, f"Request failed with error: {response.error}"
        assert isinstance(response.data, dict), "Response data should be a dict"
        assert "data" in response.data, "Response should contain 'data' key"
        assert isinstance(response.data["data"], list), "Data should be a list"

        # Validate required fields for each item in the data array
        for item in response.data["data"]:
            print(f"Validating item: {item}")  # Debug print
            for field in data_format.required_fields:
                assert field in item, f"Required field '{field}' missing from {item}"


def test_failed_request():
    """Test handling of failed requests."""
    url = "https://api.example.com/data"
    headers = {"Authorization": "Bearer token"}
    params = {"limit": 10}

    config = APIConfig(
        url=url,
        headers=headers,
        params=params,
        timeout=30,
        verify_ssl=True,
        max_retries=1,
        retry_delay=0
    )

    with requests_mock.Mocker() as m:
        # Mock a failed response
        m.get(
            url,
            status_code=500,
            text="Internal Server Error"
        )

        api_client = APIClient()
        response = api_client.fetch_data(config=config)

        assert response.success is False
        assert response.data is None
        assert "Failed after" in str(response.error)


def test_invalid_json():
    """Test handling of invalid JSON responses."""
    url = "https://api.example.com/data"
    headers = {"Authorization": "Bearer token"}
    params = {"limit": 10}

    config = APIConfig(
        url=url,
        headers=headers,
        params=params,
        timeout=30,
        verify_ssl=True,
        max_retries=1,
        retry_delay=0
    )

    data_format = DataFormat(
        type="json",
        required_fields=["id", "name", "value"]
    )

    with requests_mock.Mocker() as m:
        # Mock an invalid response structure
        m.get(
            url,
            json={"data": [{"id": 1}]},  # Missing required fields
            headers={'Content-Type': 'application/json'}
        )

        api_client = APIClient()
        response = api_client.fetch_data(config=config, data_format=data_format)

        assert response.success is False
        assert "Missing required fields" in str(response.error)


def test_validation_with_missing_fields():
    """Test validation with missing required fields."""
    data_format = DataFormat(
        type="json",
        required_fields=["id", "name", "value"]
    )

    # Test data with missing fields
    test_data = {"id": 1}  # Missing 'name' and 'value'

    is_valid, error = data_format.validate_response(test_data)
    assert not is_valid
    assert "Missing required fields" in error
    assert "name" in error
    assert "value" in error