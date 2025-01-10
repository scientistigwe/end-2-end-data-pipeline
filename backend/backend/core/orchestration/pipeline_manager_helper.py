# backend/core/orchestration/pipeline_manager_helper.py

import logging
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from backend.core.orchestration.base_manager import ChannelType
from backend.core.messaging.types import (
    ProcessingMessage,
    ProcessingStatus,
    MessageType
)
from backend.database.models.pipeline import (
    Pipeline,
    PipelineRun,
    PipelineStep,
    PipelineStepRun,
    QualityGate
)
from backend.database.models.validation import ValidationResult, QualityCheck
from backend.database.models.events import Event

logger = logging.getLogger(__name__)


class PipelineChannelType(Enum):
    """Pipeline-specific channel types"""
    # Core channels
    PIPELINE_CONTROL = "pipeline.control"
    PIPELINE_STATUS = "pipeline.status"
    PIPELINE_DATA = "pipeline.data"
    PIPELINE_VALIDATION = "pipeline.validation"

    # Additional channels mapped from base
    ROUTING = ChannelType.ROUTING.value
    STAGING = ChannelType.STAGING.value
    DATA_SOURCE = ChannelType.DATA_SOURCE.value
    PROCESSING = ChannelType.PROCESSING.value
    DECISION = ChannelType.DECISION.value
    INSIGHT = ChannelType.INSIGHT.value

    @classmethod
    def get_subscription_patterns(cls) -> List[str]:
        return [
            f"{cls.PIPELINE_CONTROL.value}.*",
            f"{cls.PIPELINE_STATUS.value}.*",
            f"{cls.PIPELINE_DATA.value}.*",
            f"{cls.PIPELINE_VALIDATION.value}.*",
            f"{cls.DATA_SOURCE.value}.*",
            f"{cls.PROCESSING.value}.*"
        ]


@dataclass
class PipelineState:
    """Pipeline state tracking"""
    pipeline_id: str
    current_stage: str
    status: ProcessingStatus
    metadata: Dict[str, Any]
    config: Dict[str, Any]
    model: Pipeline
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    stages_completed: List[str] = field(default_factory=list)
    stages_duration: Dict[str, float] = field(default_factory=dict)
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    retry_attempts: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    current_progress: float = 0.0


class DatabaseHelper:
    """Database operations helper"""

    @staticmethod
    def get_pipeline(session, pipeline_id: str) -> Optional[Pipeline]:
        try:
            return session.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
        except Exception as e:
            logger.error(f"Error fetching pipeline {pipeline_id}: {str(e)}")
            return None

    @staticmethod
    def cleanup_session(session) -> None:
        try:
            if session:
                session.close()
        except Exception as e:
            logger.error(f"Error cleaning up session: {str(e)}")

    @staticmethod
    def update_pipeline_stats(session, pipeline_id: str) -> None:
        try:
            pipeline = DatabaseHelper.get_pipeline(session, pipeline_id)
            if not pipeline:
                return

            runs = session.query(PipelineRun).filter(
                PipelineRun.pipeline_id == pipeline_id
            ).all()

            successful_runs = sum(1 for run in runs if run.status == 'completed')
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

            session.commit()
        except Exception as e:
            logger.error(f"Error updating pipeline stats: {str(e)}")
            session.rollback()


