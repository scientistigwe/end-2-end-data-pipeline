# schemas/decisions.py
from marshmallow import Schema, fields, validate
from .base import BaseRequestSchema, BaseResponseSchema

class DecisionRequestSchema(BaseRequestSchema):
   """Schema for decision request."""
   pipeline_id = fields.UUID(required=True)
   type = fields.String(required=True)
   priority = fields.String(validate=validate.OneOf(['low', 'medium', 'high', 'critical']))
   deadline = fields.DateTime(required=False)
   context = fields.Dict(required=True)

class DecisionResponseSchema(BaseResponseSchema):
   """Schema for decision response."""
   id = fields.UUID(dump_only=True)
   pipeline_id = fields.UUID()
   type = fields.String()
   status = fields.String(validate=validate.OneOf(['pending', 'approved', 'rejected', 'deferred']))
   priority = fields.String()
   deadline = fields.DateTime()
   meta_info = fields.Dict()
   impact_analysis = fields.Dict()
   created_at = fields.DateTime(dump_only=True)
   updated_at = fields.DateTime(dump_only=True)

class DecisionListResponseSchema(BaseResponseSchema):
   """Schema for list of decisions response."""
   decisions = fields.List(fields.Nested(DecisionResponseSchema))
   total_count = fields.Integer()
   pending_count = fields.Integer()

class DecisionHistoryResponseSchema(BaseResponseSchema):
   """Schema for decision history response."""
   history = fields.List(fields.Dict(
       action=fields.String(),
       previous_status=fields.String(),
       new_status=fields.String(),
       user_id=fields.UUID(),
       timestamp=fields.DateTime(),
       meta_data=fields.Dict()
   ))

class DecisionImpactResponseSchema(BaseResponseSchema):
   """Schema for decision impact analysis response."""
   impact = fields.Dict(
       severity=fields.String(validate=validate.OneOf(['low', 'medium', 'high', 'critical'])),
       affected_components=fields.List(fields.String()),
       risk_assessment=fields.Dict(),
       recommendations=fields.List(fields.Dict()),
       metrics=fields.Dict()
   )

class DecisionFeedbackRequestSchema(BaseRequestSchema):
   """Schema for decision feedback request."""
   rating = fields.Integer(validate=validate.Range(min=1, max=5))
   comment = fields.String()
   metrics = fields.Dict()
   suggestions = fields.List(fields.String())

class DecisionFeedbackResponseSchema(BaseResponseSchema):
   """Schema for decision feedback response."""
   id = fields.UUID(dump_only=True)
   decision_id = fields.UUID()
   user_id = fields.UUID()
   rating = fields.Integer()
   comment = fields.String()
   metrics = fields.Dict()
   suggestions = fields.List(fields.String())
   created_at = fields.DateTime(dump_only=True)

class DecisionOptionSchema(BaseRequestSchema):
   """Schema for decision options."""
   name = fields.String(required=True)
   description = fields.String()
   impact_score = fields.Float()
   risks = fields.Dict()
   benefits = fields.Dict()
   is_selected = fields.Boolean(default=False)

class DecisionCommentSchema(BaseRequestSchema):
   """Schema for decision comments."""
   content = fields.String(required=True)
   parent_id = fields.UUID()
   attachments = fields.List(fields.Dict())