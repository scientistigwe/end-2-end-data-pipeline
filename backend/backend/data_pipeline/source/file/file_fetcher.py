import pandas as pd
from io import BytesIO, StringIO
from .file_config import Config
from pandas.errors import EmptyDataError, ParserError

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
        self.file_format = self._infer_file_format()
        file.seek(0)
        self.file_size_mb = len(file.read()) / (1024 * 1024)
        file.seek(0)

    def _infer_file_format(self):
        """Infer file format from filename."""
        return self.file.filename.rsplit('.', 1)[-1].lower() if '.' in self.file.filename else None

    def convert_to_dataframe(self):
        """Convert file to DataFrame, handling different formats and sizes."""
        if self.file_format not in self.SUPPORTED_FORMATS:
            return None, f"Unsupported file format: {self.file_format}"

        if self.file_size_mb >= Config.FILE_SIZE_THRESHOLD_MB or self.file_format != 'parquet':
            return self._convert_to_parquet()

        return self._load_file()

    def _load_file(self):
        """Load file as DataFrame."""
        try:
            reader = self.SUPPORTED_FORMATS[self.file_format]
            if self.file_format == 'parquet':
                df = reader(BytesIO(self.file.read()))
            elif self.file_format in ['csv', 'json']:
                file_content = self.file.stream.read().decode('utf-8')
                df = reader(StringIO(file_content))
            else:  # xlsx
                df = reader(BytesIO(self.file.read()))
            return df, f"{self.file_format.upper()} loaded successfully"
        except (EmptyDataError, ParserError, UnicodeDecodeError) as e:
            return None, f"File loading error: {str(e)}"

    def _convert_to_parquet(self):
        """Convert file to Parquet buffer."""
        try:
            df, _ = self._load_file()
            buffer = BytesIO()
            df.to_parquet(buffer, index=False)
            buffer.seek(0)
            return buffer, "File converted to Parquet"
        except Exception as e:
            return None, f"Parquet conversion error: {str(e)}"

    def extract_metadata(self, data):
        """Extract metadata from loaded file."""
        if isinstance(data, pd.DataFrame):
            df = data
        else:
            df = pd.read_parquet(data)
        return {
            'filename': self.file.filename,
            'file_size': self.file_size_mb,
            'file_type': self.file_format,
            'columns': list(df.columns),
            'row_count': len(df)
        }
