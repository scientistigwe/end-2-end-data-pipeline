# app/blueprints/reports/routes.py
from flask import Blueprint, request, g, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from marshmallow import ValidationError
from ...schemas.reports import (
   ReportRequestSchema,
   ReportResponseSchema,
   ReportScheduleRequestSchema,
   ReportScheduleResponseSchema,
   ReportTemplateRequestSchema,
   ReportTemplateResponseSchema,
   ReportGenerationRequestSchema,
   ReportGenerationResponseSchema
)
from ...services.reports import ReportService
from ...utils.response_builder import ResponseBuilder
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
reports_bp = Blueprint('reports', __name__)

def get_report_service():
   """Get report service instance."""
   if 'report_service' not in g:
       g.report_service = ReportService(g.db)
   return g.report_service

@reports_bp.route('/', methods=['GET'])
@jwt_required()
def list_reports():
   """List all reports."""
   try:
       report_service = get_report_service()
       reports = report_service.list_reports()
       return ResponseBuilder.success(
           ReportResponseSchema(many=True).dump({'reports': reports})
       )
   except Exception as e:
       logger.error(f"Error listing reports: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to list reports", status_code=500)

@reports_bp.route('/', methods=['POST'])
@jwt_required()
def create_report():
   """Create a new report."""
   try:
       report_service = get_report_service()
       schema = ReportRequestSchema()
       data = schema.load(request.get_json())
       data['owner_id'] = get_jwt_identity()
       report = report_service.create_report(data)
       return ResponseBuilder.success(
           ReportResponseSchema().dump({'report': report})
       )
   except ValidationError as e:
       return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
   except Exception as e:
       logger.error(f"Error creating report: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to create report", status_code=500)

@reports_bp.route('/<report_id>', methods=['GET'])
@jwt_required()
def get_report(report_id):
   """Get report details."""
   try:
       report_service = get_report_service()
       report = report_service.get_report(UUID(report_id))
       return ResponseBuilder.success(
           ReportResponseSchema().dump({'report': report})
       )
   except ValueError:
       return ResponseBuilder.error("Invalid report ID", status_code=400)
   except Exception as e:
       logger.error(f"Error getting report: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to get report", status_code=500)

@reports_bp.route('/<report_id>', methods=['PUT'])
@jwt_required()
def update_report(report_id):
   """Update report details."""
   try:
       report_service = get_report_service()
       schema = ReportRequestSchema()
       data = schema.load(request.get_json())
       report = report_service.update_report(UUID(report_id), data)
       return ResponseBuilder.success(
           ReportResponseSchema().dump({'report': report})
       )
   except ValidationError as e:
       return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
   except ValueError:
       return ResponseBuilder.error("Invalid report ID", status_code=400)
   except Exception as e:
       logger.error(f"Error updating report: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to update report", status_code=500)

@reports_bp.route('/<report_id>/generate', methods=['POST'])
@jwt_required()
def generate_report(report_id):
   """Generate report content."""
   try:
       report_service = get_report_service()
       schema = ReportGenerationRequestSchema()
       data = schema.load(request.get_json())
       result = report_service.generate_report(UUID(report_id), data)
       return ResponseBuilder.success(
           ReportGenerationResponseSchema().dump({'result': result})
       )
   except ValidationError as e:
       return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
   except ValueError:
       return ResponseBuilder.error("Invalid report ID", status_code=400)
   except Exception as e:
       logger.error(f"Error generating report: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to generate report", status_code=500)

@reports_bp.route('/<report_id>/export', methods=['GET'])
@jwt_required()
def export_report(report_id):
   """Export report as file."""
   try:
       report_service = get_report_service()
       format = request.args.get('format', 'pdf')
       file_path = report_service.export_report(UUID(report_id), format)
       return send_file(
           file_path,
           as_attachment=True,
           download_name=f'report_{report_id}.{format}'
       )
   except ValueError:
       return ResponseBuilder.error("Invalid report ID", status_code=400)
   except Exception as e:
       logger.error(f"Error exporting report: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to export report", status_code=500)

@reports_bp.route('/schedule', methods=['POST'])
@jwt_required()
def schedule_report():
   """Schedule report generation."""
   try:
       report_service = get_report_service()
       schema = ReportScheduleRequestSchema()
       data = schema.load(request.get_json())
       schedule = report_service.schedule_report(data)
       return ResponseBuilder.success(
           ReportScheduleResponseSchema().dump({'schedule': schedule})
       )
   except ValidationError as e:
       return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
   except Exception as e:
       logger.error(f"Error scheduling report: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to schedule report", status_code=500)

@reports_bp.route('/templates', methods=['GET'])
@jwt_required()
def list_templates():
   """List report templates."""
   try:
       report_service = get_report_service()
       templates = report_service.list_templates()
       return ResponseBuilder.success(
           ReportTemplateResponseSchema(many=True).dump({'templates': templates})
       )
   except Exception as e:
       logger.error(f"Error listing templates: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to list templates", status_code=500)

@reports_bp.route('/templates', methods=['POST'])
@jwt_required()
def create_template():
   """Create report template."""
   try:
       report_service = get_report_service()
       schema = ReportTemplateRequestSchema()
       data = schema.load(request.get_json())
       template = report_service.create_template(data)
       return ResponseBuilder.success(
           ReportTemplateResponseSchema().dump({'template': template})
       )
   except ValidationError as e:
       return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)
   except Exception as e:
       logger.error(f"Error creating template: {str(e)}", exc_info=True)
       return ResponseBuilder.error("Failed to create template", status_code=500)

# Error handlers
@reports_bp.errorhandler(404)
def not_found_error(error):
   return ResponseBuilder.error("Resource not found", status_code=404)

@reports_bp.errorhandler(500)
def internal_error(error):
   logger.error(f"Internal error: {error}", exc_info=True)
   return ResponseBuilder.error("Internal server error", status_code=500)