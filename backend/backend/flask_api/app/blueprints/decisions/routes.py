# app/blueprints/decisions/routes.py
from flask import Blueprint, request, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from ...schemas.decisions import (
   DecisionRequestSchema,
   DecisionResponseSchema,
   DecisionFeedbackRequestSchema,
   DecisionFeedbackResponseSchema,
   DecisionHistoryResponseSchema,
   DecisionImpactResponseSchema,
   DecisionListResponseSchema
)
from ...services.decision_recommendation import DecisionService
from ...utils.response_builder import ResponseBuilder
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
decision_bp = Blueprint('decisions', __name__)

def get_service():
   """Get decision service instance."""
   if 'decision_service' not in g:
       g.decision_service = DecisionService(g.db)
   return g.decision_service

@decision_bp.route('/', methods=['GET'])
@jwt_required()
def list_decisions():
   """List all decisions."""
   try:
       decision_service = get_service()
       filters = request.args.to_dict()
       decisions = decision_service.list_decisions(filters)
       return ResponseBuilder.success(
           DecisionListResponseSchema().dump({'decisions': decisions})
       )
   except Exception as e:
       logger.error(f"Error listing decisions: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to list decisions", status_code=500)

@decision_bp.route('/<pipeline_id>/pending', methods=['GET'])
@jwt_required()
def get_pending_decisions(pipeline_id):
   """Get pending decisions for a pipeline."""
   try:
       decision_service = get_service()
       decisions = decision_service.get_pending_decisions(UUID(pipeline_id))
       return ResponseBuilder.success(
           DecisionListResponseSchema().dump({'decisions': decisions})
       )
   except ValueError:
       return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
   except Exception as e:
       logger.error(f"Error getting pending decisions: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to get pending decisions", status_code=500)

@decision_bp.route('/<decision_id>/make', methods=['POST'])
@jwt_required()
def make_decision(decision_id):
   """Make a decision."""
   try:
       decision_service = get_service()
       schema = DecisionRequestSchema()
       data = schema.load(request.get_json())
       data['user_id'] = get_jwt_identity()
       
       result = decision_service.make_decision(UUID(decision_id), data)
       return ResponseBuilder.success(
           DecisionResponseSchema().dump(result)
       )
   except ValidationError as e:
       return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
   except ValueError:
       return ResponseBuilder.error("Invalid decision ID", status_code=400)
   except Exception as e:
       logger.error(f"Error making decision: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to make decision", status_code=500)

@decision_bp.route('/<decision_id>/feedback', methods=['POST'])
@jwt_required()
def provide_decision_feedback(decision_id):
   """Provide feedback for a decision."""
   try:
       decision_service = get_service()
       schema = DecisionFeedbackRequestSchema()
       data = schema.load(request.get_json())
       data['user_id'] = get_jwt_identity()
       
       result = decision_service.process_feedback(UUID(decision_id), data)
       return ResponseBuilder.success(
           DecisionFeedbackResponseSchema().dump(result)
       )
   except ValidationError as e:
       return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
   except ValueError:
       return ResponseBuilder.error("Invalid decision ID", status_code=400)
   except Exception as e:
       logger.error(f"Error processing feedback: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to process feedback", status_code=500)

@decision_bp.route('/<pipeline_id>/history', methods=['GET'])
@jwt_required()
def get_decision_history(pipeline_id):
   """Get decision history for a pipeline."""
   try:
       decision_service = get_service()
       filters = request.args.to_dict()
       history = decision_service.get_decision_history(UUID(pipeline_id), filters)
       return ResponseBuilder.success(
           DecisionHistoryResponseSchema().dump({'history': history})
       )
   except ValueError:
       return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
   except Exception as e:
       logger.error(f"Error getting decision history: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to get decision history", status_code=500)

@decision_bp.route('/<decision_id>/impact', methods=['GET'])
@jwt_required()
def get_decision_impact(decision_id):
   """Get impact analysis for a decision."""
   try:
       decision_service = get_service()
       impact = decision_service.get_decision_impact(UUID(decision_id))
       return ResponseBuilder.success(
           DecisionImpactResponseSchema().dump({'impact': impact})
       )
   except ValueError:
       return ResponseBuilder.error("Invalid decision ID", status_code=400)
   except Exception as e:
       logger.error(f"Error getting decision impact: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to get decision impact", status_code=500)

# Error handlers
@decision_bp.errorhandler(404)
def not_found_error(error):
   return ResponseBuilder.error("Resource not found", status_code=404)

@decision_bp.errorhandler(500)
def internal_error(error):
   logger.error(f"Internal error: {error}", exc_info=True)
   return ResponseBuilder.error("Internal server error", status_code=500)