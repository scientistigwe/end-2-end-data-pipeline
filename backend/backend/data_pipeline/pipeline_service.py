import uuid
import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

class PipelineService:
    """
    Service for managing data processing pipelines.

    Manages pipeline lifecycle, tracks status, logs, and provides
    centralized pipeline management functionality.
    """

    def __init__(self, message_broker=None, orchestrator=None):
        """
        Initialize the PipelineService with tracking structures and dependencies.

        Args:
            message_broker: Optional MessageBroker instance
            orchestrator: Optional DataOrchestrator instance
        """
        self._active_pipelines: Dict[str, Dict[str, Any]] = {}
        self._pipeline_logs: Dict[str, List[Dict[str, Any]]] = {}
        self.logger = logging.getLogger(__name__)

        # Store injected dependencies
        self.message_broker = message_broker
        self.orchestrator = orchestrator

        if message_broker and orchestrator:
            self.logger.info("PipelineService initialized with messaging and orchestration")

    def _generate_pipeline_id(self) -> str:
        """
        Generate a unique identifier for a pipeline.

        Returns:
            str: Unique pipeline identifier
        """
        return str(uuid.uuid4())

    def _log_pipeline_event(self, pipeline_id: str, event_type: str, message: str):
        """
        Log an event for a specific pipeline.

        Args:
            pipeline_id (str): Pipeline unique identifier
            event_type (str): Type of event (e.g., 'START', 'STOP', 'ERROR')
            message (str): Descriptive event message
        """
        if pipeline_id not in self._pipeline_logs:
            self._pipeline_logs[pipeline_id] = []

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'message': message
        }

        self._pipeline_logs[pipeline_id].append(log_entry)
        self.logger.info(f"Pipeline {pipeline_id} - {event_type}: {message}")

    def stop_pipeline(self, pipeline_id: str):
        """
        Stop an active pipeline.

        Args:
            pipeline_id (str): Unique identifier for the pipeline

        Raises:
            KeyError: If pipeline is not found
            ValueError: If pipeline is already stopped
        """
        if pipeline_id not in self._active_pipelines:
            raise KeyError(f"Pipeline {pipeline_id} not found")

        pipeline = self._active_pipelines[pipeline_id]

        if pipeline['status'] == 'STOPPED':
            raise ValueError(f"Pipeline {pipeline_id} is already stopped")

        pipeline['status'] = 'STOPPED'
        pipeline['end_time'] = datetime.now().isoformat()

        self._log_pipeline_event(
            pipeline_id,
            'STOP',
            "Pipeline stopped by user request"
        )

    def get_active_pipeline_status(self) -> Dict[str, Any]:
        """Get status of all active pipelines"""
        try:
            pipeline_statuses = {}

            for pipeline_id, pipeline_info in self._active_pipelines.items():
                status_info = pipeline_info.copy()  # Create a copy of the basic info

                # Add staging status if orchestrator is available
                if self.orchestrator:
                    try:
                        staging_status = self.orchestrator.monitor_pipeline_progress(pipeline_id)
                        if staging_status:
                            status_info['staging'] = staging_status
                    except Exception as e:
                        logger.error(f"Error getting staging status for pipeline {pipeline_id}: {e}")

                pipeline_statuses[pipeline_id] = status_info

            logger.info(f"Retrieved pipeline statuses: {pipeline_statuses}")
            return pipeline_statuses

        except Exception as e:
            logger.error(f"Error getting pipeline statuses: {e}")
            return {}  # Return empty dict on error

    def start_pipeline(self, config: Dict[str, Any]) -> str:
        """Start a new pipeline with enhanced tracking"""
        pipeline_id = self._generate_pipeline_id()

        self._active_pipelines[pipeline_id] = {
            'id': pipeline_id,
            'config': config,
            'status': 'PROCESSING',
            'start_time': datetime.now().isoformat(),
            'progress': 0,
            'stages_completed': []
        }

        self._log_pipeline_event(
            pipeline_id,
            'START',
            f"Pipeline started with configuration: {config}"
        )

        return pipeline_id

    def get_pipeline_logs(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve logs for a specific pipeline.

        Args:
            pipeline_id (str): Unique identifier for the pipeline

        Returns:
            List of log entries

        Raises:
            KeyError: If pipeline logs are not found
        """
        if pipeline_id not in self._pipeline_logs:
            raise KeyError(f"No logs found for pipeline {pipeline_id}")

        return self._pipeline_logs[pipeline_id]

    def update_pipeline_progress(self, pipeline_id: str, progress: float):
        """
        Update progress of an active pipeline.

        Args:
            pipeline_id (str): Unique identifier for the pipeline
            progress (float): Progress percentage (0-100)

        Raises:
            ValueError: If progress is out of valid range
        """
        if pipeline_id not in self._active_pipelines:
            raise KeyError(f"Pipeline {pipeline_id} not found")

        if progress < 0 or progress > 100:
            raise ValueError("Progress must be between 0 and 100")

        self._active_pipelines[pipeline_id]['progress'] = progress

        if progress == 100:
            self._active_pipelines[pipeline_id]['status'] = 'COMPLETED'
            self._log_pipeline_event(
                pipeline_id,
                'COMPLETE',
                "Pipeline processing completed successfully"
            )

    def get_staging_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get staging status for a pipeline"""
        try:
            if self.orchestrator:
                return self.orchestrator.monitor_pipeline_progress(pipeline_id)
            return {
                'status': 'unknown',
                'message': 'Orchestrator not available'
            }
        except Exception as e:
            self.logger.error(f"Error getting staging status: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
