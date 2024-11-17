import pytest
from backend.backend.data_pipeline.source.api.api_validator import APIValidator

@pytest.fixture
def validator():
    return APIValidator()

def test_validate_url_success(validator):
    is_valid, error = validator.validate_url("https://example.com/api")
    assert is_valid is True
    assert error is None

def test_validate_url_failure(validator):
    is_valid, error = validator.validate_url("invalid_url")
    assert is_valid is False
    assert error == "Invalid URL format: Missing scheme or network location"

def test_validate_headers_success(validator):
    headers = {
        "Authorization": "Bearer token",
        "Content-Type": "application/json"
    }
    is_valid, error = validator.validate_headers(headers)
    assert is_valid is True
    assert error is None

def test_validate_headers_failure(validator):
    headers = {
        "invalid header": "value"
    }
    is_valid, error = validator.validate_headers(headers)
    assert is_valid is False
    assert error == "Invalid header key format: invalid header"