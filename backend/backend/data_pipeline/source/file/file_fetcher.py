import chardet
import pandas as pd
from io import BytesIO, StringIO
from .file_config import Config
from pandas.errors import EmptyDataError, ParserError
import logging
from typing import Dict, Any, Tuple

# logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileFetcher:
    """Handles file loading and conversion across different formats."""
    SUPPORTED_FORMATS = {
        'csv': pd.read_csv,
        'json': pd.read_json,
        'xlsx': pd.read_excel,
        'parquet': pd.read_parquet
    }

    def __init__(self, file):
        self.file = file
        self.file_format = self._infer_file_format().lower()
        self.file_size_mb = len(file.read()) / (1024 * 1024)
        self.file.seek(0)  # Reset file pointer after reading

    def _infer_file_format(self):
        """Infer file format from filename."""
        logger.info(f'Filename: {self.file.filename}')
        return self.file.filename.rsplit('.', 1)[-1].lower() if '.' in self.file.filename else None

    def convert_to_dataframe(self):
        """Convert file to DataFrame, handling different formats and sizes."""
        if self.file_format not in self.SUPPORTED_FORMATS:
            return None, f"Unsupported file format: {self.file_format}"

        if self.file_size_mb >= Config.FILE_SIZE_THRESHOLD_MB or self.file_format != 'parquet':
            return self._convert_to_parquet()

        return self.load_file()

    def load_file(self) -> Tuple[Any, str]:
        """Load the file into a DataFrame or equivalent structure with encoding detection."""
        try:
            reader = self.SUPPORTED_FORMATS[self.file_format]

            # Handle Parquet files
            if self.file_format == 'parquet':
                df = reader(BytesIO(self.file.read()))

            # Handle CSV and JSON files
            elif self.file_format in ['csv', 'json']:
                raw_data = self.file.read()  # Read file content as bytes
                detected_encoding = chardet.detect(raw_data)['encoding']
                logger.info(f"Detected Encoding2: {detected_encoding}")

                file_content = raw_data.decode(detected_encoding or 'utf-8')  # Decode with detected encoding
                df = reader(StringIO(file_content))  # Use pandas reader with StringIO

            # Handle Excel files
            elif self.file_format == 'xlsx':
                df = reader(BytesIO(self.file.read()))  # Load Excel file using pandas.ExcelFile

            else:
                return None, f"Unsupported file format: {self.file_format}"

            return df, f"{self.file_format.upper()} loaded successfully"

        except Exception as e:
            return None, f"File loading error: {str(e)}"

    def extract_metadata(self) -> Dict[str, Any]:
        """Extract metadata from the file content."""
        try:
            df, message = self.load_file()

            if df is None:
                print(f"File loading failed: {message}")
                return {"error": message}

            metadata = {
                "filename": getattr(self.file, 'filename', 'unknown'),
                "file_size_mb": self.file_size_mb,
                "file_type": self.file_format,
                "load_status": message
            }

            if self.file_format == 'xlsx':
                metadata['sheet_names'] = list(df.sheet_names)
                metadata['columns'] = {sheet: list(df.parse(sheet).columns) for sheet in metadata['sheet_names']}
            elif self.file_format in ['csv', 'json', 'parquet']:
                metadata['columns'] = list(df.columns) if hasattr(df, 'columns') else []
                metadata['row_count'] = len(df) if hasattr(df, '__len__') else 0

            return metadata

        except Exception as e:
            return {"error": f"Metadata extraction error: {str(e)}"}

    def _convert_to_parquet(self):
        """Convert file to Parquet buffer."""
        try:
            df, _ = self.load_file()
            buffer = BytesIO()
            df.to_parquet(buffer, index=False)
            buffer.seek(0)
            return buffer, "File converted to Parquet"
        except Exception as e:
            return None, f"Parquet conversion error: {str(e)}"
