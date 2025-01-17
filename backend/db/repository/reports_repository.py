from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy import and_, or_, desc, func

from backend.db.models.report import (
    ReportRun,
    ReportSection,
    ReportVisualization,
    ReportValidation,
    ReportSchedule,
    ReportTemplate
)


class ReportRepository:
    """Repository for report-related db operations"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_report_run(self, data: Dict[str, Any]) -> ReportRun:
        """Create new report run"""
        try:
            run = ReportRun(
                name=data['name'],
                description=data.get('description'),
                pipeline_id=data['pipeline_id'],
                report_type=data['report_type'],
                template_id=data.get('template_id'),
                format=data.get('format', 'pdf'),
                parameters=data.get('parameters', {}),
                filters=data.get('filters', {}),
                data_sources=data.get('data_sources', {}),
                status='pending',
                started_at=datetime.utcnow()
            )
            self.db_session.add(run)
            self.db_session.commit()
            return run

        except Exception as e:
            self.db_session.rollback()
            raise

    def update_run_status(
            self,
            run_id: UUID,
            status: str,
            progress: Optional[float] = None,
            error: Optional[str] = None,
            output_url: Optional[str] = None,
            output_size: Optional[int] = None
    ) -> None:
        """Update report run status"""
        try:
            run = self.get_report_run(run_id)
            if run:
                run.status = status
                if progress is not None:
                    run.progress = progress
                if error:
                    run.error = error
                    run.error_details = {'timestamp': datetime.utcnow().isoformat()}
                if output_url:
                    run.output_url = output_url
                if output_size:
                    run.output_size = output_size

                if status == 'completed':
                    run.completed_at = datetime.utcnow()
                    if run.started_at:
                        run.execution_time = (run.completed_at - run.started_at).total_seconds()

                self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_report_section(
            self,
            run_id: UUID,
            section_data: Dict[str, Any]
    ) -> ReportSection:
        """Create report section"""
        try:
            section = ReportSection(
                report_run_id=run_id,
                title=section_data['title'],
                section_type=section_data['section_type'],
                content=section_data.get('content', {}),
                order=section_data['order'],
                template_id=section_data.get('template_id'),
                parameters=section_data.get('parameters', {}),
                data_source=section_data.get('data_source', {}),
                filters=section_data.get('filters', {}),
                is_dynamic=section_data.get('is_dynamic', False),
                requires_refresh=section_data.get('requires_refresh', False),
                cache_duration=section_data.get('cache_duration')
            )
            self.db_session.add(section)
            self.db_session.commit()
            return section

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_visualization(
            self,
            run_id: UUID,
            section_id: Optional[UUID],
            viz_data: Dict[str, Any]
    ) -> ReportVisualization:
        """Create report visualization"""
        try:
            viz = ReportVisualization(
                report_run_id=run_id,
                section_id=section_id,
                title=viz_data['title'],
                viz_type=viz_data['viz_type'],
                config=viz_data.get('config', {}),
                data=viz_data.get('data', {}),
                description=viz_data.get('description'),
                parameters=viz_data.get('parameters', {}),
                source_query=viz_data.get('source_query'),
                refresh_interval=viz_data.get('refresh_interval')
            )
            self.db_session.add(viz)
            self.db_session.commit()
            return viz

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_validation(
            self,
            run_id: UUID,
            validation_data: Dict[str, Any]
    ) -> ReportValidation:
        """Create report validation"""
        try:
            validation = ReportValidation(
                report_run_id=run_id,
                name=validation_data['name'],
                validation_type=validation_data['validation_type'],
                parameters=validation_data.get('parameters', {}),
                status=validation_data['status'],
                results=validation_data.get('results', {}),
                error_message=validation_data.get('error_message'),
                execution_time=validation_data.get('execution_time'),
                severity=validation_data.get('severity', 'medium')
            )
            self.db_session.add(validation)
            self.db_session.commit()
            return validation

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_schedule(self, schedule_data: Dict[str, Any]) -> ReportSchedule:
        """Create report schedule"""
        try:
            schedule = ReportSchedule(
                report_type=schedule_data['report_type'],
                frequency=schedule_data['frequency'],
                cron_expression=schedule_data.get('cron_expression'),
                timezone=schedule_data.get('timezone', 'UTC'),
                parameters=schedule_data.get('parameters', {}),
                notification_config=schedule_data.get('notification_config', {}),
                retry_config=schedule_data.get('retry_config', {}),
                is_active=schedule_data.get('is_active', True),
                created_by=schedule_data.get('created_by'),
                modified_by=schedule_data.get('modified_by')
            )
            self.db_session.add(schedule)
            self.db_session.commit()
            return schedule

        except Exception as e:
            self.db_session.rollback()
            raise

        def create_template(self, template_data: Dict[str, Any]) -> ReportTemplate:
            """Create report template"""
            try:
                template = ReportTemplate(
                    name=template_data['name'],
                    description=template_data.get('description'),
                    template_type=template_data['template_type'],
                    content=template_data['content'],
                    parameters=template_data.get('parameters', {}),
                    default_config=template_data.get('default_config', {}),
                    validation_rules=template_data.get('validation_rules', {}),
                    version=template_data.get('version', 1),
                    is_active=template_data.get('is_active', True),
                    created_by=template_data.get('created_by'),
                    approved_by=template_data.get('approved_by'),
                    category=template_data.get('category'),
                    tags=template_data.get('tags', [])
                )
                self.db_session.add(template)
                self.db_session.commit()
                return template

            except Exception as e:
                self.db_session.rollback()
                raise

        def get_report_run(self, run_id: UUID) -> Optional[ReportRun]:
            """Get report run by ID with related data"""
            return self.db_session.query(ReportRun) \
                .options(
                joinedload(ReportRun.sections),
                joinedload(ReportRun.visualizations),
                joinedload(ReportRun.validations)
            ) \
                .get(run_id)

        def list_report_runs(
                self,
                filters: Dict[str, Any],
                page: int = 1,
                page_size: int = 50
        ) -> Tuple[List[ReportRun], int]:
            """List report runs with filtering and pagination"""
            try:
                query = self.db_session.query(ReportRun)

                # Apply filters
                if filters.get('pipeline_id'):
                    query = query.filter(ReportRun.pipeline_id == filters['pipeline_id'])
                if filters.get('report_type'):
                    query = query.filter(ReportRun.report_type == filters['report_type'])
                if filters.get('status'):
                    query = query.filter(ReportRun.status == filters['status'])
                if filters.get('template_id'):
                    query = query.filter(ReportRun.template_id == filters['template_id'])
                if filters.get('date_from'):
                    query = query.filter(ReportRun.started_at >= filters['date_from'])
                if filters.get('date_to'):
                    query = query.filter(ReportRun.started_at <= filters['date_to'])

                # Get total count
                total = query.count()

                # Apply pagination
                runs = query.order_by(desc(ReportRun.started_at)) \
                    .offset((page - 1) * page_size) \
                    .limit(page_size) \
                    .all()

                return runs, total

            except Exception as e:
                raise

        def get_report_sections(
                self,
                run_id: UUID,
                section_type: Optional[str] = None
        ) -> List[ReportSection]:
            """Get sections for a report run"""
            query = self.db_session.query(ReportSection) \
                .filter(ReportSection.report_run_id == run_id)

            if section_type:
                query = query.filter(ReportSection.section_type == section_type)

            return query.order_by(ReportSection.order).all()

        def get_visualizations(
                self,
                run_id: UUID,
                section_id: Optional[UUID] = None,
                viz_type: Optional[str] = None
        ) -> List[ReportVisualization]:
            """Get visualizations for a report run or section"""
            query = self.db_session.query(ReportVisualization) \
                .filter(ReportVisualization.report_run_id == run_id)

            if section_id:
                query = query.filter(ReportVisualization.section_id == section_id)
            if viz_type:
                query = query.filter(ReportVisualization.viz_type == viz_type)

            return query.all()

        def get_validations(
                self,
                run_id: UUID,
                status: Optional[str] = None
        ) -> List[ReportValidation]:
            """Get validations for a report run"""
            query = self.db_session.query(ReportValidation) \
                .filter(ReportValidation.report_run_id == run_id)

            if status:
                query = query.filter(ReportValidation.status == status)

            return query.all()

        def get_active_schedules(self) -> List[ReportSchedule]:
            """Get all active report schedules"""
            return self.db_session.query(ReportSchedule) \
                .filter(ReportSchedule.is_active == True) \
                .order_by(ReportSchedule.next_run) \
                .all()

        def get_template(
                self,
                template_id: UUID,
                version: Optional[int] = None
        ) -> Optional[ReportTemplate]:
            """Get report template by ID and optional version"""
            query = self.db_session.query(ReportTemplate) \
                .filter(ReportTemplate.id == template_id)

            if version:
                query = query.filter(ReportTemplate.version == version)
            else:
                # Get latest version
                query = query.order_by(desc(ReportTemplate.version))

            return query.first()

        def list_templates(
                self,
                filters: Dict[str, Any],
                page: int = 1,
                page_size: int = 50
        ) -> Tuple[List[ReportTemplate], int]:
            """List report templates with filtering and pagination"""
            try:
                query = self.db_session.query(ReportTemplate)

                # Apply filters
                if filters.get('template_type'):
                    query = query.filter(ReportTemplate.template_type == filters['template_type'])
                if filters.get('category'):
                    query = query.filter(ReportTemplate.category == filters['category'])
                if filters.get('is_active'):
                    query = query.filter(ReportTemplate.is_active == filters['is_active'])
                if filters.get('tags'):
                    query = query.filter(ReportTemplate.tags.contains(filters['tags']))

                # Get total count
                total = query.count()

                # Apply pagination
                templates = query.order_by(ReportTemplate.name) \
                    .offset((page - 1) * page_size) \
                    .limit(page_size) \
                    .all()

                return templates, total

            except Exception as e:
                raise

        def get_report_summary(self, run_id: UUID) -> Dict[str, Any]:
            """Get summary of report run"""
            run = self.get_report_run(run_id)
            if not run:
                return {}

            return {
                'name': run.name,
                'type': run.report_type,
                'status': run.status,
                'progress': run.progress,
                'section_count': len(run.sections),
                'visualization_count': len(run.visualizations),
                'validation_count': len(run.validations),
                'execution_time': run.execution_time,
                'started_at': run.started_at.isoformat() if run.started_at else None,
                'completed_at': run.completed_at.isoformat() if run.completed_at else None,
                'has_error': bool(run.error),
                'output_url': run.output_url,
                'output_size': run.output_size
            }

        def update_schedule_status(
                self,
                schedule_id: UUID,
                last_run: datetime,
                next_run: datetime,
                status: str
        ) -> None:
            """Update schedule execution status"""
            try:
                schedule = self.db_session.query(ReportSchedule).get(schedule_id)
                if schedule:
                    schedule.last_run = last_run
                    schedule.next_run = next_run
                    schedule.last_status = status
                    schedule.modified_by = schedule.created_by
                    self.db_session.commit()

            except Exception as e:
                self.db_session.rollback()
                raise

        def increment_template_usage(self, template_id: UUID) -> None:
            """Increment template usage counter"""
            try:
                template = self.db_session.query(ReportTemplate).get(template_id)
                if template:
                    template.usage_count += 1
                    self.db_session.commit()

            except Exception as e:
                self.db_session.rollback()
                raise