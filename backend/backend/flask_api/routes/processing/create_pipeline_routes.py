from flask import Blueprint, jsonify, request
from typing import Dict, Any, Tuple
from datetime import datetime
import logging
from backend.flask_api.bp_routes import pipeline_bp
from backend.data_pipeline.source.file.file_service import FileService
from backend.core.messaging.types import (
    ProcessingMessage,
    MessageType,
    ProcessingStatus,
    ModuleIdentifier
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

service = FileService()

def create_pipeline_routes(file_service):
    """Factory function to create pipeline routes with FileService instance"""

    # Get the orchestrator instance from FileService
    orchestrator = service._initialize_data_orchestrator()

    @pipeline_bp.route('/pipelines/status', methods=['GET'])
    def get_pipeline_status() -> Tuple[Dict[str, Any], int]:
        """Get status of all active pipelines"""
        try:
            active_pipelines = {}
            for pipeline_id in orchestrator.active_pipelines:
                pipeline_status = orchestrator.monitor_pipeline_progress(pipeline_id)
                active_pipelines[pipeline_id] = pipeline_status

            return jsonify({
                'status': 'success',
                'pipelines': active_pipelines
            }), 200
        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Failed to retrieve pipeline status: {str(e)}'
            }), 500

    @pipeline_bp.route('/pipelines/start', methods=['POST'])
    def start_pipeline() -> Tuple[Dict[str, Any], int]:
        """Start a new pipeline with provided configuration"""
        try:
            config = request.get_json()
            if not config:
                return jsonify({
                    'status': 'error',
                    'message': 'Missing pipeline configuration'
                }), 400

            pipeline_id = orchestrator.handle_source_data(config)

            return jsonify({
                'status': 'success',
                'pipeline_id': pipeline_id,
                'message': 'Pipeline started successfully'
            }), 200
        except Exception as e:
            logger.error(f"Error starting pipeline: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Failed to start pipeline: {str(e)}'
            }), 500

    @pipeline_bp.route('/pipelines/<pipeline_id>/stop', methods=['POST'])
    def stop_pipeline(pipeline_id: str) -> Tuple[Dict[str, Any], int]:
        """Stop a running pipeline"""
        try:
            orchestrator.stop_pipeline(pipeline_id)

            return jsonify({
                'status': 'success',
                'message': 'Pipeline stopped successfully'
            }), 200
        except Exception as e:
            logger.error(f"Error stopping pipeline: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Failed to stop pipeline: {str(e)}'
            }), 500

    @pipeline_bp.route('/pipelines/<pipeline_id>/decision', methods=['POST'])
    def handle_pipeline_decision(pipeline_id: str) -> Tuple[Dict[str, Any], int]:
        """Handle user decisions for pipeline progression"""
        try:
            data = request.get_json()
            decision = data.get('decision')

            if decision is None:
                return jsonify({
                    'status': 'error',
                    'message': 'Missing decision data'
                }), 400

            # Create decision message using the message broker from FileService
            decision_message = ProcessingMessage(
                source_identifier=orchestrator.module_id,
                message_type=MessageType.USER_DECISION,
                content={
                    'pipeline_id': pipeline_id,
                    'decision': decision,
                    'timestamp': datetime.now().isoformat()
                }
            )

            # Use the message broker from FileService
            file_service.message_broker.publish(decision_message)

            return jsonify({
                'status': 'success',
                'message': 'Decision processed successfully'
            }), 200
        except Exception as e:
            logger.error(f"Error processing decision: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Failed to process decision: {str(e)}'
            }), 500

    @pipeline_bp.route('/pipelines/<pipeline_id>/logs', methods=['GET'])
    def get_pipeline_logs(pipeline_id: str) -> Tuple[Dict[str, Any], int]:
        """Get logs for a specific pipeline"""
        try:
            logs = orchestrator.get_pipeline_logs(pipeline_id)

            return jsonify({
                'status': 'success',
                'logs': logs
            }), 200
        except Exception as e:
            logger.error(f"Error retrieving pipeline logs: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Failed to retrieve pipeline logs: {str(e)}'
            }), 500

    @pipeline_bp.route('/pipelines/<pipeline_id>/metrics', methods=['GET'])
    def get_pipeline_metrics(pipeline_id: str) -> Tuple[Dict[str, Any], int]:
        """Get detailed metrics for a specific pipeline"""
        try:
            metrics = orchestrator.get_pipeline_metrics(pipeline_id)

            if 'error' in metrics:
                return jsonify({
                    'status': 'error',
                    'message': metrics['error']
                }), 404

            return jsonify({
                'status': 'success',
                'metrics': metrics
            }), 200
        except Exception as e:
            logger.error(f"Error getting pipeline metrics: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Failed to retrieve metrics: {str(e)}'
            }), 500

    @pipeline_bp.route('/pipelines/performance', methods=['GET'])
    def get_system_performance() -> Tuple[Dict[str, Any], int]:
        """Get system-wide performance metrics"""
        try:
            performance_data = orchestrator.get_performance_summary()

            return jsonify({
                'status': 'success',
                'performance': performance_data
            }), 200
        except Exception as e:
            logger.error(f"Error getting performance data: {str(e)}", exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'Failed to retrieve performance data: {str(e)}'
            }), 500

    return pipeline_bp