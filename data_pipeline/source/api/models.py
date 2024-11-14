# api/models.py
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional, Dict, Union, List


@dataclass
class APIResponse:
    """
    Standardized response format for API requests.
    """
    success: bool
    data: Any
    timestamp: str = str(datetime.now())
    error: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert the response to a dictionary format."""
        return {
            "success": self.success,
            "data": self.data,
            "timestamp": self.timestamp,
            "error": self.error,
            "metadata": self.metadata
        }


@dataclass
class APIConfig:
    """
    Configuration parameters for API requests.
    """
    url: str
    headers: Optional[Dict] = None
    params: Optional[Dict] = None
    timeout: int = 30
    verify_ssl: bool = True
    max_retries: int = 3
    retry_delay: int = 1

    def __post_init__(self):
        """Validate and process the configuration after initialization."""
        # Ensure URL is properly formatted
        if not self.url.startswith(('http://', 'https://')):
            raise ValueError("URL must start with http:// or https://")

        # Initialize headers if None
        if self.headers is None:
            self.headers = {}

        # Merge with default headers, preserving any user-provided values
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        self.headers = {**default_headers, **self.headers}

        # Ensure timeout is positive
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

        # Ensure retry values are non-negative
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")


@dataclass
class DataFormat:
    """
    Specification for expected data format from the API.
    """
    type: str = 'json'
    schema: Optional[Dict] = None
    required_fields: Optional[List[str]] = None

    def validate_response(self, response_data: Any) -> tuple[bool, Optional[str]]:
        """
        Validate that the response data matches the expected format.
        Handles nested data structures under a 'data' key.
        """
        if not self.required_fields:
            return True, None

        try:
            # Handle nested data structure
            if isinstance(response_data, dict) and 'data' in response_data:
                data_to_validate = response_data['data']
            else:
                data_to_validate = response_data

            # Validate list of items
            if isinstance(data_to_validate, list):
                all_missing_fields = set()
                for item in data_to_validate:
                    if isinstance(item, dict):
                        missing_fields = {
                            field for field in self.required_fields
                            if field not in item
                        }
                        all_missing_fields.update(missing_fields)
                if all_missing_fields:
                    return False, f"Missing required fields: {sorted(list(all_missing_fields))}"

            # Validate single item
            elif isinstance(data_to_validate, dict):
                missing_fields = [
                    field for field in self.required_fields
                    if field not in data_to_validate
                ]
                if missing_fields:
                    return False, f"Missing required fields: {missing_fields}"
            else:
                return False, "Data must be a dictionary or list of dictionaries"

            return True, None

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    def transform_data(self, data: Any) -> Any:
        """
        Transform the response data into the expected format.
        """
        # Add data transformation logic here if needed
        return data

