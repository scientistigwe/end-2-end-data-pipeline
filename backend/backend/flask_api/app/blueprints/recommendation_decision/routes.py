# app/blueprints/recommendations/routes.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from ...schemas.recommendations import (
    RecommendationSchema, DecisionSchema,
    DecisionFeedbackSchema
)
from ...utils.response_builder import ResponseBuilder
import logging

logger = logging.getLogger(__name__)
recommendation_bp = Blueprint('recommendations', __name__)

# Recommendation Routes
@recommendation_bp.route('/recommendations/<pipeline_id>', methods=['GET'])
@jwt_required()
def get_recommendations(pipeline_id):
    try:
        recommendations = recommendation_service.get_pipeline_recommendations(pipeline_id)
        return ResponseBuilder.success({'recommendations': recommendations})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)

@recommendation_bp.route('/recommendations/apply', methods=['POST'])
@jwt_required()
def apply_recommendation():
    try:
        schema = RecommendationSchema()
        data = schema.load(request.get_json())
        result = recommendation_service.apply_recommendation(data)
        return ResponseBuilder.success(result)
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@recommendation_bp.route('/recommendations/status/<recommendation_id>', methods=['GET'])
@jwt_required()
def get_recommendation_status(recommendation_id):
    try:
        status = recommendation_service.get_recommendation_status(recommendation_id)
        return ResponseBuilder.success({'status': status})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)

# Decision Routes
@recommendation_bp.route('/decisions/pending/<pipeline_id>', methods=['GET'])
@jwt_required()
def get_pending_decisions(pipeline_id):
    try:
        decisions = decision_service.get_pending_decisions(pipeline_id)
        return ResponseBuilder.success({'decisions': decisions})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)

@recommendation_bp.route('/decisions/make', methods=['POST'])
@jwt_required()
def make_decision():
    try:
        schema = DecisionSchema()
        data = schema.load(request.get_json())
        result = decision_service.make_decision(data)
        return ResponseBuilder.success(result)
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@recommendation_bp.route('/decisions/feedback', methods=['POST'])
@jwt_required()
def provide_decision_feedback():
    try:
        schema = DecisionFeedbackSchema()
        data = schema.load(request.get_json())
        result = decision_service.process_feedback(data)
        return ResponseBuilder.success(result)
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@recommendation_bp.route('/decisions/history/<pipeline_id>', methods=['GET'])
@jwt_required()
def get_decision_history(pipeline_id):
    try:
        history = decision_service.get_decision_history(pipeline_id)
        return ResponseBuilder.success({'history': history})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)

@recommendation_bp.route('/decisions/impact/<decision_id>', methods=['GET'])
@jwt_required()
def get_decision_impact(decision_id):
    try:
        impact = decision_service.get_decision_impact(decision_id)
        return ResponseBuilder.success({'impact': impact})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)