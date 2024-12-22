import uuid
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class PipelineService:
    """Service for managing data processing pipelines."""

    def __init__(self, message_broker=None, orchestrator=None, db_session: Optional[Session] = None):
        """Initialize PipelineService with dependencies."""
        self._active_pipelines: Dict[str, Dict[str, Any]] = {}
        self._pipeline_logs: Dict[str, List[Dict[str, Any]]] = {}
        self.logger = logging.getLogger(__name__)
        
        # Dependencies
        self.message_broker = message_broker
        self.orchestrator = orchestrator
        self.db_session = db_session

        if message_broker and orchestrator:
            self.logger.info("PipelineService initialized with messaging and orchestration")

    def _generate_pipeline_id(self) -> str:
        """Generate unique pipeline identifier."""
        return str(uuid.uuid4())

    def _log_pipeline_event(self, pipeline_id: str, event_type: str, message: str) -> None:
        """Log pipeline event with error handling."""
        try:
            if pipeline_id not in self._pipeline_logs:
                self._pipeline_logs[pipeline_id] = []

            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'type': event_type,
                'message': message
            }

            self._pipeline_logs[pipeline_id].append(log_entry)

            # Store in database if session available
            if self.db_session:
                try:
                    # Assuming you have a PipelineLog model
                    pipeline_log = PipelineLog(
                        pipeline_id=pipeline_id,
                        event_type=event_type,
                        message=message
                    )
                    self.db_session.add(pipeline_log)
                    self.db_session.commit()
                except SQLAlchemyError as db_error:
                    self.logger.error(f"Database error logging pipeline event: {str(db_error)}")
                    self.db_session.rollback()

            self.logger.info(f"Pipeline {pipeline_id} - {event_type}: {message}")

        except Exception as e:
            self.logger.error(f"Error logging pipeline event: {str(e)}", exc_info=True)

    def start_pipeline(self, config: Dict[str, Any]) -> str:
        """Start a new pipeline with comprehensive error handling."""
        try:
            pipeline_id = self._generate_pipeline_id()

            # Validate configuration
            if not self._validate_pipeline_config(config):
                raise ValueError("Invalid pipeline configuration")

            # Create pipeline entry
            pipeline_data = {
                'id': pipeline_id,
                'config': config,
                'status': 'PROCESSING',
                'start_time': datetime.now().isoformat(),
                'progress': 0,
                'stages_completed': [],
                'filename': config.get('filename', 'unknown'),
                'source_type': config.get('source_type', 'unknown')
            }

            # Store in memory
            self._active_pipelines[pipeline_id] = pipeline_data

            # Store in database if session available
            if self.db_session:
                try:
                    pipeline_model = PipelineModel(**pipeline_data)
                    self.db_session.add(pipeline_model)
                    self.db_session.commit()
                except SQLAlchemyError as db_error:
                    self.logger.error(f"Database error creating pipeline: {str(db_error)}")
                    self.db_session.rollback()
                    raise

            # Log event
            self._log_pipeline_event(
                pipeline_id,
                'START',
                f"Pipeline started for {config.get('filename', 'unknown')}"
            )

            # Initialize pipeline in orchestrator if available
            if self.orchestrator:
                try:
                    self.orchestrator.initialize_pipeline(pipeline_id, config)
                except Exception as orch_error:
                    self.logger.error(f"Orchestrator initialization error: {str(orch_error)}")
                    self._handle_pipeline_error(pipeline_id, str(orch_error))
                    raise

            return pipeline_id

        except Exception as e:
            self.logger.error(f"Failed to start pipeline: {str(e)}", exc_info=True)
            raise

    def stop_pipeline(self, pipeline_id: str) -> None:
        """Stop an active pipeline with error handling."""
        try:
            if pipeline_id not in self._active_pipelines:
                raise KeyError(f"Pipeline {pipeline_id} not found")

            pipeline = self._active_pipelines[pipeline_id]

            if pipeline['status'] == 'STOPPED':
                raise ValueError(f"Pipeline {pipeline_id} is already stopped")

            # Update memory state
            pipeline['status'] = 'STOPPED'
            pipeline['end_time'] = datetime.now().isoformat()

            # Update database if session available
            if self.db_session:
                try:
                    pipeline_model = self.db_session.query(PipelineModel).filter_by(id=pipeline_id).first()
                    if pipeline_model:
                        pipeline_model.status = 'STOPPED'
                        pipeline_model.end_time = datetime.now()
                        self.db_session.commit()
                except SQLAlchemyError as db_error:
                    self.logger.error(f"Database error stopping pipeline: {str(db_error)}")
                    self.db_session.rollback()
                    raise

            # Stop in orchestrator if available
            if self.orchestrator:
                try:
                    self.orchestrator.stop_pipeline(pipeline_id)
                except Exception as orch_error:
                    self.logger.error(f"Orchestrator stop error: {str(orch_error)}")

            self._log_pipeline_event(
                pipeline_id,
                'STOP',
                "Pipeline stopped by user request"
            )

        except Exception as e:
            self.logger.error(f"Error stopping pipeline: {str(e)}", exc_info=True)
            raise

    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get detailed pipeline status with error handling."""
        try:
            if pipeline_id not in self._active_pipelines:
                raise KeyError(f"Pipeline {pipeline_id} not found")

            status = self._active_pipelines[pipeline_id].copy()

            # Add orchestrator status if available
            if self.orchestrator:
                try:
                    orchestrator_status = self.orchestrator.get_pipeline_status(pipeline_id)
                    status['orchestrator_status'] = orchestrator_status
                except Exception as orch_error:
                    self.logger.error(f"Error getting orchestrator status: {str(orch_error)}")
                    status['orchestrator_status'] = {'error': str(orch_error)}

            return status

        except Exception as e:
            self.logger.error(f"Error getting pipeline status: {str(e)}", exc_info=True)
            raise

    def _handle_pipeline_error(self, pipeline_id: str, error_message: str) -> None:
        """Handle pipeline errors consistently."""
        try:
            if pipeline_id in self._active_pipelines:
                self._active_pipelines[pipeline_id]['status'] = 'ERROR'
                self._active_pipelines[pipeline_id]['error'] = error_message

                if self.db_session:
                    try:
                        pipeline_model = self.db_session.query(PipelineModel).filter_by(id=pipeline_id).first()
                        if pipeline_model:
                            pipeline_model.status = 'ERROR'
                            pipeline_model.error_message = error_message
                            self.db_session.commit()
                    except SQLAlchemyError as db_error:
                        self.logger.error(f"Database error handling pipeline error: {str(db_error)}")
                        self.db_session.rollback()

                self._log_pipeline_event(pipeline_id, 'ERROR', error_message)

        except Exception as e:
            self.logger.error(f"Error handling pipeline error: {str(e)}", exc_info=True)

    def _validate_pipeline_config(self, config: Dict[str, Any]) -> bool:
        """Validate pipeline configuration."""
        required_fields = ['filename', 'source_type']
        return all(field in config for field in required_fields)