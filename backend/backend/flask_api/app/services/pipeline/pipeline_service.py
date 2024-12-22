# app/services/pipeline/pipeline_service.py
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from .....database.models.pipeline import (
    Pipeline, PipelineStep, PipelineRun,
    PipelineStepRun, QualityGate
)

class PipelineService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def list_pipelines(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all pipelines with optional filtering."""
        try:
            query = self.db_session.query(Pipeline)
            
            # Apply filters
            if filters.get('status'):
                query = query.filter(Pipeline.status == filters['status'])
            if filters.get('mode'):
                query = query.filter(Pipeline.mode == filters['mode'])
            if filters.get('owner_id'):
                query = query.filter(Pipeline.owner_id == filters['owner_id'])
                
            pipelines = query.all()
            return [self._format_pipeline(pipeline) for pipeline in pipelines]
        except Exception as e:
            self.logger.error(f"Error listing pipelines: {str(e)}")
            raise

    def create_pipeline(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new pipeline."""
        try:
            pipeline = Pipeline(
                name=data['name'],
                description=data.get('description'),
                mode=data.get('mode', 'development'),
                source_id=data.get('source_id'),
                target_id=data.get('target_id'),
                config=data.get('config', {}),
                owner_id=data['owner_id']
            )
            
            # Add steps if provided
            if 'steps' in data:
                for step_data in data['steps']:
                    step = PipelineStep(
                        name=step_data['name'],
                        type=step_data['type'],
                        config=step_data.get('config', {}),
                        order=step_data.get('order'),
                        enabled=step_data.get('enabled', True)
                    )
                    pipeline.steps.append(step)
            
            # Add quality gates if provided
            if 'quality_gates' in data:
                for gate_data in data['quality_gates']:
                    gate = QualityGate(
                        name=gate_data['name'],
                        rules=gate_data['rules'],
                        threshold=gate_data.get('threshold'),
                        is_active=gate_data.get('is_active', True)
                    )
                    pipeline.quality_gates.append(gate)
            
            self.db_session.add(pipeline)
            self.db_session.commit()
            
            return self._format_pipeline(pipeline)
        except Exception as e:
            self.logger.error(f"Error creating pipeline: {str(e)}")
            self.db_session.rollback()
            raise

    def get_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """Get pipeline details."""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")
            return self._format_pipeline(pipeline)
        except Exception as e:
            self.logger.error(f"Error getting pipeline: {str(e)}")
            raise

    def update_pipeline(self, pipeline_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update pipeline configuration."""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")

            # Update basic fields
            for field in ['name', 'description', 'mode', 'config']:
                if field in data:
                    setattr(pipeline, field, data[field])

            # Update steps if provided
            if 'steps' in data:
                # Remove existing steps
                pipeline.steps.clear()
                
                # Add new steps
                for step_data in data['steps']:
                    step = PipelineStep(
                        name=step_data['name'],
                        type=step_data['type'],
                        config=step_data.get('config', {}),
                        order=step_data.get('order'),
                        enabled=step_data.get('enabled', True)
                    )
                    pipeline.steps.append(step)

            # Update quality gates if provided
            if 'quality_gates' in data:
                # Remove existing gates
                pipeline.quality_gates.clear()
                
                # Add new gates
                for gate_data in data['quality_gates']:
                    gate = QualityGate(
                        name=gate_data['name'],
                        rules=gate_data['rules'],
                        threshold=gate_data.get('threshold'),
                        is_active=gate_data.get('is_active', True)
                    )
                    pipeline.quality_gates.append(gate)

            self.db_session.commit()
            return self._format_pipeline(pipeline)
        except Exception as e:
            self.logger.error(f"Error updating pipeline: {str(e)}")
            self.db_session.rollback()
            raise

    def start_pipeline(self, pipeline_id: UUID, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Start pipeline execution."""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")
            
            if pipeline.status == 'running':
                raise ValueError("Pipeline is already running")
            
            # Create pipeline run
            run = PipelineRun(
                pipeline_id=pipeline_id,
                version=pipeline.version,
                status='running',
                start_time=datetime.utcnow()
            )
            
            # Create step runs
            for step in pipeline.steps:
                if step.enabled:
                    step_run = PipelineStepRun(
                        step_id=step.id,
                        status='pending',
                        start_time=datetime.utcnow()
                    )
                    run.step_runs.append(step_run)
            
            pipeline.status = 'running'
            pipeline.last_run = datetime.utcnow()
            
            self.db_session.add(run)
            self.db_session.commit()
            
            return {
                'run_id': str(run.id),
                'status': 'running',
                'start_time': run.start_time.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error starting pipeline: {str(e)}")
            self.db_session.rollback()
            raise

    def stop_pipeline(self, pipeline_id: UUID) -> None:
        """Stop pipeline execution."""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")
            
            if pipeline.status != 'running':
                raise ValueError("Pipeline is not running")
            
            # Update current run
            current_run = self.db_session.query(PipelineRun).filter(
                PipelineRun.pipeline_id == pipeline_id,
                PipelineRun.status == 'running'
            ).first()
            
            if current_run:
                current_run.status = 'cancelled'
                current_run.end_time = datetime.utcnow()
                
                # Update step runs
                for step_run in current_run.step_runs:
                    if step_run.status in ['pending', 'running']:
                        step_run.status = 'cancelled'
                        step_run.end_time = datetime.utcnow()
            
            pipeline.status = 'idle'
            self.db_session.commit()
        except Exception as e:
            self.logger.error(f"Error stopping pipeline: {str(e)}")
            self.db_session.rollback()
            raise

    def pause_pipeline(self, pipeline_id: UUID) -> None:
        """Pause pipeline execution."""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")
            
            if pipeline.status != 'running':
                raise ValueError("Pipeline is not running")
            
            pipeline.status = 'paused'
            self.db_session.commit()
        except Exception as e:
            self.logger.error(f"Error pausing pipeline: {str(e)}")
            self.db_session.rollback()
            raise

    def resume_pipeline(self, pipeline_id: UUID) -> None:
        """Resume pipeline execution."""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")
            
            if pipeline.status != 'paused':
                raise ValueError("Pipeline is not paused")
            
            pipeline.status = 'running'
            self.db_session.commit()
        except Exception as e:
            self.logger.error(f"Error resuming pipeline: {str(e)}")
            self.db_session.rollback()
            raise

    def retry_pipeline(self, pipeline_id: UUID) -> Dict[str, Any]:
        """Retry failed pipeline."""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")
            
            if pipeline.status not in ['failed', 'cancelled']:
                raise ValueError("Pipeline is not in failed or cancelled state")
            
            # Create new run with same configuration
            last_run = self.db_session.query(PipelineRun).filter(
                PipelineRun.pipeline_id == pipeline_id
            ).order_by(PipelineRun.start_time.desc()).first()
            
            if not last_run:
                raise ValueError("No previous run found")
            
            return self.start_pipeline(pipeline_id, last_run.config)
        except Exception as e:
            self.logger.error(f"Error retrying pipeline: {str(e)}")
            self.db_session.rollback()
            raise

    def get_pipeline_status(self, pipeline_id: UUID) -> Dict[str, Any]:
        """Get pipeline execution status."""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")
            
            current_run = self.db_session.query(PipelineRun).filter(
                PipelineRun.pipeline_id == pipeline_id,
                PipelineRun.status.in_(['running', 'paused'])
            ).first()
            
            status = {
                'pipeline_status': pipeline.status,
                'current_run': None,
                'steps': [],
                'progress': pipeline.progress
            }
            
            if current_run:
                status['current_run'] = {
                    'id': str(current_run.id),
                    'status': current_run.status,
                    'start_time': current_run.start_time.isoformat(),
                    'duration': (datetime.utcnow() - current_run.start_time).total_seconds()
                }
                
                for step_run in current_run.step_runs:
                    status['steps'].append({
                        'id': str(step_run.id),
                        'name': step_run.step.name,
                        'status': step_run.status,
                        'start_time': step_run.start_time.isoformat() if step_run.start_time else None,
                        'end_time': step_run.end_time.isoformat() if step_run.end_time else None,
                        'duration': (step_run.end_time - step_run.start_time).total_seconds() if step_run.end_time else None,
                        'error': step_run.error
                    })
            
            return status
        except Exception as e:
            self.logger.error(f"Error getting pipeline status: {str(e)}")
            raise

    def get_pipeline_logs(self, pipeline_id: UUID, start_time: str = None, 
                         end_time: str = None, level: str = None) -> List[Dict[str, Any]]:
        """Get pipeline execution logs."""
        # Implementation depends on your logging strategy
        pass

    def get_pipeline_metrics(self, pipeline_id: UUID) -> Dict[str, Any]:
        """Get pipeline performance metrics."""
        try:
            pipeline = self.db_session.query(Pipeline).get(pipeline_id)
            if not pipeline:
                raise ValueError("Pipeline not found")
            
            # Calculate metrics from runs
            total_runs = pipeline.total_runs
            successful_runs = pipeline.successful_runs
            success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0
            
            return {
                'total_runs': total_runs,
                'successful_runs': successful_runs,
                'failed_runs': total_runs - successful_runs,
                'success_rate': success_rate,
                'average_duration': pipeline.average_duration,
                'last_run': pipeline.last_run.isoformat() if pipeline.last_run else None,
                'created_at': pipeline.created_at.isoformat(),
                'updated_at': pipeline.updated_at.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting pipeline metrics: {str(e)}")
            raise

    def validate_pipeline_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate pipeline configuration."""
        try:
            # Implement validation logic
            return {
                'valid': True,
                'warnings': [],
                'errors': []
            }
        except Exception as e:
            self.logger.error(f"Error validating pipeline config: {str(e)}")
            raise

    def _format_pipeline(self, pipeline: Pipeline) -> Dict[str, Any]:
        """Format pipeline for API response."""
        return {
            'id': str(pipeline.id),
            'name': pipeline.name,
            'description': pipeline.description,
            'status': pipeline.status,
            'mode': pipeline.mode,
            'version': pipeline.version,
            'config': pipeline.config,
            'progress': pipeline.progress,
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
            'metrics': {
                'total_runs': pipeline.total_runs,
                'successful_runs': pipeline.successful_runs,
                'average_duration': pipeline.average_duration
            },
            'schedule': {
                'enabled': pipeline.schedule_enabled,
                'cron': pipeline.schedule_cron,
                'timezone': pipeline.schedule_timezone
            },
            'created_at': pipeline.created_at.isoformat(),
            'updated_at': pipeline.updated_at.isoformat(),
            'last_run': pipeline.last_run.isoformat() if pipeline.last_run else None,
            'next_run': pipeline.next_run.isoformat() if pipeline.next_run else None
        }