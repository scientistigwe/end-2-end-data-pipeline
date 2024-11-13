# config.py
import tempfile
from pathlib import Path


class Config:
    UPLOAD_FOLDER = Path(tempfile.gettempdir()) / 'data_ingestion'
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'parquet'}
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    VALIDATION_SCHEMAS_PATH = 'schemas'
