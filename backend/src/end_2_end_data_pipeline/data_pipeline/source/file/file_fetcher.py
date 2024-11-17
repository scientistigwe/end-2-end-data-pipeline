import os
import pandas as pd
from .config import Config
from .file_validator import FileValidator
from pandas.errors import EmptyDataError, ParserError


class FileFetcher:
    def __init__(self, file_path: str, file_format: str = None, required_columns: list = None,
                 is_directory: bool = False):
        """
        Initializes the FileFetcher class to handle file fetching and loading.
        """
        self.file_path = file_path
        self.file_format = file_format
        self.is_directory = is_directory
        self.required_columns = required_columns or []
        self.file_size_mb = os.path.getsize(file_path) / (1024 * 1024) if os.path.exists(file_path) else 0
        self.validator = FileValidator()

    def fetch_file(self):
        """
        Fetch the file from the given path (local or cloud) and load it for processing.
        """
        # Validate the file path
        valid, message = self.validator.validate_path(self.file_path)
        if not valid:
            return None, message

        # Validate file format
        valid, message = self.validator.validate_file_format(self.file_path, self.file_format)
        if not valid:
            return None, message

        # Validate file size
        valid, message = self.validator.validate_file_size(self.file_path)
        if not valid:
            return None, message

        # Validate file integrity
        valid, message = self.validator.validate_file_integrity(self.file_path)
        if not valid:
            return None, message

        # Validate security
        valid, message = self.validator.validate_security(self.file_path)
        if not valid:
            return None, message

        # If the path is a directory, return the directory contents
        if self.is_directory:
            return self.fetch_from_directory()

        # If it's a file, proceed to load the file
        return self.fetch_from_file()

    def fetch_from_directory(self):
        """
        Fetch all files from the directory if it's a directory path.
        """
        valid_files = []
        if os.path.isdir(self.file_path):
            for file in os.listdir(self.file_path):
                file_full_path = os.path.join(self.file_path, file)
                if os.path.isfile(file_full_path):
                    valid_files.append(file_full_path)

        if valid_files:
            return valid_files, "Files fetched successfully from directory."
        return None, "No valid files found in the directory."

    def fetch_from_file(self):
        """
        Fetch a single file from the given file path.
        """
        if os.path.exists(self.file_path) and os.access(self.file_path, os.R_OK):
            return self.load_file(self.file_path)
        else:
            return None, "File not found or not accessible."

    def load_file(self, file_path: str):
        """
        Loads a file based on its format (CSV, JSON, Parquet, etc.) into a pandas DataFrame.
        """
        try:
            df = self._read_file(file_path)

            # Run validation checks on the file
            validation_report = self.validator.validate_file(df)
            if not validation_report['validation_results']['completeness']['valid']:
                return None, "Validation failed for completeness"

            return df, "File loaded and validated successfully."

        except (EmptyDataError, ParserError) as e:
            return None, f"File loading failed: {str(e)}"
        except UnicodeDecodeError as e:
            return None, f"File encoding error: {e}"

    def _read_file(self, file_path: str):
        """
        Reads the file based on its format (CSV, JSON, Parquet).
        """
        ext = os.path.splitext(file_path)[-1].lower()

        if ext == '.csv':
            return pd.read_csv(file_path)
        elif ext == '.json':
            return pd.read_json(file_path)
        elif ext == '.xlsx':
            return pd.read_excel(file_path)
        elif ext == '.parquet':
            return pd.read_parquet(file_path)
        else:
            raise ValueError("Unsupported file format")

    def load_file_in_chunks(self, file_path: str, chunk_size: int = Config.CHUNK_SIZE):
        """
        Loads large files in chunks, if the file size exceeds the threshold.
        """
        if self.file_size_mb < Config.FILE_SIZE_THRESHOLD_MB:
            return self.load_file(file_path)

        chunk_list = []
        try:
            # Read the file in chunks
            for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                chunk_list.append(chunk)

            # Concatenate chunks into a final DataFrame
            if not chunk_list:
                raise EmptyDataError("No data was read from the file")

            result = pd.concat(chunk_list, ignore_index=True)

            # Validate the final concatenated DataFrame
            validation_report = self.validator.validate_file(result)
            if not validation_report['validation_results']['completeness']['valid']:
                raise ValueError("Validation failed for completeness")

            return result

        except (EmptyDataError, ParserError) as e:
            return None, f"Chunked file loading failed: {str(e)}"
        except UnicodeDecodeError as e:
            return None, f"File encoding error: {e}"
