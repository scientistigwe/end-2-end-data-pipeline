# schemas/recommendations.py
from marshmallow import Schema, fields, validate
from .base import BaseRequestSchema, BaseResponseSchema

class RecommendationRequestSchema(BaseRequestSchema):
   """Schema for recommendation request."""
   pipeline_id = fields.UUID(required=True)
   type = fields.String(required=True)
   priority = fields.Integer(validate=validate.Range(min=1, max=5))
   description = fields.String(required=True)
   rationale = fields.String(required=True)
   action_details = fields.Dict(required=True)
   metrics = fields.Dict()
   tags = fields.List(fields.String())

class RecommendationResponseSchema(BaseResponseSchema):
   """Schema for recommendation response."""
   id = fields.UUID(dump_only=True)
   pipeline_id = fields.UUID()
   type = fields.String()
   status = fields.String(validate=validate.OneOf(['pending', 'applied', 'dismissed', 'failed']))
   priority = fields.Integer()
   confidence = fields.Float(validate=validate.Range(min=0, max=1))
   impact = fields.Float(validate=validate.Range(min=0, max=1))
   description = fields.String()
   rationale = fields.String()
   action_details = fields.Dict()
   metrics = fields.Dict()
   applied_at = fields.DateTime()
   applied_by = fields.UUID()
   dismissed_at = fields.DateTime()
   dismissed_by = fields.UUID()
   dismiss_reason = fields.String()
   created_at = fields.DateTime(dump_only=True)
   updated_at = fields.DateTime(dump_only=True)

class RecommendationListResponseSchema(BaseResponseSchema):
   """Schema for list of recommendations response."""
   recommendations = fields.List(fields.Nested(RecommendationResponseSchema))
   total_count = fields.Integer()
   pending_count = fields.Integer()
   filters_applied = fields.Dict()

class RecommendationStatusResponseSchema(BaseResponseSchema):
   """Schema for recommendation status response."""
   status = fields.String(validate=validate.OneOf(['pending', 'applied', 'dismissed', 'failed']))
   last_updated = fields.DateTime()
   metrics = fields.Dict()
   insights = fields.Dict()

class RecommendationApplyRequestSchema(BaseRequestSchema):
   """Schema for applying a recommendation."""
   options = fields.Dict()
   notes = fields.String()
   schedule_time = fields.DateTime()
   override_warnings = fields.Boolean(default=False)

class RecommendationDismissRequestSchema(BaseRequestSchema):
   """Schema for dismissing a recommendation."""
   reason = fields.String(required=True)
   additional_notes = fields.String()
   alternative_action = fields.String()

class RecommendationFeedbackRequestSchema(BaseRequestSchema):
   """Schema for recommendation feedback request."""
   recommendation_id = fields.UUID(required=True)
   rating = fields.Integer(required=True, validate=validate.Range(min=1, max=5))
   comment = fields.String()
   meta_data = fields.Dict()
   effectiveness = fields.Float(validate=validate.Range(min=0, max=1))
   improvement_suggestions = fields.List(fields.String())

class RecommendationFeedbackResponseSchema(BaseResponseSchema):
   """Schema for recommendation feedback response."""
   id = fields.UUID(dump_only=True)
   recommendation_id = fields.UUID()
   user_id = fields.UUID()
   rating = fields.Integer()
   comment = fields.String()
   meta_data = fields.Dict()
   effectiveness = fields.Float()
   improvement_suggestions = fields.List(fields.String())
   created_at = fields.DateTime(dump_only=True)

class RecommendationInsightSchema(BaseResponseSchema):
   """Schema for recommendation insights."""
   success_rate = fields.Float()
   average_impact = fields.Float()
   implementation_time = fields.Integer()  # in minutes
   feedback_summary = fields.Dict()
   common_issues = fields.List(fields.String())
   trending_patterns = fields.Dict()

class RecommendationBatchRequestSchema(BaseRequestSchema):
   """Schema for batch recommendation operations."""
   recommendation_ids = fields.List(fields.UUID(), required=True)
   action = fields.String(validate=validate.OneOf(['apply', 'dismiss', 'delay']))
   options = fields.Dict()
   notes = fields.String()