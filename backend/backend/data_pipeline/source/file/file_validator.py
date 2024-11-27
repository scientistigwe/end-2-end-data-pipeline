import os
import mimetypes
import pandas as pd
import magic
from .file_config import Config
from typing import Tuple


class FileValidator:
    """Comprehensive file validation utilities."""

    @staticmethod
    def validate_file_format(file_fetcher: 'FileFetcher', file_format=None) -> Tuple[bool, str]:
        """
        Validate if the uploaded file format is allowed using FileFetcher metadata.

        Args:
            file_fetcher: FileFetcher instance
            file_format (str, optional): Specific file format to validate against

        Returns:
            tuple: (boolean success status, validation message)
        """
        metadata = file_fetcher.get_metadata()
        ext = metadata.get('file_type', '').lower()
        allowed_formats = Config.ALLOWED_FORMATS

        if ext not in allowed_formats:
            return False, f"Invalid file format: {ext}. Allowed formats: {', '.join(allowed_formats)}."

        if file_format and file_format not in allowed_formats:
            return False, f"Invalid file format. Allowed formats: {', '.join(allowed_formats)}."

        return True, "File format is valid."

    @staticmethod
    def validate_file_size(file_fetcher: 'FileFetcher') -> Tuple[bool, str]:
        """
        Validate the file size is below the threshold using FileFetcher metadata.

        Args:
            file_fetcher: FileFetcher instance

        Returns:
            tuple: (boolean success status, size validation message)
        """
        metadata = file_fetcher.get_metadata()
        file_size_mb = metadata.get("file_size_mb", 0)

        if file_size_mb > Config.FILE_SIZE_THRESHOLD_MB:
            return False, f"File size exceeds {Config.FILE_SIZE_THRESHOLD_MB} MB. Current size: {file_size_mb:.2f} MB."

        return True, "File size is within the allowed limit."

    @staticmethod
    def validate_file_integrity(file_fetcher: 'FileFetcher') -> Tuple[bool, str]:
        """
        Check if the uploaded file is corrupt or unreadable using the preloaded data.

        Args:
            file_fetcher: FileFetcher instance

        Returns:
            tuple: (boolean success status, integrity check message)
        """
        try:
            # Use the preloaded data from FileFetcher
            df, message = file_fetcher.load_file()

            if df is None:
                return False, f"Error reading file: {message}. The file may be corrupted or unreadable."

            return True, "File integrity check passed."

        except Exception as e:
            return False, f"Error reading file: {str(e)}. The file may be corrupted or unreadable."

    @staticmethod
    def validate_security(file_fetcher: 'FileFetcher') -> Tuple[bool, str]:
        """
        Perform security checks on the uploaded file based on its content.

        Args:
            file_fetcher: FileFetcher instance

        Returns:
            tuple: (boolean security status, security check message)
        """
        try:
            # Use the preloaded content from FileFetcher
            content = file_fetcher.file.read()

            # Use python-magic to detect mime type
            mime_type = magic.from_buffer(content, mime=True)

            supported_mimes = {
                'text/csv',
                'application/json',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/x-parquet',
                'application/vnd.ms-excel',  # Additional Excel mime type
                'application/octet-stream'  # Fallback for some Parquet files
            }

            return mime_type in supported_mimes, f"Security check: {mime_type}"
        except Exception as e:
            return False, f"Security validation failed: {str(e)}"
