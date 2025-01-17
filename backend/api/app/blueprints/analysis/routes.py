# app/blueprints/analysis/routes.py
from flask import Blueprint, request, send_file, g
from marshmallow import ValidationError
from ...schemas.analysis import (
    QualityCheckRequestSchema,
    QualityCheckResponseSchema,
    InsightAnalysisRequestSchema,
    InsightAnalysisResponseSchema
)
from ...schemas.reports import (
    ReportRequestSchema,
    ReportResponseSchema
)
from ...services.analysis import QualityService, InsightService
from ...utils.response_builder import ResponseBuilder
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

def create_analysis_blueprint(quality_service: QualityService, insight_service: InsightService, db_session):
    """Create analysis blueprint with routes.
    
    Args:
        quality_service: Instance of QualityService
        insight_service: Instance of InsightService
        db_session: Database session
        
    Returns:
        Blueprint: Configured analysis blueprint
    """
    analysis_bp = Blueprint('analysis', __name__)

    # Quality Analysis Routes
    @analysis_bp.route('/quality/start', methods=['POST'])
    def start_quality_analysis():
        """Start a new quality analysis."""
        try:
            schema = QualityCheckRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id
            
            analysis = quality_service.start_analysis(data)
            return ResponseBuilder.success({
                'analysis': QualityCheckResponseSchema().dump(analysis),
                'message': 'Quality analysis started successfully'
            })
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Error starting quality analysis: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to start quality analysis", status_code=500)

    @analysis_bp.route('/quality/<analysis_id>/status', methods=['GET'])
    def get_quality_status(analysis_id):
        """Get the status of a quality analysis."""
        try:
            analysis = quality_service.get_analysis_status(UUID(analysis_id))
            return ResponseBuilder.success({
                'status': QualityCheckResponseSchema().dump(analysis)
            })
        except ValueError:
            return ResponseBuilder.error("Invalid analysis ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting quality status: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get quality status", status_code=500)

    @analysis_bp.route('/quality/<analysis_id>/report', methods=['GET'])
    def get_quality_report(analysis_id):
        """Get the report of a quality analysis."""
        try:
            report = quality_service.get_analysis_report(UUID(analysis_id))
            return ResponseBuilder.success({
                'report': ReportResponseSchema().dump(report)
            })
        except ValueError:
            return ResponseBuilder.error("Invalid analysis ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting quality report: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get quality report", status_code=500)

    @analysis_bp.route('/quality/<analysis_id>/export', methods=['GET'])
    def export_quality_report(analysis_id):
        """Export quality analysis report."""
        try:
            export_file = quality_service.export_report(UUID(analysis_id))
            return send_file(
                export_file,
                as_attachment=True,
                download_name=f'quality_report_{analysis_id}.pdf'
            )
        except ValueError:
            return ResponseBuilder.error("Invalid analysis ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error exporting quality report: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to export quality report", status_code=500)

    # Insight Analysis Routes
    @analysis_bp.route('/insight/start', methods=['POST'])
    def start_insight_analysis():
        """Start a new insight analysis."""
        try:
            schema = InsightAnalysisRequestSchema()
            data = schema.load(request.get_json())
            data['user_id'] = g.current_user.id
            
            analysis = insight_service.start_analysis(data)
            return ResponseBuilder.success({
                'analysis': InsightAnalysisResponseSchema().dump(analysis),
                'message': 'Insight analysis started successfully'
            })
        except ValidationError as e:
            return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
        except Exception as e:
            logger.error(f"Error starting insight analysis: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to start insight analysis", status_code=500)

    @analysis_bp.route('/insight/<analysis_id>/status', methods=['GET'])
    def get_insight_status(analysis_id):
        """Get the status of an insight analysis."""
        try:
            analysis = insight_service.get_analysis_status(UUID(analysis_id))
            return ResponseBuilder.success({
                'status': InsightAnalysisResponseSchema().dump(analysis)
            })
        except ValueError:
            return ResponseBuilder.error("Invalid analysis ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting insight status: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get insight status", status_code=500)

    @analysis_bp.route('/insight/<analysis_id>/report', methods=['GET'])
    def get_insight_report(analysis_id):
        """Get the report of an insight analysis."""
        try:
            report = insight_service.get_analysis_report(UUID(analysis_id))
            return ResponseBuilder.success({
                'report': ReportResponseSchema().dump(report)
            })
        except ValueError:
            return ResponseBuilder.error("Invalid analysis ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting insight report: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get insight report", status_code=500)

    @analysis_bp.route('/insight/<analysis_id>/trends', methods=['GET'])
    def get_insight_trends(analysis_id):
        """Get trends from an insight analysis."""
        try:
            trends = insight_service.get_trends(UUID(analysis_id))
            return ResponseBuilder.success({
                'trends': InsightAnalysisResponseSchema().dump(trends)
            })
        except ValueError:
            return ResponseBuilder.error("Invalid analysis ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting insight trends: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get insight trends", status_code=500)

    @analysis_bp.route('/insight/<analysis_id>/pattern/<pattern_id>', methods=['GET'])
    def get_insight_pattern(analysis_id, pattern_id):
        """Get specific pattern details from an insight analysis."""
        try:
            pattern = insight_service.get_pattern(UUID(analysis_id), UUID(pattern_id))
            return ResponseBuilder.success({
                'pattern': InsightAnalysisResponseSchema().dump(pattern)
            })
        except ValueError:
            return ResponseBuilder.error("Invalid ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting insight pattern: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get insight pattern", status_code=500)

    @analysis_bp.route('/insight/<analysis_id>/correlations', methods=['GET'])
    def get_insight_correlations(analysis_id):
        """Get correlations from an insight analysis."""
        try:
            correlations = insight_service.get_correlations(UUID(analysis_id))
            return ResponseBuilder.success({
                'correlations': InsightAnalysisResponseSchema().dump(correlations)
            })
        except ValueError:
            return ResponseBuilder.error("Invalid analysis ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting correlations: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get correlations", status_code=500)

    @analysis_bp.route('/insight/<analysis_id>/anomalies', methods=['GET'])
    def get_insight_anomalies(analysis_id):
        """Get anomalies from an insight analysis."""
        try:
            anomalies = insight_service.get_anomalies(UUID(analysis_id))
            return ResponseBuilder.success({
                'anomalies': InsightAnalysisResponseSchema().dump(anomalies)
            })
        except ValueError:
            return ResponseBuilder.error("Invalid analysis ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting anomalies: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to get anomalies", status_code=500)

    @analysis_bp.route('/insight/<analysis_id>/export', methods=['GET'])
    def export_insight_report(analysis_id):
        """Export insight analysis report."""
        try:
            export_file = insight_service.export_report(UUID(analysis_id))
            return send_file(
                export_file,
                as_attachment=True,
                download_name=f'insight_report_{analysis_id}.pdf'
            )
        except ValueError:
            return ResponseBuilder.error("Invalid analysis ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error exporting insight report: {str(e)}", exc_info=True)
            return ResponseBuilder.error("Failed to export insight report", status_code=500)

    # Error handlers
    @analysis_bp.errorhandler(404)
    def not_found_error(error):
        return ResponseBuilder.error("Resource not found", status_code=404)

    @analysis_bp.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}", exc_info=True)
        return ResponseBuilder.error("Internal server error", status_code=500)

    @analysis_bp.errorhandler(400)
    def bad_request_error(error):
        return ResponseBuilder.error("Bad request", status_code=400)

    @analysis_bp.errorhandler(401)
    def unauthorized_error(error):
        return ResponseBuilder.error("Unauthorized", status_code=401)

    @analysis_bp.errorhandler(403)
    def forbidden_error(error):
        return ResponseBuilder.error("Forbidden", status_code=403)

    return analysis_bp