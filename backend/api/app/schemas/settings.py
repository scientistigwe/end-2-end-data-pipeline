# schemas/settings.py
from marshmallow import Schema, fields, validate
from .base import BaseRequestSchema, BaseResponseSchema

class UserSettingsRequestSchema(BaseRequestSchema):
   """Schema for updating user settings."""
   preferences = fields.Dict(required=False)
   appearance = fields.Dict(required=False)
   notifications = fields.Dict(required=False)
   privacy = fields.Dict(required=False)
   shortcuts = fields.Dict(required=False)
   analytics = fields.Dict(required=False)

class UserSettingsResponseSchema(BaseResponseSchema):
   """Schema for user settings response."""
   user_id = fields.UUID()
   preferences = fields.Dict()
   appearance = fields.Dict()
   notifications = fields.Dict()
   privacy = fields.Dict()
   shortcuts = fields.Dict()
   analytics = fields.Dict()

class UserPreferencesUpdateSchema(BaseRequestSchema):
   """Schema for updating specific preferences."""
   language = fields.String(validate=validate.OneOf(['en', 'es', 'fr']))
   timezone = fields.String()
   date_format = fields.String()
   time_format = fields.String()
   currency = fields.String()

class NotificationSettingsSchema(BaseRequestSchema):
   """Schema for notification settings."""
   email_enabled = fields.Boolean()
   push_enabled = fields.Boolean()
   frequency = fields.String(validate=validate.OneOf(['instant', 'daily', 'weekly']))
   types = fields.List(fields.String())

class AppearanceSettingsSchema(BaseRequestSchema):
   """Schema for appearance settings."""
   theme = fields.String(validate=validate.OneOf(['light', 'dark', 'system']))
   font_size = fields.String(validate=validate.OneOf(['small', 'medium', 'large']))
   color_scheme = fields.String()

class SecuritySettingsRequestSchema(BaseRequestSchema):
   """Schema for security settings."""
   two_factor_enabled = fields.Boolean()
   login_alerts = fields.Boolean()
   trusted_devices = fields.List(fields.Dict())
   session_timeout = fields.Integer()

class SecuritySettingsResponseSchema(BaseResponseSchema):
   """Schema for security settings response."""
   two_factor_enabled = fields.Boolean()
   login_alerts = fields.Boolean()
   trusted_devices = fields.List(fields.Dict())
   session_timeout = fields.Integer()
   last_password_change = fields.DateTime()
   security_questions = fields.List(fields.Dict())

class SystemSettingsRequestSchema(BaseRequestSchema):
   """Schema for system settings updates."""
   key = fields.String(required=True)
   value = fields.Dict(required=True)
   description = fields.String()
   is_encrypted = fields.Boolean(default=False)
   category = fields.String(validate=validate.OneOf([
       'security', 'performance', 'integration', 'monitoring'
   ]))

class SystemSettingsResponseSchema(BaseResponseSchema):
   """Schema for system settings response."""
   key = fields.String()
   value = fields.Dict()
   description = fields.String()
   is_encrypted = fields.Boolean()
   category = fields.String()
   last_modified = fields.DateTime()
   modified_by = fields.UUID()

class IntegrationSettingsSchema(BaseRequestSchema):
   """Schema for integration settings."""
   provider = fields.String(required=True)
   config = fields.Dict(required=True)
   enabled = fields.Boolean(default=True)
   credentials = fields.Dict(load_only=True)

class ValidationRequestSchema(BaseRequestSchema):
   """Schema for settings validation."""
   settings = fields.Dict(required=True)
   context = fields.Dict(required=False)

class ValidationResponseSchema(BaseResponseSchema):
   """Schema for validation response."""
   is_valid = fields.Boolean()
   errors = fields.List(fields.Dict())
   warnings = fields.List(fields.Dict())
   suggestions = fields.List(fields.String())