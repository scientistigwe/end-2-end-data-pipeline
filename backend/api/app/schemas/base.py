# schemas/base.py
from marshmallow import Schema, fields, validate

class BaseResponseSchema(Schema):
    """Base schema for common response fields"""
    id = fields.UUID(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    updated_at = fields.DateTime(dump_only=True)
    created_by = fields.UUID(dump_only=True)
    updated_by = fields.UUID(dump_only=True)

class BaseRequestSchema(Schema):
    """Base schema for common request fields"""
    pass