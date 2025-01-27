# backend/source_handlers/api/api_validator.py

import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse
import re
import ssl
import socket
from datetime import datetime

logger = logging.getLogger(__name__)


class APIValidator:
    """Validates API source integrity"""

    def __init__(self):
        # API validation settings
        self.allowed_schemes = {'http', 'https'}
        self.allowed_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH'}
        self.required_headers = {
            'GET': {'Accept'},
            'POST': {'Content-Type', 'Accept'},
            'PUT': {'Content-Type', 'Accept'},
            'PATCH': {'Content-Type', 'Accept'},
            'DELETE': {'Accept'}
        }
        self.default_timeout = 5  # seconds

    async def validate_api_source(
            self,
            endpoint: str,
            method: str,
            headers: Optional[Dict[str, str]] = None,
            auth: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Validate API source configuration
        Only validates API-level attributes, not response content
        """
        issues = []
        warnings = []

        try:
            # Validate URL
            url_validation = self._validate_url(endpoint)
            issues.extend(url_validation.get('issues', []))
            warnings.extend(url_validation.get('warnings', []))

            # Validate method
            method = method.upper()
            if method not in self.allowed_methods:
                issues.append(f'Invalid HTTP method: {method}')

            # Validate headers
            if headers:
                header_validation = self._validate_headers(method, headers)
                issues.extend(header_validation.get('issues', []))
                warnings.extend(header_validation.get('warnings', []))

            # Validate auth configuration
            if auth:
                auth_validation = self._validate_auth_config(auth)
                issues.extend(auth_validation.get('issues', []))
                warnings.extend(auth_validation.get('warnings', []))

            # Connection check
            if not issues:  # Only check connection if no critical issues
                conn_validation = await self._validate_connection(endpoint)
                issues.extend(conn_validation.get('issues', []))
                warnings.extend(conn_validation.get('warnings', []))

            return {
                'passed': len(issues) == 0,
                'issues': issues,
                'warnings': warnings,
                'metadata': {
                    'url_info': self._get_url_info(endpoint),
                    'timestamp': datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"API validation error: {str(e)}")
            return {
                'passed': False,
                'issues': [str(e)],
                'warnings': []
            }

    def _validate_url(self, url: str) -> Dict[str, Any]:
        """Validate URL format and components"""
        issues = []
        warnings = []

        try:
            parsed = urlparse(url)

            # Scheme validation
            if not parsed.scheme:
                issues.append('URL scheme is missing')
            elif parsed.scheme not in self.allowed_schemes:
                issues.append(f'Invalid URL scheme: {parsed.scheme}')

            # Host validation
            if not parsed.netloc:
                issues.append('URL host is missing')
            elif not self._is_valid_hostname(parsed.netloc):
                issues.append(f'Invalid hostname: {parsed.netloc}')

            # Path validation
            if not parsed.path and not parsed.path == '/':
                warnings.append('URL path is missing')

            # Query parameters
            if parsed.query and not self._is_valid_query(parsed.query):
                warnings.append('Query string might contain invalid characters')

            # Fragment validation
            if parsed.fragment:
                warnings.append('URL contains fragment identifier')

            return {
                'issues': issues,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'issues': [f'URL parsing error: {str(e)}'],
                'warnings': []
            }

    def _validate_headers(
            self,
            method: str,
            headers: Dict[str, str]
    ) -> Dict[str, Any]:
        """Validate request headers"""
        issues = []
        warnings = []

        # Check required headers
        if method in self.required_headers:
            missing_headers = self.required_headers[method] - set(
                k.lower() for k in headers.keys()
            )
            if missing_headers:
                issues.append(f"Missing required headers: {', '.join(missing_headers)}")

        # Validate header values
        for key, value in headers.items():
            # Check for empty values
            if not value:
                issues.append(f'Empty value for header: {key}')

            # Check for common security headers
            if key.lower() in {'authorization', 'x-api-key'}:
                warnings.append(f'Sensitive header detected: {key}')

            # Validate header format
            if not self._is_valid_header(key, value):
                issues.append(f'Invalid header format: {key}')

        return {
            'issues': issues,
            'warnings': warnings
        }

    # backend/source_handlers/api/api_validator.py (continued)

    def _validate_auth_config(self, auth: Dict[str, Any]) -> Dict[str, Any]:
        """Validate authentication configuration"""
        issues = []
        warnings = []

        auth_type = auth.get('type', '').lower()

        if not auth_type:
            issues.append('Authentication type not specified')
            return {'issues': issues, 'warnings': warnings}

        if auth_type == 'basic':
            if not auth.get('username'):
                issues.append('Username required for basic auth')
            if not auth.get('password'):
                issues.append('Password required for basic auth')

        elif auth_type == 'bearer':
            if not auth.get('token'):
                issues.append('Token required for bearer auth')

        elif auth_type == 'api_key':
            if not auth.get('key'):
                issues.append('API key required')
            if not auth.get('location') in {'header', 'query'}:
                issues.append('Invalid API key location (must be header or query)')

        elif auth_type == 'oauth2':
            if not all(k in auth for k in ['client_id', 'client_secret', 'token_url']):
                issues.append('Missing required OAuth2 credentials')

        else:
            issues.append(f'Unsupported authentication type: {auth_type}')

        # Security recommendations
        if not auth.get('secure', True):
            warnings.append('Authentication over non-secure connection')

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

            # Check connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.default_timeout)

            try:
                if parsed.scheme == 'https':
                    context = ssl.create_default_context()
                    with context.wrap_socket(sock, server_hostname=parsed.hostname) as ssock:
                        ssock.connect((parsed.hostname, port))

                        # Verify certificate
                        cert = ssock.getpeercert()
                        if not cert:
                            warnings.append('No SSL certificate found')
                        else:
                            # Check certificate expiration
                            if not self._verify_cert_dates(cert):
                                warnings.append('SSL certificate expiration warning')
                else:
                    sock.connect((parsed.hostname, port))
                    warnings.append('Using non-secure connection')

            except (socket.timeout, ConnectionRefusedError) as e:
                issues.append(f'Connection failed: {str(e)}')
            except ssl.SSLError as e:
                issues.append(f'SSL error: {str(e)}')
            finally:
                sock.close()

            return {
                'issues': issues,
                'warnings': warnings
            }

        except Exception as e:
            return {
                'issues': [f'Connection validation error: {str(e)}'],
                'warnings': []
            }

    def _is_valid_hostname(self, hostname: str) -> bool:
        """Validate hostname format"""
        if not hostname:
            return False

        if len(hostname) > 255:
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

    def _is_valid_header(self, key: str, value: str) -> bool:
        """Validate header format"""
        # Check for invalid characters in header name
        if not re.match(r'^[a-zA-Z0-9-_]+$', key):
            return False

        # Check for newlines in value (potential header injection)
        if '\n' in value or '\r' in value:
            return False

        return True

    def _verify_cert_dates(self, cert: Dict) -> bool:
        """Verify SSL certificate dates"""
        try:
            from datetime import datetime
            import ssl

            not_after = ssl.cert_time_to_seconds(cert['notAfter'])
            not_before = ssl.cert_time_to_seconds(cert['notBefore'])
            now = datetime.now().timestamp()

            # Check if cert is current
            if now < not_before or now > not_after:
                return False

            # Warn if cert is expiring soon (30 days)
            if (not_after - now) < (30 * 24 * 60 * 60):
                return False

            return True

        except Exception:
            return False

    def _get_url_info(self, url: str) -> Dict[str, Any]:
        """Get URL components for metadata"""
        parsed = urlparse(url)
        return {
            'scheme': parsed.scheme,
            'hostname': parsed.hostname,
            'port': parsed.port,
            'path': parsed.path,
            'has_query': bool(parsed.query)
        }