# backend/data/source/file/file_service.py

import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import UploadFile
import json

from core.control.cpm import ControlPointManager
from core.managers.staging_manager import StagingManager
from .file_handler import FileHandler
from .file_validator import FileValidator
from config.validation_config import FileValidationConfig

logger = logging.getLogger(__name__)


class FileService:
    """Service for handling file operations with direct pipeline creation"""

    def __init__(
            self,
            staging_manager: StagingManager,
            cpm: ControlPointManager,
            config: Optional[FileValidationConfig] = None
    ):
        self.staging_manager = staging_manager
        self.cpm = cpm
        self.config = config or FileValidationConfig()

        # Initialize components
        self.handler = FileHandler(staging_manager)
        self.validator = FileValidator()

    async def process_file_upload(
            self,
            file: UploadFile,
            metadata: Dict[str, Any],
            user_id: str
    ) -> Dict[str, Any]:
        """
        Process file upload with manual pipeline creation to avoid
        foreign key constraints and department chain issues
        """
        try:
            logger.info(f"Processing file upload: {file.filename}")

            # 1. Generate a pipeline ID
            pipeline_id = str(uuid.uuid4())
            logger.info(f"Generated pipeline ID: {pipeline_id}")

            # 2. Create a pipeline record directly in the database
            # This bypasses the CPM's create_pipeline which requires department chains
            pipeline_created = await self._create_pipeline_direct(pipeline_id, user_id, file.filename, metadata)

            if not pipeline_created:
                return {
                    'status': 'error',
                    'error': 'Failed to create pipeline',
                    'message': 'Could not create required pipeline record',
                    'staged_id': '',
                    'control_point_id': '',
                    'tracking_url': '',
                    'upload_status': 'failed'
                }

            logger.info(f"Created pipeline with ID: {pipeline_id}")

            # 3. Add standard metadata with the pipeline ID
            complete_metadata = {
                'content_type': file.content_type,
                'original_filename': file.filename,
                'user_id': user_id,
                'upload_timestamp': datetime.now().isoformat(),
                'pipeline_id': pipeline_id,  # Critical: Include the pipeline ID
                **metadata  # Include original metadata
            }

            logger.info(f"Created metadata with pipeline_id: {complete_metadata.get('pipeline_id')}")

            # 4. Initial validation
            validation_result = await self.validator.validate_file_source(
                file.filename,
                complete_metadata
            )

            if not validation_result.get('passed', False):
                return {
                    'status': 'error',
                    'errors': validation_result.get('issues', ['Validation failed']),
                    'message': 'File validation failed',
                    'staged_id': '',
                    'control_point_id': '',
                    'tracking_url': '',
                    'upload_status': 'failed'
                }

            # 5. Process through handler (which will use the pipeline_id)
            result = await self.handler.handle_file(
                file.file,
                file.filename,
                file.content_type,
                complete_metadata
            )

            if result.get('status') != 'success':
                return {
                    'status': result.get('status', 'error'),
                    'error': result.get('error', 'Unknown error'),
                    'message': 'File handling failed',
                    'staged_id': '',
                    'control_point_id': '',
                    'tracking_url': '',
                    'upload_status': 'failed'
                }

            # 6. Return successful result - don't try to create a control point
            return {
                'status': 'success',
                'staged_id': result.get('staged_id'),
                'pipeline_id': pipeline_id,
                'tracking_url': f'/api/files/{result.get("staged_id")}/status',
                'upload_status': 'completed',
                'message': 'File uploaded successfully'
            }

        except Exception as e:
            logger.exception(f"File upload processing error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'message': "File upload failed",
                'staged_id': '',
                'control_point_id': '',
                'tracking_url': '',
                'upload_status': 'failed'
            }

    async def _create_pipeline_direct(
            self,
            pipeline_id: str,
            user_id: str,
            filename: str,
            metadata: Dict[str, Any]
    ) -> bool:
        """
        Create a pipeline record directly in the database

        Args:
            pipeline_id: Generated pipeline ID
            user_id: User ID
            filename: Original filename
            metadata: File metadata

        Returns:
            Boolean indicating success
        """
        try:
            # Get access to the database session
            db_session = getattr(self.staging_manager, 'repository', None)
            if not db_session or not hasattr(db_session, 'db_session'):
                logger.error("Could not access database session from staging manager")
                return False

            # Create pipeline data
            pipeline_data = {
                'id': pipeline_id,
                'name': f"Pipeline for {filename}",
                'description': f"Auto-generated pipeline for file upload: {filename}",
                'owner_id': user_id,
                'status': 'idle',  # Plain string, will be cast by SQL
                'mode': 'development',  # Plain string, will be cast by SQL
                'config': {
                    'file_type': metadata.get('file_type', 'csv'),
                    'source_type': 'file',
                    'auto_generated': True,
                    'created_from_upload': True
                },
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }

            # Create a SQL statement to insert the pipeline
            from sqlalchemy import text

            # Execute the query with proper parameter binding
            # Fixed SQL statement without type casting in the parameter references
            pipeline_insert = text("""
                INSERT INTO pipelines (
                    id, name, description, status, mode, config, version, 
                    owner_id, created_at, updated_at, is_deleted
                ) VALUES (
                    :id, :name, :description, :status, :mode, 
                    :config, 1, :owner_id, :created_at, :updated_at, false
                )
            """)

            # Execute the query
            await db_session.db_session.execute(
                pipeline_insert,
                {
                    'id': pipeline_id,
                    'name': pipeline_data['name'],
                    'description': pipeline_data['description'],
                    'status': pipeline_data['status'],
                    'mode': pipeline_data['mode'],
                    'config': json.dumps(pipeline_data['config']),
                    'owner_id': user_id,
                    'created_at': pipeline_data['created_at'],
                    'updated_at': pipeline_data['updated_at']
                }
            )

            # Commit the transaction
            await db_session.db_session.commit()

            # Success!
            logger.info(f"Successfully created pipeline {pipeline_id} in database")
            return True

        except Exception as e:
            logger.error(f"Pipeline direct creation error: {str(e)}")
            # Rollback if possible
            try:
                if db_session and hasattr(db_session, 'db_session'):
                    await db_session.db_session.rollback()
            except:
                pass
            return False

    async def handle_upload(
            self,
            file: UploadFile,
            user_id: str,
            metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Legacy handle_upload method - redirects to the new process_file_upload method
        """
        return await self.process_file_upload(file, metadata or {}, user_id)

    async def list_sources(self, user_id: str) -> List[Dict[str, Any]]:
        """
        List file sources for a user

        Args:
            user_id: ID of the user

        Returns:
            List of file sources
        """
        try:
            # Get files from staging area using the new method
            staged_files = await self.staging_manager.list_files(user_id)
            return staged_files

        except Exception as e:
            logger.error(f"Error listing file sources: {str(e)}")
            # Return empty list on error rather than raise
            return []