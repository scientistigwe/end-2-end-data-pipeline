# schemas/staging/decisions.py

from marshmallow import Schema, fields, validates_schema, ValidationError
from marshmallow.validate import OneOf
from marshmallow_enum import EnumField
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional

from .base import (
    StagingRequestSchema,
    StagingResponseSchema,
    BaseStagingSchema
)
from core.messaging.event_types import (
    MessageType,
    ComponentType,
    ProcessingStatus
)


class DecisionMessageType(Enum):
    """Decision types based on system message types"""
    START = MessageType.DECISION_START.value
    REQUEST = MessageType.DECISION_REQUEST.value
    OPTIONS = MessageType.DECISION_OPTIONS.value
    SUBMIT = MessageType.DECISION_SUBMIT.value
    VALIDATE = MessageType.DECISION_VALIDATE_RESULT.value
    IMPACT = MessageType.DECISION_IMPACT.value
    UPDATE = MessageType.DECISION_UPDATE.value
    COMPLETE = MessageType.DECISION_COMPLETE.value
    FEEDBACK = MessageType.DECISION_FEEDBACK.value


class FeedbackMessageType(Enum):
    """Feedback types based on system message types"""
    SUBMIT = MessageType.DECISION_FEEDBACK.value
    REQUEST = MessageType.DECISION_FEEDBACK_REQUEST.value
    QUALITY = "quality.feedback"
    INSIGHT = "insight.feedback"
    IMPACT = "impact.feedback"
    PROCESS = "process.feedback"
    GENERAL = "general.feedback"


class DecisionItemSchema(BaseStagingSchema):
    """Schema for individual decision items"""
    decision_id = fields.String(required=True)
    pipeline_id = fields.String(required=True)
    decision_type = EnumField(DecisionMessageType, by_value=True, required=True)
    description = fields.String(required=True)
    context = fields.Dict(keys=fields.String(), values=fields.Raw())
    options = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()))
    deadline = fields.DateTime(allow_none=True)
    assigned_to = fields.String(allow_none=True)
    priority = fields.Integer(validate=lambda n: 0 <= n <= 10, default=5)
    impact_level = fields.String(validate=OneOf(['LOW', 'MEDIUM', 'HIGH']), default='MEDIUM')
    decision_status = EnumField(ProcessingStatus, by_value=True, default=ProcessingStatus.PENDING)
    decision_made_at = fields.DateTime(allow_none=True)
    made_by = fields.String(allow_none=True)
    rationale = fields.String(allow_none=True)
    tags = fields.List(fields.String(), default=list)
    component_type = EnumField(ComponentType, by_value=True, default=ComponentType.DECISION_PROCESSOR)


class DecisionListResponseSchema(Schema):
    """Schema for paginated decision list responses"""
    decisions = fields.List(fields.Nested(DecisionItemSchema), required=True)
    total = fields.Integer(required=True)
    page = fields.Integer(required=True)
    per_page = fields.Integer(required=True)

    @validates_schema
    def validate_pagination(self, data: Dict[str, Any], **kwargs) -> None:
        """Validate pagination parameters"""
        if data['page'] < 1:
            raise ValidationError('Page number must be greater than 0')
        if data['per_page'] < 1:
            raise ValidationError('Items per page must be greater than 0')


class DecisionHistoryItemSchema(BaseStagingSchema):
    """Schema for decision history entries"""
    history_id = fields.String(required=True)
    decision_id = fields.String(required=True)
    event_type = EnumField(DecisionMessageType, by_value=True, required=True)
    event_time = fields.DateTime(required=True)
    user_id = fields.String(required=True)
    changes = fields.Dict(keys=fields.String(), values=fields.Raw())
    previous_state = fields.Dict(allow_none=True)
    new_state = fields.Dict(allow_none=True)
    comments = fields.String(allow_none=True)
    staging_details = fields.Dict(allow_none=True)
    component_type = EnumField(ComponentType, by_value=True)


class DecisionHistoryResponseSchema(Schema):
    """Schema for decision history responses"""
    history = fields.List(fields.Nested(DecisionHistoryItemSchema), required=True)
    total_events = fields.Integer()
    first_event_time = fields.DateTime()
    last_event_time = fields.DateTime()


class ImpactMetricsSchema(Schema):
    """Schema for decision impact metrics"""
    efficiency_score = fields.Float()
    time_to_decision = fields.Float()
    implementation_success_rate = fields.Float()
    resource_utilization = fields.Dict(keys=fields.String(), values=fields.Float())
    cost_impact = fields.Dict(keys=fields.String(), values=fields.Float())
    quality_metrics = fields.Dict(keys=fields.String(), values=fields.Raw())
    performance_indicators = fields.Dict(keys=fields.String(), values=fields.Raw())


class DecisionImpactResponseSchema(Schema):
    """Schema for decision impact analysis responses"""
    decision_id = fields.String(required=True)
    impact = fields.Nested(ImpactMetricsSchema, required=True)
    analysis_time = fields.DateTime(required=True)
    confidence_score = fields.Float(validate=lambda n: 0 <= n <= 1)
    impact_factors = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()))
    recommendations = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()))
    staging_metrics = fields.Dict(allow_none=True)
    component_type = EnumField(ComponentType, by_value=True, default=ComponentType.DECISION_PROCESSOR)


class DecisionFeedbackRequestSchema(StagingRequestSchema):
    """Schema for decision feedback requests"""
    decision_id = fields.String(required=True)
    feedback_type = EnumField(FeedbackMessageType, by_value=True, required=True)
    feedback_text = fields.String(required=True)
    rating = fields.Integer(validate=lambda n: 1 <= n <= 5)
    impact_assessment = fields.Dict(keys=fields.String(), values=fields.Raw(), allow_none=True)
    suggested_improvements = fields.String(allow_none=True)
    attachments = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()), default=list)
    component_type = EnumField(ComponentType, by_value=True, default=ComponentType.DECISION_PROCESSOR)

    @validates_schema
    def validate_feedback(self, data: Dict[str, Any], **kwargs) -> None:
        """Validate feedback data"""
        if data['feedback_type'] == FeedbackMessageType.IMPACT and not data.get('impact_assessment'):
            raise ValidationError('Impact assessment is required for impact-type feedback')
        if len(data['feedback_text']) < 10:
            raise ValidationError('Feedback text must be at least 10 characters long')


class DecisionStagingRequestSchema(StagingRequestSchema):
    """Schema for decision staging requests"""
    decision_type = EnumField(DecisionMessageType, by_value=True, required=True)
    options = fields.List(fields.Dict(), required=True)
    criteria = fields.Dict(required=True)
    constraints = fields.Dict(default=dict)
    deadline = fields.DateTime(allow_none=True)
    component_type = EnumField(ComponentType, by_value=True, default=ComponentType.DECISION_PROCESSOR)


class DecisionStagingResponseSchema(StagingResponseSchema):
    """Schema for decision staging responses"""
    recommendation = fields.Dict(required=True)
    alternatives = fields.List(fields.Dict())
    impact_analysis = fields.Dict()
    confidence_score = fields.Float()
    rationale = fields.Dict()
    component_type = EnumField(ComponentType, by_value=True, default=ComponentType.DECISION_PROCESSOR)