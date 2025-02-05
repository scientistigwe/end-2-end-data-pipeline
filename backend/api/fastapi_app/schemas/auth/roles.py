# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime

# schemas/auth/roles.py
class RoleRequestSchema(StagingRequestSchema):
    name = fields.String(required=True)
    description = fields.String()
    permissions = fields.List(fields.String(), required=True)
    scope = fields.String(validate=validate.OneOf(['global', 'tenant', 'user']))


class RoleResponseSchema(StagingResponseSchema):
    name = fields.String()
    description = fields.String()
    permissions = fields.List(fields.String())
    scope = fields.String()
    assigned_users = fields.Integer()

