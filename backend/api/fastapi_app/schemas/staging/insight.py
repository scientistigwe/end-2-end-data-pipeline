# schemas/components/insight.py
from marshmallow import fields
from marshmallow.validate import OneOf

from .base import StagingRequestSchema, StagingResponseSchema

class InsightStagingRequestSchema(StagingRequestSchema):
    analysis_config = fields.Dict(required=True)
    target_metrics = fields.List(fields.String(), required=True)
    insight_types = fields.List(fields.String(), validate=OneOf(['trend', 'anomaly', 'correlation', 'pattern']))
    time_window = fields.Dict(required=True)


class InsightStagingResponseSchema(StagingResponseSchema):
    insights = fields.List(fields.Dict())
    confidence_scores = fields.Dict()
    supporting_metrics = fields.Dict()
    impact_analysis = fields.Dict()

