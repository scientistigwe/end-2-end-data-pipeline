# backend/source_handlers/file/file_validator.py

import logging
from typing import Dict, Any
from pathlib import Path
import magic
import os
from backend.core.utils.encryption import AESEncryption

logger = logging.getLogger(__name__)


class FileValidator:
    """Validates file source integrity"""

    def __init__(self):
        self.encryption = AESEncryption()

        # File source validation settings
        self.max_file_size = 1024 * 1024 * 1024  # 1GB
        self.allowed_extensions = {
            '.csv', '.json', '.xlsx', '.xls', '.txt',
            '.parquet', '.xml', '.yaml', '.yml'
        }
        self.blocked_extensions = {
            '.exe', '.dll', '.bat', '.cmd', '.sh',
            '.js', '.vbs', '.ps1'
        }

    async def validate_file_source(
            self,
            file_path: Path,
            original_filename: str,
            content_type: str = None
    ) -> Dict[str, Any]:
        """
        Validate file source integrity
        Only validates file-level attributes, not data content
        """
        issues = []
        warnings = []

        try:
            # Check if file exists
            if not file_path.exists():
                return {
                    'passed': False,
                    'issues': ['File does not exist'],
                    'warnings': []
                }

            # Check file size
            file_size = file_path.stat().st_size
            if file_size > self.max_file_size:
                issues.append(f'File size exceeds maximum allowed ({self.max_file_size} bytes)')

            # Validate extension
            ext = Path(original_filename).suffix.lower()
            if ext in self.blocked_extensions:
                issues.append(f'File type not allowed: {ext}')
            elif ext not in self.allowed_extensions:
                warnings.append(f'Unusual file extension: {ext}')

            # Verify file is not empty
            if file_size == 0:
                issues.append('File is empty')

            # Basic content type verification
            detected_type = magic.from_file(str(file_path), mime=True)
            if content_type and detected_type != content_type:
                warnings.append(f'Content type mismatch: declared {content_type}, detected {detected_type}')

            # File permission check
            if not os.access(file_path, os.R_OK):
                issues.append('File is not readable')

            return {
                'passed': len(issues) == 0,
                'issues': issues,
                'warnings': warnings,
                'metadata': {
                    'size': file_size,
                    'detected_type': detected_type,
                    'extension': ext
                }
            }

        except Exception as e:
            logger.error(f"File validation error: {str(e)}")
            return {
                'passed': False,
                'issues': [str(e)],
                'warnings': []
            }

