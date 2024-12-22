# app/services/reports/report_service.py
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from .....database.models.reports import (
    Report, ReportTemplate, ReportSection,
    ReportSchedule, ReportExecution
)

class ReportService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def list_reports(self) -> List[Dict[str, Any]]:
        """List all reports."""
        try:
            reports = self.db_session.query(Report).all()
            return [self._format_report(report) for report in reports]
        except Exception as e:
            self.logger.error(f"Error listing reports: {str(e)}")
            raise

    def create_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new report."""
        try:
            report = Report(
                title=data['title'],
                description=data.get('description'),
                type=data['type'],
                format=data.get('format', 'pdf'),
                config=data.get('config', {}),
                owner_id=data['owner_id']
            )
            
            if 'template_id' in data:
                report.template_id = data['template_id']
                
            self.db_session.add(report)
            self.db_session.commit()
            
            return self._format_report(report)
        except Exception as e:
            self.logger.error(f"Error creating report: {str(e)}")
            self.db_session.rollback()
            raise

    def get_report(self, report_id: UUID) -> Dict[str, Any]:
        """Get report details."""
        try:
            report = self.db_session.query(Report).get(report_id)
            if not report:
                raise ValueError("Report not found")
            return self._format_report(report)
        except Exception as e:
            self.logger.error(f"Error getting report: {str(e)}")
            raise

    def update_report(self, report_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update report details."""
        try:
            report = self.db_session.query(Report).get(report_id)
            if not report:
                raise ValueError("Report not found")
                
            # Update fields
            for key, value in data.items():
                if hasattr(report, key):
                    setattr(report, key, value)
                    
            self.db_session.commit()
            return self._format_report(report)
        except Exception as e:
            self.logger.error(f"Error updating report: {str(e)}")
            self.db_session.rollback()
            raise

    def generate_report(self, report_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report content."""
        try:
            report = self.db_session.query(Report).get(report_id)
            if not report:
                raise ValueError("Report not found")
                
            # Create execution record
            execution = ReportExecution(
                report_id=report_id,
                status='running',
                start_time=datetime.utcnow(),
                parameters=data
            )
            self.db_session.add(execution)
            
            try:
                # Generate report content based on type
                if report.type == 'analysis':
                    content = self._generate_analysis_report(report, data)
                elif report.type == 'metrics':
                    content = self._generate_metrics_report(report, data)
                else:
                    content = self._generate_custom_report(report, data)
                    
                execution.status = 'completed'
                execution.end_time = datetime.utcnow()
                execution.output_url = content['url']
                
                self.db_session.commit()
                return content
                
            except Exception as e:
                execution.status = 'failed'
                execution.end_time = datetime.utcnow()
                execution.error = str(e)
                self.db_session.commit()
                raise
                
        except Exception as e:
            self.logger.error(f"Error generating report: {str(e)}")
            self.db_session.rollback()
            raise

    def export_report(self, report_id: UUID, format: str) -> str:
        """Export report as file."""
        try:
            report = self.db_session.query(Report).get(report_id)
            if not report:
                raise ValueError("Report not found")
                
            # Implementation for report export
            pass
        except Exception as e:
            self.logger.error(f"Error exporting report: {str(e)}")
            raise

    def schedule_report(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Schedule report generation."""
        try:
            schedule = ReportSchedule(
                report_id=data['report_id'],
                frequency=data['frequency'],
                cron_expression=data['cron_expression'],
                timezone=data.get('timezone', 'UTC'),
                parameters=data.get('parameters', {})
            )
            
            self.db_session.add(schedule)
            self.db_session.commit()
            
            return self._format_schedule(schedule)
        except Exception as e:
            self.logger.error(f"Error scheduling report: {str(e)}")
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
                description=data.get('description'),
                type=data['type'],
                content=data['content'],
                parameters=data.get('parameters', {}),
                metadata=data.get('metadata', {})
            )
            
            self.db_session.add(template)
            self.db_session.commit()
            
            return self._format_template(template)
        except Exception as e:
            self.logger.error(f"Error creating template: {str(e)}")
            self.db_session.rollback()
            raise

    def _format_report(self, report: Report) -> Dict[str, Any]:
        """Format report for API response."""
        return {
            'id': str(report.id),
            'title': report.title,
            'description': report.description,
            'type': report.type,
            'status': report.status,
            'format': report.format,
            'config': report.config,
            'created_at': report.created_at.isoformat(),
            'updated_at': report.updated_at.isoformat()
        }

    def _format_template(self, template: ReportTemplate) -> Dict[str, Any]:
        """Format template for API response."""
        return {
            'id': str(template.id),
            'name': template.name,
            'description': template.description,
            'type': template.type,
            'content': template.content,
            'parameters': template.parameters,
            'metadata': template.metadata,
            'created_at': template.created_at.isoformat()
        }

    def _format_schedule(self, schedule: ReportSchedule) -> Dict[str, Any]:
        """Format schedule for API response."""
        return {
            'id': str(schedule.id),
            'report_id': str(schedule.report_id),
            'frequency': schedule.frequency,
            'cron_expression': schedule.cron_expression,
            'timezone': schedule.timezone,
            'parameters': schedule.parameters,
            'next_run': schedule.next_run.isoformat() if schedule.next_run else None,
            'last_run': schedule.last_run.isoformat() if schedule.last_run else None
        }