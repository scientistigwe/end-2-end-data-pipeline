# backend\backend\data_pipeline\source\file\file_service.py
import os
import mimetypes
import pandas as pd
import magic
from .file_config import Config
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

class FileValidator:
    """Comprehensive file validation utilities."""

    @staticmethod
    def validate_file_format(metadata: dict, file_format=None) -> Tuple[bool, str]:
        """
        Validate if the uploaded file format is allowed using metadata.

        Args:
            metadata: File metadata dictionary
            file_format (str, optional): Specific file format to validate against

        Returns:
            tuple: (boolean success status, validation message)
        """
        ext = metadata.get('file_type', '').lower()
        allowed_formats = Config.ALLOWED_FORMATS

        if ext not in allowed_formats:
            return False, f"Invalid file format: {ext}. Allowed formats: {', '.join(allowed_formats)}."

        if file_format and file_format not in allowed_formats:
            return False, f"Invalid file format. Allowed formats: {', '.join(allowed_formats)}."

        return True, "File format is valid."

    @staticmethod
    def validate_file_size(metadata: dict) -> Tuple[bool, str]:
        """
        Validate the file size is below the threshold.

        Args:
            metadata: File metadata dictionary

        Returns:
            tuple: (boolean success status, size validation message)
        """
        file_size_mb = metadata.get("file_size_mb", 0)

        if file_size_mb > Config.FILE_SIZE_THRESHOLD_MB:
            return False, f"File size exceeds {Config.FILE_SIZE_THRESHOLD_MB} MB. Current size: {file_size_mb:.2f} MB."

        return True, "File size is within the allowed limit."

    @staticmethod
    def validate_file_integrity(data: pd.DataFrame) -> Tuple[bool, str]:
        """
        Check if the data is valid and readable.

        Args:
            data: Pandas DataFrame of file contents

        Returns:
            tuple: (boolean success status, integrity check message)
        """
        try:
            if data is None or data.empty:
                return False, "File appears to be empty or unreadable."

            return True, "File integrity check passed."

        except Exception as e:
            return False, f"Error reading file: {str(e)}. The file may be corrupted or unreadable."

    @staticmethod
    def validate_security(content: bytes) -> Tuple[bool, str]:
        """
        Perform security checks on the file content.

        Args:
            content: Raw file content in bytes

        Returns:
            tuple: (boolean security status, security check message)
        """
        try:
            if not content:  # Check if content is empty
                return False, "Empty file content"

            # Use python-magic to detect mime type
            mime_type = magic.from_buffer(content, mime=True)

            supported_mimes = {
                'text/csv',
                'application/json',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/x-parquet',
                'application/vnd.ms-excel',
                'application/octet-stream',  # For some binary formats
                'text/plain'  # For some CSV files
            }

            if mime_type in supported_mimes:
                return True, f"Security check passed: {mime_type}"

            return False, f"Unsupported mime type: {mime_type}"

        except Exception as e:
            return False, f"Security validation failed: {str(e)}"