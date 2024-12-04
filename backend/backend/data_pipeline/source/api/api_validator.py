# api_validator.py
import requests
import json
from typing import Tuple, Dict, Any
import logging
from .api_config import Config

logger = logging.getLogger(__name__)


class APIValidator:
    """Comprehensive API validation utilities."""

    @staticmethod
    def validate_endpoint(url: str) -> Tuple[bool, str]:
        """Validate API endpoint URL format."""
        try:
            response = requests.head(url, timeout=Config.REQUEST_TIMEOUT)
            return True, f"Endpoint is accessible: {response.status_code}"
        except requests.exceptions.RequestException as e:
            return False, f"Endpoint validation failed: {str(e)}"

    @staticmethod
    def validate_credentials(credentials: Dict[str, Any], url: str) -> Tuple[bool, str]:
        """Validate API credentials."""
        try:
            response = requests.get(
                url,
                headers=credentials.get('headers', {}),
                auth=(
                    credentials.get('username'),
                    credentials.get('password')
                ) if 'username' in credentials else None,
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return True, "Credentials validated successfully"
        except requests.exceptions.RequestException as e:
            return False, f"Credential validation failed: {str(e)}"

    @staticmethod
    def validate_response_format(response: requests.Response) -> Tuple[bool, str]:
        """Validate API response format."""
        try:
            if response.headers.get('content-type', '').startswith('application/json'):
                json.loads(response.text)
                return True, "Response format is valid JSON"
            return False, "Response is not in JSON format"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON response: {str(e)}"

    @staticmethod
    def validate_rate_limits(response: requests.Response) -> Dict[str, Any]:
        """Check and validate API rate limits from response headers."""
        rate_limit_info = {
            'limit': response.headers.get('X-RateLimit-Limit'),
            'remaining': response.headers.get('X-RateLimit-Remaining'),
            'reset': response.headers.get('X-RateLimit-Reset')
        }
        return rate_limit_info

