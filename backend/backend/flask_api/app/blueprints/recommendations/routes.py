# app/blueprints/recommendations/routes.py
from flask import Blueprint, request, g
from marshmallow import ValidationError
from ...schemas.recommendations import (
   RecommendationRequestSchema,
   RecommendationResponseSchema,
   RecommendationStatusResponseSchema,
   RecommendationApplyRequestSchema,
   RecommendationDismissRequestSchema,
   RecommendationListResponseSchema
)
from ...services.decision_recommendation import RecommendationService
from ...utils.response_builder import ResponseBuilder
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

def create_recommendation_blueprint(recommendation_service: RecommendationService, db_session):
    """Create recommendation blueprint with all routes.
    
    Args:
        recommendation_service: Instance of RecommendationService
        db_session: Database session
        
    Returns:
        Blueprint: Configured recommendation blueprint
    """
    recommendation_bp = Blueprint('recommendations', __name__)

    @recommendation_bp.route('/', methods=['GET'])
    def list_recommendations():
        """List all recommendations."""
        try:
            filters = request.args.to_dict()
            recommendations = recommendation_service.list_recommendations(filters)
            return ResponseBuilder.success(
                RecommendationListResponseSchema().dump({'recommendations': recommendations})
            )
        except Exception as e:
            logger.error(f"Error listing recommendations: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to list recommendations", status_code=500)

    @recommendation_bp.route('/<pipeline_id>', methods=['GET'])
    def get_recommendations(pipeline_id):
        """Get recommendations for a specific pipeline."""
        try:
            recommendations = recommendation_service.get_pipeline_recommendations(
                UUID(pipeline_id)
            )
            return ResponseBuilder.success(
                RecommendationListResponseSchema().dump({'recommendations': recommendations})
            )
        except ValueError:
            return ResponseBuilder.error("Invalid pipeline ID", status_code=400)
        except Exception as e:
            logger.error(f"Error getting recommendations: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get recommendations", status_code=500)

    @recommendation_bp.route('/<recommendation_id>/apply', methods=['POST'])
    def apply_recommendation(recommendation_id):
        """Apply a specific recommendation."""
        try:
            user_id = g.current_user.id
            
            schema = RecommendationApplyRequestSchema()
            data = schema.load(request.get_json() or {})
            data['user_id'] = user_id
            
            result = recommendation_service.apply_recommendation(
                UUID(recommendation_id),
                user_id,
                data
            )
            return ResponseBuilder.success(
                RecommendationResponseSchema().dump(result)
            )
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except ValueError:
            return ResponseBuilder.error("Invalid recommendation ID", status_code=400)
        except Exception as e:
            logger.error(f"Error applying recommendation: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to apply recommendation", status_code=500)

    @recommendation_bp.route('/<recommendation_id>/dismiss', methods=['POST'])
    def dismiss_recommendation(recommendation_id):
        """Dismiss a recommendation."""
        try:
            user_id = g.current_user.id
            
            schema = RecommendationDismissRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = user_id
            
            result = recommendation_service.dismiss_recommendation(
                UUID(recommendation_id),
                user_id,
                data.get('reason')
            )
            return ResponseBuilder.success(
                RecommendationResponseSchema().dump(result)
            )
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except ValueError:
            return ResponseBuilder.error("Invalid recommendation ID", status_code=400)
        except Exception as e:
            logger.error(f"Error dismissing recommendation: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to dismiss recommendation", status_code=500)

    @recommendation_bp.route('/<recommendation_id>/status', methods=['GET'])
    def get_recommendation_status(recommendation_id):
        """Get status of a recommendation."""
        try:
            status = recommendation_service.get_recommendation_status(UUID(recommendation_id))
            return ResponseBuilder.success(
                RecommendationStatusResponseSchema().dump({'status': status})
            )
        except ValueError:
            return ResponseBuilder.error("Invalid recommendation ID", status_code=400)
        except Exception as e:
            logger.error(f"Error getting recommendation status: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get recommendation status", status_code=500)

    # Error handlers
    @recommendation_bp.errorhandler(404)
    def not_found_error(error):
        return ResponseBuilder.error("Resource not found", status_code=404)

    @recommendation_bp.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}", exc_info=True)
        return ResponseBuilder.error("Internal server error", status_code=500)
        
    return recommendation_bp