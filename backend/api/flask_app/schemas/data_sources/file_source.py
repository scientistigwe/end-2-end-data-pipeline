# schemas/data_sources/file_source.py
from marshmallow import fields, validates_schema, validate
from marshmallow.validate import OneOf
from typing import Dict, Any

from ..staging.base import StagingRequestSchema, StagingResponseSchema


class FileUploadRequestSchema(StagingRequestSchema):
    """Schema for file upload requests"""
    filename = fields.String(required=True)
    content_type = fields.String(required=True)
    chunk_number = fields.Integer(required=True)
    total_chunks = fields.Integer(required=True)
    chunk_size = fields.Integer(required=True)
    total_size = fields.Integer(required=True)
    identifier = fields.String(required=True)  # Unique upload identifier


class FileUploadResponseSchema(StagingResponseSchema):
    """Schema for file upload responses"""
    upload_id = fields.String()
    chunks_received = fields.Integer()
    bytes_received = fields.Integer()
    upload_status = fields.String(validate=OneOf([
        'in_progress', 'completed', 'failed'
    ]))
    upload_url = fields.String(allow_none=True)
    next_chunk = fields.Integer(allow_none=True)


class FileSourceRequestSchema(StagingRequestSchema):
    """Schema for file data source requests"""
    original_filename = fields.String(required=True)
    file_type = fields.String(required=True, validate=OneOf(['csv', 'json', 'xlsx', 'parquet', 'xml']))
    mime_type = fields.String(required=True)
    encoding = fields.String(default='utf-8')

    # File Processing Config
    delimiter = fields.String(allow_none=True)
    compression = fields.String(validate=OneOf(['gzip', 'zip', 'bzip2', None]), allow_none=True)
    chunk_size = fields.Integer(default=1000)

    # Validation
    checksum = fields.String(allow_none=True)
    max_file_size = fields.Integer()  # bytes
    allowed_extensions = fields.List(fields.String())

    @validates_schema
    def validate_file_config(self, data: Dict[str, Any], **kwargs) -> None:
        if data['file_type'] == 'csv' and not data.get('delimiter'):
            data['delimiter'] = ','


class FileSourceResponseSchema(StagingResponseSchema):
    """Schema for file data source responses"""
    storage_location = fields.String()
    file_size = fields.Integer()  # bytes
    row_count = fields.Integer(allow_none=True)
    column_count = fields.Integer(allow_none=True)
    detected_encoding = fields.String()
    preview_data = fields.List(fields.Dict(), validate=lambda x: len(x) <= 5)
    processing_metrics = fields.Dict()


class FileMetadataResponseSchema(StagingResponseSchema):
   """Schema for file metadata response"""
   metadata = fields.Dict(keys=fields.String(), values=fields.Raw())
   file_size = fields.Integer()
   mime_type = fields.String()
   created_at = fields.DateTime()
   modified_at = fields.DateTime()
   checksum = fields.String()
   encoding = fields.String()
   line_count = fields.Integer()
   headers = fields.List(fields.String())
   sheet_names = fields.List(fields.String())
   preview_data = fields.List(fields.Dict())
   processing_status = fields.String(validate=validate.OneOf([
       'pending', 'processing', 'completed', 'failed'
   ]))