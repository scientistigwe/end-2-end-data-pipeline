# backend/db/repository/pipeline_repository.py

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import logging
from db.models.pipeline import (
    Pipeline, PipelineStep, PipelineRun,
    PipelineStepRun, QualityGate, PipelineLog,
    PipelineTemplate, PipelineVersion
)
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

class PipelineRepository:
    """Handles all pipeline-related db operations"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def create_pipeline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new pipeline with steps and quality gates"""
        try:
            # Create pipeline
            pipeline = Pipeline(
                name=data['name'],
                description=data.get('description'),
                mode=data.get('mode', 'development'),
                source_id=data.get('source_id'),
                target_id=data.get('target_id'),
                config=data.get('config', {}),
                owner_id=data['owner_id'],
                status='created',
                version=1,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # Add steps
            for step_data in data.get('steps', []):
                step = PipelineStep(
                    name=step_data['name'],
                    type=step_data['type'],
                    config=step_data.get('config', {}),
                    order=step_data.get('order'),
                    enabled=step_data.get('enabled', True)
                )
                pipeline.steps.append(step)

            # Add quality gates
            for gate_data in data.get('quality_gates', []):
                gate = QualityGate(
                    name=gate_data['name'],
                    rules=gate_data['rules'],
                    threshold=gate_data.get('threshold'),
                    is_active=gate_data.get('is_active', True)
                )
                pipeline.quality_gates.append(gate)

            self.db_session.add(pipeline)
            self.db_session.commit()

            return self._to_dict(pipeline)

        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating pipeline: {str(e)}")
            self.db_session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error creating pipeline: {str(e)}")
            self.db_session.rollback()
            raise

    def get_pipeline(self, pipeline_id: UUID) -> Optional[Dict[str, Any]]:
        """Get pipeline by ID with related data"""
        try:
            pipeline = self.db_session.query(Pipeline)\
                .filter(Pipeline.id == pipeline_id)\
                .first()
            return self._to_dict(pipeline) if pipeline else None

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting pipeline {pipeline_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting pipeline {pipeline_id}: {str(e)}")
            raise

    def update_pipeline(self, pipeline_id: UUID, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update pipeline configuration"""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                return None

            # Update version
            self._create_version_snapshot(pipeline)
            pipeline.version += 1

            # Update basic fields
            updateable_fields = [
                'name', 'description', 'mode', 'config',
                'source_id', 'target_id'
            ]
            for field in updateable_fields:
                if field in data:
                    setattr(pipeline, field, data[field])

            # Update steps
            if 'steps' in data:
                pipeline.steps.clear()
                for step_data in data['steps']:
                    step = PipelineStep(
                        name=step_data['name'],
                        type=step_data['type'],
                        config=step_data.get('config', {}),
                        order=step_data.get('order'),
                        enabled=step_data.get('enabled', True)
                    )
                    pipeline.steps.append(step)

            # Update quality gates
            if 'quality_gates' in data:
                pipeline.quality_gates.clear()
                for gate_data in data['quality_gates']:
                    gate = QualityGate(
                        name=gate_data['name'],
                        rules=gate_data['rules'],
                        threshold=gate_data.get('threshold'),
                        is_active=gate_data.get('is_active', True)
                    )
                    pipeline.quality_gates.append(gate)

            pipeline.updated_at = datetime.utcnow()
            self.db_session.commit()

            return self._to_dict(pipeline)

        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating pipeline {pipeline_id}: {str(e)}")
            self.db_session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error updating pipeline {pipeline_id}: {str(e)}")
            self.db_session.rollback()
            raise

    def delete_pipeline(self, pipeline_id: UUID) -> bool:
        """Delete pipeline and related data"""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                return False

            # Delete related data
            self.db_session.query(PipelineLog)\
                .filter(PipelineLog.pipeline_id == pipeline_id)\
                .delete()
            self.db_session.query(PipelineRun)\
                .filter(PipelineRun.pipeline_id == pipeline_id)\
                .delete()
            self.db_session.query(PipelineVersion)\
                .filter(PipelineVersion.pipeline_id == pipeline_id)\
                .delete()

            self.db_session.delete(pipeline)
            self.db_session.commit()
            return True

        except SQLAlchemyError as e:
            self.logger.error(f"Database error deleting pipeline {pipeline_id}: {str(e)}")
            self.db_session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error deleting pipeline {pipeline_id}: {str(e)}")
            self.db_session.rollback()
            raise

    def list_pipelines(self, filters: Dict[str, Any], 
                      page: int = 1, 
                      page_size: int = 50) -> Tuple[List[Dict[str, Any]], int]:
        """List pipelines with filtering and pagination"""
        try:
            query = self.db_session.query(Pipeline)

            # Apply filters
            if filters.get('status'):
                query = query.filter(Pipeline.status == filters['status'])
            if filters.get('mode'):
                query = query.filter(Pipeline.mode == filters['mode'])
            if filters.get('owner_id'):
                query = query.filter(Pipeline.owner_id == filters['owner_id'])
            if filters.get('search'):
                search = f"%{filters['search']}%"
                query = query.filter(
                    or_(
                        Pipeline.name.ilike(search),
                        Pipeline.description.ilike(search)
                    )
                )

            # Get total count
            total_count = query.count()

            # Apply pagination
            query = query.order_by(desc(Pipeline.updated_at))\
                .offset((page - 1) * page_size)\
                .limit(page_size)

            pipelines = [self._to_dict(p) for p in query.all()]
            return pipelines, total_count

        except SQLAlchemyError as e:
            self.logger.error(f"Database error listing pipelines: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error listing pipelines: {str(e)}")
            raise

    def save_pipeline_state(self, pipeline_id: UUID, state: Dict[str, Any]) -> None:
        """Save pipeline state with optimistic locking"""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            # Update state fields
            pipeline.status = state['status']
            pipeline.current_step = state.get('current_step')
            pipeline.progress = state.get('progress', 0)
            pipeline.updated_at = datetime.utcnow()

            # Update metrics if completed
            if state['status'] == 'completed':
                pipeline.last_run = datetime.utcnow()
                pipeline.total_runs = Pipeline.total_runs + 1
                pipeline.successful_runs = Pipeline.successful_runs + 1

            self.db_session.commit()

        except SQLAlchemyError as e:
            self.logger.error(f"Database error saving pipeline state {pipeline_id}: {str(e)}")
            self.db_session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error saving pipeline state {pipeline_id}: {str(e)}")
            self.db_session.rollback()
            raise

    def create_run(self, pipeline_id: UUID, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create new pipeline run"""
        try:
            run = PipelineRun(
                pipeline_id=pipeline_id,
                status='pending',
                config=config,
                start_time=datetime.utcnow()
            )
            self.db_session.add(run)
            self.db_session.commit()

            return self._run_to_dict(run)

        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating run for {pipeline_id}: {str(e)}")
            self.db_session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error creating run for {pipeline_id}: {str(e)}")
            self.db_session.rollback()
            raise

    def get_pipeline_metrics(self, pipeline_id: UUID,
                           time_range: Optional[timedelta] = None) -> Dict[str, Any]:
        """Get pipeline performance metrics"""
        try:
            # Base query
            query = self.db_session.query(PipelineRun)\
                .filter(PipelineRun.pipeline_id == pipeline_id)

            # Apply time range if specified
            if time_range:
                start_time = datetime.utcnow() - time_range
                query = query.filter(PipelineRun.start_time >= start_time)

            # Calculate metrics
            metrics = {
                'total_runs': query.count(),
                'successful_runs': query.filter(PipelineRun.status == 'completed').count(),
                'failed_runs': query.filter(PipelineRun.status == 'failed').count(),
                'average_duration': query.with_entities(
                    func.avg(PipelineRun.end_time - PipelineRun.start_time)
                ).scalar(),
                'last_run': query.order_by(desc(PipelineRun.start_time)).first(),
                'failure_rate': 0  # Calculated below
            }

            if metrics['total_runs'] > 0:
                metrics['failure_rate'] = (
                    metrics['failed_runs'] / metrics['total_runs']
                ) * 100

            return metrics

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting metrics for {pipeline_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting metrics for {pipeline_id}: {str(e)}")
            raise

    def _to_dict(self, pipeline: Pipeline) -> Dict[str, Any]:
        """Convert pipeline model to dictionary"""
        if not pipeline:
            return None

        return {
            'id': str(pipeline.id),
            'name': pipeline.name,
            'description': pipeline.description,
            'mode': pipeline.mode,
            'status': pipeline.status,
            'version': pipeline.version,
            'config': pipeline.config,
            'source_id': str(pipeline.source_id) if pipeline.source_id else None,
            'target_id': str(pipeline.target_id) if pipeline.target_id else None,
            'owner_id': str(pipeline.owner_id),
            'progress': pipeline.progress,
            'current_step': pipeline.current_step,
            'steps': [
                {
                    'id': str(step.id),
                    'name': step.name,
                    'type': step.type,
                    'config': step.config,
                    'order': step.order,
                    'enabled': step.enabled
                }
                for step in pipeline.steps
            ],
            'quality_gates': [
                {
                    'id': str(gate.id),
                    'name': gate.name,
                    'rules': gate.rules,
                    'threshold': gate.threshold,
                    'is_active': gate.is_active
                }
                for gate in pipeline.quality_gates
            ],
            'created_at': pipeline.created_at.isoformat(),
            'updated_at': pipeline.updated_at.isoformat(),
            'last_run': pipeline.last_run.isoformat() if pipeline.last_run else None
        }

    def _run_to_dict(self, run: PipelineRun) -> Dict[str, Any]:
        """Convert pipeline run model to dictionary"""
        if not run:
            return None

        return {
            'id': str(run.id),
            'pipeline_id': str(run.pipeline_id),
            'status': run.status,
            'config': run.config,
            'start_time': run.start_time.isoformat(),
            'end_time': run.end_time.isoformat() if run.end_time else None,
            'duration': str(run.end_time - run.start_time) if run.end_time else None,
            'error': run.error
        }

    def _create_version_snapshot(self, pipeline: Pipeline) -> None:
        """Create version snapshot of pipeline"""
        try:
            version = PipelineVersion(
                pipeline_id=pipeline.id,
                version_number=pipeline.version,
                config={
                    'name': pipeline.name,
                    'description': pipeline.description,
                    'mode': pipeline.mode,
                    'config': pipeline.config,
                    'steps': [
                        {
                            'name': step.name,
                            'type': step.type,
                            'config': step.config,
                            'order': step.order,
                            'enabled': step.enabled
                        }
                        for step in pipeline.steps
                    ],
                    'quality_gates': [
                        {
                            'name': gate.name,
                            'rules': gate.rules,
                            'threshold': gate.threshold,
                            'is_active': gate.is_active
                        }
                        for gate in pipeline.quality_gates
                    ]
                },
                created_at=datetime.utcnow()
            )
            self.db_session.add(version)
            self.db_session.flush()
        except Exception as e:
            self.logger.error(f"Error creating version snapshot: {str(e)}")
            raise

    def get_pipeline_versions(self, pipeline_id: UUID) -> List[Dict[str, Any]]:
        """Get all versions of a pipeline"""
        try:
            versions = self.db_session.query(PipelineVersion)\
                .filter(PipelineVersion.pipeline_id == pipeline_id)\
                .order_by(desc(PipelineVersion.version_number))\
                .all()
            
            return [{
                'version_number': v.version_number,
                'config': v.config,
                'created_at': v.created_at.isoformat()
            } for v in versions]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting pipeline versions: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting pipeline versions: {str(e)}")
            raise

    def get_pipeline_version(self, pipeline_id: UUID, version_number: int) -> Optional[Dict[str, Any]]:
        """Get specific version of a pipeline"""
        try:
            version = self.db_session.query(PipelineVersion)\
                .filter(
                    PipelineVersion.pipeline_id == pipeline_id,
                    PipelineVersion.version_number == version_number
                ).first()
            
            if not version:
                return None
                
            return {
                'version_number': version.version_number,
                'config': version.config,
                'created_at': version.created_at.isoformat()
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting pipeline version: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting pipeline version: {str(e)}")
            raise

    def log_pipeline_event(self, pipeline_id: UUID, event: Dict[str, Any]) -> None:
        """Log pipeline event"""
        try:
            log_entry = PipelineLog(
                pipeline_id=pipeline_id,
                event_type=event['type'],
                message=event['message'],
                details=event.get('details', {}),
                timestamp=datetime.utcnow()
            )
            self.db_session.add(log_entry)
            self.db_session.commit()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error logging pipeline event: {str(e)}")
            self.db_session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error logging pipeline event: {str(e)}")
            self.db_session.rollback()
            raise

    def get_pipeline_logs(self, pipeline_id: UUID,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         event_types: Optional[List[str]] = None,
                         page: int = 1,
                         page_size: int = 50) -> Tuple[List[Dict[str, Any]], int]:
        """Get pipeline logs with filtering and pagination"""
        try:
            query = self.db_session.query(PipelineLog)\
                .filter(PipelineLog.pipeline_id == pipeline_id)

            if start_time:
                query = query.filter(PipelineLog.timestamp >= start_time)
            if end_time:
                query = query.filter(PipelineLog.timestamp <= end_time)
            if event_types:
                query = query.filter(PipelineLog.event_type.in_(event_types))

            total_count = query.count()

            logs = query.order_by(desc(PipelineLog.timestamp))\
                .offset((page - 1) * page_size)\
                .limit(page_size)\
                .all()

            return [{
                'id': str(log.id),
                'event_type': log.event_type,
                'message': log.message,
                'details': log.details,
                'timestamp': log.timestamp.isoformat()
            } for log in logs], total_count

        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting pipeline logs: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting pipeline logs: {str(e)}")
            raise

    def update_pipeline_schedule(self, pipeline_id: UUID, schedule: Dict[str, Any]) -> None:
        """Update pipeline schedule"""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")

            pipeline.schedule_enabled = schedule.get('enabled', False)
            pipeline.schedule_cron = schedule.get('cron')
            pipeline.schedule_timezone = schedule.get('timezone', 'UTC')
            pipeline.next_run = schedule.get('next_run')

            self.db_session.commit()
        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating pipeline schedule: {str(e)}")
            self.db_session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error updating pipeline schedule: {str(e)}")
            self.db_session.rollback()
            raise

    def get_scheduled_pipelines(self, before_time: datetime) -> List[Dict[str, Any]]:
        """Get pipelines scheduled to run before given time"""
        try:
            pipelines = self.db_session.query(Pipeline)\
                .filter(
                    Pipeline.schedule_enabled == True,
                    Pipeline.next_run <= before_time
                ).all()

            return [self._to_dict(p) for p in pipelines]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting scheduled pipelines: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting scheduled pipelines: {str(e)}")
            raise

    def create_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create pipeline template"""
        try:
            template = PipelineTemplate(
                name=data['name'],
                description=data.get('description'),
                config=data['config'],
                created_by=data['created_by'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.db_session.add(template)
            self.db_session.commit()

            return {
                'id': str(template.id),
                'name': template.name,
                'description': template.description,
                'config': template.config,
                'created_by': str(template.created_by),
                'created_at': template.created_at.isoformat(),
                'updated_at': template.updated_at.isoformat()
            }
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating template: {str(e)}")
            self.db_session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Error creating template: {str(e)}")
            self.db_session.rollback()
            raise

    def list_templates(self) -> List[Dict[str, Any]]:
        """List all pipeline templates"""
        try:
            templates = self.db_session.query(PipelineTemplate)\
                .order_by(PipelineTemplate.name)\
                .all()

            return [{
                'id': str(template.id),
                'name': template.name,
                'description': template.description,
                'config': template.config,
                'created_by': str(template.created_by),
                'created_at': template.created_at.isoformat(),
                'updated_at': template.updated_at.isoformat()
            } for template in templates]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error listing templates: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error listing templates: {str(e)}")
            raise