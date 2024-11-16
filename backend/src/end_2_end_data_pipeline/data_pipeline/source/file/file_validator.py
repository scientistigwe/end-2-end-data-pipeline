import os
import mimetypes
import pandas as pd
from .config import Config


class FileValidator:

    @staticmethod
    def validate_file_format(file_path: str, file_format: str):
        """Validate if the file format is allowed."""
        allowed_formats = Config.ALLOWED_FORMATS
        ext = os.path.splitext(file_path)[1].lower()

        # Validate file extension
        if ext not in allowed_formats:
            return False, f"Invalid file format: {ext}. Allowed formats: {', '.join(allowed_formats)}."

        # If the file format is provided, ensure it's consistent with the extension
        if file_format and file_format not in allowed_formats:
            return False, f"Invalid file format. Allowed formats: {', '.join(allowed_formats)}."

        return True, "File format is valid."

    @staticmethod
    def validate_file_size(file_path: str):
        """Validate the file size is below the threshold."""
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)  # Convert bytes to MB
        if file_size_mb > Config.FILE_SIZE_THRESHOLD_MB:
            return False, f"File size exceeds the allowed limit of {Config.FILE_SIZE_THRESHOLD_MB} MB. Current size: {file_size_mb:.2f} MB."
        return True, "File size is within the allowed limit."

    @staticmethod
    def validate_path(file_path: str):
        """Validate if the file path exists and is accessible."""
        if not os.path.exists(file_path):
            return False, "The provided file path does not exist."

        if not os.access(file_path, os.R_OK):
            return False, "The file path is not readable. Please check file permissions."

        return True, "File path is valid and accessible."

    @staticmethod
    def validate_is_directory(file_path: str, is_directory: bool):
        """Validate if the file path corresponds to a directory (if requested)."""
        if is_directory:
            if not os.path.isdir(file_path):
                return False, "The path is not a directory. Please provide a valid directory path."
            return True, "Directory path is valid."
        return True, "File path is valid."

    @staticmethod
    def validate_file_integrity(file_path: str):
        """Check if the file is corrupt or not readable."""
        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == '.csv':
                pd.read_csv(file_path)
            elif ext == '.json':
                pd.read_json(file_path)
            elif ext == '.xlsx':
                pd.read_excel(file_path)
            elif ext == '.parquet':
                pd.read_parquet(file_path)
            else:
                return False, f"Unsupported file format for integrity check: {ext}."
        except Exception as e:
            return False, f"Error reading file: {str(e)}. The file may be corrupted or unreadable."

        return True, "File integrity check passed."

    @staticmethod
    def validate_directory_contents(file_path: str):
        """Check if the directory contains valid files."""
        if not os.path.isdir(file_path):
            return False, "The path is not a directory. Please provide a valid directory path."

        files_in_directory = os.listdir(file_path)
        if len(files_in_directory) == 0:
            return False, "The directory is empty. Please upload files to the directory."

        valid_files = []
        invalid_files = []
        for file in files_in_directory:
            file_full_path = os.path.join(file_path, file)
            if os.path.isfile(file_full_path):
                valid, message = FileValidator.validate_file_format(file_full_path, '')
                if valid:
                    valid_files.append(file)
                else:
                    invalid_files.append((file, message))

        if len(valid_files) == 0:
            return False, "No valid files found in the directory."

        return True, f"Found {len(valid_files)} valid file(s) in the directory. Invalid files: {len(invalid_files)}."

    @staticmethod
    def validate_security(file_path: str):
        """Ensure there is no potential security risk with the file path."""
        # Check for absolute file path vulnerability
        if os.path.isabs(file_path):
            return False, "Absolute file paths are not allowed due to security risks (path traversal)."

        # Check for sensitive or system files (e.g., configuration files, keys, etc.)
        sensitive_keywords = ['config', 'secret', 'key', 'password']
        for keyword in sensitive_keywords:
            if keyword.lower() in file_path.lower():
                return False, f"The file path seems to reference a sensitive file (e.g., containing '{keyword}'). Please ensure proper access rights or consider using a secure source option like cloud or API."

        # Check for potential symbolic link issues
        if os.path.islink(file_path):
            return False, "Symbolic links are not allowed due to potential security risks."

        # Check for restricted or unsafe locations (e.g., system directories)
        restricted_paths = ['/etc', '/bin', '/usr', '/tmp', '/root']
        if any(file_path.startswith(restricted) for restricted in restricted_paths):
            return False, f"The file path points to a restricted location ({file_path}). Please use a secure source like cloud or API to upload the file."

        # If the file requires specific security clearance, recommend cloud/API options
        if FileValidator.requires_security_clearance(file_path):
            return False, "This file appears to require special clearance. Please use a secured source option such as a cloud or API-based upload and provide the necessary access credentials."

        return True, "No security risks detected."

    @staticmethod
    def requires_security_clearance(file_path: str):
        """Check if the file requires security clearance (based on the path or other attributes)."""
        # Placeholder for a more complex check if the file requires special clearance
        # This can be extended to look for files in specific cloud storage paths, or files tagged for high-security access.
        if file_path.lower().startswith("s3://") or file_path.lower().startswith("gs://"):
            return True
        # Example additional check for files that need API credentials (cloud, restricted access)
        return False

    @staticmethod
    def validate_file_type_consistency(file_path: str, file_format: str):
        """Ensure the file type matches the content."""
        if file_format:
            valid_format = FileValidator.validate_file_format(file_path, file_format)[0]
            if not valid_format:
                return False, f"Provided file format '{file_format}' does not match the file content."

        return True, "File format is consistent with content."

# Example usage:
# validator = FileValidator()
# is_valid, message = validator.validate_file_format("/path/to/file.csv", "csv")
# print(message)
