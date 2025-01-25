# schemas/staging/quality.py
from marshmallow import fields
from marshmallow.validate import OneOf
from .base import StagingRequestSchema, StagingResponseSchema

# schemas/components/reports.py
class ReportStagingRequestSchema(StagingRequestSchema):
    report_type = fields.String(required=True)
    format = fields.String(validate=OneOf(['pdf', 'excel', 'csv', 'json']))
    sections = fields.List(fields.Dict())
    parameters = fields.Dict()
    template_id = fields.UUID(allow_none=True)


class ReportStagingResponseSchema(StagingResponseSchema):
    output_path = fields.String()
    sections = fields.List(fields.Dict())
    metrics = fields.Dict()
    visualizations = fields.List(fields.Dict())

