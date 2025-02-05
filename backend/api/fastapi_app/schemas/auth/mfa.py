# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from .tokens import TokenResponseSchema
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime

# schemas/auth/mfa.py
class MFASetupRequestSchema(StagingRequestSchema):
    mfa_type = fields.String(validate=validate.OneOf(['fastapi_app', 'sms', 'email']))
    phone_number = fields.String()
    backup_codes = fields.List(fields.String())


class MFASetupResponseSchema(StagingResponseSchema):
    secret_key = fields.String()
    qr_code = fields.String()
    backup_codes = fields.List(fields.String())


class MFAVerifyRequestSchema(StagingRequestSchema):
    code = fields.String(required=True)
    mfa_type = fields.String()
    remember_device = fields.Boolean(default=False)


class MFAVerifyResponseSchema(StagingResponseSchema):
    verified = fields.Boolean()
    token = fields.Nested(TokenResponseSchema)
    device_token = fields.String()