class PipelineOperations:
    """Handles core pipeline operations"""

    @staticmethod
    def start_pipeline(session, pipeline_id: str, state_manager) -> None:
        try:
            pipeline = DatabaseHelper.get_pipeline(session, pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            pipeline.status = 'running'
            pipeline.last_run = datetime.utcnow()
            pipeline.total_runs += 1

            run = PipelineRun(
                pipeline_id=pipeline.id,
                version=pipeline.version,
                status='running',
                start_time=datetime.utcnow()
            )
            session.add(run)

            state = state_manager.get_pipeline_state(pipeline_id)
            if state:
                state.status = ProcessingStatus.RUNNING
                state.current_stage = 'data_validation'

            session.commit()
            logger.info(f"Pipeline {pipeline_id} started successfully")

        except Exception as e:
            session.rollback()
            logger.error(f"Error starting pipeline: {str(e)}")
            raise

    @staticmethod
    def pause_pipeline(session, pipeline_id: str, state_manager) -> None:
        try:
            pipeline = DatabaseHelper.get_pipeline(session, pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            pipeline.status = 'paused'
            current_run = session.query(PipelineRun).filter(
                and_(
                    PipelineRun.pipeline_id == pipeline_id,
                    PipelineRun.status == 'running'
                )
            ).first()

            if current_run:
                current_run.status = 'paused'

            state = state_manager.get_pipeline_state(pipeline_id)
            if state:
                state.status = ProcessingStatus.PAUSED

            session.add(Event(
                type='pipeline_state',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline {pipeline_id} paused"
            ))
            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Error pausing pipeline: {str(e)}")
            raise

    @staticmethod
    def resume_pipeline(session, pipeline_id: str, state_manager) -> None:
        """Resume paused pipeline execution"""
        try:
            pipeline = DatabaseHelper.get_pipeline(session, pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            if pipeline.status != 'paused':
                raise ValueError(f"Pipeline {pipeline_id} is not paused")

            pipeline.status = 'running'

            # Update current run
            current_run = session.query(PipelineRun).filter(
                and_(
                    PipelineRun.pipeline_id == pipeline_id,
                    PipelineRun.status == 'paused'
                )
            ).first()

            if current_run:
                current_run.status = 'running'
                current_run.resumed_at = datetime.utcnow()

            # Update state
            state = state_manager.get_pipeline_state(pipeline_id)
            if state:
                state.status = ProcessingStatus.RUNNING
                state.metadata['resume_history'] = state.metadata.get('resume_history', [])
                state.metadata['resume_history'].append(datetime.utcnow().isoformat())

            session.add(Event(
                type='pipeline_state',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline {pipeline_id} resumed"
            ))
            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Error resuming pipeline: {str(e)}")
            raise

    @staticmethod
    def cancel_pipeline(session, pipeline_id: str, state_manager) -> None:
        """Cancel pipeline execution"""
        try:
            pipeline = DatabaseHelper.get_pipeline(session, pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline {pipeline_id} not found")

            pipeline.status = 'cancelled'
            pipeline.cancelled_at = datetime.utcnow()

            # Update all active runs
            active_runs = session.query(PipelineRun).filter(
                and_(
                    PipelineRun.pipeline_id == pipeline_id,
                    PipelineRun.status.in_(['running', 'paused'])
                )
            ).all()

            for run in active_runs:
                run.status = 'cancelled'
                run.end_time = datetime.utcnow()
                run.error = {
                    'message': 'Pipeline cancelled by user/system',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Update state
            state = state_manager.get_pipeline_state(pipeline_id)
            if state:
                state.status = ProcessingStatus.CANCELLED
                state.end_time = datetime.utcnow()
                state.metadata['cancellation'] = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'reason': 'User/system initiated cancellation'
                }

            session.add(Event(
                type='pipeline_state',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Pipeline {pipeline_id} cancelled",
                details={
                    'cancelled_runs': len(active_runs),
                    'timestamp': datetime.utcnow().isoformat()
                }
            ))
            session.commit()

        except Exception as e:
            session.rollback()
            logger.error(f"Error cancelling pipeline: {str(e)}")
            raise

class MessageHandler:
    """Handles pipeline message processing"""

    @staticmethod
    def handle_pipeline_message(message: ProcessingMessage, handlers: Dict) -> None:
        try:
            if not isinstance(message, ProcessingMessage):
                logger.warning(f"Received invalid message type: {type(message)}")
                return

            message_type = message.message_type
            if message_type in handlers:
                handlers[message_type](message)
            else:
                logger.warning(f"No handler registered for message type: {message_type}")
        except Exception as e:
            logger.error(f"Error handling pipeline message: {str(e)}")
            raise

    @staticmethod
    def get_default_handlers():
        """Get default message type handlers"""
        return {
            MessageType.PIPELINE_START: lambda msg: logger.info(f"Pipeline start: {msg.metadata.get('pipeline_id')}"),
            MessageType.PIPELINE_PAUSE: lambda msg: logger.info(f"Pipeline pause: {msg.metadata.get('pipeline_id')}"),
            MessageType.PIPELINE_RESUME: lambda msg: logger.info(f"Pipeline resume: {msg.metadata.get('pipeline_id')}"),
            MessageType.PIPELINE_CANCEL: lambda msg: logger.info(f"Pipeline cancel: {msg.metadata.get('pipeline_id')}")
        }


class QualityHandler:
    """Handles quality-related operations"""

    @staticmethod
    def handle_quality_message(session, message: ProcessingMessage, state_manager) -> None:
        pipeline_id = message.metadata.get('pipeline_id')
        try:
            if message.message_type == MessageType.QUALITY_COMPLETE:
                QualityHandler.process_quality_complete(session, message, state_manager)
            elif message.message_type == MessageType.QUALITY_ERROR:
                QualityHandler.handle_quality_error(session, message, pipeline_id)
            elif message.message_type == MessageType.QUALITY_UPDATE:
                QualityHandler.handle_quality_update(session, message, pipeline_id)
        except Exception as e:
            logger.error(f"Error handling quality message: {str(e)}")
            raise

    @staticmethod
    def process_quality_complete(session, message: ProcessingMessage, state_manager) -> None:
        pipeline_id = message.metadata.get('pipeline_id')
        try:
            check_results = message.metadata.get('results', {})
            quality_check = QualityCheck(
                pipeline_run_id=message.metadata.get('run_id'),
                type=message.metadata.get('check_type'),
                results=check_results,
                status='completed'
            )
            session.add(quality_check)

            state = state_manager.get_pipeline_state(pipeline_id)
            if state:
                state.metadata.setdefault('quality_checks', []).append({
                    'check_id': str(quality_check.id),
                    'type': message.metadata.get('check_type'),
                    'timestamp': datetime.utcnow().isoformat(),
                    'status': 'completed'
                })

            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing quality complete: {str(e)}")
            raise

    @staticmethod
    def handle_quality_error(session, message: ProcessingMessage, pipeline_id: str) -> None:
        """Handle quality check errors"""
        try:
            error = message.metadata.get('error')
            session.add(Event(
                type='quality_check',
                severity='error',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message=f"Quality check failed: {str(error)}",
                details={
                    'error': str(error),
                    'check_type': message.metadata.get('check_type'),
                    'timestamp': datetime.utcnow().isoformat()
                }
            ))
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error handling quality error: {str(e)}")
            raise

    @staticmethod
    def handle_quality_update(session, message: ProcessingMessage, pipeline_id: str) -> None:
        """Handle quality check updates"""
        try:
            update_data = message.metadata.get('update_data', {})
            pipeline = DatabaseHelper.get_pipeline(session, pipeline_id)
            if pipeline:
                if 'quality_settings' in update_data:
                    pipeline.config['quality_settings'] = update_data['quality_settings']
                if 'quality_metrics' in update_data:
                    pipeline.quality_metrics = update_data['quality_metrics']

            session.add(Event(
                type='quality_check',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message="Quality check settings updated",
                details=update_data
            ))
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error handling quality update: {str(e)}")
            raise

class SourceHandler:
    """Handles source-related operations"""

    @staticmethod
    def handle_source_message(session, message: ProcessingMessage, state_manager) -> None:
        pipeline_id = message.metadata.get('pipeline_id')
        try:
            if message.message_type == MessageType.SOURCE_SUCCESS:
                SourceHandler.process_source_success(session, message, state_manager)
            elif message.message_type == MessageType.SOURCE_ERROR:
                SourceHandler.handle_source_error(session, message, pipeline_id)
            elif message.message_type == MessageType.SOURCE_UPDATE:
                SourceHandler.handle_source_update(session, message, state_manager)
        except Exception as e:
            logger.error(f"Error handling source message: {str(e)}")
            raise

    @staticmethod
    def process_source_success(session, message: ProcessingMessage, state_manager) -> None:
        pipeline_id = message.metadata.get('pipeline_id')
        try:
            state = state_manager.get_pipeline_state(pipeline_id)
            if state:
                state.metadata['source_processing'] = {
                    'status': 'completed',
                    'timestamp': datetime.utcnow().isoformat(),
                    'details': message.metadata.get('details', {})
                }
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing source success: {str(e)}")
            raise

    @staticmethod
    def handle_source_update(session, message: ProcessingMessage, state_manager) -> None:
        """Handle source update messages"""
        pipeline_id = message.metadata.get('pipeline_id')
        try:
            update_data = message.metadata.get('update_data', {})
            pipeline = DatabaseHelper.get_pipeline(session, pipeline_id)
            if pipeline:
                if 'source_config' in update_data:
                    pipeline.config['source_settings'] = update_data['source_config']
                if 'source_state' in update_data:
                    pipeline.source_state = update_data['source_state']

                state = state_manager.get_pipeline_state(pipeline_id)
                if state:
                    state.metadata['source_updates'] = state.metadata.get('source_updates', [])
                    state.metadata['source_updates'].append({
                        'timestamp': datetime.utcnow().isoformat(),
                        'details': update_data
                    })

            session.add(Event(
                type='source_update',
                severity='info',
                source='pipeline_manager',
                entity_type='pipeline',
                entity_id=pipeline_id,
                message="Source configuration updated",
                details=update_data
            ))
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error handling source update: {str(e)}")
            raise


@staticmethod
def handle_source_error(session, message: ProcessingMessage, pipeline_id: str) -> None:
    """
    Handle source operation errors.

    Args:
        session: Database session
        message: Processing message containing error details
        pipeline_id: Unique identifier for the pipeline
    """
    try:
        error_message = message.metadata.get('error', 'Unknown source error')

        # Log error event
        session.add(Event(
            type='source_error',
            severity='error',
            source='pipeline_manager',
            entity_type='pipeline',
            entity_id=pipeline_id,
            message=f"Source operation error: {error_message}",
            details={
                'error': error_message,
                'operation': message.metadata.get('operation', 'unknown'),
                'timestamp': datetime.utcnow().isoformat()
            }
        ))

        # Update pipeline status
        pipeline = DatabaseHelper.get_pipeline(session, pipeline_id)
        if pipeline:
            pipeline.status = 'error'
            pipeline.last_error = {
                'message': error_message,
                'timestamp': datetime.utcnow().isoformat()
            }

        # Update current run
        current_run = session.query(PipelineRun).filter(
            and_(
                PipelineRun.pipeline_id == pipeline_id,
                PipelineRun.status.in_(['running', 'pending'])
            )
        ).first()

        if current_run:
            current_run.status = 'error'
            current_run.error = {
                'message': error_message,
                'timestamp': datetime.utcnow().isoformat()
            }

        session.commit()
        logger.error(f"Source error in pipeline {pipeline_id}: {error_message}")

    except Exception as e:
        session.rollback()
        logger.error(f"Error handling source error for pipeline {pipeline_id}: {str(e)}")
        raise

class PipelineStateManager:
    """Manages pipeline states and transitions"""

    def __init__(self):
        self.active_pipelines: Dict[str, PipelineState] = {}

    def add_pipeline(self, state: PipelineState) -> None:
        self.active_pipelines[state.pipeline_id] = state

    def remove_pipeline(self, pipeline_id: str) -> None:
        self.active_pipelines.pop(pipeline_id, None)

    def get_pipeline_state(self, pipeline_id: str) -> Optional[PipelineState]:
        return self.active_pipelines.get(pipeline_id)

    def update_pipeline_state(self, pipeline_id: str, **updates) -> None:
        if pipeline_id in self.active_pipelines:
            state = self.active_pipelines[pipeline_id]
            for key, value in updates.items():
                if hasattr(state, key):
                    setattr(state, key, value)