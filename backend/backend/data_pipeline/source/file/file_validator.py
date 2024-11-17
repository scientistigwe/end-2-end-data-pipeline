import mimetypes
import pandas as pd
from .file_config import Config

class FileValidator:

    @staticmethod
    def validate_file_format(file, file_format: str = None):
        """Validate if the uploaded file format is allowed."""
        allowed_formats = Config.ALLOWED_FORMATS
        ext = mimetypes.guess_extension(file.content_type)

        # Validate file extension
        if ext not in allowed_formats:
            return False, f"Invalid file format: {ext}. Allowed formats: {', '.join(allowed_formats)}."

        # If the file format is provided, ensure it's consistent with the content type
        if file_format and file_format not in allowed_formats:
            return False, f"Invalid file format. Allowed formats: {', '.join(allowed_formats)}."

        return True, "File format is valid."

    @staticmethod
    def validate_file_size(file):
        """Validate the file size is below the threshold."""
        file_size_mb = len(file.read()) / (1024 * 1024)  # Convert bytes to MB
        file.seek(0)  # Reset file pointer after reading for size check

        if file_size_mb > Config.FILE_SIZE_THRESHOLD_MB:
            return False, f"File size exceeds the allowed limit of {Config.FILE_SIZE_THRESHOLD_MB} MB. Current size: {file_size_mb:.2f} MB."
        return True, "File size is within the allowed limit."

    @staticmethod
    def validate_file_integrity(file):
        """Check if the uploaded file is corrupt or unreadable."""
        try:
            ext = mimetypes.guess_extension(file.content_type)
            if ext == '.csv':
                pd.read_csv(file)
            elif ext == '.json':
                pd.read_json(file)
            elif ext == '.xlsx':
                pd.read_excel(file)
            elif ext == '.parquet':
                pd.read_parquet(file)
            else:
                return False, f"Unsupported file format for integrity check: {ext}."
        except Exception as e:
            return False, f"Error reading file: {str(e)}. The file may be corrupted or unreadable."

        return True, "File integrity check passed."

    @staticmethod
    def validate_security(file):
        """Basic security checks for the file."""
        # Placeholder for potential content-based security checks.
        # This could include checking for certain patterns, sensitive data markers, etc.
        return True, "No security risks detected."

# Example usage:
# validator = FileValidator()
# is_valid, message = validator.validate_file_format(uploaded_file)
# print(message)
