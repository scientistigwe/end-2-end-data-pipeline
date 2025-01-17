# app/blueprints/decisions/routes.py
from flask import Blueprint, request, g
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

def create_decision_blueprint(decision_service: DecisionService, db_session):
    """Create decision blueprint with all routes.
    
    Args:
        decision_service: Instance of DecisionService
        db_session: Database session
        
    Returns:
        Blueprint: Configured decision blueprint
    """
    decision_bp = Blueprint('decisions', __name__)

    @decision_bp.route('/', methods=['GET'])
    def list_decisions():
        """List all decisions."""
        try:
            filters = request.args.to_dict()
            decisions = decision_service.list_decisions(filters)
            return ResponseBuilder.success(
                DecisionListResponseSchema().dump({'decisions': decisions})
            )
        except Exception as e:
            logger.error(f"Error listing decisions: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to list decisions", status_code=500)

    @decision_bp.route('/<pipeline_id>/pending', methods=['GET'])
    def get_pending_decisions(pipeline_id):
        """Get pending decisions for a pipeline."""
        try:
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
    def make_decision(decision_id):
        """Make a decision."""
        try:
            schema = DecisionRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id
            
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
    def provide_decision_feedback(decision_id):
        """Provide feedback for a decision."""
        try:
            schema = DecisionFeedbackRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id
            
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
    def get_decision_history(pipeline_id):
        """Get decision history for a pipeline."""
        try:
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
    def get_decision_impact(decision_id):
        """Get impact analysis for a decision."""
        try:
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
        
    return decision_bp