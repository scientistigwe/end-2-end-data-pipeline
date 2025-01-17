# schemas/data_sources/s3_source.py
from marshmallow import Schema, fields, validate
from ..base import BaseRequestSchema, BaseResponseSchema

class S3SourceConfigSchema(BaseRequestSchema):
    bucket = fields.String(required=True)
    region = fields.String(required=True)
    prefix = fields.String()
    access_key = fields.String(required=True, load_only=True)
    secret_key = fields.String(required=True, load_only=True)
    encryption_config = fields.Dict()
    storage_class = fields.String()
    versioning_enabled = fields.Boolean()
    transfer_config = fields.Dict()

class S3SourceResponseSchema(BaseResponseSchema):
    total_objects = fields.Integer()
    total_size = fields.Integer()
    last_sync = fields.DateTime()