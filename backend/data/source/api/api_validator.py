# backend/source_handlers/api/api_validator.py

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import re
import ssl
import socket
from datetime import datetime

from config.validation_config import APIValidationConfig

logger = logging.getLogger(__name__)

class APIValidator:
    """Enhanced API validator with integrated config"""

    def __init__(self, config: Optional[APIValidationConfig] = None):
        self.config = config or APIValidationConfig()

    async def validate_api_source(
            self,
            endpoint: str,
            method: str,
            headers: Optional[Dict[str, str]] = None,
            auth: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate API source configuration
        Provides comprehensive validation with issues and warnings
        """
        try:
            issues = []
            warnings = []

            # Validate URL
            url_validation = await self._validate_url(endpoint)
            issues.extend(url_validation.get('issues', []))
            warnings.extend(url_validation.get('warnings', []))

            # Validate method
            method_validation = await self._validate_method(method)
            issues.extend(method_validation.get('issues', []))
            warnings.extend(method_validation.get('warnings', []))

            # Validate headers
            if headers:
                header_validation = await self._validate_headers(method, headers)
                issues.extend(header_validation.get('issues', []))
                warnings.extend(header_validation.get('warnings', []))

            # Validate authentication
            if auth:
                auth_validation = await self._validate_auth(auth)
                issues.extend(auth_validation.get('issues', []))
                warnings.extend(auth_validation.get('warnings', []))

            # Connection check (only if no critical issues)
            if not issues:
                connection_validation = await self._validate_connection(endpoint)
                issues.extend(connection_validation.get('issues', []))
                warnings.extend(connection_validation.get('warnings', []))

            return self._build_result(
                passed=len(issues) == 0,
                issues=issues,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"API validation error: {str(e)}")
            return self._build_result(
                passed=False,
                issues=[str(e)],
                warnings=[]
            )

    async def _validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL format and components"""
        issues = []
        warnings = []

        try:
            parsed = urlparse(url)

            # Scheme validation
            if not parsed.scheme:
                issues.append('URL scheme is missing')
            elif parsed.scheme not in self.config.allowed_schemes:
                issues.append(f'Invalid URL scheme: {parsed.scheme}')

            # Host validation
            if not parsed.netloc:
                issues.append('URL host is missing')
            elif not self._is_valid_hostname(parsed.netloc):
                issues.append(f'Invalid hostname: {parsed.netloc}')

            # Path validation
            if not parsed.path:
                warnings.append('URL path is empty')

            # Query validation
            if parsed.query and not self._is_valid_query(parsed.query):
                warnings.append('Query string might contain invalid characters')

            return {
                'issues': issues,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'issues': [f'URL parsing error: {str(e)}'],
                'warnings': []
            }

    async def _validate_method(self, method: str) -> Dict[str, Any]:
        """Validate HTTP method"""
        issues = []
        warnings = []

        method = method.upper()
        if method not in self.config.allowed_methods:
            issues.append(f'Invalid HTTP method: {method}')

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_headers(
            self,
            method: str,
            headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Validate request headers"""
        issues = []
        warnings = []

        # Check required headers
        method_headers = self.config.required_headers.get(method, set())
        missing_headers = method_headers - set(headers.keys())
        if missing_headers:
            issues.append(f"Missing required headers: {', '.join(missing_headers)}")

        # Check for blocked patterns in headers
        for key, value in headers.items():
            # Check for sensitive header names
            if any(re.search(pattern, key, re.IGNORECASE) for pattern in self.config.blocked_patterns):
                warnings.append(f'Sensitive header detected: {key}')

            # Check for empty values
            if not value:
                issues.append(f'Empty value for header: {key}')

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_auth(self, auth: Dict[str, Any]) -> Dict[str, Any]:
        """Validate authentication configuration"""
        issues = []
        warnings = []

        auth_type = auth.get('type', '').lower()

        # Check auth type
        if not auth_type:
            issues.append('Authentication type is missing')
        elif auth_type not in self.config.supported_auth_types:
            issues.append(f'Unsupported authentication type: {auth_type}')

        # Specific auth type validations
        if auth_type == 'basic':
            if not auth.get('username'):
                issues.append('Username is required for basic authentication')
            if not auth.get('password'):
                issues.append('Password is required for basic authentication')

        elif auth_type == 'bearer':
            if not auth.get('token'):
                issues.append('Token is required for bearer authentication')

        elif auth_type == 'oauth2':
            required_fields = ['client_id', 'client_secret', 'token_url']
            for field in required_fields:
                if not auth.get(field):
                    issues.append(f'{field.replace("_", " ").title()} is required for OAuth2')

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_connection(self, url: str) -> Dict[str, Any]:
        """Validate basic connection to API endpoint"""
        issues = []
        warnings = []

        try:
            parsed = urlparse(url)
            port = parsed.port or (443 if parsed.scheme == 'https' else 80)

            # Check DNS
            try:
                socket.gethostbyname(parsed.hostname)
            except socket.gaierror:
                issues.append(f'Could not resolve hostname: {parsed.hostname}')
                return {'issues': issues, 'warnings': warnings}

            # Connection check
            with socket.create_connection(
                    (parsed.hostname, port),
                    timeout=self.config.connection_timeout
            ):
                # SSL verification for HTTPS
                if parsed.scheme == 'https' and self.config.require_ssl:
                    try:
                        with ssl.create_default_context().wrap_socket(
                                socket.socket(socket.AF_INET),
                                server_hostname=parsed.hostname
                        ) as ssock:
                            ssock.connect((parsed.hostname, port))
                    except ssl.SSLError:
                        warnings.append('SSL certificate validation failed')

            return {
                'issues': issues,
                'warnings': warnings
            }

        except (socket.timeout, ConnectionRefusedError):
            issues.append('Connection failed')
            return {
                'issues': issues,
                'warnings': warnings
            }
        except Exception as e:
            return {
                'issues': [f'Connection validation error: {str(e)}'],
                'warnings': []
            }

    def _build_result(
            self,
            passed: bool,
            issues: list[str],
            warnings: list[str]
    ) -> Dict[str, Any]:
        """Build structured validation result"""
        return {
            'passed': passed,
            'issues': issues,
            'warnings': warnings,
            'validation_time': datetime.utcnow().isoformat()
        }

    def _is_valid_hostname(self, hostname: str) -> bool:
        """Validate hostname format"""
        if not hostname or len(hostname) > 255:
            return False

        if hostname[-1] == ".":
            hostname = hostname[:-1]

        allowed = re.compile(r"(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
        return all(allowed.match(x) for x in hostname.split("."))

    def _is_valid_query(self, query: str) -> bool:
        """Validate query string format"""
        # Basic validation of query string characters
        invalid_chars = set('"\'\n\r\t<>')
        return not any(char in query for char in invalid_chars)