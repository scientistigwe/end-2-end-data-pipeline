# schemas/components/recommendations.py
from marshmallow import fields
from marshmallow.validate import OneOf
from .base import StagingRequestSchema, StagingResponseSchema

class RecommendationStagingRequestSchema(StagingRequestSchema):
    type = fields.String(required=True)
    context = fields.Dict(required=True)
    constraints = fields.Dict()
    priority = fields.String(validate=OneOf(['low', 'medium', 'high', 'critical']))
    target_metrics = fields.List(fields.String())


class RecommendationStagingResponseSchema(StagingResponseSchema):
    recommendations = fields.List(fields.Dict())
    confidence_scores = fields.Dict()
    impact_analysis = fields.Dict()
    priority_ranking = fields.Dict()


