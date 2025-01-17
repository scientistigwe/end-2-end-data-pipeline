import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from .....db.models.report_model import (
    ReportRun,
    ReportSection,
    ReportTemplate,
    ReportSchedule,
    ReportVisualization
)


class ReportService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def list_reports(self) -> List[Dict[str, Any]]:
        """List all report runs."""
        try:
            reports = self.db_session.query(ReportRun).all()
            return [self._format_report_run(report) for report in reports]
        except Exception as e:
            self.logger.error(f"Error listing reports: {str(e)}")
            raise

    def create_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new report run."""
        try:
            report_run = ReportRun(
                name=data.get('name', 'Unnamed Report'),
                description=data.get('description', ''),
                pipeline_id=data['pipeline_id'],
                report_type=data['report_type'],
                format=data.get('format', 'pdf'),
                parameters=data.get('parameters', {}),
                filters=data.get('filters', {}),
                data_sources=data.get('data_sources', {})
            )

            if 'template_id' in data:
                report_run.template_id = data['template_id']

            self.db_session.add(report_run)
            self.db_session.commit()

            return self._format_report_run(report_run)
        except Exception as e:
            self.logger.error(f"Error creating report run: {str(e)}")
            self.db_session.rollback()
            raise

    def get_report(self, report_id: UUID) -> Dict[str, Any]:
        """Get report run details."""
        try:
            report = self.db_session.query(ReportRun).get(report_id)
            if not report:
                raise ValueError("Report run not found")
            return self._format_report_run(report)
        except Exception as e:
            self.logger.error(f"Error getting report run: {str(e)}")
            raise

    def generate_report(self, report_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report content."""
        try:
            report = self.db_session.query(ReportRun).get(report_id)
            if not report:
                raise ValueError("Report run not found")

            # Update report run status
            report.status = 'running'
            report.started_at = datetime.utcnow()

            try:
                # Add sections to the report
                sections = data.get('sections', [])
                for idx, section_data in enumerate(sections):
                    section = ReportSection(
                        report_run_id=report_id,
                        title=section_data.get('title', f'Section {idx + 1}'),
                        section_type=section_data.get('type', 'default'),
                        content=section_data.get('content', {}),
                        order=idx,
                        parameters=section_data.get('parameters', {}),
                        data_source=section_data.get('data_source', {})
                    )
                    self.db_session.add(section)

                # Add visualizations if present
                visualizations = data.get('visualizations', [])
                for viz_data in visualizations:
                    viz = ReportVisualization(
                        report_run_id=report_id,
                        title=viz_data.get('title', 'Unnamed Visualization'),
                        viz_type=viz_data.get('type', 'chart'),
                        config=viz_data.get('config', {}),
                        data=viz_data.get('data', {}),
                        description=viz_data.get('description', '')
                    )
                    self.db_session.add(viz)

                # Mark report as complete
                report.status = 'completed'
                report.completed_at = datetime.utcnow()
                report.output_url = data.get('output_url', '')
                report.output_size = len(str(data)) if 'output_url' in data else 0
                report.execution_time = (report.completed_at - report.started_at).total_seconds()

                self.db_session.commit()

                return self._format_report_run(report)

            except Exception as e:
                report.status = 'failed'
                report.error = str(e)
                self.db_session.commit()
                raise

        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            self.db_session.rollback()
            raise

    def list_templates(self) -> List[Dict[str, Any]]:
        """List report templates."""
        try:
            templates = self.db_session.query(ReportTemplate).filter_by(
                is_active=True
            ).all()
            return [self._format_template(template) for template in templates]
        except Exception as e:
            self.logger.error(f"Error listing templates: {str(e)}")
            raise

    def create_template(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create report template."""
        try:
            template = ReportTemplate(
                name=data['name'],
                description=data.get('description', ''),
                template_type=data['template_type'],
                content=data.get('content', {}),
                parameters=data.get('parameters', {}),
                default_config=data.get('default_config', {}),
                created_by=data.get('created_by')
            )

            self.db_session.add(template)
            self.db_session.commit()

            return self._format_template(template)
        except Exception as e:
            self.logger.error(f"Error creating template: {str(e)}")
            self.db_session.rollback()
            raise

    def schedule_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule report generation."""
        try:
            schedule = ReportSchedule(
                report_type=data['report_type'],
                frequency=data['frequency'],
                cron_expression=data.get('cron_expression'),
                timezone=data.get('timezone', 'UTC'),
                parameters=data.get('parameters', {}),
                created_by=data.get('created_by'),
                is_active=data.get('is_active', True)
            )

            self.db_session.add(schedule)
            self.db_session.commit()

            return self._format_schedule(schedule)
        except Exception as e:
            self.logger.error(f"Error scheduling report: {str(e)}")
            self.db_session.rollback()
            raise

    def _format_report_run(self, report: ReportRun) -> Dict[str, Any]:
        """Format report run for API response."""
        return {
            'id': str(report.id),
            'name': report.name,
            'description': report.description,
            'pipeline_id': str(report.pipeline_id),
            'report_type': report.report_type,
            'status': report.status,
            'progress': report.progress,
            'format': report.format,
            'output_url': report.output_url,
            'started_at': report.started_at.isoformat() if report.started_at else None,
            'completed_at': report.completed_at.isoformat() if report.completed_at else None,
            'execution_time': report.execution_time,
            'error': report.error
        }

    def _format_template(self, template: ReportTemplate) -> Dict[str, Any]:
        """Format template for API response."""
        return {
            'id': str(template.id),
            'name': template.name,
            'description': template.description,
            'template_type': template.template_type,
            'version': template.version,
            'is_active': template.is_active,
            'created_by': str(template.created_by) if template.created_by else None,
            'category': template.category,
            'usage_count': template.usage_count
        }

    def _format_schedule(self, schedule: ReportSchedule) -> Dict[str, Any]:
        """Format schedule for API response."""
        return {
            'id': str(schedule.id),
            'report_type': schedule.report_type,
            'frequency': schedule.frequency,
            'cron_expression': schedule.cron_expression,
            'timezone': schedule.timezone,
            'is_active': schedule.is_active,
            'last_run': schedule.last_run.isoformat() if schedule.last_run else None,
            'next_run': schedule.next_run.isoformat() if schedule.next_run else None,
            'last_status': schedule.last_status
        }