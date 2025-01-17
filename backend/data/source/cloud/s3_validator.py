from __future__ import annotations

import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import boto3
from botocore.exceptions import ClientError

from backend.core.monitoring.process import ProcessMonitor
from backend.core.monitoring.collectors import MetricsCollector
from .s3_config import Config

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


class S3Validator:
    """Enhanced S3 validator with comprehensive validation capabilities"""

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
            source_type="s3_validator",
            source_id="validator"
        )

        # Validation thresholds
        self.validation_thresholds = {
            'max_key_length': 1024,
            'max_bucket_name_length': 63,
            'max_object_size': self.config.S3.MAX_FILE_SIZE,
            'max_multipart_size': self.config.S3.MULTIPART_THRESHOLD
        }

    async def validate_connection_comprehensive(
            self,
            connection_data: Dict[str, Any],
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive connection validation

        Args:
            connection_data: Connection configuration to validate
            metadata: Additional metadata for validation

        Returns:
            Dictionary containing validation results
        """
        try:
            validation_start = datetime.now()
            results = []

            # Execute validations concurrently
            validation_tasks = [
                self.validate_credentials(connection_data.get('credentials', {})),
                self.validate_region(connection_data.get('region')),
                self.validate_bucket_name(connection_data.get('bucket')),
                self.validate_endpoint(connection_data.get('endpoint'))
            ]

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
                'connection_validation',
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

    async def validate_credentials(
            self,
            credentials: Dict[str, Any]
    ) -> ValidationResult:
        """Validate AWS credentials"""
        try:
            if not credentials:
                return ValidationResult(
                    passed=False,
                    check_type='credentials',
                    message="Credentials are required",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            required_fields = ['aws_access_key_id', 'aws_secret_access_key']
            missing_fields = [
                field for field in required_fields
                if field not in credentials
            ]

            if missing_fields:
                return ValidationResult(
                    passed=False,
                    check_type='credentials',
                    message=f"Missing required credentials: {', '.join(missing_fields)}",
                    details={'missing_fields': missing_fields},
                    severity=ValidationLevel.ERROR
                )

            # Test credentials
            session = boto3.Session(
                aws_access_key_id=credentials['aws_access_key_id'],
                aws_secret_access_key=credentials['aws_secret_access_key']
            )

            s3 = session.client('s3')
            s3.list_buckets()

            return ValidationResult(
                passed=True,
                check_type='credentials',
                message="Credentials validated successfully",
                details={'permissions': ['list_buckets']},
                severity=ValidationLevel.INFO
            )

        except ClientError as e:
            error_code = e.response['Error']['Code']
            return ValidationResult(
                passed=False,
                check_type='credentials',
                message=f"Credential validation failed: {error_code}",
                details={'error_code': error_code},
                severity=ValidationLevel.ERROR
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='credentials',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_region(
            self,
            region: Optional[str]
    ) -> ValidationResult:
        """Validate AWS region"""
        try:
            if not region:
                region = self.config.DEFAULT_REGION

            if region not in self.config.AWS_ENDPOINTS:
                return ValidationResult(
                    passed=False,
                    check_type='region',
                    message=f"Invalid region: {region}",
                    details={
                        'region': region,
                        'valid_regions': list(self.config.AWS_ENDPOINTS.keys())
                    },
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='region',
                message="Region is valid",
                details={
                    'region': region,
                    'endpoint': self.config.AWS_ENDPOINTS[region]
                },
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='region',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_bucket_name(
            self,
            bucket: Optional[str]
    ) -> ValidationResult:
        """Validate S3 bucket name"""
        try:
            if not bucket:
                return ValidationResult(
                    passed=False,
                    check_type='bucket',
                    message="Bucket name is required",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            issues = []

            # Length check
            if len(bucket) > self.validation_thresholds['max_bucket_name_length']:
                issues.append("Bucket name too long")

            # Format check
            if not bucket.islower():
                issues.append("Bucket name must be lowercase")

            if not bucket.isalnum() and not all(c in '.-' for c in bucket if not c.isalnum()):
                issues.append("Invalid characters in bucket name")

            if bucket.startswith('.') or bucket.startswith('-'):
                issues.append("Bucket name cannot start with dots or hyphens")

            if issues:
                return ValidationResult(
                    passed=False,
                    check_type='bucket',
                    message="Invalid bucket name",
                    details={'issues': issues},
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='bucket',
                message="Bucket name is valid",
                details={'bucket': bucket},
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='bucket',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_endpoint(
            self,
            endpoint: Optional[str]
    ) -> ValidationResult:
        """Validate S3 endpoint"""
        try:
            if not endpoint:
                return ValidationResult(
                    passed=True,
                    check_type='endpoint',
                    message="Using default endpoint",
                    details={'endpoint': 's3.amazonaws.com'},
                    severity=ValidationLevel.INFO
                )

            # Validate endpoint format
            import re
            endpoint_pattern = r'^s3[.-]([a-z0-9-]+\.)?amazonaws\.com$'
            if not re.match(endpoint_pattern, endpoint):
                return ValidationResult(
                    passed=False,
                    check_type='endpoint',
                    message="Invalid endpoint format",
                    details={'endpoint': endpoint},
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='endpoint',
                message="Endpoint is valid",
                details={'endpoint': endpoint},
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='endpoint',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_object_request(
            self,
            request_data: Dict[str, Any],
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate object request parameters"""
        try:
            validation_start = datetime.now()
            results = []

            validation_tasks = [
                self.validate_object_key(request_data.get('key')),
                self.validate_operation(request_data.get('operation')),
                self.validate_request_parameters(request_data.get('parameters', {}))
            ]

            results.extend(await asyncio.gather(*validation_tasks, return_exceptions=True))

            validation_summary = self._compile_validation_results(results)

            await self.process_monitor.record_operation_metric(
                'object_request_validation',
                success=validation_summary['passed'],
                duration=(datetime.now() - validation_start).total_seconds()
            )

            return validation_summary

        except Exception as e:
            logger.error(f"Object request validation error: {str(e)}")
            return {
                'passed': False,
                'error': str(e),
                'checks': []
            }

    async def validate_object_key(
            self,
            key: Optional[str]
    ) -> ValidationResult:
        """Validate S3 object key"""
        try:
            if not key:
                return ValidationResult(
                    passed=False,
                    check_type='key',
                    message="Object key is required",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            issues = []

            # Length check
            if len(key) > self.validation_thresholds['max_key_length']:
                issues.append("Object key too long")

            # Format check
            if key.startswith('/'):
                issues.append("Object key cannot start with forward slash")

            # Special characters check
            invalid_chars = set('&$@=;:+ ,\\{}^%`[]\'"><~#|')
            if any(c in invalid_chars for c in key):
                issues.append("Invalid characters in object key")

            if issues:
                return ValidationResult(
                    passed=False,
                    check_type='key',
                    message="Invalid object key",
                    details={'issues': issues},
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='key',
                message="Object key is valid",
                details={'key': key},
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='key',
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

    async def validate_operation(
            self,
            operation: Optional[str]
    ) -> ValidationResult:
        """Validate S3 operation type"""
        try:
            if not operation:
                return ValidationResult(
                    passed=False,
                    check_type='operation',
                    message="Operation type is required",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            valid_operations = ['get', 'put', 'delete', 'list', 'head']

            if operation.lower() not in valid_operations:
                return ValidationResult(
                    passed=False,
                    check_type='operation',
                    message=f"Invalid operation: {operation}",
                    details={
                        'operation': operation,
                        'valid_operations': valid_operations
                    },
                    severity=ValidationLevel.ERROR
                )

            return ValidationResult(
                passed=True,
                check_type='operation',
                message="Operation is valid",
                details={'operation': operation},
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='operation',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_request_parameters(
            self,
            parameters: Dict[str, Any]
    ) -> ValidationResult:
        """Validate request parameters"""
        try:
            issues = []

            # Check for required parameters based on operation
            operation = parameters.get('operation', '').lower()
            if operation == 'get':
                if not parameters.get('range'):
                    issues.append("Range parameter recommended for large objects")
            elif operation == 'put':
                if not parameters.get('content_type'):
                    issues.append("Content-Type should be specified")
            elif operation == 'list':
                max_keys = parameters.get('max_keys', 1000)
                if max_keys > 1000:
                    issues.append("max_keys cannot exceed 1000")

            # Validate common parameters
            if parameters.get('expires_in'):
                try:
                    expires = int(parameters['expires_in'])
                    if expires > 604800:  # 7 days in seconds
                        issues.append("Expiration cannot exceed 7 days")
                except ValueError:
                    issues.append("expires_in must be an integer")

            severity = (
                ValidationLevel.WARNING if issues else ValidationLevel.INFO
            )

            return ValidationResult(
                passed=not any(i for i in issues if "must" in i or "cannot" in i),
                check_type='parameters',
                message="Parameter validation complete",
                details={'issues': issues},
                severity=severity
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='parameters',
                message=f"Validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_object_access(
            self,
            s3_client: Any,
            bucket: str,
            key: str
    ) -> ValidationResult:
        """Validate access to specific S3 object"""
        try:
            try:
                response = await self._check_object_access(s3_client, bucket, key)
                permissions = self._extract_permissions(response)

                return ValidationResult(
                    passed=True,
                    check_type='access',
                    message="Object access verified",
                    details={
                        'permissions': permissions,
                        'metadata': response.get('ResponseMetadata', {})
                    },
                    severity=ValidationLevel.INFO
                )

            except ClientError as e:
                error_code = e.response['Error']['Code']
                return ValidationResult(
                    passed=False,
                    check_type='access',
                    message=f"Access denied: {error_code}",
                    details={'error_code': error_code},
                    severity=ValidationLevel.ERROR
                )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='access',
                message=f"Access validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def validate_object_data(
            self,
            data: Dict[str, Any],
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate object data comprehensively"""
        try:
            validation_start = datetime.now()
            results = []

            # Content validation
            results.append(await self._validate_content(data))

            # Format-specific validation
            if format_type := metadata.get('content_type'):
                results.append(
                    await self._validate_format_specific(data, format_type)
                )

            # Size validation
            if size := metadata.get('size'):
                results.append(await self._validate_size(size))

            # Compile results
            validation_summary = self._compile_validation_results(results)

            # Record metrics
            await self.process_monitor.record_operation_metric(
                'object_data_validation',
                success=validation_summary['passed'],
                duration=(datetime.now() - validation_start).total_seconds(),
                size=size
            )

            # Add recommendations if needed
            validation_summary['recommendations'] = (
                self._generate_recommendations(validation_summary)
            )

            return validation_summary

        except Exception as e:
            logger.error(f"Object data validation error: {str(e)}")
            return {
                'passed': False,
                'error': str(e),
                'checks': []
            }

    async def _validate_content(
            self,
            data: Dict[str, Any]
    ) -> ValidationResult:
        """Validate object content"""
        try:
            issues = []

            # Check for empty content
            if not data:
                return ValidationResult(
                    passed=False,
                    check_type='content',
                    message="Empty object content",
                    details={},
                    severity=ValidationLevel.ERROR
                )

            # Check content structure
            if 'Body' not in data:
                issues.append("Missing object body")

            if 'Metadata' not in data:
                issues.append("Missing object metadata")

            severity = (
                ValidationLevel.WARNING if issues else ValidationLevel.INFO
            )

            return ValidationResult(
                passed=not any(i for i in issues if "Missing" in i),
                check_type='content',
                message="Content validation complete",
                details={'issues': issues},
                severity=severity
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='content',
                message=f"Content validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def _validate_format_specific(
            self,
            data: Dict[str, Any],
            content_type: str
    ) -> ValidationResult:
        """Validate format-specific requirements"""
        try:
            format_type = content_type.split('/')[-1].lower()

            if format_type not in self.config.SUPPORTED_FORMATS:
                return ValidationResult(
                    passed=False,
                    check_type='format',
                    message=f"Unsupported format: {format_type}",
                    details={'format': format_type},
                    severity=ValidationLevel.ERROR
                )

            # Format-specific checks
            if format_type == 'parquet':
                return await self._validate_parquet(data)
            elif format_type == 'csv':
                return await self._validate_csv(data)

            return ValidationResult(
                passed=True,
                check_type='format',
                message="Format validation passed",
                details={'format': format_type},
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='format',
                message=f"Format validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    async def _validate_size(self, size: int) -> ValidationResult:
        """Validate object size"""
        try:
            if size > self.validation_thresholds['max_object_size']:
                return ValidationResult(
                    passed=False,
                    check_type='size',
                    message="Object size exceeds maximum allowed",
                    details={
                        'size': size,
                        'max_size': self.validation_thresholds['max_object_size']
                    },
                    severity=ValidationLevel.ERROR
                )

            # Check if multipart recommended
            if size > self.validation_thresholds['max_multipart_size']:
                return ValidationResult(
                    passed=True,
                    check_type='size',
                    message="Multipart upload recommended",
                    details={'size': size},
                    severity=ValidationLevel.WARNING
                )

            return ValidationResult(
                passed=True,
                check_type='size',
                message="Size validation passed",
                details={'size': size},
                severity=ValidationLevel.INFO
            )

        except Exception as e:
            return ValidationResult(
                passed=False,
                check_type='size',
                message=f"Size validation error: {str(e)}",
                details={'error': str(e)},
                severity=ValidationLevel.ERROR
            )

    def _generate_recommendations(
            self,
            validation_summary: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on validation results"""
        recommendations = []

        # Check for warnings
        warnings = [
            check for check in validation_summary['checks']
            if check['severity'] == ValidationLevel.WARNING.value
        ]

        for warning in warnings:
            if warning['type'] == 'size':
                recommendations.append({
                    'type': 'optimization',
                    'message': 'Consider using multipart upload/download',
                    'details': warning['details']
                })
            elif warning['type'] == 'parameters':
                recommendations.append({
                    'type': 'configuration',
                    'message': 'Review parameter configurations',
                    'details': warning['details']
                })

        return recommendations

    async def _check_object_access(
            self,
            s3_client: Any,
            bucket: str,
            key: str
    ) -> Dict[str, Any]:
        """Check object accessibility"""
        try:
            return await s3_client.head_object(
                Bucket=bucket,
                Key=key
            )
        except Exception as e:
            raise

    def _extract_permissions(
            self,
            response: Dict[str, Any]
    ) -> List[str]:
        """Extract permissions from response"""
        permissions = []

        if acl := response.get('ACL'):
            for grant in acl.get('Grants', []):
                permissions.append(grant.get('Permission'))

        return permissions