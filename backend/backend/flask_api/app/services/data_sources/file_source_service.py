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

class FileSourceService(BaseSourceService):
    def __init__(self):
        self.pipeline_service = FilePipelineService()

    def handle_file_upload(self, file: FileStorage, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Pass file to pipeline for processing."""
        try:
            # 1. Prepare data for pipeline
            file_data = {
                'file': file,
                'metadata': metadata,
                'user_id': metadata.get('user_id')
            }

            # 2. Send to pipeline service
            result = self.pipeline_service.handle_file_upload(file_data)

            return result

        except Exception as e:
            self.logger.error(f"Error passing file to pipeline: {str(e)}")
            raise ValueError(f"File upload failed: {str(e)}")