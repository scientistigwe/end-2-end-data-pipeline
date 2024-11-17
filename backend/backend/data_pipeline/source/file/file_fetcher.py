import pandas as pd
from io import BytesIO, StringIO
from .file_config import Config
from .file_validator import FileValidator
from pandas.errors import EmptyDataError, ParserError


class FileFetcher:
    def __init__(self, file, file_format: str = None):
        """
        Initializes the FileFetcher class to handle file uploading and loading directly from memory.

        Args:
            file: The file-like object to be processed (e.g., Flask's FileStorage).
            file_format: The format of the file, if known (e.g., 'csv', 'json').
        """
        self.file = file
        self.file_format = file_format or self._infer_file_format()
        self.file_size_mb = len(file.read()) / (1024 * 1024)
        file.seek(0)  # Reset file pointer after reading
        self.validator = FileValidator()

    def _infer_file_format(self):
        """Infers the file format based on the filename extension."""
        return self.file.filename.rsplit('.', 1)[-1].lower() if '.' in self.file.filename else None

    def fetch_file(self):
        """
        Validates and loads an uploaded file.
        """
        # Validate file format
        valid, message = self.validator.validate_file_format(self.file.filename, self.file_format)
        if not valid:
            return None, message

        # Validate file size
        valid, message = self.validator.validate_file_size(self.file)
        if not valid:
            return None, message

        # Validate file integrity
        valid, message = self.validator.validate_file_integrity(self.file)
        if not valid:
            return None, message

        # Validate security
        valid, message = self.validator.validate_security(self.file)
        if not valid:
            return None, message

        # Load the file
        return self.load_file()

    def load_file(self):
        """
        Loads an uploaded file based on its format (CSV, JSON, Parquet, etc.) into a pandas DataFrame.
        """
        try:
            df = self._read_file()
            return df, "File loaded successfully."

        except (EmptyDataError, ParserError) as e:
            return None, f"File loading failed: {str(e)}"
        except UnicodeDecodeError as e:
            return None, f"File encoding error: {e}"

    def _read_file(self):
        """
        Reads the file directly from memory based on its format (CSV, JSON, Parquet).
        """
        ext = f".{self.file_format}"

        if ext == '.csv':
            return pd.read_csv(StringIO(self.file.stream.read().decode('utf-8')))
        elif ext == '.json':
            return pd.read_json(StringIO(self.file.stream.read().decode('utf-8')))
        elif ext == '.xlsx':
            return pd.read_excel(BytesIO(self.file.read()))
        elif ext == '.parquet':
            return pd.read_parquet(BytesIO(self.file.read()))
        else:
            raise ValueError("Unsupported file format")

    def load_file_in_chunks(self, chunk_size: int = Config.CHUNK_SIZE):
        """
        Loads large files in chunks if the file size exceeds the threshold.
        """
        if self.file_size_mb < Config.FILE_SIZE_THRESHOLD_MB:
            return self.load_file()

        chunk_list = []
        try:
            # Read the file in chunks (assuming CSV for simplicity)
            self.file.seek(0)  # Reset file pointer
            for chunk in pd.read_csv(StringIO(self.file.stream.read().decode('utf-8')), chunksize=chunk_size):
                chunk_list.append(chunk)

            # Concatenate chunks into a final DataFrame
            if not chunk_list:
                raise EmptyDataError("No data was read from the file")

            result = pd.concat(chunk_list, ignore_index=True)
            return result, "File loaded in chunks successfully."

        except (EmptyDataError, ParserError) as e:
            return None, f"Chunked file loading failed: {str(e)}"
        except UnicodeDecodeError as e:
            return None, f"File encoding error: {e}"
