# backend/data/source/file/file_validator.py

import logging
import magic
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FileValidationConfig:
    """Configuration for file validation"""

    # Size limits
    max_file_size_mb: int = 100
    min_file_size_bytes: int = 1  # Non-empty files

    # Format settings
    allowed_formats: List[str] = field(default_factory=lambda: [
        'csv', 'xlsx', 'xls', 'json', 'parquet', 'txt'
    ])

    # MIME type mappings
    mime_types: Dict[str, List[str]] = field(default_factory=lambda: {
        'csv': ['text/csv', 'text/plain'],
        'xlsx': [
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-excel'
        ],
        'xls': ['application/vnd.ms-excel'],
        'json': ['application/json', 'text/plain'],
        'parquet': ['application/octet-stream'],
        'txt': ['text/plain']
    })

    # Security settings
    blocked_patterns: List[str] = field(default_factory=lambda: [
        r'password', r'secret', r'key', r'token', r'credential'
    ])

    scan_viruses: bool = True
    scan_encoding: bool = True


class FileValidator:
    """Enhanced file validator with integrated config"""

    def __init__(self, config: Optional[FileValidationConfig] = None):
        self.config = config or FileValidationConfig()

    async def validate_file_source(
            self,
            file_path: Path,
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate file source with comprehensive checks"""
        try:
            issues = []
            warnings = []

            # Basic checks
            if not file_path.exists():
                issues.append("File does not exist")
                return self._build_result(False, issues, warnings)

            # Size validation
            size_validation = await self._validate_size(file_path)
            issues.extend(size_validation.get('issues', []))
            warnings.extend(size_validation.get('warnings', []))

            # Format validation
            format_validation = await self._validate_format(
                file_path,
                metadata.get('content_type')
            )
            issues.extend(format_validation.get('issues', []))
            warnings.extend(format_validation.get('warnings', []))

            # Security validation
            security_validation = await self._validate_security(file_path, metadata)
            issues.extend(security_validation.get('issues', []))
            warnings.extend(security_validation.get('warnings', []))

            return self._build_result(len(issues) == 0, issues, warnings)

        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return self._build_result(False, [str(e)], [])

    async def _validate_size(self, file_path: Path) -> Dict[str, Any]:
        """Validate file size constraints"""
        issues = []
        warnings = []

        try:
            size_bytes = file_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)

            if size_bytes < self.config.min_file_size_bytes:
                issues.append("File is empty")

            if size_mb > self.config.max_file_size_mb:
                issues.append(
                    f"File size ({size_mb:.2f}MB) exceeds limit "
                    f"({self.config.max_file_size_mb}MB)"
                )

            if size_mb > self.config.max_file_size_mb * 0.9:
                warnings.append("File size approaching limit")

            return {'issues': issues, 'warnings': warnings}

        except Exception as e:
            logger.error(f"Size validation error: {str(e)}")
            return {'issues': [str(e)], 'warnings': []}

    async def _validate_format(
            self,
            file_path: Path,
            content_type: Optional[str]
    ) -> Dict[str, Any]:
        """Validate file format and content type"""
        issues = []
        warnings = []

        try:
            # Extension check
            ext = file_path.suffix[1:].lower()
            if ext not in self.config.allowed_formats:
                issues.append(f"Unsupported file format: {ext}")

            # MIME type check
            detected_type = magic.from_file(str(file_path), mime=True)
            if content_type and detected_type != content_type:
                warnings.append(
                    f"Content type mismatch: declared {content_type}, "
                    f"detected {detected_type}"
                )

            # Validate against allowed MIME types
            allowed_mimes = self.config.mime_types.get(ext, [])
            if detected_type not in allowed_mimes:
                issues.append(f"Invalid content type for {ext}: {detected_type}")

            return {'issues': issues, 'warnings': warnings}

        except Exception as e:
            logger.error(f"Format validation error: {str(e)}")
            return {'issues': [str(e)], 'warnings': []}

    async def _validate_security(
            self,
            file_path: Path,
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate file security aspects"""
        issues = []
        warnings = []

        try:
            # Check filename patterns
            filename = metadata.get('filename', file_path.name)
            for pattern in self.config.blocked_patterns:
                if pattern.lower() in filename.lower():
                    issues.append(f"Filename contains blocked pattern: {pattern}")

            # Check file permissions
            if not os.access(file_path, os.R_OK):
                issues.append("File is not readable")

            if os.access(file_path, os.X_OK):
                warnings.append("File has execute permissions")

            return {'issues': issues, 'warnings': warnings}

        except Exception as e:
            logger.error(f"Security validation error: {str(e)}")
            return {'issues': [str(e)], 'warnings': []}

    def _build_result(
            self,
            passed: bool,
            issues: List[str],
            warnings: List[str]
    ) -> Dict[str, Any]:
        """Build structured validation result"""
        return {
            'passed': passed,
            'issues': issues,
            'warnings': warnings,
            'validation_time': datetime.utcnow().isoformat()
        }