# api_fetcher.py
import requests
from typing import Dict, Any, Optional, Generator
import logging
import json
from .api_config import Config

logger = logging.getLogger(__name__)


class APIFetcher:
    """Handles API data fetching and pagination."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize APIFetcher with configuration."""
        self.config = config
        self.session = requests.Session()
        self.setup_session()

    def setup_session(self):
        """Configure request session with authentication and headers."""
        if 'credentials' in self.config:
            decrypted_creds = Config.decrypt_credentials(self.config['credentials'])
            if 'token' in decrypted_creds:
                self.session.headers['Authorization'] = f"Bearer {decrypted_creds['token']}"
            elif 'username' in decrypted_creds:
                self.session.auth = (decrypted_creds['username'], decrypted_creds['password'])

        if 'headers' in self.config:
            self.session.headers.update(self.config['headers'])

    def fetch_data(self, endpoint: str, method: str = 'GET', params: Optional[Dict] = None) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            response = self.session.request(
                method=method,
                url=endpoint,
                params=params,
                timeout=Config.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return {
                'data': response.json(),
                'status_code': response.status_code,
                'headers': dict(response.headers)
            }
        except Exception as e:
            logger.error(f"API fetch error: {str(e)}")
            raise

    def paginated_fetch(self, endpoint: str, page_param: str = 'page') -> Generator[Dict[str, Any], None, None]:
        """Handle paginated API responses."""
        page = 1
        while True:
            result = self.fetch_data(endpoint, params={page_param: page})
            yield result['data']

            if not self._has_more_pages(result):
                break
            page += 1

    def _has_more_pages(self, result: Dict[str, Any]) -> bool:
        """Check if more pages are available based on response."""
        if 'next_page' in result.get('data', {}):
            return bool(result['data']['next_page'])
        return len(result.get('data', [])) >= Config.BATCH_SIZE