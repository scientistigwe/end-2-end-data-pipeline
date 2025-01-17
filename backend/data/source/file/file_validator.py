from __future__ import annotations

import asyncio
import logging
import os
import re
import magic
import hashlib
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from backend.core.monitoring.collectors import MetricsCollector

logger = logging.getLogger(__name__)

class ValidationLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class FileSourceConfig:
    """Configuration for file data source validation"""
    # Allowed file formats and extensions
    ALLOWED_FORMATS: List[str] = field(default_factory=lambda: [
        'csv', 'xlsx', 'xls', 'json', 'parquet', 'txt'
    ])

    # Allowed MIME types for each format
    MIME_TYPES: Dict[str, List[str]] = field(default_factory=lambda: {
        'csv': ['text/csv', 'text/plain', 'application/csv'],
        'xlsx': [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel.sheet.macroEnabled.12',
            'application/vnd.ms-excel'
        ],
        'xls': ['application/vnd.ms-excel'],
        'json': ['application/json', 'text/plain'],
        'parquet': ['application/octet-stream'],
        'txt': ['text/plain']
    })

    # Maximum file size (in MB)
    MAX_FILE_SIZE_MB: int = 100

    # Sensitive file name patterns to block
    BLOCKED_FILENAME_PATTERNS: List[str] = field(default_factory=lambda: [
        r'password', r'secret', r'credentials', r'key', r'token'
    ])

    # Allowed file name characters
    FILENAME_REGEX: str = r'^[a-zA-Z0-9_\-\.]+\.[a-zA-Z0-9]+$'

@dataclass
class ValidationResult:
    """Structured validation result for file source"""
    passed: bool
    check_type: str
    message: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    severity: ValidationLevel = ValidationLevel.ERROR

class FileSourceValidator:
    """
    Validator for file data source attributes
    Focuses on source-level validation without parsing internal data
    """
    def __init__(
        self, 
        config: Optional[FileSourceConfig] = None,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        """
        Initialize validator with configuration and optional metrics collector
        
        Args:
            config: Optional configuration for file source validation
            metrics_collector: Optional metrics collector
        """
        self.config = config or FileSourceConfig()
        self.metrics_collector = metrics_collector

    async def validate_file_source(
        self, 
        file_path: str, 
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform comprehensive file source validation
        
        Args:
            file_path: Path to the file
            metadata: File metadata dictionary
        
        Returns:
            Comprehensive validation results
        """
        try:
            validation_start = datetime.now()
            
            # Execute validations
            validation_tasks = [
                self.validate_file_extension(file_path, metadata),
                self.validate_file_size(file_path, metadata),
                self.validate_file_name(metadata.get('filename', '')),
                self.validate_mime_type(file_path, metadata)
            ]
            
            # Gather results
            results = await asyncio.gather(*validation_tasks, return_exceptions=True)
            
            # Process results
            processed_results = []
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append(ValidationResult(
                        passed=False,
                        check_type='error',
                        message=f"Validation error: {str(result)}",
                        details={'error': str(result)},
                        severity=ValidationLevel.CRITICAL
                    ))
                elif isinstance(result, ValidationResult):
                    processed_results.append(result)
            
            # Compile validation summary
            validation_summary = self._compile_validation_results(processed_results)

            # Record validation metrics if collector exists
            if self.metrics_collector:
                await self.metrics_collector.record_validation_metrics(
                    source_type='file',
                    validation_results=validation_summary,
                    duration=(datetime.now() - validation_start).total_seconds()
                )

            return validation_summary
        
        except Exception as e:
            logger.error(f"Comprehensive file source validation error: {str(e)}", exc_info=True)
            
            # Record error metrics if collector exists
            if self.metrics_collector:
                await self.metrics_collector.record_validation_error(
                    source_type='file',
                    error=str(e)
                )
            
            return {
                'passed': False,
                'error': str(e),
                'checks': [],
                'summary': {
                    'total_checks': 0,
                    'passed_checks': 0,
                    'failed_checks': 1,
                    'highest_severity': ValidationLevel.CRITICAL.value
                }
            }

    # ... [rest of the methods remain the same as in the previous implementation]

    def _compile_validation_results(
        self, 
        results: List[ValidationResult]
    ) -> Dict[str, Any]:
        """
        Compile validation results into a summary
        
        Args:
            results: List of validation results
        
        Returns:
            Comprehensive validation summary
        """
        # Base implementation remains the same as before
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

    async def share_validation_report(
        self, 
        validation_results: Dict[str, Any], 
        file_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Share validation report with additional processing
        
        Args:
            validation_results: Validation results to share
            file_id: Optional file identifier
        
        Returns:
            Processed validation report
        """
        try:
            # Enrich validation report with additional metadata
            enriched_report = {
                'id': file_id or str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'validation': validation_results
            }

            # Optionally push to metrics or logging
            if self.metrics_collector:
                await self.metrics_collector.log_validation_report(
                    source_type='file',
                    report=enriched_report
                )

            return enriched_report

        except Exception as e:
            logger.error(f"Error sharing validation report: {str(e)}", exc_info=True)
            return {
                'error': str(e),
                'validation': validation_results
            }