# schemas/validation.py
from marshmallow import Schema, fields, validate
from .base import BaseRequestSchema, BaseResponseSchema

class ValidationResultRequestSchema(BaseRequestSchema):
    name = fields.String(required=True)
    type = fields.String(required=True)
    source_id = fields.UUID(required=True)

class ValidationResultResponseSchema(BaseResponseSchema):
    status = fields.String(validate=validate.OneOf(['passed', 'failed', 'warning']))
    results = fields.Dict()
    error_count = fields.Integer()
    warning_count = fields.Integer()
    error_details = fields.Dict()
    impact_score = fields.Float()