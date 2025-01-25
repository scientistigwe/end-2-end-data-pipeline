# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime

# schemas/auth/audit.py
class AuditLogSchema(StagingResponseSchema):
    action = fields.String()
    actor_id = fields.UUID()
    actor_type = fields.String()
    target_id = fields.UUID()
    target_type = fields.String()
    changes = fields.Dict()
    ip_address = fields.String()
    user_agent = fields.String()
    metadata = fields.Dict()