# backend/flask_api/app/services/data_sources/file_service.py

import os
import pandas as pd
from typing import Dict, Any, List
from werkzeug.datastructures import FileStorage
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename
from .base_service import BaseSourceService
from .....database.models.data_source import DataSource, FileSourceInfo


class FileSourceService(BaseSourceService):
    """Service for handling file-based data sources."""

    source_type = 'file'

    def __init__(self, db_session: Session, allowed_extensions: List[str], max_file_size: int):
        """
        Initialize the FileSourceService.

        :param db_session: The database session.
        :param allowed_extensions: The list of allowed file extensions.
        :param max_file_size: The maximum allowed file size in bytes.
        """
        super().__init__(db_session)
        self.allowed_extensions = allowed_extensions
        self.max_file_size = max_file_size

    def list_sources(self) -> List[DataSource]:
        """
        List all file data sources.
        
        Returns:
            List[DataSource]: List of all file data sources
        """
        try:
            return (self.db_session.query(DataSource)
                    .filter(DataSource.type == self.source_type)
                    .all())
        except Exception as exc:
            self.logger.error(f"Error listing file sources: {str(exc)}")
            raise
        
    def handle_file_upload(self, file: FileStorage, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file upload with validation."""
        try:
            # Validate file
            if not self._allowed_file(file.filename):
                raise ValueError(f"File type not allowed. Allowed types: {', '.join(self.allowed_extensions)}")

            if file.content_length > self.max_file_size:
                raise ValueError(f"File size exceeds maximum allowed size of {self.max_file_size} bytes")

            filename = secure_filename(file.filename)
            file_path = os.path.join(os.environ['UPLOAD_FOLDER'], filename)

            # Create source record
            source = DataSource(
                name=metadata.get('name', filename),
                type=self.source_type,
                status='pending',
                config={'file_path': file_path},
                metadata=metadata
            )

            # Create file info
            file_info = FileSourceInfo(
                source=source,
                original_filename=filename,
                file_type=os.path.splitext(filename)[1].lower(),
                mime_type=file.mimetype,
                size=file.content_length,
                encoding=metadata.get('encoding', 'utf-8'),
                delimiter=metadata.get('delimiter', ',')
            )

            # Save file
            with open(file_path, 'wb') as f:
                f.write(file.read())

            # Update status after successful save
            source.status = 'active'

            self.db_session.add(source)
            self.db_session.add(file_info)
            self.db_session.commit()

            return self._format_source(source)

        except Exception as exc:
            self.logger.error(f"File upload error: {str(exc)}")
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
            self.db_session.rollback()
            raise

    def _allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed."""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def _validate_source_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate file source configuration."""
        errors = []
        required_fields = ['encoding', 'delimiter']

        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")

        return errors

    def _test_source_connection(self, source: DataSource) -> Dict[str, Any]:
        """Test file accessibility."""
        if not os.path.exists(source.config['file_path']):
            raise ValueError("File not found")

        return {
            "accessible": True,
            "size": os.path.getsize(source.config['file_path']),
            "last_modified": os.path.getmtime(source.config['file_path'])
        }

    def _sync_source_data(self, source: DataSource) -> Dict[str, Any]:
        """Sync file data (for file sources, this mainly involves validation)."""
        file_info = source.file_info
        file_path = source.config['file_path']

        if file_info.file_type.lower() in ['.csv', '.tsv']:
            df = pd.read_csv(file_path, encoding=file_info.encoding, delimiter=file_info.delimiter)
        elif file_info.file_type.lower() == '.json':
            df = pd.read_json(file_path)
        else:
            raise ValueError(f"Unsupported file type: {file_info.file_type}")

        return {
            "records_processed": len(df),
            "bytes_processed": os.path.getsize(file_path)
        }

    def _get_source_preview(self, source: DataSource, limit: int) -> List[Dict[str, Any]]:
        """Get preview of file contents."""
        file_info = source.file_info
        file_path = source.config['file_path']

        if file_info.file_type.lower() in ['.csv', '.tsv']:
            df = pd.read_csv(file_path, encoding=file_info.encoding, delimiter=file_info.delimiter, nrows=limit)
        elif file_info.file_type.lower() == '.json':
            df = pd.read_json(file_path).head(limit)
        else:
            raise ValueError(f"Unsupported file type: {file_info.file_type}")

        return df.to_dict('records')

    def _disconnect_source(self, source: DataSource) -> None:
        """Clean up file resources."""
        # For file sources, disconnecting might involve cleaning up temporary files
        # or releasing file handles
        pass