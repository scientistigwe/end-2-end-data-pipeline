# backend/flask_api/app/services/data_sources/api_service.py

import requests
from typing import Dict, Any
from .....database.models.data_source import DataSource, APISourceConfig
from .database_service import BaseSourceService


class APISourceService(BaseSourceService):
    source_type = 'api'

    def connect(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create API connection and source."""
        try:
            # Validate API connection
            response = requests.get(
                data['base_url'],
                headers=data.get('headers', {}),
                timeout=data.get('timeout', 30)
            )
            response.raise_for_status()
            
            # Create source record
            source = DataSource(
                name=data['name'],
                type=self.source_type,
                status='active',
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
                timeout=data.get('timeout', 30)
            )
            
            self.db_session.add(source)
            self.db_session.add(api_config)
            self.db_session.commit()
            
            return self._format_source(source)
        except Exception as e:
            self.logger.error(f"API connection error: {str(e)}")
            self.db_session.rollback()
            raise

    def execute_request(self, connection_id: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API request."""
        try:
            source = self.db_session.query(DataSource).get(connection_id)
            if not source:
                raise ValueError("API source not found")

            api_config = source.api_config
            method = request_data.get('method', 'GET')
            endpoint = request_data.get('endpoint', '')
            
            response = requests.request(
                method=method,
                url=f"{source.config['base_url']}/{endpoint.lstrip('/')}",
                headers=api_config.headers,
                json=request_data.get('body'),
                params=request_data.get('params'),
                timeout=api_config.timeout
            )
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            self.logger.error(f"API request error: {str(e)}")
            raise