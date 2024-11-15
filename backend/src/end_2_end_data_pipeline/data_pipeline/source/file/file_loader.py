import pandas as pd
import os
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.config import Config
from backend.src.end_2_end_data_pipeline.data_pipeline.source.file.file_validator import FileValidator

class FileLoader:
    def __init__(self, file_path, required_columns=None):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file '{file_path}' does not exist.")

        self.file_path = file_path
        self.required_columns = required_columns or []
        self.file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        self.validator = FileValidator(required_columns=self.required_columns)

    def load_file(self, chunk_size=None):
        extension = os.path.splitext(self.file_path)[-1].lower()

        try:
            # Validate the file using FileValidator
            validation_report = self.validator.validate_file(self.file_path)
            if validation_report['quality_gauge'] < 90:
                raise ValueError(f"File quality gauge is too low: {validation_report['quality_gauge']}%")

            # Raise errors if any validation failed
            for check, result in validation_report['validation_results'].items():
                if not result['valid']:
                    raise ValueError(f"Validation failed for {check}: {result['error']}")

            # Check file format before attempting to load
            if extension not in ['.csv', '.json', '.xlsx', '.parquet']:
                raise ValueError(f"Unsupported file format: {extension}")

            try:
                if extension == '.csv':
                    return self._load_csv(chunk_size)
                elif extension == '.json':
                    return self._load_json()
                elif extension == '.xlsx':
                    return self._load_excel()
                else:  # .parquet
                    return self._load_parquet()
            except (UnicodeDecodeError, pd.errors.EmptyDataError, Exception):
                raise ValueError("File validation failed")

        except ValueError as e:
            # Re-raise ValueError with original message
            raise

    def _load_csv(self, chunk_size=None):
        if chunk_size or (self.file_size_mb > Config.FILE_SIZE_THRESHOLD_MB):
            return self._load_in_chunks(pd.read_csv)
        df = pd.read_csv(self.file_path)
        self._validate(df)
        return df

    def _load_json(self):
        df = pd.read_json(self.file_path)
        self._validate(df)
        return df

    def _load_excel(self):
        df = pd.read_excel(self.file_path)
        self._validate(df)
        return df

    def _load_parquet(self):
        df = pd.read_parquet(self.file_path)
        self._validate(df)
        return df

    def _load_in_chunks(self, reader_func):
        chunks = []
        for chunk in reader_func(self.file_path, chunksize=Config.CHUNK_SIZE):
            chunks.append(chunk)
            self._validate(chunk)
        return pd.concat(chunks, ignore_index=True)

    def _validate(self, df):
        valid, message = self.validator.validate_completeness(self.file_path)
        if not valid:
            raise ValueError("File validation failed")