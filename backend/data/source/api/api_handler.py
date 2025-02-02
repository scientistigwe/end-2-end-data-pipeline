# backend/source_handlers/api/api_handler.py

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
import aiohttp

from core.managers.staging_manager import StagingManager
from .api_validator import APIValidator
from config.validation_config import APIValidationConfig

logger = logging.getLogger(__name__)

class APIHandler:
    """Handler for API data source operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            validator_config: Optional[APIValidationConfig] = None,
            timeout: int = 30,
            max_retries: int = 3
    ):
        self.staging_manager = staging_manager
        self.validator = APIValidator(config=validator_config)
        self.timeout = timeout
        self.max_retries = max_retries
        self.chunk_size = 8192  # 8KB chunks

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
        """Process API request"""
        try:
            # Validate source configuration
            validation_result = await self.validator.validate_source({
                'endpoint': endpoint,
                'method': method,
                'headers': headers,
                'auth': auth
            })

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Process API request
            request_result = await self._process_api_data(
                endpoint, method, headers, params, body, auth
            )

            # Stage the data
            staged_id = await self._stage_data(
                endpoint,
                request_result,
                metadata
            )

            return {
                'status': 'success',
                'staged_id': staged_id,
                'api_info': request_result
            }

        except Exception as e:
            logger.error(f"API request handling error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def _process_api_data(
            self,
            endpoint: str,
            method: str,
            headers: Optional[Dict[str, str]] = None,
            params: Optional[Dict[str, Any]] = None,
            body: Optional[Dict[str, Any]] = None,
            auth: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process API data with retry mechanism"""
        async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            retries = 0
            while retries < self.max_retries:
                try:
                    response_data = await self._make_request(
                        session, method, endpoint, headers, params, body, auth
                    )
                    return response_data

                except Exception as e:
                    retries += 1
                    if retries >= self.max_retries:
                        raise
                    await asyncio.sleep(2 ** retries)

    async def _make_request(
            self,
            session: aiohttp.ClientSession,
            method: str,
            endpoint: str,
            headers: Optional[Dict[str, str]],
            params: Optional[Dict[str, Any]],
            body: Optional[Dict[str, Any]],
            auth: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Make HTTP request"""
        async with session.request(
                method=method,
                url=endpoint,
                headers=headers,
                params=params,
                json=body,
                auth=self._get_auth(auth) if auth else None
        ) as response:
            content_type = response.headers.get('Content-Type', '')
            data = await response.json() if 'application/json' in content_type else await response.text()

            return {
                'status_code': response.status,
                'content_type': content_type,
                'headers': dict(response.headers),
                'data': data,
                'size_bytes': len(str(data).encode())
            }

    async def _stage_data(
            self,
            endpoint: str,
            request_result: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store API response in staging"""
        try:
            staging_metadata = {
                'endpoint': endpoint,
                'status_code': request_result['status_code'],
                'content_type': request_result['content_type'],
                'size_bytes': request_result['size_bytes'],
                'timestamp': datetime.utcnow().isoformat(),
                **(metadata or {})
            }

            return await self.staging_manager.store_data(
                data=request_result['data'],
                metadata=staging_metadata,
                source_type='api'
            )

        except Exception as e:
            logger.error(f"API data staging error: {str(e)}")
            raise

    def _get_auth(self, auth: Dict[str, Any]) -> Optional[aiohttp.BasicAuth]:
        """Get authentication configuration"""
        if not auth or 'type' not in auth:
            return None

        auth_type = auth['type'].lower()
        if auth_type == 'basic':
            return aiohttp.BasicAuth(
                login=auth['username'],
                password=auth['password']
            )
        return None