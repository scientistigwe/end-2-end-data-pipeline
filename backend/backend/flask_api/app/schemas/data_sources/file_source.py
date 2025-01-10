# schemas/data_sources/file_source.py
from marshmallow import Schema, fields, validate
from ..base import BaseRequestSchema, BaseResponseSchema

# In schemas/data_sources/file_source.py
from marshmallow import Schema, fields, validate, post_load


class FileSourceConfigSchema(BaseRequestSchema):
   original_filename = fields.String(required=True)
   file_type = fields.String(required=True, validate=validate.OneOf(['csv', 'json', 'xlsx', 'parquet']))
   mime_type = fields.String()
   size = fields.Integer()
   hash = fields.String()  # For integrity checking
   encoding = fields.String()

   # New fields to match the payload
   delimiter = fields.String(required=False)
   compression = fields.String(
      validate=validate.OneOf(['gzip', 'zip', None]),
      allow_none=True
   )

   # Additional fields for CSV parsing
   parse_options = fields.Dict(keys=fields.String(), values=fields.Raw(), required=False)

   @post_load
   def process_config(self, data, **kwargs):
      # Remove any keys with None values
      return {k: v for k, v in data.items() if v is not None}

class FileSourceResponseSchema(BaseResponseSchema):
   location = fields.String()
   status = fields.String(validate=validate.OneOf(['active', 'archived', 'deleted']))
   last_modified = fields.DateTime()
   row_count = fields.Integer()

class FileUploadRequestSchema(BaseRequestSchema):
   """Schema for file upload request validation"""
   filename = fields.String(required=True)
   content_type = fields.String(required=False)
   type = fields.String(validate=validate.OneOf(['csv', 'json', 'xlsx', 'parquet']))
   chunk_size = fields.Integer()
   total_chunks = fields.Integer()
   current_chunk = fields.Integer()
   description = fields.String()
   tags = fields.List(fields.String())

class FileMetadataResponseSchema(BaseResponseSchema):
   """Schema for file metadata response"""
   metadata = fields.Dict(keys=fields.String(), values=fields.Raw())
   file_size = fields.Integer()
   mime_type = fields.String()
   created_at = fields.DateTime()
   modified_at = fields.DateTime()
   checksum = fields.String()
   encoding = fields.String()
   line_count = fields.Integer()
   headers = fields.List(fields.String())  # For CSV/Excel files
   sheet_names = fields.List(fields.String())  # For Excel files
   preview_data = fields.List(fields.Dict())  # Sample of file content
   processing_status = fields.String(validate=validate.OneOf([
       'pending', 'processing', 'completed', 'failed'
   ]))