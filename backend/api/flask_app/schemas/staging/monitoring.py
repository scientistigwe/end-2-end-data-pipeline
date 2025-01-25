# schemas/staging/quality.py
from marshmallow import fields
from marshmallow.validate import OneOf
from .base import StagingRequestSchema, StagingResponseSchema

# schemas/components/monitoring.py
class MonitoringStagingRequestSchema(StagingRequestSchema):
   metrics = fields.List(fields.String(), required=True)
   aggregation = fields.String(validate=OneOf(['sum', 'avg', 'min', 'max']))
   time_window = fields.Dict(required=True)
   filters = fields.Dict()

class MonitoringStagingResponseSchema(StagingResponseSchema):
   results = fields.List(fields.Dict(
       metric=fields.String(),
       value=fields.Float(),
       timestamp=fields.DateTime()
   ))
   aggregates = fields.Dict()

class AlertStagingRequestSchema(StagingRequestSchema):
   alert_type = fields.String(required=True)
   severity = fields.String(validate=OneOf(['info', 'warning', 'critical']))
   conditions = fields.Dict(required=True)
   notification_config = fields.Dict()

class AlertStagingResponseSchema(StagingResponseSchema):
   alert_status = fields.String(validate=OneOf(['active', 'acknowledged', 'resolved']))
   triggered_at = fields.DateTime()
   acknowledged_by = fields.String(allow_none=True)
   resolved_by = fields.String(allow_none=True)