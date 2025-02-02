# backend/source_handlers/s3/s3_validator.py

import logging
import re
from typing import Dict, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from config.validation_config import S3ValidationConfig

logger = logging.getLogger(__name__)


class S3Validator:
    """Enhanced S3 source validator with integrated config"""

    def __init__(self, config: Optional[S3ValidationConfig] = None):
        self.config = config or S3ValidationConfig()

    async def validate_s3_source(
            self,
            source_data: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive validation of S3 source configuration

        Args:
            source_data: Dictionary containing S3 source details
            metadata: Optional additional metadata

        Returns:
            Validation result with issues and warnings
        """
        try:
            issues = []
            warnings = []

            # Validate bucket
            bucket_validation = await self._validate_bucket(
                source_data.get('bucket', '')
            )
            issues.extend(bucket_validation.get('issues', []))
            warnings.extend(bucket_validation.get('warnings', []))

            # Validate credentials
            if 'credentials' in source_data:
                cred_validation = await self._validate_credentials(
                    source_data['credentials']
                )
                issues.extend(cred_validation.get('issues', []))
                warnings.extend(cred_validation.get('warnings', []))

            # Validate region
            region_validation = await self._validate_region(
                source_data.get('region', '')
            )
            issues.extend(region_validation.get('issues', []))
            warnings.extend(region_validation.get('warnings', []))

            # Validate endpoint
            endpoint_validation = await self._validate_endpoint(
                source_data.get('endpoint', '')
            )
            issues.extend(endpoint_validation.get('issues', []))
            warnings.extend(endpoint_validation.get('warnings', []))

            return self._build_result(
                passed=len(issues) == 0,
                issues=issues,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"S3 source validation error: {str(e)}")
            return self._build_result(
                passed=False,
                issues=[str(e)],
                warnings=[]
            )

    async def _validate_bucket(self, bucket: str) -> Dict[str, Any]:
        """Validate S3 bucket name"""
        issues = []
        warnings = []

        # Check for empty bucket
        if not bucket:
            issues.append("Bucket name is required")
            return {'issues': issues, 'warnings': warnings}

        # Length validation
        if len(bucket) > self.config.max_bucket_name_length:
            issues.append(f"Bucket name exceeds {self.config.max_bucket_name_length} characters")

        if len(bucket) < self.config.min_bucket_name_length:
            issues.append(f"Bucket name must be at least {self.config.min_bucket_name_length} characters")

        # Character validation
        if not re.match(self.config.allowed_bucket_chars, bucket):
            issues.append("Invalid characters in bucket name")

        # Additional S3-specific checks
        if bucket.startswith('.') or bucket.startswith('-'):
            issues.append("Bucket name cannot start with dots or hyphens")

        if '..' in bucket:
            issues.append("Bucket name cannot contain consecutive dots")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_credentials(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Validate AWS S3 credentials"""
        issues = []
        warnings = []

        # Check for required credential fields
        required_fields = ['aws_access_key_id', 'aws_secret_access_key']
        for field in required_fields:
            if field not in credentials:
                issues.append(f"Missing required credential: {field}")

        # Check for sensitive information in credentials
        for key in credentials:
            if any(re.search(pattern, key, re.IGNORECASE) for pattern in self.config.blocked_patterns):
                warnings.append(f"Potentially sensitive credential key: {key}")

        # Optionally, attempt to validate credentials
        if not issues:
            try:
                session = boto3.Session(
                    aws_access_key_id=credentials['aws_access_key_id'],
                    aws_secret_access_key=credentials['aws_secret_access_key']
                )
                s3_client = session.client('s3')
                s3_client.list_buckets()
            except ClientError as e:
                issues.append(f"Credential validation failed: {e}")
            except Exception as e:
                issues.append(f"Unexpected credential validation error: {e}")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_region(self, region: str) -> Dict[str, Any]:
        """Validate AWS region"""
        issues = []
        warnings = []

        # Check for empty region
        if not region:
            warnings.append("No region specified, using default")
            return {'issues': issues, 'warnings': warnings}

        # Region validation
        if region not in self.config.allowed_regions:
            issues.append(f"Invalid region: {region}")
            issues.append(f"Allowed regions: {', '.join(self.config.allowed_regions)}")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_endpoint(self, endpoint: str) -> Dict[str, Any]:
        """Validate S3 endpoint"""
        issues = []
        warnings = []

        # Optional endpoint
        if not endpoint:
            warnings.append("No custom endpoint specified, using default")
            return {'issues': issues, 'warnings': warnings}

        # Basic endpoint validation
        try:
            from urllib.parse import urlparse
            parsed = urlparse(endpoint)

            # Check scheme
            if parsed.scheme not in ['http', 'https']:
                issues.append(f"Invalid endpoint scheme: {parsed.scheme}")

            # Check hostname
            if not parsed.hostname:
                issues.append("Endpoint is missing hostname")

        except Exception as e:
            issues.append(f"Endpoint parsing error: {str(e)}")

        return {
            'issues': issues,
            'warnings': warnings
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

    async def validate_s3_object(
            self,
            object_data: Dict[str, Any],
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Validate S3 object details"""
        try:
            issues = []
            warnings = []

            # Validate object key
            key_validation = await self._validate_object_key(
                object_data.get('key', '')
            )
            issues.extend(key_validation.get('issues', []))
            warnings.extend(key_validation.get('warnings', []))

            # Validate operation
            operation_validation = await self._validate_operation(
                object_data.get('operation', '')
            )
            issues.extend(operation_validation.get('issues', []))
            warnings.extend(operation_validation.get('warnings', []))

            return self._build_result(
                passed=len(issues) == 0,
                issues=issues,
                warnings=warnings
            )

        except Exception as e:
            logger.error(f"S3 object validation error: {str(e)}")
            return self._build_result(
                passed=False,
                issues=[str(e)],
                warnings=[]
            )

    async def _validate_object_key(self, key: str) -> Dict[str, Any]:
        """Validate S3 object key"""
        issues = []
        warnings = []

        # Check for empty key
        if not key:
            issues.append("Object key is required")
            return {'issues': issues, 'warnings': warnings}

        # Length validation
        if len(key) > self.config.max_key_length:
            issues.append(f"Object key exceeds {self.config.max_key_length} characters")

        # Character validation
        if not re.match(self.config.allowed_key_chars, key):
            issues.append("Invalid characters in object key")

        # Check for sensitive information in key
        if any(re.search(pattern, key, re.IGNORECASE) for pattern in self.config.blocked_patterns):
            warnings.append("Potential sensitive information in object key")

        return {
            'issues': issues,
            'warnings': warnings
        }

    async def _validate_operation(self, operation: str) -> Dict[str, Any]:
        """Validate S3 operation"""
        issues = []
        warnings = []

        # Check for empty operation
        if not operation:
            issues.append("Operation is required")
            return {'issues': issues, 'warnings': warnings}

        # Normalize operation
        operation = operation.lower()

        # Validate operation
        if operation not in self.config.allowed_operations:
            issues.append(f"Invalid operation: {operation}")
            issues.append(f"Allowed operations: {', '.join(self.config.allowed_operations)}")

        return {
            'issues': issues,
            'warnings': warnings
        }