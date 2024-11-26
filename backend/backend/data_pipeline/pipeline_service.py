import uuid
import logging
from typing import Dict, Any, List
from datetime import datetime


class PipelineService:
    """
    Service for managing data processing pipelines.

    Manages pipeline lifecycle, tracks status, logs, and provides
    centralized pipeline management functionality.
    """

    def __init__(self):
        """
        Initialize the PipelineService with tracking structures.
        """
        self._active_pipelines: Dict[str, Dict[str, Any]] = {}
        self._pipeline_logs: Dict[str, List[Dict[str, Any]]] = {}
        self.logger = logging.getLogger(__name__)

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

    def start_pipeline(self, config: Dict[str, Any]) -> str:
        """
        Start a new data processing pipeline.

        Args:
            config (Dict[str, Any]): Configuration for the pipeline

        Returns:
            str: Unique pipeline identifier

        Raises:
            ValueError: If configuration is invalid
        """
        if not config:
            raise ValueError("Pipeline configuration cannot be empty")

        pipeline_id = self._generate_pipeline_id()

        # Validate configuration
        if not isinstance(config, dict):
            raise ValueError("Configuration must be a dictionary")

        # Store pipeline details
        self._active_pipelines[pipeline_id] = {
            'id': pipeline_id,
            'config': config,
            'status': 'RUNNING',
            'start_time': datetime.now().isoformat(),
            'progress': 0
        }

        self._log_pipeline_event(
            pipeline_id,
            'START',
            f"Pipeline started with configuration: {config}"
        )

        return pipeline_id

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
        """
        Retrieve status of all active pipelines.

        Returns:
            Dict of active pipeline statuses
        """
        return {
            pid: {
                'id': details['id'],
                'status': details['status'],
                'start_time': details['start_time'],
                'progress': details.get('progress', 0)
            } for pid, details in self._active_pipelines.items()
        }

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