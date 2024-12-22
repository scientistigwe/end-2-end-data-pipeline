# schemas/analysis.py
from marshmallow import Schema, fields, validate
from .base import BaseRequestSchema, BaseResponseSchema

class QualityCheckRequestSchema(BaseRequestSchema):
    dataset_id = fields.UUID(required=True)
    type = fields.String(required=True)
    name = fields.String(required=True)
    config = fields.Dict(required=False)

class QualityCheckResponseSchema(BaseResponseSchema):
    pipeline_run_id = fields.UUID()
    status = fields.String(validate=validate.OneOf(['pending', 'running', 'completed', 'failed']))
    results = fields.Dict()
    score = fields.Float()
    impact = fields.String(validate=validate.OneOf(['low', 'medium', 'high', 'critical']))

class InsightAnalysisRequestSchema(BaseRequestSchema):
    pipeline_id = fields.UUID(required=True)
    type = fields.String(required=True)
    config = fields.Dict(required=False)

class InsightAnalysisResponseSchema(BaseResponseSchema):
    status = fields.String(validate=validate.OneOf(['pending', 'running', 'completed', 'failed']))
    results = fields.Dict()
    metrics = fields.Dict()