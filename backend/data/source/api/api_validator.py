from __future__ import annotations

import logging
import asyncio
import re
import aiohttp
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json

from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from .api_config import Config

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """Validation severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """Structured validation result"""
    passed: bool
    check_type: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    severity: ValidationLevel = ValidationLevel.ERROR


class APIValidator:
    """Enhanced API validator with comprehensive validation capabilities"""

    def __init__(
            self,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None
    ):
        """Initialize validator with configuration"""
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()
        self.process_monitor = ProcessMonitor(
            metrics_collector=self.metrics_collector,
            source_type="api_validator",
            source_id="validator"
        )

        # Validation thresholds
        self.validation_thresholds = {
            'timeout_seconds': self.config.REQUEST.REQUEST_TIMEOUT,
            'max_retries': self.config.RETRY.MAX_RETRIES,
            'max_redirects': self.config.REQUEST.MAX_REDIRECTS,
            'max_content_length': self.config.REQUEST.MAX_CONTENT_LENGTH
        }

        # Initialize HTTP session
        self.session = None

    async def __aenter__(self):
        """Async context manager entry"""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
            self.session = None

    async def validate_request_comprehensive(
            self,
            request_data: Dict[str, Any],
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive request validation

        Args:
            request_data: Request configuration to validate
            metadata: Additional metadata for validation

        Returns:
            Dictionary containing validation results
        """
        try:
            validation_start = datetime.now()
            results = []

            # Execute validations concurrently
            validation_tasks = [
                self.validate_endpoint(request_data.get('endpoint', '')),
                self.validate_method(request_data.get('method', 'GET')),
                self.validate_headers(request_data.get('headers', {})),
                self.validate_params(request_data.get('params', {})),
                self.validate_body(request_data.get('body'))
            ]

            if 'auth' in request_data:
                validation_tasks.append(
                    self.validate_auth_config(request_data['auth'])
                )

            # Gather results
            results.extend(await asyncio.gather(*validation_tasks, return_exceptions=True))

            # Filter out exceptions and create error validations
            filtered_results = []
            for result in results:
                if isinstance(result, Exception):
                    filtered_results.append(ValidationResult(
                        passed=False,
                        check_type='error',
                        message=f"Validation error: {str(result)}",
                        details={'error': str(result)},
                        severity=ValidationLevel.ERROR
                    ))
                else:
                    filtered_results.append(result)

            # Compile results
            validation_summary = self._compile_validation_results(filtered_results)

            # Record metrics
            await self.process_monitor.record_operation_metric(
                'request_validation',
                success=validation_summary['passed'],
                duration=(datetime.now() - validation_start).total_seconds(),
                check_count=len(filtered_results)
            )

            return validation_summary

        except Exception as e:
            logger.error(f"Comprehensive validation error: {str(e)}", exc_info=True)
            return {
                'passed': False,
                'error': str(e),
                'checks': []
            }

    async def validate_endpoint(self, endpoint: str) -> ValidationResult:
        """Validate API endpoint"""
        try:
            if not endpoint:
                return ValidationResult(
                    passed=False,
                    check_type='endpoint',
                    message="Endpoint URL is required",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            # URL format validation
            url_pattern = r'^https?:\/\/[\w\-\.]+(:\d+)?(\/[\w\-\.\/?%&=]*)?$'
            if not re.match(url_pattern, endpoint):
                return ValidationResult(
                    passed=False,
                    check_type='endpoint',
                    message="Invalid URL format",
                    details={'endpoint': endpoint},
                    severity=ValidationLevel.ERROR
                )

            # Check endpoint accessibility
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.head(
                            endpoint,
                            timeout=self.validation_thresholds['timeout_seconds'],
                            allow_redirects=True
                    ) as response:
                        return ValidationResult(
                            passed=response.status < 400,
                            check_type='endpoint',
                            message=f"Endpoint check: {response.status}",
                            details={
                                'status': response.status,
                                'headers': dict(response.headers)
                            },
                            severity=ValidationLevel.ERROR if response.status >= 400 else ValidationLevel.INFO
                        )
                except asyncio.TimeoutError:
                    return ValidationResult(
                        passed=False,
                        check_type='endpoint',
                        message="Endpoint timeout",
                        details={'timeout': self.validation_thresholds['timeout_seconds']},
                        severity=ValidationLevel.ERROR
                    )

        except Exception as e:
            logger.error(f"Endpoint validation error: {str(e)}", exc_info=True)
            return ValidationResult(
                passed=False,
                check_type='endpoint',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_method(self, method: str) -> ValidationResult:
        """Validate HTTP method"""
        try:
            if not method:
                return ValidationResult(
                    passed=False,
                    check_type='method',
                    message="HTTP method is required",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            method = method.upper()
            if method not in self.config.ALLOWED_METHODS:
                return ValidationResult(
                    passed=False,
                    check_type='method',
                    message=f"Invalid HTTP method: {method}",
                    details={
                        'method': method,
                        'allowed_methods': self.config.ALLOWED_METHODS
                    },
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='method',
                message="Valid HTTP method",
                details={'method': method},
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='method',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_headers(
            self,
            headers: Dict[str, str]
    ) -> ValidationResult:
        """Validate request headers"""
        try:
            issues = []

            # Check for required headers
            required_headers = {'Accept', 'User-Agent'}
            missing_headers = required_headers - set(headers.keys())
            if missing_headers:
                issues.append(f"Missing required headers: {', '.join(missing_headers)}")

            # Validate content type if present
            content_type = headers.get('Content-Type', '')
            if content_type and not any(
                    ct in content_type
                    for ct in ['application/json', 'application/x-www-form-urlencoded']
            ):
                issues.append(f"Unsupported Content-Type: {content_type}")

            # Check for sensitive information in headers
            sensitive_patterns = [
                r'(?i)(api[-_]?key|token|secret)',
                r'(?i)(auth|bearer)'
            ]
            for key in headers.keys():
                if any(re.search(pattern, key) for pattern in sensitive_patterns):
                    issues.append(f"Sensitive information found in header: {key}")

            return ValidationResult(
                passed=len(issues) == 0,
                check_type='headers',
                message="Header validation complete",
                details={
                    'issues': issues,
                    'valid_headers': list(headers.keys())
                },
                severity=ValidationLevel.ERROR if issues else ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='headers',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_auth_config(
            self,
            auth_config: Dict[str, Any]
    ) -> ValidationResult:
        """Validate authentication configuration"""
        try:
            auth_type = auth_config.get('type', '').lower()
            issues = []

            if not auth_type:
                return ValidationResult(
                    passed=False,
                    check_type='auth',
                    message="Auth type is required",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            # Validate based on auth type
            if auth_type == 'basic':
                if 'username' not in auth_config:
                    issues.append("Missing username for basic auth")
                if 'password' not in auth_config:
                    issues.append("Missing password for basic auth")

            elif auth_type == 'bearer':
                if 'token' not in auth_config:
                    issues.append("Missing token for bearer auth")

            elif auth_type == 'oauth2':
                required_fields = ['client_id', 'client_secret', 'token_url']
                missing_fields = [
                    field for field in required_fields
                    if field not in auth_config
                ]
                if missing_fields:
                    issues.append(f"Missing OAuth2 fields: {', '.join(missing_fields)}")

            else:
                issues.append(f"Unsupported auth type: {auth_type}")

            return ValidationResult(
                passed=len(issues) == 0,
                check_type='auth',
                message="Auth configuration validation complete",
                details={
                    'issues': issues,
                    'auth_type': auth_type
                },
                severity=ValidationLevel.ERROR if issues else ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='auth',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_params(
            self,
            params: Dict[str, Any]
    ) -> ValidationResult:
        """Validate request parameters"""
        try:
            issues = []

            # Check param values
            for key, value in params.items():
                # Check for empty values
                if value is None or value == '':
                    issues.append(f"Empty value for parameter: {key}")

                # Check value types
                if not isinstance(value, (str, int, float, bool, list)):
                    issues.append(f"Invalid type for parameter {key}: {type(value)}")

                # Check list parameters
                if isinstance(value, list):
                    if not all(isinstance(v, (str, int, float, bool)) for v in value):
                        issues.append(f"Invalid value type in list parameter: {key}")

            return ValidationResult(
                passed=len(issues) == 0,
                check_type='params',
                message="Parameter validation complete",
                details={
                    'issues': issues,
                    'param_count': len(params)
                },
                severity=ValidationLevel.ERROR if issues else ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='params',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    def _compile_validation_results(
            self,
            results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """Compile validation results into summary"""
        return {
            'passed': all(result.passed for result in results),
            'checks': [
                {
                    'type': result.check_type,
                    'passed': result.passed,
                    'message': result.message,
                    'details': result.details,
                    'severity': result.severity.value,
                    'timestamp': result.timestamp.isoformat()
                }
                for result in results
            ],
            'summary': {
                'total_checks': len(results),
                'passed_checks': sum(1 for result in results if result.passed),
                'failed_checks': sum(1 for result in results if not result.passed),
                'highest_severity': max(
                    (result.severity for result in results),
                    default=ValidationLevel.INFO
                ).value
            }
        }
    
    async def validate_config(self, config: Config) -> ValidationResult:
        """
        Validate API configuration
        
        Args:
            config: Config instance to validate
            
        Returns:
            ValidationResult containing validation outcome
        """
        try:
            issues = []

            # Validate auth configuration
            if config.auth_type != "none":
                if config.auth_type == "basic" and not (config.api_key and config.api_secret):
                    issues.append("Basic auth requires both api_key and api_secret")
                elif config.auth_type == "bearer" and not config.auth_token:
                    issues.append("Bearer auth requires auth_token")
                elif config.auth_type == "oauth2" and not (config.api_key and config.api_secret):
                    issues.append("OAuth2 requires both api_key and api_secret")
                elif config.auth_type not in ["basic", "bearer", "oauth2"]:
                    issues.append(f"Unsupported auth type: {config.auth_type}")

            # Validate base URL
            if config.base_url:
                if not config.base_url.startswith(('http://', 'https://')):
                    issues.append("Base URL must start with http:// or https://")
                
                # Additional URL validation using existing endpoint validator
                endpoint_validation = await self.validate_endpoint(config.base_url)
                if not endpoint_validation.passed:
                    issues.append(f"Base URL validation failed: {endpoint_validation.message}")

            # Validate rate limiting
            if config.rate_limit_calls <= 0:
                issues.append("Rate limit calls must be positive")
            if config.rate_limit_period <= 0:
                issues.append("Rate limit period must be positive")

            return ValidationResult(
                passed=len(issues) == 0,
                check_type='config',
                message="Configuration validation complete",
                details={
                    'issues': issues,
                    'auth_type': config.auth_type,
                    'has_base_url': bool(config.base_url),
                    'rate_limits': {
                        'calls': config.rate_limit_calls,
                        'period': config.rate_limit_period
                    }
                },
                severity=ValidationLevel.ERROR if issues else ValidationLevel.INFO
            )

        except Exception as e:
            logger.error(f"Config validation error: {str(e)}", exc_info=True)
            return ValidationResult(
                passed=False,
                check_type='config',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )