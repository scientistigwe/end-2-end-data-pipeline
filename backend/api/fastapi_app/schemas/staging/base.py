# schemas/base.py - Updated with staging concerns
from marshmallow import Schema, fields, validates_schema, ValidationError
from marshmallow.validate import OneOf
from marshmallow_enum import EnumField
from datetime import datetime
from typing import Dict, Any

from core.messaging.event_types import (
    ComponentType,
    ProcessingStage,
    ProcessingStatus
)


class BaseStagingSchema(Schema):
    """Base schema for all ETL staging operations"""
    id = fields.String(required=True)
    pipeline_id = fields.String(required=True)
    stage = EnumField(ProcessingStage, by_value=True)
    status = EnumField(ProcessingStatus, by_value=True, default=ProcessingStatus.PENDING)
    component_type = EnumField(ComponentType, by_value=True)

    # Storage details
    storage_path = fields.String(allow_none=True)
    data_size = fields.Integer(default=0)
    expires_at = fields.DateTime(allow_none=True)
    is_temporary = fields.Boolean(default=True)

    # Metadata
    created_at = fields.DateTime(default=lambda: datetime.utcnow())
    updated_at = fields.DateTime(default=lambda: datetime.utcnow())
    metadata = fields.Dict(keys=fields.String(), values=fields.Raw(), default=dict)

    @validates_schema
    def validate_dates(self, data: Dict[str, Any], **kwargs) -> None:
        if data.get('expires_at') and data['expires_at'] < datetime.utcnow():
            raise ValidationError('Expiration date must be in the future')


class StagingRequestSchema(BaseStagingSchema):
    """Base schema for staging requests with processing config"""
    request_id = fields.String(required=True)
    user_id = fields.String(required=True)
    priority = fields.Integer(validate=lambda n: 0 <= n <= 10, default=5)

    # Processing config
    processing_config = fields.Dict(default=dict)
    validation_rules = fields.Dict(default=dict)
    error_handling = fields.Dict(default=dict)


class StagingResponseSchema(BaseStagingSchema):
    """Base schema for staging responses with processing results"""
    processed_at = fields.DateTime()
    processing_duration = fields.Float()
    error_details = fields.Dict(allow_none=True)
    warnings = fields.List(fields.String())
    metrics = fields.Dict()


class StagingStateSchema(Schema):
    """Schema for tracking staging state transitions"""
    event_id = fields.String(required=True)
    pipeline_id = fields.String(required=True)
    previous_status = EnumField(ProcessingStatus, by_value=True)
    new_status = EnumField(ProcessingStatus, by_value=True)
    transition_time = fields.DateTime()
    triggered_by = fields.String()
    reason = fields.String(allow_none=True)

    @validates_schema
    def validate_state_transition(self, data: Dict[str, Any], **kwargs) -> None:
        valid_transitions = {
            ProcessingStatus.PENDING: [ProcessingStatus.IN_PROGRESS, ProcessingStatus.FAILED],
            ProcessingStatus.IN_PROGRESS: [ProcessingStatus.COMPLETED, ProcessingStatus.FAILED,
                                           ProcessingStatus.PAUSED],
            ProcessingStatus.PAUSED: [ProcessingStatus.IN_PROGRESS, ProcessingStatus.FAILED],
            ProcessingStatus.COMPLETED: [ProcessingStatus.ARCHIVED],
            ProcessingStatus.FAILED: [ProcessingStatus.PENDING]
        }

        if data['new_status'] not in valid_transitions.get(data['previous_status'], []):
            raise ValidationError(f'Invalid state transition from {data["previous_status"]} to {data["new_status"]}')