# schemas/components/settings.py
from marshmallow import fields
from marshmallow.validate import OneOf
from ..staging.base import StagingRequestSchema, StagingResponseSchema


class SettingsStagingRequestSchema(StagingRequestSchema):
   category = fields.String(validate=OneOf([
       'user', 'system', 'security', 'notifications',
       'appearance', 'integrations'
   ]))
   settings = fields.Dict(required=True)
   overrides = fields.Dict()
   scope = fields.String(validate=OneOf(['global', 'user', 'pipeline']))

class SettingsStagingResponseSchema(StagingResponseSchema):
   applied_settings = fields.Dict()
   effective_settings = fields.Dict()
   override_history = fields.List(fields.Dict())

