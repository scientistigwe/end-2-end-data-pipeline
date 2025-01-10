# backend\backend\flask_api\app\services\data_sources\file_source_service.py

import os
import pandas as pd
from typing import Dict, Any, List
from werkzeug.datastructures import FileStorage
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename
from .base_service import BaseSourceService
from .....database.models.data_source import DataSource, FileSourceInfo
from backend.data_pipeline.source.file.file_service import FileService as FilePipelineService
import logging

logger = logging.Logger(__name__)

class FileSourceService(BaseSourceService):
    def __init__(self, db_session: Session, allowed_extensions: List[str] = None, max_file_size: int = None):
        """Initialize FileSourceService

        Args:
            db_session (Session): SQLAlchemy database session
            allowed_extensions (List[str], optional): List of allowed file extensions
            max_file_size (int, optional): Maximum allowed file size in bytes
        """
        # Call parent class's __init__ with db_session
        super().__init__(db_session=db_session)

        # Set source type for BaseSourceService
        self.source_type = 'file'

        # Initialize file-specific attributes
        self.allowed_extensions = allowed_extensions or ['csv', 'xlsx', 'xls', 'json']
        self.max_file_size = max_file_size or 10 * 1024 * 1024  # Default 10MB
        self.pipeline_service = FilePipelineService()

    def handle_file_upload(self, file: FileStorage, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Pass file to pipeline for processing."""
        try:
            # 1. Validate file
            filename = secure_filename(file.filename)
            if not self._is_allowed_file(filename):
                raise ValueError(f"File type not allowed. Allowed types: {self.allowed_extensions}")

            if not self._check_file_size(file):
                raise ValueError(f"File too large. Maximum size: {self.max_file_size / 1024 / 1024}MB")

            # 2. Prepare data for pipeline
            file_data = {
                'file': file,
                'metadata': metadata,
                'user_id': metadata.get('user_id')
            }

            # 3. Send to pipeline service
            result = self.pipeline_service.handle_file_upload(file_data)

            return result

        except Exception as e:
            self.logger.error(f"Error passing file to pipeline: {str(e)}")
            raise ValueError(f"File upload failed: {str(e)}")

    def process_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and validate file source configuration before saving.

        Args:
            config (Dict[str, Any]): File source configuration
        Returns:
            Dict[str, Any]: Processed configuration
        """
        try:
            # Extract file_config
            file_config = config.get('file_config', {})

            # Try to get user ID from Flask's g object if not provided
            from flask import g
            user_id = config.get('user_id') or (hasattr(g, 'current_user') and g.current_user.id)

            # Validate and prepare configuration
            processed_config = {
                'original_filename': file_config.get('original_filename', config.get('name', '')),
                'file_type': file_config.get('file_type', ''),
                'delimiter': file_config.get('delimiter', ','),
                'encoding': file_config.get('encoding', 'utf-8'),
                'mime_type': file_config.get('mime_type', 'text/csv'),
                'size': file_config.get('size', 0),
                'hash': file_config.get('hash', ''),
                'compression': file_config.get('compression'),
                'parse_options': file_config.get('parse_options', {}),

                # Additional metadata from the root config
                'user_id': user_id,
                'name': config.get('name'),
                'is_active': config.get('is_active', True),
                'refresh_interval': config.get('refresh_interval', 0)
            }

            # Additional validations
            if not processed_config['file_type']:
                raise ValueError("File type is required")

            if processed_config['file_type'] not in ['csv', 'json', 'xlsx', 'parquet']:
                raise ValueError(f"Invalid file type: {processed_config['file_type']}")

            if not processed_config['user_id']:
                raise ValueError("User ID is required")

            return processed_config

        except Exception as e:
            self.logger.error(f"Error processing file source config: {str(e)}")
            raise ValueError(f"Configuration processing failed: {str(e)}")

    def create_source(self, processed_config: Dict[str, Any]) -> DataSource:
        """
        Create a new file data source record.

        Args:
            processed_config (Dict[str, Any]): Processed configuration

        Returns:
            DataSource: Created data source record
        """
        try:
            # Prepare config dictionary
            source_config = {
                'file_type': processed_config.get('file_type'),
                'file_path': f"/uploads/{processed_config.get('original_filename', 'unknown')}",  # Generate a file path
                'delimiter': processed_config.get('delimiter'),
                'encoding': processed_config.get('encoding'),
                'parse_options': processed_config.get('parse_options', {})
            }

            # Create DataSource record
            data_source = DataSource(
                name=processed_config.get('name', processed_config.get('original_filename', 'Unnamed File Source')),
                type=self.source_type,
                owner_id=processed_config.get('user_id'),
                status='active' if processed_config.get('is_active', True) else 'inactive',
                refresh_interval=processed_config.get('refresh_interval', 0),
                config=source_config  # Store configuration in config column
            )
            self.db_session.add(data_source)

            # Flush to ensure data_source has an ID
            self.db_session.flush()

            # Create FileSourceInfo record
            file_source_info = FileSourceInfo(
                source_id=data_source.id,
                original_filename=processed_config.get('original_filename', ''),
                file_type=processed_config.get('file_type', ''),
                mime_type=processed_config.get('mime_type', 'text/csv'),
                size=processed_config.get('size', 0),
                hash=processed_config.get('hash', ''),
                encoding=processed_config.get('encoding', 'utf-8'),
                delimiter=processed_config.get('delimiter', ','),
                compression=processed_config.get('compression')
            )
            self.db_session.add(file_source_info)

            # Commit changes
            self.db_session.commit()

            return data_source

        except Exception as e:
            self.db_session.rollback()
            self.logger.error(f"Error creating file source: {str(e)}")
            raise ValueError(f"Failed to create file source: {str(e)}")

    def _is_allowed_file(self, filename: str) -> bool:
        """Check if file extension is allowed"""
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in self.allowed_extensions

    def _check_file_size(self, file: FileStorage) -> bool:
        """Check if file size is within limits"""
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)  # Reset file pointer
        return size <= self.max_file_size