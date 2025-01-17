# backend/api/app/services/analysis/insight_service.py
import logging
import asyncio
from typing import Dict, Any, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from backend.db.models.insight_model import (
    InsightRun,
    Insight,
    InsightPattern,
    InsightCorrelation
)

logger = logging.getLogger(__name__)


class InsightService:
    """Service for managing insights and analysis."""

    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logger

        # Initialize event loop if needed for future async operations
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

    async def start_analysis_async(self, data: Dict[str, Any]) -> UUID:
        """Async version of start_analysis."""
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
            await self.db_session.flush()
            await self.db_session.commit()
            return insight_run.id
        except Exception as e:
            self.logger.error(f"Error starting insight analysis: {str(e)}")
            await self.db_session.rollback()
            raise

    def start_analysis(self, data: Dict[str, Any]) -> UUID:
        """Synchronous wrapper for start_analysis_async."""
        return self.loop.run_until_complete(self.start_analysis_async(data))

    async def get_analysis_status_async(self, analysis_id: UUID) -> Dict[str, Any]:
        """Async version of get_analysis_status."""
        insight_run = await self.db_session.query(InsightRun).get(analysis_id)
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

    def get_analysis_status(self, analysis_id: UUID) -> Dict[str, Any]:
        """Synchronous wrapper for get_analysis_status_async."""
        return self.loop.run_until_complete(
            self.get_analysis_status_async(analysis_id)
        )

    def cleanup(self):
        """Cleanup service resources."""
        try:
            if hasattr(self, 'loop') and self.loop.is_running():
                self.loop.stop()
                self.loop.close()
        except Exception as e:
            self.logger.error(f"Error during service cleanup: {str(e)}")

    def __del__(self):
        """Cleanup on destruction."""
        self.cleanup()

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