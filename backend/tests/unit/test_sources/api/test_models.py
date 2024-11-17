from backend.backend.data_pipeline.source.api.api_models import APIResponse, APIConfig, DataFormat


def test_api_response():
    response = APIResponse(
        success=True,
        data={"key": "value"},
        metadata={"status_code": 200}
    )
    assert response.success is True
    assert response.data == {"key": "value"}
    assert response.metadata == {"status_code": 200}

    response_dict = response.to_dict()
    assert response_dict == {
        "success": True,
        "data": {"key": "value"},
        "timestamp": response.timestamp,
        "error": None,
        "metadata": {"status_code": 200}
    }


def test_api_config():
    config = APIConfig(
        url="https://example.com/api",
        headers={"Authorization": "Bearer token"},
        params={"limit": 10},
        timeout=30,
        verify_ssl=True,
        max_retries=3,
        retry_delay=1
    )

    expected_headers = {
        "Authorization": "Bearer token",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    assert config.url == "https://example.com/api"
    assert config.headers == expected_headers
    assert config.params == {"limit": 10}
    assert config.timeout == 30
    assert config.verify_ssl is True
    assert config.max_retries == 3
    assert config.retry_delay == 1


def test_data_format():
    format_spec = DataFormat(
        type="json",
        required_fields=["id", "name", "value"]
    )
    assert format_spec.type == "json"
    assert format_spec.required_fields == ["id", "name", "value"]

    # Test valid single object
    is_valid, error = format_spec.validate_response({"id": 1, "name": "John", "value": 10})
    assert is_valid is True
    assert error is None

    # Test invalid single object
    is_valid, error = format_spec.validate_response({"id": 1, "name": "John"})
    assert is_valid is False
    assert error == "Missing required fields: ['value']"

    # Test valid list of objects
    is_valid, error = format_spec.validate_response([
        {"id": 1, "name": "John", "value": 10},
        {"id": 2, "name": "Jane", "value": 20}
    ])
    assert is_valid is True
    assert error is None

    # Test invalid list of objects
    is_valid, error = format_spec.validate_response([
        {"id": 1, "name": "John"},
        {"id": 2, "value": 20}
    ])
    assert is_valid is False
    assert error == "Missing required fields: ['name', 'value']"  # Changed this line


def test_data_format_nested_structure():
    """Test validation of nested data structures."""
    format_spec = DataFormat(
        type="json",
        required_fields=["id", "name", "value"]
    )

    # Test valid nested object
    nested_data = {
        "data": [
            {"id": 1, "name": "John", "value": 10},
            {"id": 2, "name": "Jane", "value": 20}
        ]
    }
    is_valid, error = format_spec.validate_response(nested_data)
    assert is_valid is True
    assert error is None

    # Test invalid nested object
    invalid_nested_data = {
        "data": [
            {"id": 1, "name": "John"},
            {"id": 2, "value": 20}
        ]
    }
    is_valid, error = format_spec.validate_response(invalid_nested_data)
    assert is_valid is False
    assert error == "Missing required fields: ['name', 'value']"  # Match the actual error format

    # Test nested single object
    single_nested_data = {
        "data": {"id": 1, "name": "John", "value": 10}
    }
    is_valid, error = format_spec.validate_response(single_nested_data)
    assert is_valid is True
    assert error is None


def test_data_format_edge_cases():
    """Test validation of edge cases and invalid inputs."""
    format_spec = DataFormat(
        type="json",
        required_fields=["id", "name", "value"]
    )

    # Test empty data
    is_valid, error = format_spec.validate_response({})
    assert is_valid is False
    assert error == "Missing required fields: ['id', 'name', 'value']"

    # Test None input
    is_valid, error = format_spec.validate_response(None)
    assert is_valid is False
    assert error == "Data must be a dictionary or list of dictionaries"

    # Test invalid data type
    is_valid, error = format_spec.validate_response("invalid")
    assert is_valid is False
    assert error == "Data must be a dictionary or list of dictionaries"

    # Test empty list
    is_valid, error = format_spec.validate_response([])
    assert is_valid is True  # Empty list is valid as there's nothing to validate
    assert error is None


def test_data_format_without_required_fields():
    """Test validation when no required fields are specified."""
    format_spec = DataFormat(type="json")  # No required_fields specified

    # All these should pass validation
    test_cases = [
        {"any": "data"},
        ["list", "of", "items"],
        {"nested": {"data": "structure"}},
        None,
        [],
        {}
    ]

    for test_case in test_cases:
        is_valid, error = format_spec.validate_response(test_case)
        assert is_valid is True
        assert error is None


def test_data_format_transform():
    """Test the transform_data method."""
    format_spec = DataFormat(
        type="json",
        required_fields=["id", "name", "value"]
    )

    # Test that transform returns data unchanged by default
    test_data = {"id": 1, "name": "John", "value": 10}
    transformed = format_spec.transform_data(test_data)
    assert transformed == test_data