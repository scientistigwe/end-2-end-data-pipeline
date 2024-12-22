# backend/flask_api/app/services/analysis/insight_service.py
import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session
from .....database.models.analysis import InsightAnalysis, Pattern, Correlation, Anomaly

logger = logging.getLogger(__name__)

class InsightService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def start_analysis(self, data: Dict[str, Any]) -> UUID:
        """Start an insight analysis."""
        try:
            analysis = InsightAnalysis(
                pipeline_id=data['pipeline_id'],
                type=data['type'],
                status='pending',
                config=data.get('config', {})
            )
            self.db_session.add(analysis)
            self.db_session.commit()
            return analysis.id
        except Exception as e:
            self.logger.error(f"Error starting insight analysis: {str(e)}")
            self.db_session.rollback()
            raise

    def get_analysis_status(self, analysis_id: UUID) -> Dict[str, Any]:
        """Get status of an insight analysis."""
        analysis = self.db_session.query(InsightAnalysis).get(analysis_id)
        if not analysis:
            raise ValueError(f"Insight analysis {analysis_id} not found")
        return {
            'status': analysis.status,
            'metrics': analysis.metrics,
            'created_at': analysis.created_at,
            'updated_at': analysis.updated_at
        }

    def get_analysis_report(self, analysis_id: UUID) -> Dict[str, Any]:
        """Get results of an insight analysis."""
        analysis = self.db_session.query(InsightAnalysis).get(analysis_id)
        if not analysis:
            raise ValueError(f"Insight analysis {analysis_id} not found")
        return analysis.results

    def get_trends(self, analysis_id: UUID) -> List[Dict[str, Any]]:
        """Get trends from an insight analysis."""
        analysis = self.db_session.query(InsightAnalysis).get(analysis_id)
        if not analysis:
            raise ValueError(f"Insight analysis {analysis_id} not found")
        return analysis.results.get('trends', [])

    def get_pattern(self, analysis_id: UUID, pattern_id: UUID) -> Dict[str, Any]:
        """Get specific pattern details."""
        pattern = self.db_session.query(Pattern).filter(
            Pattern.analysis_id == analysis_id,
            Pattern.id == pattern_id
        ).first()
        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found")
        return {
            'type': pattern.type,
            'name': pattern.name,
            'description': pattern.description,
            'confidence': pattern.confidence,
            'support': pattern.support,
            'data': pattern.data
        }

    def get_correlations(self, analysis_id: UUID) -> List[Dict[str, Any]]:
        """Get correlations from analysis."""
        correlations = self.db_session.query(Correlation).filter(
            Correlation.analysis_id == analysis_id
        ).all()
        return [{
            'field_a': c.field_a,
            'field_b': c.field_b,
            'coefficient': c.coefficient,
            'significance': c.significance,
            'type': c.type,
            'metadata': c.metadata
        } for c in correlations]

    def get_anomalies(self, analysis_id: UUID) -> List[Dict[str, Any]]:
        """Get anomalies from analysis."""
        anomalies = self.db_session.query(Anomaly).filter(
            Anomaly.analysis_id == analysis_id
        ).all()
        return [{
            'field': a.field,
            'type': a.type,
            'severity': a.severity,
            'timestamp': a.timestamp,
            'value': a.value,
            'expected_range': a.expected_range,
            'metadata': a.metadata
        } for a in anomalies]

    def export_report(self, analysis_id: UUID) -> str:
        """Export insight report as a file."""
        analysis = self.db_session.query(InsightAnalysis).get(analysis_id)
        if not analysis:
            raise ValueError(f"Insight analysis {analysis_id} not found")
        # Implementation for report export
        pass