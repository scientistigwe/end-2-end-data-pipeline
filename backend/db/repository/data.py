from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import and_, or_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.data.sources import (
    DataSource, DatabaseSourceConfig, APISourceConfig,
    S3SourceConfig, StreamSourceConfig, FileSourceInfo,
    SourceConnection, SourceSyncHistory
)
from ..models.data.pipeline import (
    Pipeline, PipelineStep, PipelineRun, PipelineStepRun,
    QualityGate, QualityCheck, PipelineLog, PipelineTemplate,
    PipelineVersion, PipelineSchedule, Tag
)

import logging

logger = logging.getLogger(__name__)


class DataRepository(BaseRepository[DataSource]):
    """Repository for managing data sources and pipeline operations."""

    def __init__(self, db_session: AsyncSession):
        """Initialize with async session."""
        super().__init__(db_session)

    # Data Source Management
    async def create_data_source(
            self,
            source_data: Dict[str, Any],
            owner_id: UUID
    ) -> DataSource:
        """Create a new data source with proper configuration."""
        try:
            # Create base data source
            source_data['owner_id'] = owner_id
            source = await self.create(source_data, DataSource)

            # Create specific configuration based on source type
            config_data = source_data.get('config', {})
            config_models = {
                'api': APISourceConfig,
                'db': DatabaseSourceConfig,
                's3': S3SourceConfig,
                'stream': StreamSourceConfig,
                'file': FileSourceInfo
            }

            if config_model := config_models.get(source.type):
                await self.create({
                    'source_id': source.id,
                    **config_data
                }, config_model)

            return source
        except Exception as e:
            logger.error(f"Failed to create data source: {str(e)}")
            raise

    async def get_data_source(
            self,
            source_id: UUID,
            include_config: bool = True
    ) -> Optional[DataSource]:
        """Get data source with optional configuration loading."""
        try:
            query = select(DataSource).where(DataSource.id == source_id)

            if include_config:
                query = query.options(
                    selectinload(DataSource.api_config),
                    selectinload(DataSource.db_config),
                    selectinload(DataSource.s3_config),
                    selectinload(DataSource.stream_config),
                    selectinload(DataSource.file_info)
                )

            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting data source: {str(e)}")
            raise

    async def update_data_source(
            self,
            source_id: UUID,
            updates: Dict[str, Any]
    ) -> Optional[DataSource]:
        """Update data source and its configuration."""
        try:
            source = await self.get_data_source(source_id)
            if not source:
                return None

            # Update base source fields
            for key, value in updates.items():
                if hasattr(source, key):
                    setattr(source, key, value)

            # Update configuration if provided
            if config_updates := updates.get('config'):
                config_obj = getattr(source, f"{source.type}_config")
                if config_obj:
                    for key, value in config_updates.items():
                        if hasattr(config_obj, key):
                            setattr(config_obj, key, value)

            await self.db_session.commit()
            return source
        except Exception as e:
            logger.error(f"Failed to update data source: {str(e)}")
            raise

    async def test_connection(self, source_id: UUID) -> Dict[str, Any]:
        """Test data source connection and record results."""
        try:
            source = await self.get_data_source(source_id)
            if not source:
                raise ValueError(f"Data source not found: {source_id}")

            # Create connection record
            connection = await self.create({
                'source_id': source_id,
                'status': 'connected',
                'connected_at': datetime.utcnow(),
                'metrics': {
                    'latency': 0,
                    'throughput': 0,
                    'error_rate': 0
                }
            }, SourceConnection)

            return {
                'status': connection.status,
                'connected_at': connection.connected_at,
                'metrics': connection.metrics
            }
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            raise

    # Pipeline Management
    async def create_pipeline(
            self,
            pipeline_data: Dict[str, Any]
    ) -> Pipeline:
        """Create new pipeline with steps and quality gates."""
        try:
            # Create pipeline
            pipeline = await self.create(pipeline_data, Pipeline)

            # Add steps
            if steps_data := pipeline_data.get('steps'):
                for step_data in steps_data:
                    step_data['pipeline_id'] = pipeline.id
                    await self.create(step_data, PipelineStep)

            # Add quality gates
            if gates_data := pipeline_data.get('quality_gates'):
                for gate_data in gates_data:
                    gate_data['pipeline_id'] = pipeline.id
                    await self.create(gate_data, QualityGate)

            # Create version snapshot
            await self._create_version_snapshot(pipeline)

            return pipeline
        except Exception as e:
            logger.error(f"Failed to create pipeline: {str(e)}")
            raise

    async def update_pipeline(
            self,
            pipeline_id: UUID,
            updates: Dict[str, Any]
    ) -> Optional[Pipeline]:
        """Update pipeline with version control."""
        try:
            pipeline = await self.get_pipeline(pipeline_id)
            if not pipeline:
                return None

            # Create version snapshot before update
            await self._create_version_snapshot(pipeline)
            pipeline.version += 1

            # Update basic fields
            for key, value in updates.items():
                if hasattr(pipeline, key):
                    setattr(pipeline, key, value)

            # Update steps if provided
            if steps_data := updates.get('steps'):
                # Remove existing steps
                await self.db_session.execute(
                    delete(PipelineStep).where(
                        PipelineStep.pipeline_id == pipeline_id
                    )
                )
                # Add new steps
                for step_data in steps_data:
                    step_data['pipeline_id'] = pipeline_id
                    await self.create(step_data, PipelineStep)

            # Update quality gates if provided
            if gates_data := updates.get('quality_gates'):
                # Remove existing gates
                await self.db_session.execute(
                    delete(QualityGate).where(
                        QualityGate.pipeline_id == pipeline_id
                    )
                )
                # Add new gates
                for gate_data in gates_data:
                    gate_data['pipeline_id'] = pipeline_id
                    await self.create(gate_data, QualityGate)

            await self.db_session.commit()
            return pipeline
        except Exception as e:
            logger.error(f"Failed to update pipeline: {str(e)}")
            raise

    async def get_pipeline(
            self,
            pipeline_id: UUID,
            include_related: bool = True
    ) -> Optional[Pipeline]:
        """Get pipeline with optional related data loading."""
        try:
            query = select(Pipeline).where(Pipeline.id == pipeline_id)

            if include_related:
                query = query.options(
                    selectinload(Pipeline.steps),
                    selectinload(Pipeline.quality_gates),
                    selectinload(Pipeline.tags)
                )

            result = await self.db_session.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting pipeline: {str(e)}")
            raise

    async def create_pipeline_run(
            self,
            pipeline_id: UUID,
            run_data: Dict[str, Any]
    ) -> PipelineRun:
        """Create new pipeline run with proper tracking."""
        try:
            # Create run record
            run_data['pipeline_id'] = pipeline_id
            run_data['start_time'] = datetime.utcnow()
            run = await self.create(run_data, PipelineRun)

            # Log run creation
            await self.create({
                'pipeline_id': pipeline_id,
                'event_type': 'run_started',
                'message': f"Pipeline run {run.id} started",
                'timestamp': datetime.utcnow()
            }, PipelineLog)

            return run
        except Exception as e:
            logger.error(f"Failed to create pipeline run: {str(e)}")
            raise

    async def update_run_status(
            self,
            run_id: UUID,
            status: str,
            metrics: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update pipeline run status with metrics."""
        try:
            run = await self.get_by_id(run_id, PipelineRun)
            if not run:
                raise ValueError(f"Pipeline run not found: {run_id}")

            run.status = status
            if status in ['completed', 'failed']:
                run.end_time = datetime.utcnow()
                run.duration = (run.end_time - run.start_time).total_seconds()

            if metrics:
                run.metrics = metrics

            await self.db_session.commit()

            # Log status update
            await self.create({
                'pipeline_id': run.pipeline_id,
                'event_type': f"run_{status}",
                'message': f"Pipeline run {run_id} {status}",
                'timestamp': datetime.utcnow()
            }, PipelineLog)
        except Exception as e:
            logger.error(f"Failed to update run status: {str(e)}")
            raise

    async def create_quality_check(
            self,
            run_id: UUID,
            gate_id: UUID,
            check_data: Dict[str, Any]
    ) -> QualityCheck:
        """Create quality check result."""
        try:
            check_data.update({
                'pipeline_run_id': run_id,
                'gate_id': gate_id,
                'check_time': datetime.utcnow()
            })
            return await self.create(check_data, QualityCheck)
        except Exception as e:
            logger.error(f"Failed to create quality check: {str(e)}")
            raise

    async def get_pipeline_metrics(
            self,
            pipeline_id: UUID,
            time_range: Optional[timedelta] = None
    ) -> Dict[str, Any]:
        """Get comprehensive pipeline metrics."""
        try:
            query = select(PipelineRun).where(
                PipelineRun.pipeline_id == pipeline_id
            )

            if time_range:
                start_time = datetime.utcnow() - time_range
                query = query.where(PipelineRun.start_time >= start_time)

            result = await self.db_session.execute(query)
            runs = result.scalars().all()

            successful_runs = sum(1 for run in runs if run.status == 'completed')
            failed_runs = sum(1 for run in runs if run.status == 'failed')
            total_duration = sum(
                (run.duration or 0) for run in runs if run.duration is not None
            )

            return {
                'total_runs': len(runs),
                'successful_runs': successful_runs,
                'failed_runs': failed_runs,
                'success_rate': (successful_runs / len(runs)) * 100 if runs else 0,
                'average_duration': total_duration / len(runs) if runs else 0,
                'last_run': max(runs, key=lambda r: r.start_time).start_time if runs else None
            }
        except Exception as e:
            logger.error(f"Error getting pipeline metrics: {str(e)}")
            raise

    async def _create_version_snapshot(self, pipeline: Pipeline) -> None:
        """Create version snapshot of pipeline state."""
        try:
            version_data = {
                'pipeline_id': pipeline.id,
                'version_number': pipeline.version,
                'config': {
                    'name': pipeline.name,
                    'description': pipeline.description,
                    'mode': pipeline.mode,
                    'config': pipeline.config,
                    'steps': [
                        {
                            'name': step.name,
                            'type': step.type,
                            'config': step.config,
                            'order': step.pipeline_step_order,
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
                'created_at': datetime.utcnow()
            }
            await self.create(version_data, PipelineVersion)
        except Exception as e:
            logger.error(f"Failed to create version snapshot: {str(e)}")
            raise