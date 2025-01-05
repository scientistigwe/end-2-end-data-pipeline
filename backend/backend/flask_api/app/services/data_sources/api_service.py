# backend/flask_api/app/services/data_sources/api_service.py

import requests
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime, timedelta
from .base_service import BaseSourceService
from .....database.models.data_source import DataSource, APISourceConfig

class APISourceService(BaseSourceService):
    source_type = 'api'

    def connect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create and validate API connection."""
        try:
            # Validate API configuration
            validation_result = self.validate_config(data)
            if validation_result.status == 'failed':
                raise ValueError(f"Invalid API configuration: {validation_result.details}")

            # Create source record
            source = DataSource(
                name=data['name'],
                type=self.source_type,
                status='pending',
                config={
                    'base_url': data['base_url'],
                    'auth_type': data['auth_type']
                }
            )

            # Create API config
            api_config = APISourceConfig(
                source=source,
                auth_type=data['auth_type'],
                auth_config=data.get('auth_config', {}),
                rate_limit=data.get('rate_limit'),
                timeout=data.get('timeout', 30),
                headers=data.get('headers', {}),
                retry_config=data.get('retry_config', {
                    'max_retries': 3,
                    'backoff_factor': 1.0
                })
            )

            # Test connection before committing
            self._test_api_endpoint(
                data['base_url'], 
                api_config.headers, 
                api_config.timeout
            )

            source.status = 'active'
            self.db_session.add(source)
            self.db_session.add(api_config)
            self.db_session.commit()

            return self._format_source(source)
        except Exception as e:
            self.logger.error(f"API connection error: {str(e)}")
            self.db_session.rollback()
            raise

    def execute_request(self, connection_id: UUID, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API request with rate limiting and retries."""
        try:
            source = self._get_source_or_error(connection_id)
            api_config = source.api_config

            if not self._check_rate_limit(source):
                raise ValueError("Rate limit exceeded")

            method = request_data.get('method', 'GET')
            endpoint = request_data.get('endpoint', '')
            url = f"{source.config['base_url']}/{endpoint.lstrip('/')}"

            response = requests.request(
                method=method,
                url=url,
                headers=api_config.headers,
                json=request_data.get('body'),
                params=request_data.get('params'),
                timeout=api_config.timeout
            )
            response.raise_for_status()

            # Update rate limit tracking
            self._update_rate_limit_tracking(source)

            return {
                'status_code': response.status_code,
                'data': response.json(),
                'headers': dict(response.headers)
            }
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request error: {str(e)}")
            raise ValueError(f"API request failed: {str(e)}")

    def _validate_source_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate API source configuration."""
        errors = []
        required_fields = ['base_url', 'auth_type']
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        if 'base_url' in config:
            if not config['base_url'].startswith(('http://', 'https://')):
                errors.append("base_url must start with http:// or https://")

        valid_auth_types = ['none', 'basic', 'bearer', 'oauth2']
        if 'auth_type' in config and config['auth_type'] not in valid_auth_types:
            errors.append(f"Invalid auth_type. Must be one of: {', '.join(valid_auth_types)}")

        return errors

    def list_sources(self) -> List[DataSource]:
        """
        List all API data sources.
        
        Returns:
            List[DataSource]: List of all API data sources
        """
        try:
            return (self.db_session.query(DataSource)
                    .filter(DataSource.type == self.source_type)
                    .all())
        except Exception as exc:
            self.logger.error(f"Error listing API sources: {str(exc)}")
            raise
        
    def _test_source_connection(self, source: DataSource) -> Dict[str, Any]:
        """Test API connection and return metrics."""
        api_config = source.api_config
        start_time = datetime.utcnow()

        response = self._test_api_endpoint(
            source.config['base_url'],
            api_config.headers,
            api_config.timeout
        )

        end_time = datetime.utcnow()
        response_time = (end_time - start_time).total_seconds() * 1000

        return {
            "response_time_ms": response_time,
            "status_code": response.status_code,
            "headers": dict(response.headers)
        }

    def _sync_source_data(self, source: DataSource) -> Dict[str, Any]:
        """Sync API data based on configuration."""
        api_config = source.api_config
        sync_config = source.config.get('sync_config', {})
        
        # Example implementation for REST API synchronization
        endpoints = sync_config.get('endpoints', [])
        total_records = 0
        total_bytes = 0

        for endpoint in endpoints:
            response = requests.get(
                f"{source.config['base_url']}/{endpoint.lstrip('/')}",
                headers=api_config.headers,
                timeout=api_config.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            total_records += len(data)
            total_bytes += len(response.content)

        return {
            "records_processed": total_records,
            "bytes_processed": total_bytes
        }

    def _get_source_preview(self, source: DataSource, limit: int) -> List[Dict[str, Any]]:
        """Get preview of API data."""
        api_config = source.api_config
        preview_endpoint = source.config.get('preview_endpoint', '')

        response = requests.get(
            f"{source.config['base_url']}/{preview_endpoint.lstrip('/')}",
            headers=api_config.headers,
            params={'limit': limit},
            timeout=api_config.timeout
        )
        response.raise_for_status()

        data = response.json()
        return data[:limit] if isinstance(data, list) else [data]

    def _disconnect_source(self, source: DataSource) -> None:
        """Clean up API resources and revoke tokens if necessary."""
        api_config = source.api_config
        
        if api_config.auth_type == 'oauth2':
            revoke_url = source.config.get('revoke_token_url')
            if revoke_url and api_config.auth_config.get('access_token'):
                try:
                    requests.post(
                        revoke_url,
                        json={'token': api_config.auth_config['access_token']},
                        timeout=api_config.timeout
                    )
                except Exception as e:
                    self.logger.warning(f"Failed to revoke token: {str(e)}")

    def _test_api_endpoint(self, base_url: str, headers: Dict[str, str], timeout: int) -> requests.Response:
        """Test API endpoint accessibility."""
        response = requests.get(
            base_url,
            headers=headers,
            timeout=timeout
        )
        response.raise_for_status()
        return response

    def _check_rate_limit(self, source: DataSource) -> bool:
        """Check if request is within rate limit."""
        api_config = source.api_config
        if not api_config.rate_limit:
            return True

        current_time = datetime.utcnow()
        rate_limit_key = f"rate_limit_{source.id}"
        rate_limit_data = self.db_session.info.get(rate_limit_key, {})

        if not rate_limit_data:
            return True

        requests_made = rate_limit_data.get('requests', 0)
        window_start = rate_limit_data.get('window_start')

        if not window_start or \
           (current_time - window_start) > timedelta(seconds=60):
            return True

        return requests_made < api_config.rate_limit

    def _update_rate_limit_tracking(self, source: DataSource) -> None:
        """Update rate limit tracking information."""
        current_time = datetime.utcnow()
        rate_limit_key = f"rate_limit_{source.id}"
        rate_limit_data = self.db_session.info.get(rate_limit_key, {
            'requests': 0,
            'window_start': current_time
        })

        if (current_time - rate_limit_data['window_start']) > timedelta(seconds=60):
            rate_limit_data = {
                'requests': 1,
                'window_start': current_time
            }
        else:
            rate_limit_data['requests'] += 1

        self.db_session.info[rate_limit_key] = rate_limit_data