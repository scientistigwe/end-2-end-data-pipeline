# schemas/data_sources/file_source.py
from marshmallow import fields, validates_schema, validate
from marshmallow.validate import OneOf, ValidationError
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
    status = fields.String(required=True, validate=OneOf([
        'success', 'error', 'in_progress'
    ]))
    staged_id = fields.String(required=True)
    control_point_id = fields.String(required=True)
    tracking_url = fields.String(required=True)
    upload_status = fields.String(validate=OneOf([
        'in_progress', 'completed', 'failed'
    ]), required=False)
    error = fields.String(required=False, allow_none=True)
    message = fields.String(required=False, allow_none=True)


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


class FileSourceConfigSchema(StagingRequestSchema):
    """Schema for file source configuration and validation"""
    file_type = fields.String(required=True, validate=OneOf([
        'csv', 'json', 'xlsx', 'parquet', 'xml', 'txt'
    ]))

    # File Processing Settings
    encoding = fields.String(default='utf-8')
    delimiter = fields.String(allow_none=True)
    compression = fields.String(validate=OneOf(['gzip', 'zip', 'bzip2', None]), allow_none=True)
    chunk_size = fields.Integer(default=1024 * 1024)  # 1MB default

    # CSV Specific Settings
    has_header = fields.Boolean(default=True)
    skip_rows = fields.Integer(default=0)
    comment_char = fields.String(allow_none=True)
    quoting = fields.String(validate=OneOf(['minimal', 'all', 'none']), default='minimal')

    # Excel Specific Settings
    sheet_name = fields.String(allow_none=True)
    sheet_index = fields.Integer(allow_none=True)
    header_row = fields.Integer(default=0)

    # Validation Settings
    validate_schema = fields.Boolean(default=True)
    max_file_size = fields.Integer()  # In bytes
    allowed_extensions = fields.List(fields.String())
    required_columns = fields.List(fields.String(), allow_none=True)

    # Storage Settings
    storage_format = fields.String(validate=OneOf(['csv', 'parquet', 'json']), default='parquet')
    partition_by = fields.List(fields.String(), allow_none=True)

    @validates_schema
    def validate_file_config(self, data: Dict[str, Any], **kwargs) -> None:
        # Set default delimiter for CSV files
        if data['file_type'] == 'csv' and not data.get('delimiter'):
            data['delimiter'] = ','

        # Sheet name or index required for Excel files
        if data['file_type'] == 'xlsx' and not (data.get('sheet_name') or data.get('sheet_index') is not None):
            raise ValidationError("Either sheet_name or sheet_index must be provided for Excel files")

        # Validate partition columns exist in required columns
        if data.get('partition_by') and data.get('required_columns'):
            invalid_partitions = set(data['partition_by']) - set(data['required_columns'])
            if invalid_partitions:
                raise ValidationError(f"Partition columns {invalid_partitions} not found in required columns")