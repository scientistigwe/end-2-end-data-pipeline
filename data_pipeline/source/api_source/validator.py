# api/validator.py
from urllib.parse import urlparse
from typing import Dict, Optional, Tuple
import re
import logging


class APIValidator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def validate_url(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate if the provided URL is properly formatted
        """
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False, "Invalid URL format: Missing scheme or network location"
            if result.scheme not in ['http', 'https']:
                return False, "Invalid URL format: Scheme must be http or https"
            return True, None
        except Exception as e:
            return False, f"Invalid URL format: {str(e)}"

    def validate_headers(self, headers: Dict) -> Tuple[bool, Optional[str]]:
        """Validate request headers format"""
        if not isinstance(headers, dict):
            return False, "Headers must be a dictionary"

        # Basic header key format validation
        header_pattern = re.compile(r'^[A-Za-z0-9-]+$')
        for key in headers:
            if not header_pattern.match(key):
                return False, f"Invalid header key format: {key}"

        return True, None