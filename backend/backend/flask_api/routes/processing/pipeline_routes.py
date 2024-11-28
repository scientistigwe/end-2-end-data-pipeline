from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any
from backend.data_pipeline.pipeline_service import PipelineService
from flask_cors import CORS

logger = logging.getLogger(__name__)


def create_pipeline_routes(pipeline_service: PipelineService) -> Blueprint:
    """
    Create pipeline management routes blueprint.
    """
    pipeline_bp = Blueprint('pipeline_bp', __name__)

    @pipeline_bp.route('/status', methods=['GET', 'OPTIONS'])
    def get_pipeline_status():
        if request.method == 'OPTIONS':
            return jsonify({}), 200

        try:
            statuses = pipeline_service.get_active_pipeline_status()
            logger.info(f"Pipeline statuses: {statuses}")

            # Return a properly structured response
            return jsonify({
                'status': 'success',
                'data': {
                    'pipelines': statuses
                }
            }), 200

        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @pipeline_bp.route('/<pipeline_id>/staging', methods=['GET'])
    def get_staging_status(pipeline_id: str):
        """Get detailed staging status for a specific pipeline"""
        try:
            staging_status = pipeline_service.get_staging_status(pipeline_id)
            return jsonify({
                'status': 'success',
                'data': staging_status
            }), 200
        except Exception as e:
            logger.error(f"Error getting staging status: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @pipeline_bp.route('/start', methods=['POST'])
    def start_pipeline():
        """Start a new data processing pipeline"""
        try:
            config = request.get_json()
            pipeline_id = pipeline_service.start_pipeline(config)

            # Get initial status after starting
            initial_status = pipeline_service.get_staging_status(pipeline_id)

            return jsonify({
                'status': 'success',
                'pipeline_id': pipeline_id,
                'initial_status': initial_status
            }), 200
        except Exception as e:
            logger.error(f"Pipeline start error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @pipeline_bp.route('/<pipeline_id>/stop', methods=['POST'])
    def stop_pipeline(pipeline_id: str):
        """Stop an active pipeline"""
        try:
            pipeline_service.stop_pipeline(pipeline_id)

            # Get final status after stopping
            final_status = pipeline_service.get_staging_status(pipeline_id)

            return jsonify({
                'status': 'success',
                'message': 'Pipeline stopped successfully',
                'final_status': final_status
            }), 200
        except Exception as e:
            logger.error(f"Pipeline stop error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @pipeline_bp.route('/<pipeline_id>/logs', methods=['GET'])
    def get_pipeline_logs(pipeline_id: str):
        """Get logs for a specific pipeline"""
        try:
            logs = pipeline_service.get_pipeline_logs(pipeline_id)

            # Add staging events to logs if available
            if hasattr(pipeline_service, 'get_staging_logs'):
                staging_logs = pipeline_service.get_staging_logs(pipeline_id)
                logs.extend(staging_logs)

                # Sort combined logs by timestamp
                logs.sort(key=lambda x: x.get('timestamp', ''))

            return jsonify({
                'status': 'success',
                'logs': logs
            }), 200
        except Exception as e:
            logger.error(f"Pipeline logs error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @pipeline_bp.route('/<pipeline_id>/quality-report', methods=['GET'])
    def get_quality_report(pipeline_id: str):
        """Get quality report for a specific pipeline"""
        try:
            if hasattr(pipeline_service, 'get_quality_report'):
                report = pipeline_service.get_quality_report(pipeline_id)
                return jsonify({
                    'status': 'success',
                    'report': report
                }), 200
            else:
                return jsonify({
                    'status': 'error',
                    'message': 'Quality report feature not available'
                }), 404
        except Exception as e:
            logger.error(f"Quality report error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @pipeline_bp.route('/upload', methods=['OPTIONS'])
    def handle_options():
        return '', 200

    return pipeline_bp