from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any
from backend.data_pipeline.pipeline_service import PipelineService
from flask_cors import CORS  # Import flask_cors

logger = logging.getLogger(__name__)

def create_pipeline_routes(pipeline_service: PipelineService) -> Blueprint:
    """
    Create pipeline management routes blueprint.

    Args:
        pipeline_service (PipelineService): Service for managing data pipelines

    Returns:
        Blueprint: Flask blueprint with pipeline routes
    """
    pipeline_bp = Blueprint('pipeline_bp', __name__)

    @pipeline_bp.route('/status', methods=['GET', 'OPTIONS'])
    def get_pipeline_status():
        if request.method == 'OPTIONS':
            # Preflight request automatically handled by flask_cors
            return jsonify({}), 200  # Return empty response for OPTIONS
        try:
            statuses = pipeline_service.get_active_pipeline_status()
            logger.info(f"Pipeline statuses: {statuses}")
            response = jsonify({
                'status': 'success',
                'data': {'pipelines': statuses}
            })
            return response, 200
        except Exception as e:
            logger.error(f"Error getting pipeline status: {e}")
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @pipeline_bp.route('/start', methods=['POST'])
    def start_pipeline():
        """
        Start a new data processing pipeline.

        Returns:
            JSON response with pipeline start details
        """
        try:
            config = request.get_json()
            pipeline_id = pipeline_service.start_pipeline(config)
            return jsonify({
                'status': 'success',
                'pipeline_id': pipeline_id
            }), 200
        except Exception as e:
            logger.error(f"Pipeline start error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @pipeline_bp.route('/<pipeline_id>/stop', methods=['POST'])
    def stop_pipeline(pipeline_id: str):
        """
        Stop an active pipeline.

        Args:
            pipeline_id (str): Unique identifier for the pipeline

        Returns:
            JSON response with pipeline stop status
        """
        try:
            pipeline_service.stop_pipeline(pipeline_id)
            return jsonify({
                'status': 'success',
                'message': 'Pipeline stopped successfully'
            }), 200
        except Exception as e:
            logger.error(f"Pipeline stop error: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @pipeline_bp.route('/<pipeline_id>/logs', methods=['GET'])
    def get_pipeline_logs(pipeline_id: str):
        """
        Retrieve logs for a specific pipeline.

        Args:
            pipeline_id (str): Unique identifier for the pipeline

        Returns:
            JSON response with pipeline logs
        """
        try:
            logs = pipeline_service.get_pipeline_logs(pipeline_id)
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

    @pipeline_bp.route('/upload', methods=['OPTIONS'])
    def handle_options():
        return '', 200  # Ensure OPTIONS requests are accepted

    return pipeline_bp
