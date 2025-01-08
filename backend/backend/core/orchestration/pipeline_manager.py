# backend/core/managers/pipeline_manager.py

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_

from backend.core.orchestration.base_manager import BaseManager, ResourceState, ChannelType
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import MessageType, ProcessingMessage, ProcessingStatus
from backend.core.formatters.report_formatter import ReportFormatter
from backend.data_pipeline.analytics.analytics_processor import AnalyticsProcessor

# Import models
from backend.database.models.pipeline import (
    Pipeline, PipelineRun, PipelineStep, PipelineStepRun, QualityGate
)
from backend.database.models.dataset import Dataset
from backend.database.models.data_source import DataSource
from backend.database.models.validation import ValidationRule, QualityCheck, ValidationResult
from backend.database.models.analysis import InsightAnalysis, Pattern, Correlation, Anomaly
from backend.database.models.decisions_recommendations import (
    Decision, DecisionOption, DecisionHistory, Recommendation
)
from backend.database.models.events import Event


@dataclass
class PipelineState:
    """Enhanced pipeline state tracking with SQLAlchemy model integration"""
    pipeline_id: str
    current_stage: str
    status: ProcessingStatus
    metadata: Dict[str, Any]
    config: Dict[str, Any]
    model: Pipeline  # SQLAlchemy Pipeline model instance
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    stages_completed: List[str] = field(default_factory=list)
    stages_duration: Dict[str, float] = field(default_factory=dict)
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    retry_attempts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    current_progress: float = 0.0


