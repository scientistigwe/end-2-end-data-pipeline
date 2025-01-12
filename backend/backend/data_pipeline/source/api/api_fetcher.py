from __future__ import annotations

import logging
import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
import json
from dataclasses import dataclass, field

from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from backend.core.utils.rate_limiter import AsyncRateLimiter
from .api_config import Config

logger = logging.getLogger(__name__)


@dataclass
class APIResponse:
    """Structured API response"""
    status_code: int
    data: Any
    headers: Dict[str, str]
    duration: float
    timestamp: datetime = field(default_factory=datetime.now)
    rate_limits: Dict[str, Any] = field(default_factory=dict)


class APIFetcher:
    """Enhanced API data fetcher with comprehensive capabilities"""

    def __init__(
            self,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize fetcher with configuration"""
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Initialize monitoring
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="api_fetcher",
            source_id="fetcher"
        )

        # Initialize rate limiter
        self.rate_limiter = AsyncRateLimiter(
            max_calls=self.config.RATE_LIMIT_MAX_CALLS,
            period=self.config.RATE_LIMIT_PERIOD
        )

        # Session management
        self.session: Optional[aiohttp.ClientSession] = None
        self._session_lock = asyncio.Lock()

        # Response caching
        self.response_cache = {}

        # Retry configuration
        self.retry_config = {
            'max_retries': self.config.MAX_RETRIES,
            'retry_delay': 1,  # Initial delay in seconds
            'max_delay': 30,  # Maximum delay in seconds
            'retry_codes': {408, 429, 500, 502, 503, 504}
        }

    async def __aenter__(self):
        """Async context manager entry"""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._cleanup_session()

    async def _ensure_session(self):
        """Ensure HTTP session exists"""
        async with self._session_lock:
            if not self.session:
                self.session = aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(
                        total=self.config.REQUEST_TIMEOUT
                    )
                )

    async def _cleanup_session(self):
        """Clean up HTTP session"""
        async with self._session_lock:
            if self.session:
                await self.session.close()
                self.session = None

    async def fetch_data(
            self,
            endpoint: str,
            method: str = 'GET',
            params: Optional[Dict] = None,
            data: Optional[Dict] = None,
            headers: Optional[Dict] = None,
            auth: Optional[Dict] = None,
            cache: bool = True
    ) -> APIResponse:
        """
        Fetch data from API endpoint with comprehensive handling

        Args:
            endpoint: API endpoint URL
            method: HTTP method
            params: Query parameters
            data: Request body data
            headers: Request headers
            auth: Authentication configuration
            cache: Whether to use response caching

        Returns:
            APIResponse containing response data and metadata
        """
        try:
            start_time = datetime.now()

            # Check cache
            cache_key = self._get_cache_key(endpoint, method, params, data)
            if cache and cache_key in self.response_cache:
                await self._record_cache_hit(cache_key)
                return self.response_cache[cache_key]

            # Rate limiting
            async with self.rate_limiter:
                # Ensure session
                await self._ensure_session()

                # Prepare request
                request_args = await self._prepare_request(
                    endpoint, method, params, data, headers, auth
                )

                # Execute request with retries
                response = await self._execute_with_retry(request_args)

                # Process response
                api_response = await self._process_response(
                    response,
                    start_time
                )

                # Cache response if needed
                if cache:
                    self.response_cache[cache_key] = api_response

                return api_response

        except Exception as e:
            logger.error(f"API fetch error: {str(e)}", exc_info=True)
            await self._record_error("fetch_error", str(e))
            raise

    async def fetch_paginated(
            self,
            endpoint: str,
            params: Optional[Dict] = None,
            **kwargs
    ) -> AsyncGenerator[APIResponse, None]:
        """
        Handle paginated API responses

        Args:
            endpoint: Base endpoint URL
            params: Initial query parameters
            **kwargs: Additional fetch arguments

        Yields:
            APIResponse for each page
        """
        params = params or {}
        page = 1

        while True:
            params['page'] = page
            response = await self.fetch_data(endpoint, params=params, **kwargs)

            yield response

            if not await self._has_next_page(response):
                break

            page += 1

    async def check_connection(
            self,
            timeout: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Check API connection and diagnostics

        Args:
            timeout: Optional timeout override

        Returns:
            Dictionary containing connection status and diagnostics
        """
        try:
            start_time = datetime.now()

            # Ensure session
            await self._ensure_session()

            # Basic connectivity check
            async with self.session.get(
                    self.config.HEALTH_CHECK_ENDPOINT,
                    timeout=timeout or self.config.REQUEST_TIMEOUT
            ) as response:
                duration = (datetime.now() - start_time).total_seconds()

                return {
                    'status': 'connected' if response.status == 200 else 'error',
                    'diagnostics': {
                        'status_code': response.status,
                        'latency': duration,
                        'ssl_verified': response.url.scheme == 'https',
                        'headers': dict(response.headers)
                    },
                    'rate_limits': self._extract_rate_limits(response)
                }

        except Exception as e:
            logger.error(f"Connection check error: {str(e)}", exc_info=True)
            return {
                'status': 'error',
                'diagnostics': {
                    'error': str(e),
                    'type': type(e).__name__
                }
            }

    async def _prepare_request(
            self,
            endpoint: str,
            method: str,
            params: Optional[Dict],
            data: Optional[Dict],
            headers: Optional[Dict],
            auth: Optional[Dict]
    ) -> Dict[str, Any]:
        """Prepare request arguments"""
        headers = headers or {}
        request_args = {
            'method': method,
            'url': endpoint,
            'params': params,
            'headers': headers
        }

        # Add data if present
        if data:
            if method in ['POST', 'PUT', 'PATCH']:
                request_args['json'] = data
            else:
                request_args['params'] = {**(params or {}), **data}

        # Add authentication
        if auth:
            auth_type = auth.get('type', '').lower()
            if auth_type == 'basic':
                request_args['auth'] = aiohttp.BasicAuth(
                    auth['username'],
                    auth['password']
                )
            elif auth_type == 'bearer':
                headers['Authorization'] = f"Bearer {auth['token']}"
            elif auth_type == 'oauth2':
                # Implement OAuth2 handling
                pass

        return request_args

    async def _execute_with_retry(
            self,
            request_args: Dict[str, Any]
    ) -> aiohttp.ClientResponse:
        """Execute request with retry logic"""
        last_exception = None
        delay = self.retry_config['retry_delay']

        for attempt in range(self.retry_config['max_retries'] + 1):
            try:
                async with self.session.request(**request_args) as response:
                    if response.status not in self.retry_config['retry_codes']:
                        return response

                    last_exception = Exception(
                        f"Retry-able status code: {response.status}"
                    )

            except Exception as e:
                last_exception = e

            if attempt < self.retry_config['max_retries']:
                await asyncio.sleep(min(
                    delay * (2 ** attempt),
                    self.retry_config['max_delay']
                ))

        raise last_exception or Exception("Max retries exceeded")

    async def _process_response(
            self,
            response: aiohttp.ClientResponse,
            start_time: datetime
    ) -> APIResponse:
        """Process API response"""
        duration = (datetime.now() - start_time).total_seconds()

        # Record response metrics
        await self._record_response_metrics(response, duration)

        return APIResponse(
            status_code=response.status,
            data=await response.json(),
            headers=dict(response.headers),
            duration=duration,
            rate_limits=self._extract_rate_limits(response)
        )

    def _get_cache_key(
            self,
            endpoint: str,
            method: str,
            params: Optional[Dict],
            data: Optional[Dict]
    ) -> str:
        """Generate cache key for request"""
        key_parts = [method, endpoint]

        if params:
            key_parts.append(json.dumps(params, sort_keys=True))
        if data:
            key_parts.append(json.dumps(data, sort_keys=True))

        return "|".join(key_parts)

    async def _record_response_metrics(
            self,
            response: aiohttp.ClientResponse,
            duration: float
    ) -> None:
        """Record response metrics"""
        await self.process_monitor.record_operation_metric(
            'api_request',
            success=response.status < 400,
            duration=duration,
            status_code=response.status
        )

        # Record rate limit metrics if present
        rate_limits = self._extract_rate_limits(response)
        if rate_limits.get('remaining') is not None:
            await self.process_monitor.record_metric(
                'rate_limit_remaining',
                float(rate_limits['remaining']),
                limit=rate_limits.get('limit')
            )

    async def _record_cache_hit(self, cache_key: str) -> None:
        """Record cache hit metrics"""
        await self.process_monitor.record_metric(
            'cache_hit',
            1,
            cache_key=cache_key
        )

    async def _record_error(
            self,
            error_type: str,
            error_message: str
    ) -> None:
        """Record error metrics"""
        await self.process_monitor.record_error(
            error_type,
            error_message=error_message
        )

    def _extract_rate_limits(
            self,
            response: aiohttp.ClientResponse
    ) -> Dict[str, Any]:
        """Extract rate limit information from response"""
        headers = response.headers
        return {
            'limit': headers.get('X-RateLimit-Limit'),
            'remaining': headers.get('X-RateLimit-Remaining'),
            'reset': headers.get('X-RateLimit-Reset'),
            'retry_after': headers.get('Retry-After')
        }

    async def _has_next_page(self, response: APIResponse) -> bool:
        """Check if paginated response has next page"""
        # Implement based on API pagination pattern
        data = response.data
        return (
                isinstance(data, dict) and
                data.get('next_page') or
                len(data.get('items', [])) >= self.config.BATCH_SIZE
        )