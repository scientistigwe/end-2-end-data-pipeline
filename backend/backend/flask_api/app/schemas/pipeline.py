 # app/schemas/pipeline.py
from marshmallow import Schema, fields, validate


class PipelineStartRequestSchema(Schema):
    source_type = fields.String(required=True, validate=validate.OneOf(['file', 'api', 'stream']))
    config = fields.Dict(required=True)


class PipelineStatusResponseSchema(Schema):
    pipelines = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()))


class PipelineLogResponseSchema(Schema):
    logs = fields.List(fields.Dict(keys=fields.String(), values=fields.Raw()))

