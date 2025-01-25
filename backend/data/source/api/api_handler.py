# backend/source_handlers/api/api_handler.py

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union
from urllib.parse import urlparse

import aiohttp

from core.messaging.broker import MessageBroker
from core.staging.staging_manager import StagingManager
from core.messaging.event_types import (
    MessageType, ProcessingMessage, ModuleIdentifier, ComponentType
)
from .api_validator import APIValidator, APIValidationConfig

logger = logging.getLogger(__name__)


class APIHandler:
    """Core handler for API data source operations"""

    def __init__(
            self,
            staging_manager: StagingManager,
            message_broker: MessageBroker,
            validator_config: Optional[APIValidationConfig] = None,
            timeout: int = 30,
            max_retries: int = 3
    ):
        self.staging_manager = staging_manager
        self.message_broker = message_broker
        self.timeout = timeout
        self.max_retries = max_retries
        self.validator = APIValidator(config=validator_config)

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="api_handler",
            component_type=ComponentType.HANDLER,
            department="source",
            role="handler"
        )

        # Chunk size for processing
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
        """
        Process incoming API request

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
            # Validate source configuration
            source_data = {
                'endpoint': endpoint,
                'method': method,
                'headers': headers,
                'auth': auth
            }
            validation_result = await self.validator.validate_source(source_data)

            if not validation_result['passed']:
                return {
                    'status': 'error',
                    'errors': validation_result['issues']
                }

            # Fetch API data
            request_result = await self._process_api_data(
                endpoint, method, headers, params, body, auth
            )

            # Stage the received data
            staged_id = await self._stage_api_data(
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
        """
        Fetch and process API data with retry mechanism

        Args:
            endpoint: API endpoint URL
            method: HTTP method
            headers: Request headers
            params: Query parameters
            body: Request body
            auth: Authentication details

        Returns:
            Dictionary with API response details
        """
        async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as session:
            retries = 0
            while retries < self.max_retries:
                try:
                    async with session.request(
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
                            'content_type': content_type,
                            'headers': dict(response.headers),
                            'data': data,
                            'size_bytes': len(json.dumps(data).encode()),
                            'temp_path': None  # Placeholder for potential temp file storage
                        }

                except Exception as e:
                    retries += 1
                    if retries >= self.max_retries:
                        raise

                    # Exponential backoff
                    await asyncio.sleep(2 ** retries)

    async def _stage_api_data(
            self,
            endpoint: str,
            request_result: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store API response in staging area

        Args:
            endpoint: API endpoint URL
            request_result: Processed API response
            metadata: Additional metadata

        Returns:
            Staged data identifier
        """
        try:
            # Prepare staging metadata
            staging_metadata = {
                'endpoint': endpoint,
                'status_code': request_result['status_code'],
                'content_type': request_result['content_type'],
                'size_bytes': request_result['size_bytes'],
                **(metadata or {})
            }

            # Store in staging
            staged_id = await self.staging_manager.store_data(
                data=request_result['data'],
                metadata=staging_metadata,
                source_type='api'
            )

            # Notify about staging
            await self._notify_staging(staged_id, staging_metadata)

            return staged_id

        except Exception as e:
            logger.error(f"API data staging error: {str(e)}")
            raise

    async def _notify_staging(
            self,
            staged_id: str,
            metadata: Dict[str, Any]
    ) -> None:
        """
        Notify about staged API data

        Args:
            staged_id: Identifier of staged data
            metadata: Staging metadata
        """
        try:
            message = ProcessingMessage(
                source_identifier=self.module_identifier,
                message_type=MessageType.DATA_STORAGE,
                content={
                    'staged_id': staged_id,
                    'source_type': 'api',
                    'metadata': metadata,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )

            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Staging notification error: {str(e)}")

    def _get_auth(self, auth: Dict[str, Any]) -> Union[aiohttp.BasicAuth, None]:
        """
        Get authentication for request

        Args:
            auth: Authentication configuration

        Returns:
            Authentication object or None
        """
        auth_type = auth.get('type', '').lower()

        if auth_type == 'basic':
            return aiohttp.BasicAuth(
                login=auth['username'],
                password=auth['password']
            )
        elif auth_type == 'bearer':
            return None  # Handle via headers

        return None