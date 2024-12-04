# app/blueprints/analysis/routes.py
from flask import Blueprint, request
from flask_jwt_extended import jwt_required
from marshmallow import ValidationError
from ...schemas.analysis import (
    QualityAnalysisSchema, InsightAnalysisSchema,
    QualityReportSchema, InsightReportSchema
)
from ...utils.response_builder import ResponseBuilder
import logging

logger = logging.getLogger(__name__)
analysis_bp = Blueprint('analysis', __name__)

# Quality Analysis Routes
@analysis_bp.route('/quality/start', methods=['POST'])
@jwt_required()
def start_quality_analysis():
    try:
        schema = QualityAnalysisSchema()
        data = schema.load(request.get_json())
        analysis_id = quality_service.start_analysis(data)
        return ResponseBuilder.success({'analysis_id': analysis_id})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@analysis_bp.route('/quality/<analysis_id>/status', methods=['GET'])
@jwt_required()
def get_quality_status(analysis_id):
    try:
        status = quality_service.get_analysis_status(analysis_id)
        return ResponseBuilder.success({'status': status})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)

@analysis_bp.route('/quality/<analysis_id>/report', methods=['GET'])
@jwt_required()
def get_quality_report(analysis_id):
    try:
        report = quality_service.get_analysis_report(analysis_id)
        return ResponseBuilder.success({'report': report})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)

@analysis_bp.route('/quality/issues/<pipeline_id>', methods=['GET'])
@jwt_required()
def get_quality_issues(pipeline_id):
    try:
        issues = quality_service.get_pipeline_issues(pipeline_id)
        return ResponseBuilder.success({'issues': issues})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)

# Insight Analysis Routes
@analysis_bp.route('/insight/start', methods=['POST'])
@jwt_required()
def start_insight_analysis():
    try:
        schema = InsightAnalysisSchema()
        data = schema.load(request.get_json())
        analysis_id = insight_service.start_analysis(data)
        return ResponseBuilder.success({'analysis_id': analysis_id})
    except ValidationError as e:
        return ResponseBuilder.error("Validation error", details=e.messages, status_code=400)

@analysis_bp.route('/insight/<analysis_id>/status', methods=['GET'])
@jwt_required()
def get_insight_status(analysis_id):
    try:
        status = insight_service.get_analysis_status(analysis_id)
        return ResponseBuilder.success({'status': status})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)

@analysis_bp.route('/insight/<analysis_id>/report', methods=['GET'])
@jwt_required()
def get_insight_report(analysis_id):
    try:
        report = insight_service.get_analysis_report(analysis_id)
        return ResponseBuilder.success({'report': report})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)

@analysis_bp.route('/insight/metrics/<pipeline_id>', methods=['GET'])
@jwt_required()
def get_insight_metrics(pipeline_id):
    try:
        metrics = insight_service.get_pipeline_metrics(pipeline_id)
        return ResponseBuilder.success({'metrics': metrics})
    except Exception as e:
        return ResponseBuilder.error(str(e), status_code=500)