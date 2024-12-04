# app/schemas/file.py
from marshmallow import Schema, fields, validate


class FileUploadRequestSchema(Schema):
    filename = fields.String(required=True)
    content_type = fields.String(required=False)


class FileMetadataResponseSchema(Schema):
    metadata = fields.Dict(keys=fields.String(), values=fields.Raw())
