# schemas/data_sources/__init__.py
from .base import DataSourceSchema
from .api_source import (
    APISourceRequestSchema, APISourceResponseSchema,
    APIUploadResponseSchema, APIUploadRequestSchema,
    APIMetadataResponseSchema, APISourceConfigSchema  # Add this
)
from .database_source import (
    DatabaseSourceRequestSchema, DatabaseSourceResponseSchema,
    DBUploadRequestSchema, DBMetadataResponseSchema,
    DBUploadResponseSchema, DatabaseSourceConfigSchema  # Add this
)
from .file_source import (
    FileSourceRequestSchema, FileSourceResponseSchema,
    FileUploadRequestSchema, FileUploadResponseSchema,
    FileMetadataResponseSchema, FileSourceConfigSchema
)
from .s3_source import (
    S3SourceRequestSchema, S3SourceResponseSchema,
    S3UploadRequestSchema, S3MetadataResponseSchema,
    S3UploadResponseSchema, S3SourceConfigSchema  # Add this
)
from .stream_source import (
    StreamSourceRequestSchema, StreamSourceResponseSchema,
    StreamUploadRequestSchema, StreamMetadataResponseSchema,
    StreamUploadResponseSchema, StreamSourceConfigSchema  # Add this
)

__all__ = [
   # API Schemas
   'APISourceRequestSchema', 'APISourceResponseSchema',
   'APIUploadRequestSchema', 'APIUploadResponseSchema',
   'APIMetadataResponseSchema', 'APISourceConfigSchema',  # Add this

   # Database Schemas
   'DatabaseSourceRequestSchema', 'DatabaseSourceResponseSchema',
   'DBUploadRequestSchema', 'DBUploadResponseSchema',
   'DBMetadataResponseSchema', 'DatabaseSourceConfigSchema',  # Add this

   # File Schemas
   'FileSourceRequestSchema', 'FileSourceResponseSchema',
   'FileUploadRequestSchema', 'FileUploadResponseSchema',
   'FileMetadataResponseSchema', 'FileSourceConfigSchema',

   # S3 Schemas
   'S3SourceRequestSchema', 'S3SourceResponseSchema',
   'S3UploadRequestSchema', 'S3UploadResponseSchema',
   'S3MetadataResponseSchema', 'S3SourceConfigSchema',  # Add this

   # Stream Schemas
   'StreamSourceRequestSchema', 'StreamSourceResponseSchema',
   'StreamUploadRequestSchema', 'StreamUploadResponseSchema',
   'StreamMetadataResponseSchema', 'StreamSourceConfigSchema'  # Add this
]