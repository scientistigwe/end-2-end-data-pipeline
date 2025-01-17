# backend/source_handlers/api/api_handler.py

# Standard library imports
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
from urllib.parse import urlparse

# Third-party imports
import aiohttp

# Local imports
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType
from backend.core.staging.staging_manager import StagingManager
from backend.core.monitoring.process import ProcessMonitor
from backend.core.utils.encryption import AESEncryption
from .api_validator import APIValidator

logger = logging.getLogger(__name__)


class APIHandler:
    """Handles API data source operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            message_broker: MessageBroker,
            timeout: int = 30,
            max_retries: int = 3
    ):
        self.staging_manager = staging_manager
        self.message_broker = message_broker
        self.timeout = timeout
        self.max_retries = max_retries
        self.validator = APIValidator()
        self.encryption = AESEncryption()
        self.process_monitor = ProcessMonitor()

        # Session management
        self.session = None
        self._session_lock = asyncio.Lock()

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
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                )

    async def _cleanup_session(self):
        """Clean up HTTP session"""
        async with self._session_lock:
            if self.session:
                await self.session.close()
                self.session = None

    async def handle_api_request(
            self,
            endpoint: str,
            method: str = 'GET',
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
            body: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Handle API request source

        Args:
            endpoint: API endpoint URL
            method: HTTP method
            headers: Request headers
            params: Query parameters
            body: Request body
            auth: Authentication details
            metadata: Additional metadata

        Returns:
            Dictionary containing staging information
        """
        try:
            start_time = datetime.now()

            # Validate API request
            validation_result = await self.validator.validate_api_source(
                endpoint=endpoint,
                method=method,
                headers=headers,
                auth=auth
            )

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'error': 'API validation failed',
                    'details': validation_result
                }

            # Create staging area
            staged_id = await self.staging_manager.create_staging_area(
                source_type='api',
                source_identifier=endpoint,
                metadata={
                    'method': method,
                    'headers': headers,
                    'params': params,
                    'auth': self._secure_auth_info(auth) if auth else None,
                    **(metadata or {})
                }
            )

            # Make API request
            response = await self._make_request(
                endpoint=endpoint,
                method=method,
                headers=headers,
                params=params,
                body=body,
                auth=auth
            )

            # Store response in staging
            await self.staging_manager.store_staged_data(
                staged_id,
                response['data'],
                metadata={
                    'status_code': response['status_code'],
                    'headers': dict(response['headers']),
                    'size': len(response['data']),
                    'response_type': response.get('content_type')
                }
            )

            # Record metrics
            duration = (datetime.now() - start_time).total_seconds()
            await self.process_monitor.record_operation_metric(
                'api_request',
                success=True,
                duration=duration,
                status_code=response['status_code']
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                'response_info': {
                    'status_code': response['status_code'],
                    'content_type': response.get('content_type'),
                    'size': len(response['data'])
                }
            }

        except Exception as e:
            logger.error(f"Error handling API request: {str(e)}")

            # Record error
            await self.process_monitor.record_error(
                'api_request_error',
                error=str(e),
                endpoint=endpoint
            )

            raise

    async def _make_request(
            self,
            endpoint: str,
            method: str,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
            body: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retries"""
        await self._ensure_session()

        retries = 0
        last_error = None

        while retries < self.max_retries:
            try:
                async with self.session.request(
                        method=method,
                        url=endpoint,
                        headers=headers,
                        params=params,
                        json=body,
                        auth=self._get_auth(auth) if auth else None
                ) as response:
                    content_type = response.headers.get('Content-Type', '')

                    # Parse response based on content type
                    if 'application/json' in content_type:
                        data = await response.json()
                    else:
                        data = await response.text()

                    return {
                        'status_code': response.status,
                        'headers': response.headers,
                        'data': data,
                        'content_type': content_type
                    }

            except Exception as e:
                last_error = e
                retries += 1
                if retries < self.max_retries:
                    await asyncio.sleep(2 ** retries)  # Exponential backoff

        raise last_error or Exception("Request failed after retries")

    def _get_auth(self, auth: Dict[str, Any]) -> Union[aiohttp.BasicAuth, None]:
        """Get authentication for request"""
        auth_type = auth.get('type', '').lower()

        if auth_type == 'basic':
            return aiohttp.BasicAuth(
                login=auth['username'],
                password=auth['password']
            )
        elif auth_type == 'bearer':
            return None  # Handle via headers

        return None

    def _secure_auth_info(self, auth: Dict[str, Any]) -> Dict[str, Any]:
        """Secure sensitive authentication information"""
        if not auth:
            return None

        # Encrypt sensitive fields
        secured_auth = auth.copy()
        sensitive_fields = {'password', 'token', 'api_key', 'secret'}

        for field in sensitive_fields:
            if field in secured_auth:
                secured_auth[f'encrypted_{field}'] = self.encryption.encrypt(
                    secured_auth.pop(field)
                )

        return secured_auth

    async def check_api_status(
            self,
            staged_id: str
    ) -> Dict[str, Any]:
        """Get status of staged API request"""
        try:
            staged_data = await self.staging_manager.get_staged_data(staged_id)
            if not staged_data:
                return None

            return {
                'endpoint': staged_data['source_identifier'],
                'method': staged_data['metadata'].get('method'),
                'status_code': staged_data['metadata'].get('status_code'),
                'content_type': staged_data['metadata'].get('response_type'),
                'response_size': staged_data['metadata'].get('size'),
                'created_at': staged_data['created_at']
            }

        except Exception as e:
            logger.error(f"Error checking API status: {str(e)}")
            raise

    async def cleanup(self):
        """Clean up resources"""
        await self._cleanup_session()