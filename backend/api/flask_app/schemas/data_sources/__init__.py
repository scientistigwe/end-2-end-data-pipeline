# schemas/data_sources/__init__.py
from .base import DataSourceSchema
from .api_source import APISourceRequestSchema, APISourceResponseSchema, APIUploadResponseSchema, APIUploadRequestSchema, APIMetadataResponseSchema
from .database_source import DatabaseSourceRequestSchema, DatabaseSourceResponseSchema, DBUploadRequestSchema, DBMetadataResponseSchema, DBUploadResponseSchema
from .file_source import FileSourceRequestSchema, FileSourceResponseSchema, FileUploadRequestSchema, FileUploadResponseSchema, FileMetadataResponseSchema
from .s3_source import S3SourceRequestSchema, S3SourceResponseSchema, S3UploadRequestSchema, S3MetadataResponseSchema, S3UploadResponseSchema
from .stream_source import StreamSourceRequestSchema, StreamSourceResponseSchema, StreamUploadRequestSchema, StreamMetadataResponseSchema, StreamUploadResponseSchema

__all__ = [
   'APISourceRequestSchema', 'APISourceResponseSchema',
   'APIUploadRequestSchema', 'APIUploadResponseSchema',
   'APIMetadataResponseSchema',

   'DatabaseSourceRequestSchema', 'DatabaseSourceResponseSchema',
   'DBUploadRequestSchema', 'DBUploadResponseSchema',
   'DBMetadataResponseSchema',

   'FileSourceRequestSchema', 'FileSourceResponseSchema',
   'FileUploadRequestSchema', 'FileUploadResponseSchema',
   'FileMetadataResponseSchema',

   'S3SourceRequestSchema', 'S3SourceResponseSchema',
   'S3UploadRequestSchema', 'S3UploadResponseSchema',
   'S3MetadataResponseSchema',

   'StreamSourceRequestSchema', 'StreamSourceResponseSchema',
   'StreamUploadRequestSchema', 'StreamUploadResponseSchema',
   'StreamMetadataResponseSchema'
]