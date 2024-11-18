import os
import mimetypes
import pandas as pd
import magic
from .file_config import Config


class FileValidator:
    """Comprehensive file validation utilities."""

    @staticmethod
    def validate_file_format(file, file_format=None):
        """
        Validate if the uploaded file format is allowed.

        Args:
            file: File object to validate
            file_format (str, optional): Specific file format to validate against

        Returns:
            tuple: (boolean success status, validation message)
        """
        # Detect file extension from filename or content type
        ext = (os.path.splitext(file.filename)[1].lower().replace('.', '')
               if hasattr(file, 'filename')
               else mimetypes.guess_extension(file.content_type))

        allowed_formats = Config.ALLOWED_FORMATS

        if ext not in allowed_formats:
            return False, f"Invalid file format: {ext}. Allowed formats: {', '.join(allowed_formats)}."

        if file_format and file_format not in allowed_formats:
            return False, f"Invalid file format. Allowed formats: {', '.join(allowed_formats)}."

        return True, "File format is valid."

    @staticmethod
    def validate_file_size(file):
        """
        Validate the file size is below the threshold.

        Args:
            file: File object to check

        Returns:
            tuple: (boolean success status, size validation message)
        """
        file.seek(0)
        file_size_mb = len(file.read()) / (1024 * 1024)
        file.seek(0)

        if file_size_mb > Config.FILE_SIZE_THRESHOLD_MB:
            return False, f"File size exceeds {Config.FILE_SIZE_THRESHOLD_MB} MB. Current size: {file_size_mb:.2f} MB."
        return True, "File size is within the allowed limit."

    @staticmethod
    def validate_file_integrity(file):
        """
        Check if the uploaded file is corrupt or unreadable.

        Args:
            file: File object to validate

        Returns:
            tuple: (boolean success status, integrity check message)
        """
        try:
            # Determine file extension
            ext = (os.path.splitext(file.filename)[1].lower().replace('.', '')
                   if hasattr(file, 'filename')
                   else mimetypes.guess_extension(file.content_type))

            readers = {
                'csv': pd.read_csv,
                'json': pd.read_json,
                'xlsx': pd.read_excel,
                'parquet': pd.read_parquet
            }

            if ext not in readers:
                return False, f"Unsupported file format for integrity check: {ext}."

            # Read the entire content
            content = file.read()

            # Use BytesIO to create a file-like object
            import io
            file_buffer = io.BytesIO(content)

            readers[ext](file_buffer)

        except Exception as e:
            return False, f"Error reading file: {str(e)}. The file may be corrupted or unreadable."

        return True, "File integrity check passed."

    @staticmethod
    def validate_security(file):
        """
        Perform security checks on the uploaded file.

        Args:
            file: File object to validate

        Returns:
            tuple: (boolean security status, security check message)
        """
        try:
            # Read the entire content
            content = file.read()

            # Use python-magic to detect mime type
            import magic
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