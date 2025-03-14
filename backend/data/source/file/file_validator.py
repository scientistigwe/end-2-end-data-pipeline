# backend/data/source/file/file_validator.py

import logging
import mimetypes
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from datetime import datetime

from config.validation_config import FileValidationConfig

logger = logging.getLogger(__name__)


class FileValidator:
    """Enhanced file validator without magic dependency"""

    def __init__(self, config: Optional[FileValidationConfig] = None):
        self.config = config or FileValidationConfig()
        # Initialize mimetypes database
        mimetypes.init()

        # Define allowed file types that match frontend mapping
        self.allowed_file_types = {'csv', 'excel', 'json', 'parquet'}

        # Mapping of file extensions to expected file types (should match frontend)
        self.extension_to_type_map = {
            'csv': 'csv',
            'xlsx': 'excel',
            'xls': 'excel',
            'json': 'json',
            'parquet': 'parquet',
            'txt': 'csv'  # Default txt files to CSV
        }

        # Map file types to their allowed extensions (reverse of above)
        self.file_type_map = {
            'csv': ['csv', 'txt'],
            'excel': ['xlsx', 'xls'],
            'json': ['json'],
            'parquet': ['parquet']
        }

    async def validate_file_source(
            self,
            filename: str,
            metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate file source with flexible metadata handling"""
        try:
            issues = []
            warnings = []

            # Log incoming data for debugging
            logger.debug(f"Validating file: {filename}")
            logger.debug(f"Metadata: {metadata}")

            # Validate filename
            if not filename:
                issues.append("Filename is required")
                return self._build_result(False, issues, warnings)

            # Extract and validate file extension
            ext = Path(filename).suffix[1:].lower()
            if not ext:
                warnings.append("File has no extension")
                # Treat as CSV by default if no extension
                ext = 'csv'

            # Get expected file type from extension
            expected_type = self.extension_to_type_map.get(ext)
            if not expected_type:
                warnings.append(f"Unsupported file extension: {ext}")
                # Default to csv for unknown extensions
                expected_type = 'csv'

            # Validate file type from metadata
            file_type = metadata.get('file_type')
            if not file_type:
                issues.append("File type is required in metadata")
                return self._build_result(False, issues, warnings)

            # Check file type is supported
            if file_type not in self.allowed_file_types:
                issues.append(f"Unsupported file type: {file_type}")
                return self._build_result(False, issues, warnings)

            # More relaxed extension validation - allow any recognized extension
            # that maps to the specified file type
            valid_extensions = self.file_type_map.get(file_type, [])
            if ext not in valid_extensions:
                # Just warn about mismatches instead of failing
                warnings.append(f"File extension ({ext}) doesn't match declared type ({file_type})")

            # Validate specific metadata fields based on file type
            if file_type == 'excel':
                # Validate sheet name if provided
                sheet_name = metadata.get('sheet_name')
                if not sheet_name:
                    metadata['sheet_name'] = 'Sheet1'  # Default sheet name
                    warnings.append("No sheet name specified, using 'Sheet1'")

            elif file_type == 'csv':
                # Validate delimiter
                delimiter = metadata.get('delimiter')
                if not delimiter:
                    metadata['delimiter'] = ','  # Default delimiter
                    warnings.append("No delimiter specified, using comma (,)")
                elif delimiter not in [',', ';', '\t', '|']:
                    warnings.append(f"Unusual delimiter: {delimiter}")

            # Encoding validation (be more permissive)
            encoding = metadata.get('encoding', 'utf-8')
            common_encodings = ['utf-8', 'utf-16', 'windows-1252', 'ascii', 'ISO-8859-1', 'latin-1']
            if encoding.lower() not in [enc.lower() for enc in common_encodings]:
                warnings.append(f"Unusual encoding detected: {encoding}")
                # Don't fail on unusual encodings, just warn

            # Parse options validation
            parse_options = metadata.get('parse_options', {})
            if parse_options:
                # Validate date format
                date_format = parse_options.get('date_format')
                if date_format and not self._is_valid_date_format(date_format):
                    warnings.append(f"Unusual date format: {date_format}")
                    # Set default if invalid
                    parse_options['date_format'] = 'YYYY-MM-DD'

                # Validate null values
                null_values = parse_options.get('null_values')
                if null_values:
                    if not isinstance(null_values, list):
                        warnings.append("Null values should be a list")
                        # Convert to list if not already
                        parse_options['null_values'] = [str(null_values)]

            # Tags validation
            tags = metadata.get('tags', [])
            if not isinstance(tags, list):
                warnings.append("Tags should be a list")
                # Convert to list if not already
                metadata['tags'] = [str(tags)]

            # If we have warnings but no blocking issues, log them
            if warnings and not issues:
                logger.info(f"File validation passed with warnings: {warnings}")

            return self._build_result(len(issues) == 0, issues, warnings)

        except Exception as e:
            error_msg = f"File validation error: {str(e)}"
            logger.error(f"{error_msg}, filename: {filename}, metadata: {metadata}", exc_info=True)
            return self._build_result(False, [error_msg], [])

    def _is_valid_date_format(self, date_format: str) -> bool:
        """
        Basic validation of date format
        Extended to support more formats
        """
        valid_formats = [
            'YYYY-MM-DD', 'MM/DD/YYYY', 'DD-MM-YYYY',
            'YYYY/MM/DD', 'DD/MM/YYYY', 'MM-DD-YYYY',
            'YYYY.MM.DD', 'DD.MM.YYYY', 'MM.DD.YYYY'
        ]
        return date_format in valid_formats

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
                warnings.append(f"Unsupported file format: {ext}")
                # Don't block upload just because of extension

            # Validate content type (be more permissive)
            if content_type:
                allowed_mimes = self.config.mime_types.get(ext, [])
                # Handle common mismatches (e.g., text/csv vs text/plain)
                if content_type not in allowed_mimes:
                    if ext == 'csv' and content_type == 'text/plain':
                        # This is acceptable for CSV
                        pass
                    else:
                        warnings.append(f"Content type mismatch: {content_type} for .{ext} file")

            return {'issues': issues, 'warnings': warnings}

        except Exception as e:
            logger.error(f"Format validation error: {str(e)}")
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

    # Other validation methods remain unchanged...

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
