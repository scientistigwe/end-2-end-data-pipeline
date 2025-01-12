# schemas/report_model.py
from marshmallow import Schema, fields, validate
from .base import BaseRequestSchema, BaseResponseSchema

class ReportRequestSchema(BaseRequestSchema):
    """Schema for creating/updating reports."""
    title = fields.String(required=True)
    description = fields.String()
    type = fields.String(required=True)
    format = fields.String(validate=validate.OneOf(['pdf', 'excel', 'csv']))
    parameters = fields.Dict(required=False)

class ReportResponseSchema(BaseResponseSchema):
    """Schema for report responses."""
    title = fields.String()
    description = fields.String()
    type = fields.String()
    format = fields.String()
    status = fields.String(validate=validate.OneOf(['draft', 'generating', 'completed', 'failed']))
    config = fields.Dict()
    report_meta = fields.Dict()
    owner_id = fields.UUID(dump_only=True)

class ReportScheduleRequestSchema(BaseRequestSchema):
    """Schema for scheduling reports."""
    report_id = fields.UUID(required=True)
    frequency = fields.String(validate=validate.OneOf(['daily', 'weekly', 'monthly']))
    cron_expression = fields.String(required=True)
    timezone = fields.String()
    parameters = fields.Dict()

class ReportScheduleResponseSchema(BaseResponseSchema):
    """Schema for schedule responses."""
    report_id = fields.UUID()
    frequency = fields.String()
    cron_expression = fields.String()
    timezone = fields.String()
    is_active = fields.Boolean()
    next_run = fields.DateTime()
    last_run = fields.DateTime()
    parameters = fields.Dict()

class ReportTemplateRequestSchema(BaseRequestSchema):
    """Schema for report templates."""
    name = fields.String(required=True)
    description = fields.String()
    type = fields.String(required=True)
    content = fields.Dict(required=True)
    parameters = fields.Dict()

class ReportTemplateResponseSchema(BaseResponseSchema):
    """Schema for template responses."""
    name = fields.String()
    description = fields.String()
    type = fields.String()
    content = fields.Dict()
    parameters = fields.Dict()
    is_active = fields.Boolean()

class ReportGenerationRequestSchema(BaseRequestSchema):
    """Schema for report generation requests."""
    template_id = fields.UUID(required=False)
    parameters = fields.Dict(required=False)
    format = fields.String(validate=validate.OneOf(['pdf', 'excel', 'csv']))
    options = fields.Dict()

class ReportGenerationResponseSchema(BaseResponseSchema):
    """Schema for generation responses."""
    status = fields.String(validate=validate.OneOf(['pending', 'processing', 'completed', 'failed']))
    progress = fields.Float()
    output_url = fields.String()
    error = fields.String()