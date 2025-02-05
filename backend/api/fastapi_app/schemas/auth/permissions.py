# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime

# schemas/auth/permissions.py
class PermissionRequestSchema(StagingRequestSchema):
    name = fields.String(required=True)
    description = fields.String()
    resource_type = fields.String(required=True)
    actions = fields.List(fields.String(), required=True)
    conditions = fields.Dict()


class PermissionResponseSchema(StagingResponseSchema):
    name = fields.String()
    description = fields.String()
    resource_type = fields.String()
    actions = fields.List(fields.String())
    conditions = fields.Dict()
    roles = fields.List(fields.String())


