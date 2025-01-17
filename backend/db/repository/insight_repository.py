from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy import and_, or_, desc, func

from backend.db.models.insight_model import (
    InsightRun,
    Insight,
    InsightPattern,
    InsightCorrelation,
    InsightAction,
    BusinessGoal,
    InsightImpact,
    InsightFeedback
)


class InsightRepository:
    """Repository for insight-related db operations"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_insight_run(self, data: Dict[str, Any]) -> InsightRun:
        """Create new insight run"""
        try:
            run = InsightRun(
                name=data['name'],
                description=data.get('description'),
                pipeline_id=data['pipeline_id'],
                source_id=data.get('source_id'),
                analysis_type=data['analysis_type'],
                configuration=data.get('configuration', {}),
                business_goals=data.get('business_goals', {}),
                parameters=data.get('parameters', {}),
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
            results: Optional[Dict[str, Any]] = None,
            error: Optional[str] = None
    ) -> None:
        """Update insight run status"""
        try:
            run = self.get_insight_run(run_id)
            if run:
                run.status = status
                if progress is not None:
                    run.progress = progress
                if results:
                    self._process_insight_results(run.id, results)
                if error:
                    run.error = error
                    run.error_details = {'timestamp': datetime.utcnow().isoformat()}

                if status == 'completed':
                    run.completed_at = datetime.utcnow()
                    if run.started_at:
                        run.execution_time = (run.completed_at - run.started_at).total_seconds()

                self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_insight(self, run_id: UUID, insight_data: Dict[str, Any]) -> Insight:
        """Create new insight"""
        try:
            insight = Insight(
                insight_run_id=run_id,
                title=insight_data['title'],
                description=insight_data['description'],
                insight_type=insight_data['insight_type'],
                category=insight_data.get('category'),
                business_impact=insight_data.get('business_impact'),
                recommendations=insight_data.get('recommendations', {}),
                priority=insight_data.get('priority', 'medium'),
                confidence=insight_data.get('confidence'),
                significance=insight_data.get('significance'),
                impact_score=insight_data.get('impact_score'),
                evidence=insight_data.get('evidence', {}),
                visualization=insight_data.get('visualization', {}),
                related_metrics=insight_data.get('related_metrics', {})
            )
            self.db_session.add(insight)
            self.db_session.commit()
            return insight

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_insight_pattern(
            self,
            run_id: UUID,
            pattern_data: Dict[str, Any]
    ) -> InsightPattern:
        """Create insight pattern"""
        try:
            pattern = InsightPattern(
                insight_run_id=run_id,
                name=pattern_data['name'],
                pattern_type=pattern_data['pattern_type'],
                description=pattern_data.get('description'),
                frequency=pattern_data.get('frequency'),
                duration=pattern_data.get('duration'),
                seasonality=pattern_data.get('seasonality', {}),
                trend=pattern_data.get('trend', {}),
                confidence=pattern_data.get('confidence'),
                support=pattern_data.get('support'),
                strength=pattern_data.get('strength'),
                conditions=pattern_data.get('conditions', {}),
                exceptions=pattern_data.get('exceptions', {}),
                related_entities=pattern_data.get('related_entities', {})
            )
            self.db_session.add(pattern)
            self.db_session.commit()
            return pattern

        except Exception as e:
            self.db_session.rollback()
            raise


    def create_insight_correlation(
            self,
            run_id: UUID,
            correlation_data: Dict[str, Any]
    ) -> InsightCorrelation:
        """Create insight correlation"""
        try:
            correlation = InsightCorrelation(
                insight_run_id=run_id,
                name=correlation_data['name'],
                correlation_type=correlation_data['correlation_type'],
                entity_a=correlation_data['entity_a'],
                entity_b=correlation_data['entity_b'],
                correlation_coefficient=correlation_data.get('correlation_coefficient'),
                significance=correlation_data.get('significance'),
                confidence_interval=correlation_data.get('confidence_interval', {}),
                time_window=correlation_data.get('time_window'),
                lag=correlation_data.get('lag'),
                seasonally_adjusted=correlation_data.get('seasonally_adjusted', False),
                causality_indicators=correlation_data.get('causality_indicators', {}),
                external_factors=correlation_data.get('external_factors', {}),
                limitations=correlation_data.get('limitations', {})
            )
            self.db_session.add(correlation)
            self.db_session.commit()
            return correlation

        except Exception as e:
            self.db_session.rollback()
            raise


    def create_insight_action(
            self,
            insight_id: UUID,
            action_data: Dict[str, Any]
    ) -> InsightAction:
        """Create action for an insight"""
        try:
            action = InsightAction(
                insight_id=insight_id,
                action_type=action_data['action_type'],
                description=action_data['description'],
                priority=action_data.get('priority', 'medium'),
                status='pending',
                assigned_to=action_data.get('assigned_to'),
                implementation_plan=action_data.get('implementation_plan', {}),
                resources_required=action_data.get('resources_required', {}),
                dependencies=action_data.get('dependencies', {})
            )
            self.db_session.add(action)
            self.db_session.commit()
            return action

        except Exception as e:
            self.db_session.rollback()
            raise


    def create_business_goal(self, goal_data: Dict[str, Any]) -> BusinessGoal:
        """Create business goal"""
        try:
            goal = BusinessGoal(
                name=goal_data['name'],
                description=goal_data.get('description'),
                category=goal_data.get('category'),
                target_value=goal_data.get('target_value'),
                current_value=goal_data.get('current_value'),
                start_date=goal_data.get('start_date'),
                target_date=goal_data.get('target_date'),
                status='active',
                priority=goal_data.get('priority', 'medium'),
                metrics=goal_data.get('metrics', {}),
                thresholds=goal_data.get('thresholds', {}),
                dependencies=goal_data.get('dependencies', {})
            )
            self.db_session.add(goal)
            self.db_session.commit()
            return goal

        except Exception as e:
            self.db_session.rollback()
            raise


    def track_insight_impact(
            self,
            insight_id: UUID,
            impact_data: Dict[str, Any]
    ) -> InsightImpact:
        """Track impact of an insight"""
        try:
            impact = InsightImpact(
                insight_id=insight_id,
                metric_name=impact_data['metric_name'],
                baseline_value=impact_data.get('baseline_value'),
                current_value=impact_data.get('current_value'),
                target_value=impact_data.get('target_value'),
                measurement_date=datetime.utcnow(),
                baseline_date=impact_data.get('baseline_date'),
                change_percentage=impact_data.get('change_percentage'),
                absolute_change=impact_data.get('absolute_change'),
                impact_duration=impact_data.get('impact_duration'),
                confidence_level=impact_data.get('confidence_level'),
                measurement_method=impact_data.get('measurement_method'),
                control_variables=impact_data.get('control_variables', {}),
                external_factors=impact_data.get('external_factors', {}),
                limitations=impact_data.get('limitations', {})
            )
            self.db_session.add(impact)
            self.db_session.commit()
            return impact

        except Exception as e:
            self.db_session.rollback()
            raise


    def add_insight_feedback(
            self,
            insight_id: UUID,
            feedback_data: Dict[str, Any]
    ) -> InsightFeedback:
        """Add feedback for an insight"""
        try:
            feedback = InsightFeedback(
                insight_id=insight_id,
                user_id=feedback_data['user_id'],
                rating=feedback_data.get('rating'),
                feedback_type=feedback_data.get('feedback_type'),
                comment=feedback_data.get('comment'),
                suggestions=feedback_data.get('suggestions'),
                accuracy_rating=feedback_data.get('accuracy_rating'),
                actionability_rating=feedback_data.get('actionability_rating'),
                relevance_rating=feedback_data.get('relevance_rating'),
                context=feedback_data.get('context', {})
            )
            self.db_session.add(feedback)
            self.db_session.commit()
            return feedback

        except Exception as e:
            self.db_session.rollback()
            raise


    def _process_insight_results(self, run_id: UUID, results: Dict[str, Any]) -> None:
        """Process and store insight results"""
        try:
            # Update run metrics
            run = self.get_insight_run(run_id)
            if run:
                run.total_insights = len(results.get('insights', []))
                run.significant_insights = len([
                    i for i in results.get('insights', [])
                    if i.get('significance', 0) > 0.8
                ])
                run.actionable_insights = len([
                    i for i in results.get('insights', [])
                    if i.get('recommendations')
                ])

                # Calculate overall impact score
                impact_scores = [
                    i.get('impact_score', 0)
                    for i in results.get('insights', [])
                ]
                run.impact_score = sum(impact_scores) / len(impact_scores) if impact_scores else 0

            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise


    def get_insight_run(self, run_id: UUID) -> Optional[InsightRun]:
        """Get insight run by ID with related data"""
        return self.db_session.query(InsightRun) \
            .options(
            joinedload(InsightRun.insights),
            joinedload(InsightRun.patterns),
            joinedload(InsightRun.correlations)
        ) \
            .get(run_id)


    def list_insight_runs(
            self,
            filters: Dict[str, Any],
            page: int = 1,
            page_size: int = 50
    ) -> Tuple[List[InsightRun], int]:
        """List insight runs with filtering and pagination"""
        try:
            query = self.db_session.query(InsightRun)

            # Apply filters
            if filters.get('pipeline_id'):
                query = query.filter(InsightRun.pipeline_id == filters['pipeline_id'])
            if filters.get('source_id'):
                query = query.filter(InsightRun.source_id == filters['source_id'])
            if filters.get('analysis_type'):
                query = query.filter(InsightRun.analysis_type == filters['analysis_type'])
            if filters.get('status'):
                query = query.filter(InsightRun.status == filters['status'])
            if filters.get('min_impact'):
                query = query.filter(InsightRun.impact_score >= filters['min_impact'])

            # Get total count
            total = query.count()

            # Apply pagination
            runs = query.order_by(desc(InsightRun.started_at)) \
                .offset((page - 1) * page_size) \
                .limit(page_size) \
                .all()

            return runs, total

        except Exception as e:
            raise


    def get_insights_by_goal(
            self,
            goal_id: UUID,
            min_impact: Optional[float] = None
    ) -> List[Insight]:
        """Get insights related to a business goal"""
        query = self.db_session.query(Insight) \
            .join(BusinessGoal, Insight.business_goals) \
            .filter(BusinessGoal.id == goal_id)

        if min_impact:
            query = query.filter(Insight.impact_score >= min_impact)

        return query.order_by(desc(Insight.impact_score)).all()


    def get_insight_impact_summary(self, insight_id: UUID) -> Dict[str, Any]:
        """Get impact summary for an insight"""
        impact_records = self.db_session.query(InsightImpact) \
            .filter(InsightImpact.insight_id == insight_id) \
            .order_by(desc(InsightImpact.measurement_date)) \
            .all()

        if not impact_records:
            return {}

        latest_impact = impact_records[0]
        return {
            'metric_name': latest_impact.metric_name,
            'baseline_value': latest_impact.baseline_value,
            'current_value': latest_impact.current_value,
            'change_percentage': latest_impact.change_percentage,
            'impact_duration': latest_impact.impact_duration,
            'confidence_level': latest_impact.confidence_level,
            'measurement_date': latest_impact.measurement_date.isoformat(),
            'has_limitations': bool(latest_impact.limitations)
        }


    def get_actionable_insights(
            self,
            min_confidence: float = 0.7,
            limit: int = 10
    ) -> List[Insight]:
        """Get high-confidence actionable insights"""
        return self.db_session.query(Insight) \
            .filter(
            Insight.confidence >= min_confidence,
            Insight.status == 'new',
            Insight.recommendations.is_not(None)
        ) \
            .order_by(
            desc(Insight.impact_score),
            desc(Insight.confidence)
        ) \
            .limit(limit) \
            .all()


    def get_insight_feedback_summary(self, insight_id: UUID) -> Dict[str, Any]:
        """Get feedback summary for an insight"""
        feedback_records = self.db_session.query(InsightFeedback) \
            .filter(InsightFeedback.insight_id == insight_id) \
            .all()

        if not feedback_records:
            return {}

        return {
            'average_rating': sum(f.rating for f in feedback_records) / len(feedback_records),
            'accuracy_score': sum(f.accuracy_rating for f in feedback_records) / len(feedback_records),
            'actionability_score': sum(f.actionability_rating for f in feedback_records) / len(feedback_records),
            'relevance_score': sum(f.relevance_rating for f in feedback_records) / len(feedback_records),
            'feedback_count': len(feedback_records),
            'has_suggestions': any(f.suggestions for f in feedback_records)
        }