from __future__ import annotations

import logging
import magic
import hashlib
import asyncio
import re
from typing import Dict, Any, Tuple, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import pandas as pd
import aiofiles

from backend.core.monitoring.collectors import MetricsCollector
from .file_config import Config

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
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


class FileValidator:
    """Enhanced file validator with comprehensive validation capabilities"""

    def __init__(
            self,
            config: Optional[Config] = None,
            metrics_collector: Optional[MetricsCollector] = None,
    ):
        """Initialize validator with configurable components"""
        self.config = config or Config()
        self.metrics_collector = metrics_collector or MetricsCollector()

        # Validation thresholds - can be overridden via config
        self.validation_thresholds = {
            'max_columns': self.config.MAX_COLUMNS,
            'max_null_percentage': self.config.MAX_NULL_PERCENTAGE,
            'min_rows': self.config.MIN_ROWS,
            'suspicious_patterns': self.config.SUSPICIOUS_PATTERNS
        }

        # MIME type mappings - can be extended via config
        self.mime_mappings = self.config.MIME_MAPPINGS or {
            'csv': ['text/csv', 'text/plain'],
            'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
            'xls': ['application/vnd.ms-excel'],
            'parquet': ['application/octet-stream'],
            'json': ['application/json', 'text/plain']
        }

    async def validate_file_comprehensive(
            self,
            file_path: str,
            metadata: Dict[str, Any],
            validation_level: ValidationLevel = ValidationLevel.ERROR
    ) -> Dict[str, Any]:
        """
        Perform comprehensive file validation

        Args:
            file_path: Path to the file
            metadata: File metadata
            validation_level: Level of validation to perform

        Returns:
            Dictionary containing validation results
        """
        try:
            validation_start = datetime.now()
            results = []

            # Execute validations concurrently
            validation_tasks = [
                self.validate_file_format(file_path, metadata),
                self.validate_file_size(file_path, metadata),
                self.validate_security(file_path, metadata)
            ]

            # Add data quality check for data files
            if metadata.get('format') in ['csv', 'xlsx', 'parquet']:
                validation_tasks.append(self.validate_data_quality(file_path, metadata))

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

            # Record metrics if collector exists
            if self.metrics_collector:
                await self.metrics_collector.record_validation_metrics(
                    file_id=metadata.get('file_id'),
                    duration=(datetime.now() - validation_start).total_seconds(),
                    results=validation_summary
                )

            return validation_summary

        except Exception as e:
            logger.error(f"Comprehensive validation error: {str(e)}", exc_info=True)
            return {
                'passed': False,
                'error': str(e),
                'checks': [],
                'summary': {
                    'total_checks': 0,
                    'passed_checks': 0,
                    'failed_checks': 1,
                    'highest_severity': ValidationLevel.ERROR.value
                }
            }

    async def validate_file_format(
            self,
            file_path: str,
            metadata: Dict[str, Any]
    ) -> ValidationResult:
        """Validate file format and extension"""
        try:
            file_extension = metadata.get('extension', '').lower()
            allowed_formats = self.config.get('allowed_formats', ['csv', 'xlsx', 'parquet', 'json'])

            # Check extension
            if file_extension not in allowed_formats:
                return ValidationResult(
                    passed=False,
                    check_type='format',
                    message=f"Unsupported file format: {file_extension}",
                    details={
                        'extension': file_extension,
                        'allowed_formats': allowed_formats
                    }
                )

            # Check MIME type
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read(8192)  # Read first 8KB
                mime_type = magic.from_buffer(content, mime=True)

                if not self._validate_mime_type(mime_type, file_extension):
                    return ValidationResult(
                        passed=False,
                        check_type='format',
                        message=f"MIME type mismatch: {mime_type}",
                        details={
                            'mime_type': mime_type,
                            'extension': file_extension
                        }
                    )

            return ValidationResult(
                passed=True,
                check_type='format',
                message="File format validation passed",
                details={
                    'mime_type': mime_type,
                    'extension': file_extension
                }
            )

        except Exception as e:
            raise ValueError(f"Format validation error: {str(e)}")

    async def validate_file_size(
            self,
            file_path: str,
            metadata: Dict[str, Any]
    ) -> ValidationResult:
        """Validate file size constraints"""
        try:
            file_size = metadata.get('file_size', 0)
            max_size = self.config.get('max_file_size_mb', 50) * 1024 * 1024

            if file_size > max_size:
                return ValidationResult(
                    passed=False,
                    check_type='size',
                    message=f"File size exceeds limit of {max_size / (1024 * 1024)}MB",
                    details={
                        'file_size': file_size,
                        'max_size': max_size
                    }
                )

            return ValidationResult(
                passed=True,
                check_type='size',
                message="File size validation passed",
                details={
                    'file_size': file_size,
                    'max_size': max_size
                }
            )

        except Exception as e:
            raise ValueError(f"Size validation error: {str(e)}")

    async def validate_security(
            self,
            file_path: str,
            metadata: Dict[str, Any]
    ) -> ValidationResult:
        """Perform security validation"""
        try:
            # Calculate file hash
            async with aiofiles.open(file_path, 'rb') as f:
                content = await f.read()
                file_hash = hashlib.sha256(content).hexdigest()

            # Check for sensitive patterns
            if await self._check_sensitive_patterns(content):
                return ValidationResult(
                    passed=False,
                    check_type='security',
                    message="Sensitive data patterns detected",
                    details={'file_hash': file_hash},
                    severity=ValidationLevel.WARNING
                )

            return ValidationResult(
                passed=True,
                check_type='security',
                message="Security validation passed",
                details={'file_hash': file_hash}
            )

        except Exception as e:
            raise ValueError(f"Security validation error: {str(e)}")

    async def validate_data_quality(
            self,
            file_path: str,
            metadata: Dict[str, Any]
    ) -> ValidationResult:
        """Validate data quality metrics"""
        try:
            # Read file into DataFrame
            df = await self._read_dataframe(file_path, metadata)

            # Calculate quality metrics
            quality_metrics = {
                'row_count': len(df),
                'column_count': len(df.columns),
                'null_percentages': df.isnull().mean().to_dict(),
                'duplicate_rows': df.duplicated().sum(),
                'unique_values': {col: df[col].nunique() for col in df.columns}
            }

            # Check against thresholds
            quality_issues = []

            if quality_metrics['row_count'] < self.validation_thresholds['min_rows']:
                quality_issues.append("Insufficient data rows")

            if quality_metrics['column_count'] > self.validation_thresholds['max_columns']:
                quality_issues.append("Excessive number of columns")

            for col, null_pct in quality_metrics['null_percentages'].items():
                if null_pct * 100 > self.validation_thresholds['max_null_percentage']:
                    quality_issues.append(f"High null percentage in column {col}")

            if quality_issues:
                return ValidationResult(
                    passed=False,
                    check_type='quality',
                    message="Data quality issues detected",
                    details={
                        'issues': quality_issues,
                        'metrics': quality_metrics
                    }
                )

            return ValidationResult(
                passed=True,
                check_type='quality',
                message="Data quality validation passed",
                details={'metrics': quality_metrics}
            )

        except Exception as e:
            raise ValueError(f"Quality validation error: {str(e)}")

    async def _read_dataframe(
            self,
            file_path: str,
            metadata: Dict[str, Any]
    ) -> pd.DataFrame:
        """Read file into DataFrame based on format"""
        file_format = metadata.get('format', '').lower()

        if file_format == 'csv':
            return pd.read_csv(file_path)
        elif file_format in ['xlsx', 'xls']:
            return pd.read_excel(file_path)
        elif file_format == 'parquet':
            return pd.read_parquet(file_path)
        else:
            raise ValueError(f"Unsupported format for DataFrame: {file_format}")

    def _validate_mime_type(self, mime_type: str, extension: str) -> bool:
        """Validate MIME type matches extension"""
        return mime_type in self.mime_mappings.get(extension, [])

    async def _check_sensitive_patterns(self, content: bytes) -> bool:
        """Check for sensitive data patterns"""
        import re
        content_str = content.decode('utf-8', errors='ignore')
        return any(
            re.search(pattern, content_str)
            for pattern in self.validation_thresholds['suspicious_patterns']
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