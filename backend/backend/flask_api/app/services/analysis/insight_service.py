import logging
from typing import Dict, Any, List
from uuid import UUID
from sqlalchemy.orm import Session
from .....database.models.insight_model import (
    InsightRun,
    Insight,
    InsightPattern,
    InsightCorrelation
)

logger = logging.getLogger(__name__)


class InsightService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def start_analysis(self, data: Dict[str, Any]) -> UUID:
        """Start an insight analysis."""
        try:
            insight_run = InsightRun(
                name=data.get('name', 'Unnamed Insight Run'),
                description=data.get('description', ''),
                pipeline_id=data['pipeline_id'],
                analysis_type=data['type'],
                status='pending',
                configuration=data.get('config', {}),
                business_goals=data.get('business_goals', {})
            )
            self.db_session.add(insight_run)
            self.db_session.commit()
            return insight_run.id
        except Exception as e:
            self.logger.error(f"Error starting insight analysis: {str(e)}")
            self.db_session.rollback()
            raise

    def get_analysis_status(self, analysis_id: UUID) -> Dict[str, Any]:
        """Get status of an insight analysis."""
        insight_run = self.db_session.query(InsightRun).get(analysis_id)
        if not insight_run:
            raise ValueError(f"Insight run {analysis_id} not found")
        return {
            'status': insight_run.status,
            'progress': insight_run.progress,
            'total_insights': insight_run.total_insights,
            'significant_insights': insight_run.significant_insights,
            'started_at': insight_run.started_at,
            'completed_at': insight_run.completed_at,
            'error': insight_run.error
        }

    def get_analysis_report(self, analysis_id: UUID) -> List[Dict[str, Any]]:
        """Get results of an insight analysis."""
        insights = self.db_session.query(Insight).filter(
            Insight.insight_run_id == analysis_id
        ).all()

        return [{
            'id': insight.id,
            'title': insight.title,
            'description': insight.description,
            'type': insight.insight_type,
            'category': insight.category,
            'priority': insight.priority,
            'confidence': insight.confidence,
            'business_impact': insight.business_impact,
            'recommendations': insight.recommendations
        } for insight in insights]

    def get_trends(self, analysis_id: UUID) -> List[Dict[str, Any]]:
        """Get trends from an insight analysis."""
        patterns = self.db_session.query(InsightPattern).filter(
            InsightPattern.insight_run_id == analysis_id
        ).all()

        return [{
            'id': pattern.id,
            'name': pattern.name,
            'type': pattern.pattern_type,
            'description': pattern.description,
            'frequency': pattern.frequency,
            'confidence': pattern.confidence,
            'trend': pattern.trend
        } for pattern in patterns]

    def get_pattern(self, analysis_id: UUID, pattern_id: UUID) -> Dict[str, Any]:
        """Get specific pattern details."""
        pattern = self.db_session.query(InsightPattern).filter(
            InsightPattern.insight_run_id == analysis_id,
            InsightPattern.id == pattern_id
        ).first()

        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found")

        return {
            'name': pattern.name,
            'type': pattern.pattern_type,
            'description': pattern.description,
            'frequency': pattern.frequency,
            'duration': pattern.duration,
            'seasonality': pattern.seasonality,
            'confidence': pattern.confidence,
            'support': pattern.support,
            'conditions': pattern.conditions,
            'exceptions': pattern.exceptions
        }

    def get_correlations(self, analysis_id: UUID) -> List[Dict[str, Any]]:
        """Get correlations from analysis."""
        correlations = self.db_session.query(InsightCorrelation).filter(
            InsightCorrelation.insight_run_id == analysis_id
        ).all()

        return [{
            'id': corr.id,
            'name': corr.name,
            'type': corr.correlation_type,
            'entity_a': corr.entity_a,
            'entity_b': corr.entity_b,
            'correlation_coefficient': corr.correlation_coefficient,
            'significance': corr.significance,
            'time_window': corr.time_window,
            'causality_indicators': corr.causality_indicators
        } for corr in correlations]

    def export_report(self, analysis_id: UUID) -> Dict[str, Any]:
        """Export comprehensive insight report."""
        insight_run = self.db_session.query(InsightRun).get(analysis_id)
        if not insight_run:
            raise ValueError(f"Insight run {analysis_id} not found")

        return {
            'run_details': {
                'name': insight_run.name,
                'description': insight_run.description,
                'analysis_type': insight_run.analysis_type,
                'status': insight_run.status,
                'started_at': insight_run.started_at,
                'completed_at': insight_run.completed_at,
                'total_insights': insight_run.total_insights,
                'significant_insights': insight_run.significant_insights,
                'impact_score': insight_run.impact_score
            },
            'insights': self.get_analysis_report(analysis_id),
            'patterns': self.get_trends(analysis_id),
            'correlations': self.get_correlations(analysis_id)
        }