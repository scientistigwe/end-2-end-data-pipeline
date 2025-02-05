# schemas/staging/quality.py
from marshmallow import fields

from ..staging.base import StagingRequestSchema, StagingResponseSchema

# schemas/components/analytics.py
class AnalyticsStagingRequestSchema(StagingRequestSchema):
    model_type = fields.String(required=True)
    features = fields.List(fields.String(), required=True)
    parameters = fields.Dict(required=True)
    training_config = fields.Dict()


class AnalyticsStagingResponseSchema(StagingResponseSchema):
    model_artifacts = fields.Dict()
    performance_metrics = fields.Dict()
    feature_importance = fields.Dict()
    predictions = fields.List(fields.Dict())
