# schemas/data_sources/database_source.py
from marshmallow import Schema, fields, validate
from ..base import BaseRequestSchema, BaseResponseSchema

class DatabaseSourceConfigSchema(BaseRequestSchema):
    dialect = fields.String(required=True, validate=validate.OneOf(['postgresql', 'mysql', 'oracle', 'mssql']))
    host = fields.String(required=True)
    port = fields.Integer(required=True)
    database = fields.String(required=True)
    username = fields.String(required=True)
    password = fields.String(required=True, load_only=True)
    schema = fields.String()
    ssl_config = fields.Dict()
    pool_size = fields.Integer()
    max_overflow = fields.Integer()
    connection_timeout = fields.Integer()
    query_timeout = fields.Integer()

class DatabaseSourceResponseSchema(BaseResponseSchema):
    connection_status = fields.String(validate=validate.OneOf(['connected', 'disconnected', 'error']))
    last_connected = fields.DateTime()
    tables = fields.List(fields.String())