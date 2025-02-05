# backend/data/source/file/file_validator.py

import logging
import mimetypes
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from config.validation_config import FileValidationConfig

logger = logging.getLogger(__name__)

class FileValidator:
    """Enhanced file validator without magic dependency"""

    def __init__(self, config: Optional[FileValidationConfig] = None):
        self.config = config or FileValidationConfig()
        # Initialize mimetypes database
        mimetypes.init()

    async def validate_file_source(
            self,
            filename: str,  # Change parameter name to be clearer
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate file source with comprehensive checks"""
        try:
            issues = []
            warnings = []

            # Validate filename without checking existence
            if not filename:
                issues.append("Filename is required")
                return self._build_result(False, issues, warnings)

            # Format validation
            format_validation = await self._validate_format_from_name(
                filename,
                metadata.get('content_type')
            )
            issues.extend(format_validation.get('issues', []))
            warnings.extend(format_validation.get('warnings', []))

            # Security validation for filename
            security_validation = await self._validate_filename_security(filename, metadata)
            issues.extend(security_validation.get('issues', []))
            warnings.extend(security_validation.get('warnings', []))

            return self._build_result(len(issues) == 0, issues, warnings)

        except Exception as e:
            logger.error(f"Validation error: {str(e)}", exc_info=True)
            return self._build_result(False, [str(e)], [])

    async def _validate_format_from_name(
            self,
            filename: str,
            content_type: Optional[str]
    ) -> Dict[str, Any]:
        """Validate file format using filename and content type"""
        issues = []
        warnings = []

        try:
            # Extension check
            ext = Path(filename).suffix[1:].lower()
            if ext not in self.config.allowed_formats:
                issues.append(f"Unsupported file format: {ext}")

            # Validate content type
            if content_type:
                allowed_mimes = self.config.mime_types.get(ext, [])
                if content_type not in allowed_mimes:
                    issues.append(f"Invalid content type for {ext}: {content_type}")

            return {'issues': issues, 'warnings': warnings}

        except Exception as e:
            logger.error(f"Format validation error: {str(e)}")
            return {'issues': [str(e)], 'warnings': []}

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
        """Validate file format using file signatures and extension"""
        issues = []
        warnings = []

        try:
            # Extension check
            ext = file_path.suffix[1:].lower()
            if ext not in self.config.allowed_formats:
                issues.append(f"Unsupported file format: {ext}")

            # Check file signature
            detected_type = self._detect_file_type(file_path, ext)
            declared_type = content_type or mimetypes.guess_type(str(file_path))[0]

            if detected_type != ext:
                warnings.append(
                    f"File signature mismatch: extension is {ext}, "
                    f"detected format is {detected_type}"
                )

            # Validate against allowed MIME types
            if declared_type:
                allowed_mimes = self.config.mime_types.get(ext, [])
                if declared_type not in allowed_mimes:
                    issues.append(f"Invalid content type for {ext}: {declared_type}")

            return {'issues': issues, 'warnings': warnings}

        except Exception as e:
            logger.error(f"Format validation error: {str(e)}")
            return {'issues': [str(e)], 'warnings': []}

    def _detect_file_type(self, file_path: Path, extension: str) -> str:
        """Detect file type using file signatures"""
        try:
            with open(file_path, 'rb') as f:
                header = f.read(16)  # Read first 16 bytes for signature checking

            # Check against known signatures
            for fmt, signatures in self.config.file_signatures.items():
                if not signatures:  # Skip formats without signatures
                    continue
                if any(header.startswith(sig) for sig in signatures):
                    return fmt

            # If no signature match, do basic text file detection
            if self._is_text_file(file_path):
                if extension == 'csv' and self._is_csv_file(file_path):
                    return 'csv'
                if extension == 'json' and self._is_json_file(file_path):
                    return 'json'
                return 'txt'

            return extension

        except Exception as e:
            logger.error(f"File type detection error: {str(e)}")
            return extension

    def _is_text_file(self, file_path: Path) -> bool:
        """Check if file is text based"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)  # Try to read as text
            return True
        except UnicodeDecodeError:
            return False

    def _is_csv_file(self, file_path: Path) -> bool:
        """Basic CSV detection"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                return ',' in first_line or ';' in first_line
        except:
            return False

    def _is_json_file(self, file_path: Path) -> bool:
        """Basic JSON detection"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_char = f.read(1).strip()
                return first_char in '{['
        except:
            return False

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

    async def _validate_filename_security(
            self,
            filename: str,
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate filename for security concerns

        Args:
            filename: Name of the file to validate
            metadata: Additional metadata about the file

        Returns:
            Dict containing validation issues and warnings
        """
        issues = []
        warnings = []

        try:
            # Check filename patterns
            for pattern in self.config.blocked_patterns:
                if pattern.lower() in filename.lower():
                    issues.append(f"Filename contains blocked pattern: {pattern}")

            # Check filename length
            if len(filename) > 255:
                issues.append("Filename is too long (max 255 characters)")

            # Check for dangerous characters
            dangerous_chars = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
            for char in dangerous_chars:
                if char in filename:
                    issues.append(f"Filename contains invalid character: {char}")

            # Check file extension
            ext = Path(filename).suffix.lower()
            if not ext:
                warnings.append("File has no extension")
            elif ext[1:] not in self.config.allowed_formats:
                issues.append(f"Unsupported file extension: {ext}")

            return {'issues': issues, 'warnings': warnings}

        except Exception as e:
            logger.error(f"Security validation error: {str(e)}")
            return {'issues': [str(e)], 'warnings': []}