class PipelineManager(BaseManager):
    """Unified pipeline manager with enhanced SQLAlchemy integration"""

    def __init__(self, message_broker: MessageBroker, db_session: Session):
        """Initialize with required dependencies"""
        super().__init__(message_broker, "PipelineManager")
        self.db_session = db_session
        self.report_formatter = ReportFormatter(message_broker)
        self.analytics_processor = AnalyticsProcessor(message_broker)
        self.active_pipelines: Dict[str, PipelineState] = {}

        # Initialize handlers
        self._initialize_handlers()
        self.logger.info("PipelineManager initialized successfully")

    def create_pipeline(self,
                        name: str,
                        owner_id: str,
                        source_id: Optional[str] = None,
                        dataset_id: Optional[str] = None,
                        config: Optional[Dict[str, Any]] = None) -> Tuple[Pipeline, str]:
        """Create a new pipeline with SQLAlchemy model"""
        try:
            # Create Pipeline model instance
            pipeline = Pipeline(
                name=name,
                owner_id=owner_id,
                source_id=source_id,
                dataset_id=dataset_id,
                config=config or {},
                status='idle',
                mode='development'
            )

            # Add and commit to get ID
            self.db_session.add(pipeline)
            self.db_session.flush()

            # Initialize pipeline state
            state = PipelineState(
                pipeline_id=str(pipeline.id),
                current_stage='init',
                status=ProcessingStatus.PENDING,
                metadata={},
                config=config or {},
                model=pipeline
            )

            self.active_pipelines[str(pipeline.id)] = state

            # Create initial pipeline run
            run = PipelineRun(
                pipeline_id=pipeline.id,
                version=1,
                status='running',
                start_time=datetime.utcnow(),
                triggered_by=owner_id
            )
            self.db_session.add(run)

            self.db_session.commit()
            return pipeline, str(pipeline.id)

        except SQLAlchemyError as e:
            self.db_session.rollback()
            self.logger.error(f"Database error creating pipeline: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating pipeline: {str(e)}")
            raise

    def start_pipeline(self, pipeline_id: str) -> None:
        """Start pipeline execution"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            if not pipeline.can_start():
                raise ValueError(f"Pipeline {pipeline_id} cannot be started in current state")

            # Update model status
            pipeline.status = 'running'
            pipeline.last_run = datetime.utcnow()
            pipeline.total_runs += 1

            # Create new pipeline run
            run = PipelineRun(
                pipeline_id=pipeline.id,
                version=pipeline.version,
                status='running',
                start_time=datetime.utcnow()
            )
            self.db_session.add(run)

            # Update state
            state = self.active_pipelines[pipeline_id]
            state.status = ProcessingStatus.RUNNING
            state.current_stage = 'data_validation'

            self.db_session.commit()

            # Start first stage
            self._start_next_stage(pipeline_id, 'data_validation')

        except Exception as e:
            self.db_session.rollback()
            self._handle_pipeline_error(pipeline_id, "startup", e)

    def _get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Get pipeline model by ID"""
        try:
            return self.db_session.query(Pipeline).filter(
                Pipeline.id == pipeline_id
            ).first()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error fetching pipeline: {str(e)}")
            return None

    def _create_validation_result(self,
                                  pipeline_id: str,
                                  check_id: str,
                                  status: str,
                                  results: Dict[str, Any]) -> ValidationResult:
        """Create validation result record"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            validation_result = ValidationResult(
                source_id=pipeline.source_id,
                quality_check_id=check_id,
                status=status,
                results=results,
                validated_at=datetime.utcnow()
            )
            self.db_session.add(validation_result)
            self.db_session.commit()
            return validation_result
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise

    def _create_insight(self,
                        pipeline_id: str,
                        insight_type: str,
                        results: Dict[str, Any]) -> InsightAnalysis:
        """Create insight analysis record"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            insight = InsightAnalysis(
                name=f"{pipeline.name} - {insight_type}",
                analysis_type=insight_type,
                source_id=pipeline.source_id,
                results=results,
                status='completed'
            )
            self.db_session.add(insight)
            self.db_session.commit()
            return insight
        except SQLAlchemyError as e:
            self.db_session.rollback()
            raise

    def _update_pipeline_stats(self, pipeline_id: str) -> None:
        """Update pipeline statistics"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            if not pipeline:
                return

            # Calculate stats from runs
            runs = self.db_session.query(PipelineRun).filter(
                PipelineRun.pipeline_id == pipeline_id
            ).all()

            successful_runs = sum(1 for run in runs if run.status == 'completed')

            # Update pipeline stats
            pipeline.successful_runs = successful_runs
            pipeline.total_runs = len(runs)

            if runs:
                durations = [
                    (run.end_time - run.start_time).total_seconds()
                    for run in runs
                    if run.end_time and run.status == 'completed'
                ]
                if durations:
                    pipeline.average_duration = sum(durations) / len(durations)

            self.db_session.commit()

        except SQLAlchemyError as e:
            self.db_session.rollback()
            self.logger.error(f"Error updating pipeline stats: {str(e)}")

    def _handle_pipeline_error(self, pipeline_id: str, stage: str, error: Exception) -> None:
        """Handle pipeline errors with proper model updates"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            if not pipeline:
                return

            # Update pipeline state
            pipeline.status = 'failed'
            pipeline.error = str(error)
            pipeline.failure_count += 1

            # Update current run
            current_run = self.db_session.query(PipelineRun).filter(
                and_(
                    PipelineRun.pipeline_id == pipeline_id,
                    PipelineRun.status == 'running'
                )
            ).first()

            if current_run:
                current_run.status = 'failed'
                current_run.error = {
                    'message': str(error),
                    'stage': stage,
                    'timestamp': datetime.utcnow().isoformat()
                }
                current_run.end_time = datetime.utcnow()

            # Create error event
            error_event = Event(
                type='pipeline_state',
                severity='error',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline error in stage {stage}: {str(error)}",
                details={
                    'error': str(error),
                    'stage': stage,
                    'stack_trace': getattr(error, '__traceback__', None)
                }
            )
            self.db_session.add(error_event)

            # Update state tracking
            if pipeline_id in self.active_pipelines:
                state = self.active_pipelines[pipeline_id]
                state.status = ProcessingStatus.FAILED
                state.error_history.append({
                    'stage': stage,
                    'error': str(error),
                    'timestamp': datetime.utcnow().isoformat()
                })

            self.db_session.commit()

        except SQLAlchemyError as e:
            self.db_session.rollback()
            self.logger.error(f"Error handling pipeline error: {str(e)}")
        finally:
            self._cleanup_pipeline_resources(pipeline_id)

    def _finalize_pipeline(self, pipeline_id: str) -> None:
        """Finalize pipeline execution with model updates"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            if not pipeline:
                return

            # Update pipeline model
            pipeline.status = 'completed'
            pipeline.last_success = datetime.utcnow()
            pipeline.progress = 100.0

            # Update current run
            current_run = self.db_session.query(PipelineRun).filter(
                and_(
                    PipelineRun.pipeline_id == pipeline_id,
                    PipelineRun.status == 'running'
                )
            ).first()

            if current_run:
                current_run.status = 'completed'
                current_run.end_time = datetime.utcnow()

            # Create completion event
            completion_event = Event(
                type='pipeline_state',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline {pipeline_id} completed successfully"
            )
            self.db_session.add(completion_event)

            # Update stats
            self._update_pipeline_stats(pipeline_id)

            self.db_session.commit()

        except SQLAlchemyError as e:
            self.db_session.rollback()
            self._handle_pipeline_error(pipeline_id, "finalization", e)
        finally:
            self._cleanup_pipeline_resources(pipeline_id)

    def get_pipeline_status(self, pipeline_id: str) -> Dict[str, Any]:
        """Get comprehensive pipeline status"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            # Get latest run
            latest_run = self.db_session.query(PipelineRun).filter(
                PipelineRun.pipeline_id == pipeline_id
            ).order_by(PipelineRun.start_time.desc()).first()

            # Get validation results
            validation_results = self.db_session.query(ValidationResult).join(
                QualityCheck
            ).filter(
                QualityCheck.pipeline_run_id == latest_run.id if latest_run else None
            ).all()

            # Get insights
            insights = self.db_session.query(InsightAnalysis).filter(
                InsightAnalysis.source_id == pipeline.source_id
            ).all()

            return {
                'pipeline_id': str(pipeline.id),
                'name': pipeline.name,
                'status': pipeline.status,
                'progress': pipeline.progress,
                'current_run': {
                    'id': str(latest_run.id) if latest_run else None,
                    'status': latest_run.status if latest_run else None,
                    'start_time': latest_run.start_time if latest_run else None,
                    'end_time': latest_run.end_time if latest_run else None
                } if latest_run else None,
                'stats': {
                    'total_runs': pipeline.total_runs,
                    'successful_runs': pipeline.successful_runs,
                    'average_duration': pipeline.average_duration,
                    'failure_count': pipeline.failure_count
                },
                'validation_results': [
                    {
                        'id': str(result.id),
                        'status': result.status,
                        'error_count': result.error_count,
                        'warning_count': result.warning_count
                    }
                    for result in validation_results
                ],
                'insights': [
                    {
                        'id': str(insight.id),
                        'type': insight.analysis_type,
                        'status': insight.status
                    }
                    for insight in insights
                ]
            }

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting pipeline status: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting pipeline status: {str(e)}")
            raise ValueError(f"Failed to get pipeline status: {str(e)}")

    def pause_pipeline(self, pipeline_id: str) -> None:
        """Pause pipeline execution"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            if pipeline.status != 'running':
                raise ValueError(f"Pipeline {pipeline_id} is not running")

            # Update pipeline state
            pipeline.status = 'paused'

            # Update current run
            current_run = self.db_session.query(PipelineRun).filter(
                and_(
                    PipelineRun.pipeline_id == pipeline_id,
                    PipelineRun.status == 'running'
                )
            ).first()

            if current_run:
                current_run.status = 'paused'

            # Create pause event
            pause_event = Event(
                type='pipeline_state',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline {pipeline_id} paused"
            )
            self.db_session.add(pause_event)

            self.db_session.commit()

        except SQLAlchemyError as e:
            self.db_session.rollback()
            self.logger.error(f"Database error pausing pipeline: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error pausing pipeline: {str(e)}")
            raise


    def resume_pipeline(self, pipeline_id: str) -> None:
        """Resume paused pipeline execution"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            if pipeline.status != 'paused':
                raise ValueError(f"Pipeline {pipeline_id} is not paused")

            # Update pipeline state
            pipeline.status = 'running'

            # Update current run
            current_run = self.db_session.query(PipelineRun).filter(
                and_(
                    PipelineRun.pipeline_id == pipeline_id,
                    or_(PipelineRun.status == 'paused', PipelineRun.status == 'running')
                )
            ).first()

            if current_run:
                current_run.status = 'running'

            # Create resume event
            resume_event = Event(
                type='pipeline_state',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline {pipeline_id} resumed"
            )
            self.db_session.add(resume_event)

            self.db_session.commit()

            # Resume from last stage
            state = self.active_pipelines.get(pipeline_id)
            if state:
                self._start_next_stage(pipeline_id, state.current_stage)

        except SQLAlchemyError as e:
            self.db_session.rollback()
            self.logger.error(f"Database error resuming pipeline: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error resuming pipeline: {str(e)}")
            raise


    def cancel_pipeline(self, pipeline_id: str) -> None:
        """Cancel pipeline execution"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            # Update pipeline state
            pipeline.status = 'cancelled'

            # Update current run
            current_run = self.db_session.query(PipelineRun).filter(
                and_(
                    PipelineRun.pipeline_id == pipeline_id,
                    or_(
                        PipelineRun.status == 'running',
                        PipelineRun.status == 'paused'
                    )
                )
            ).first()

            if current_run:
                current_run.status = 'cancelled'
                current_run.end_time = datetime.utcnow()

            # Create cancel event
            cancel_event = Event(
                type='pipeline_state',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline {pipeline_id} cancelled"
            )
            self.db_session.add(cancel_event)

            self.db_session.commit()

        except SQLAlchemyError as e:
            self.db_session.rollback()
            self.logger.error(f"Database error cancelling pipeline: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error cancelling pipeline: {str(e)}")
            raise
        finally:
            self._cleanup_pipeline_resources(pipeline_id)


    def retry_pipeline(self, pipeline_id: str) -> None:
        """Retry failed pipeline execution"""
        try:
            pipeline = self._get_pipeline(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            if pipeline.status not in ['failed', 'cancelled']:
                raise ValueError(f"Pipeline {pipeline_id} cannot be retried")

            # Get last failed run
            last_run = self.db_session.query(PipelineRun).filter(
                PipelineRun.pipeline_id == pipeline_id
            ).order_by(PipelineRun.start_time.desc()).first()

            # Create new run
            new_run = PipelineRun(
                pipeline_id=pipeline_id,
                version=pipeline.version,
                status='running',
                start_time=datetime.utcnow(),
                triggered_by=last_run.triggered_by if last_run else None
            )
            self.db_session.add(new_run)

            # Update pipeline state
            pipeline.status = 'running'
            pipeline.error = None

            # Create retry event
            retry_event = Event(
                type='pipeline_state',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline {pipeline_id} retry started"
            )
            self.db_session.add(retry_event)

            self.db_session.commit()

            # Start execution
            self.start_pipeline(pipeline_id)

        except SQLAlchemyError as e:
            self.db_session.rollback()
            self.logger.error(f"Database error retrying pipeline: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error retrying pipeline: {str(e)}")
            raise


    def _cleanup_pipeline_resources(self, pipeline_id: str) -> None:
        """Clean up pipeline resources"""
        try:
            # Clean up active pipeline state
            if pipeline_id in self.active_pipelines:
                del self.active_pipelines[pipeline_id]

            # Clean up handlers
            for handler in self.channel_handlers.values():
                handler.cleanup_pipeline(pipeline_id)

            # Create cleanup event
            cleanup_event = Event(
                type='pipeline_state',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline {pipeline_id} resources cleaned up"
            )
            self.db_session.add(cleanup_event)

            self.db_session.commit()

        except SQLAlchemyError as e:
            self.db_session.rollback()
            self.logger.error(f"Database error during cleanup: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error during pipeline cleanup: {str(e)}")


    def __del__(self):
        """Cleanup on deletion"""
        try:
            # Cleanup all active pipelines
            for pipeline_id in list(self.active_pipelines.keys()):
                self.cancel_pipeline(pipeline_id)
                self._cleanup_pipeline_resources(pipeline_id)

            # Clear all data structures
            self.active_pipelines.clear()

        except Exception as e:
            self.logger.error(f"Error during manager cleanup: {str(e)}")
        finally:
            super().__del__()
