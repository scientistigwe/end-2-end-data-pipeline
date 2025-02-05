# schemas/staging/validation.py
from marshmallow import Schema, fields, validates_schema, ValidationError
from marshmallow.validate import OneOf
from marshmallow_enum import EnumField
from typing import Dict, Any

from core.messaging.event_types import ProcessingStage, ProcessingStatus
from .base import StagingRequestSchema, StagingResponseSchema

class ValidationRuleSchema(Schema):
   """Schema for individual validation rules"""
   rule_type = fields.String(required=True)
   field = fields.String(required=True)
   condition = fields.String(required=True)
   value = fields.Raw(required=True)
   severity = fields.String(validate=OneOf(['error', 'warning', 'info']))
   message = fields.String()

class ValidationRequestSchema(StagingRequestSchema):
   """Schema for validation requests"""
   target_type = fields.String(required=True)
   rules = fields.List(fields.Nested(ValidationRuleSchema), required=True)
   validation_context = fields.Dict()
   threshold = fields.Float(validate=lambda x: 0 <= x <= 1)

class ValidationResultSchema(Schema):
   """Schema for individual validation results"""
   rule_id = fields.String(required=True)
   passed = fields.Boolean(required=True)
   details = fields.Dict()
   severity = fields.String()
   message = fields.String()

class ValidationResponseSchema(StagingResponseSchema):
   """Schema for validation responses"""
   validation_id = fields.String(required=True)
   passed = fields.Boolean(required=True)
   results = fields.List(fields.Nested(ValidationResultSchema))
   validation_time = fields.DateTime()
   metrics = fields.Dict()

   @validates_schema
   def validate_results(self, data: Dict[str, Any], **kwargs) -> None:
       if not data['passed'] and not data.get('results'):
           raise ValidationError('Failed validation requires detailed results')