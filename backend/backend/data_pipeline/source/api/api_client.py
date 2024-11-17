# api/api_client.py
import requests
from typing import Optional
import logging
import time
from backend.backend.data_pipeline.source.api.api_models import APIConfig, APIResponse, DataFormat


class APIClient:
    """
    Client for fetching data from REST APIs.

    This client focuses on reliable data retrieval with features like:
    - Automatic retries for failed requests
    - Response validation
    - Detailed error reporting
    - Response format validation

    Attributes:
        logger: Logger instance for tracking operations
        session: Requests session for connection pooling
    """

    def __init__(self):
        """Initialize the API client with logging and session setup."""
        self.logger = logging.getLogger(__name__)
        self.session = requests.Session()

    def fetch_data(
            self,
            config: APIConfig,
            data_format: Optional[DataFormat] = None
    ) -> APIResponse:
        """
        Fetch data from the specified API endpoint.

        Args:
            config: APIConfig instance with request configuration
            data_format: Optional DataFormat instance for response validation

        Returns:
            APIResponse containing the fetched data or error information
        """
        attempt = 0
        last_error = None

        while attempt < config.max_retries + 1:
            try:
                self.logger.info(f"Fetching data from {config.url} (attempt {attempt + 1})")

                response = self.session.get(
                    url=config.url,
                    headers=config.headers,
                    params=config.params,
                    timeout=config.timeout,
                    verify=config.verify_ssl
                )
                response.raise_for_status()

                # Try to parse as JSON
                try:
                    data = response.json()
                except ValueError:
                    # If not JSON, return raw text
                    data = response.text

                # Validate response format if specified
                if data_format:
                    is_valid, error = data_format.validate_response(data)
                    if not is_valid:
                        return APIResponse(
                            success=False,
                            data=None,
                            error=f"Response format validation failed: {error}"
                        )
                    data = data_format.transform_data(data)

                return APIResponse(
                    success=True,
                    data=data,
                    metadata={
                        'status_code': response.status_code,
                        'content_type': response.headers.get('content-type'),
                        'response_time': response.elapsed.total_seconds(),
                        'url': config.url,
                        'attempt': attempt + 1
                    }
                )

            except requests.exceptions.RequestException as e:
                last_error = str(e)
                self.logger.error(f"Request failed (attempt {attempt + 1}): {last_error}")

                if attempt < config.max_retries:
                    time.sleep(config.retry_delay)
                    attempt += 1
                    continue
                break

            except Exception as e:
                self.logger.error(f"Unexpected error: {str(e)}")
                return APIResponse(
                    success=False,
                    data=None,
                    error=f"Unexpected error: {str(e)}"
                )

        return APIResponse(
            success=False,
            data=None,
            error=f"Failed after {attempt + 1} attempts. Last error: {last_error}"
        )
