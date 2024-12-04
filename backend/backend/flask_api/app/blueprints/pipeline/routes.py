# app/blueprints/pipeline/routes.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from ...schemas.pipeline import PipelineConfigSchema, PipelineStatusSchema
from ...utils.response_builder import ResponseBuilder
import logging

logger = logging.getLogger(__name__)
pipeline_bp = Blueprint('pipeline', __name__)

@pipeline_bp.route('/start', methods=['POST'])
@jwt_required()
def start_pipeline():
    try:
        schema = PipelineConfigSchema()
        config = schema.load(request.get_json())
        pipeline_id = pipeline_service.start_pipeline(config)
        return ResponseBuilder.success({'pipeline_id': pipeline_id})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@pipeline_bp.route('/<pipeline_id>/status', methods=['GET'])
@jwt_required()
def get_pipeline_status(pipeline_id):
    try:
        status = pipeline_service.get_pipeline_status(pipeline_id)
        return ResponseBuilder.success({'status': status})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@pipeline_bp.route('/<pipeline_id>/stop', methods=['POST'])
@jwt_required()
def stop_pipeline(pipeline_id):
    try:
        pipeline_service.stop_pipeline(pipeline_id)
        return ResponseBuilder.success({'message': 'Pipeline stopped successfully'})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@pipeline_bp.route('/<pipeline_id>/logs', methods=['GET'])
@jwt_required()
def get_pipeline_logs(pipeline_id):
    try:
        logs = pipeline_service.get_pipeline_logs(pipeline_id)
        return ResponseBuilder.success({'logs': logs})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)