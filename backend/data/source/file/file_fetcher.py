# backend\backend\data_pipeline\source\file\file_fetcher.py
import chardet
import pandas as pd
from io import BytesIO, StringIO
from .file_config import Config
from pandas.errors import EmptyDataError, ParserError
import logging
from typing import Dict, Any, Tuple, Optional

from backend.core.messaging.broker import MessageBroker

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
    def __init__(self, file, message_broker: Optional[MessageBroker] = None):
        self.file = file
        self.message_broker = message_broker
        self.file_format = self._infer_file_format().lower()
        self.file_size_mb = len(file.read()) / (1024 * 1024)
        self.file.seek(0)  # Reset file pointer after reading

    def _infer_file_format(self):
        """Infer file format from filename."""
        logger.info(f'Filename: {self.file.filename}')
        return self.file.filename.rsplit('.', 1)[-1].lower() if '.' in self.file.filename else None

    def convert_to_dataframe(self) -> Tuple[pd.DataFrame, str]:
        """
        Convert the file to a DataFrame based on its format.

        Supports file formats: CSV, JSON, Excel (XLSX), and Parquet.

        Returns:
            Tuple:
            - DataFrame: The converted DataFrame (or None if conversion fails)
            - str: Message indicating success or failure
        """
        if self.file_format not in self.SUPPORTED_FORMATS:
            return None, f"Unsupported file format: {self.file_format}"

        try:
            # Reset file pointer before reading
            self.file.seek(0)

            # Get the appropriate reader for the file format
            reader = self.SUPPORTED_FORMATS[self.file_format]

            if self.file_format == "parquet":
                # Read Parquet file directly
                df = reader(BytesIO(self.file.read()))

            elif self.file_format in ["csv", "json"]:
                # Detect encoding and read CSV/JSON files
                raw_data = self.file.read()
                detected_encoding = chardet.detect(raw_data).get("encoding", "utf-8")
                logger.info(f"Detected encoding for {self.file_format.upper()}: {detected_encoding}")
                file_content = raw_data.decode(detected_encoding)
                df = reader(StringIO(file_content))

            elif self.file_format == "xlsx":
                # Read Excel file
                df = reader(BytesIO(self.file.read()))

            else:
                return None, f"Unsupported file format: {self.file_format}"

            return df, f"{self.file_format.upper()} loaded successfully"

        except EmptyDataError:
            return None, "File is empty or contains no data"
        except ParserError as e:
            return None, f"File parsing error: {str(e)}"
        except Exception as e:
            logger.error(f"Error converting {self.file_format.upper()} to DataFrame: {str(e)}", exc_info=True)
            return None, f"Conversion error: {str(e)}"

        # Use FileFetcher for comprehensive conversion
        try:
            file_fetcher = FileFetcher(file)
            return file_fetcher.convert_to_dataframe()
        except Exception as e:
            return None, f"Conversion failed: {str(e)}"

        return self.load_file()

    def load_file(self) -> Tuple[Any, str]:
        """Load the file into a DataFrame or equivalent structure with encoding detection."""
        try:
            # Always reset file pointer to the beginning
            self.file.seek(0)

            reader = self.SUPPORTED_FORMATS[self.file_format]

            # Handle Parquet files
            if self.file_format == 'parquet':
                df = reader(BytesIO(self.file.read()))

            # Handle CSV and JSON files
            elif self.file_format in ['csv', 'json']:
                raw_data = self.file.read()  # Read file content as bytes
                detected_encoding = chardet.detect(raw_data)['encoding']
                logger.info(f"Detected Encoding: {detected_encoding}")

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

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata from the file. Alias for extract_metadata for consistency.
        Ensures backward compatibility with FileManager's expectations.
        """
        return self.extract_metadata()

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

    async def notify_conversion_status(self, status: str, details: Dict[str, Any]) -> None:
        """Notify about file conversion status"""
        if self.message_broker:
            await self.message_broker.publish(
                ProcessingMessage(
                    source_identifier=ModuleIdentifier("file_fetcher"),
                    target_identifier=ModuleIdentifier("file_manager"),
                    message_type=MessageType.SOURCE_STATUS,
                    content={
                        'status': status,
                        'details': details,
                        'file_format': self.file_format,
                        'timestamp': datetime.now().isoformat()
                    }
                )
            )