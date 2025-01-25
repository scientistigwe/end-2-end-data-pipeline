# schemas/auth/base.py
from marshmallow import Schema, fields, validate, ValidationError
from ..staging.base import StagingRequestSchema, StagingResponseSchema
from datetime import datetime


def password_validator(password):
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters long")
    if not any(char.isupper() for char in password):
        raise ValidationError("Must contain uppercase letter")
    if not any(char.islower() for char in password):
        raise ValidationError("Must contain lowercase letter")
    if not any(char.isdigit() for char in password):
        raise ValidationError("Must contain number")
    if not any(char in "!@#$%^&*()_+-=[]{}|;:,.<>?" for char in password):
        raise ValidationError("Must contain special character")


def name_validator(name):
    if not name or not name.strip():
        raise ValidationError("Name cannot be empty")
    if not all(char.isalpha() or char.isspace() for char in name):
        raise ValidationError("Name can only contain letters and spaces")
    if len(name.strip()) < 2:
        raise ValidationError("Name must be at least 2 characters")

