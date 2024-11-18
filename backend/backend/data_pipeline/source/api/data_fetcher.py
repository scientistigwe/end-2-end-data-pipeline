# api/data_fetcher.py
from typing import Optional, Dict
from backend.data_pipeline.source.api.api_validator import APIValidator
from backend.data_pipeline.source.api.api_client import APIClient
from backend.data_pipeline.source.api.api_models import APIResponse, APIConfig


class APIDataFetcher:
    def __init__(self):
        """
        Initialize the API fetcher with base URL and optional API key
        """
        self.validator = APIValidator()
        self.client = APIClient()
        self.logger = logging.getLogger(__name__)

    def test_connection(self, url: str) -> APIResponse:
        """Test connection to the API endpoint"""
        is_valid, error = self.validator.validate_url(url)
        if not is_valid:
            return APIResponse(success=False, data=None, error=error)

        config = APIConfig(
            url=url,
            timeout=10
        )
        return self.client.fetch_data(config)

    def fetch_data(
            self,
            url: str,
            headers: Optional[Dict] = None,
            params: Optional[Dict] = None
    ) -> APIResponse:
        """Fetch data from the API endpoint"""
        # Validate URL
        is_valid, error = self.validator.validate_url(url)
        if not is_valid:
            return APIResponse(success=False, data=None, error=error)

        # Validate headers if provided
        if headers:
            is_valid, error = self.validator.validate_headers(headers)
            if not is_valid:
                return APIResponse(success=False, data=None, error=error)

        # Create configuration
        config = APIConfig(
            url=url,
            headers=headers,
            params=params
        )

        # Make request
        return self.client.fetch_data(config)

# api/utils.py
import logging
from typing import Dict, Any
import json


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging for the API module"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def format_response(response: Dict[str, Any]) -> str:
    """Format API response for display"""
    return json.dumps(response, indent=2)


