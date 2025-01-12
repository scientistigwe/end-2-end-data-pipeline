from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy import and_, or_, desc

from backend.database.models.advanced_analytics import (
    AnalyticsRun,
    AnalyticsModel,
    AnalyticsFeature,
    AnalyticsResult,
    AnalyticsVisualization
)


class AdvancedAnalyticsRepository:
    """Repository for advanced advanced_analytics-related database operations"""

    def __init__(self, db_session: Session):
        """Initialize repository with database session"""
        self.db_session = db_session

    def create_analytics_run(self, data: Dict[str, Any]) -> AnalyticsRun:
        """Create new advanced_analytics run"""
        try:
            run = AnalyticsRun(
                pipeline_id=data['pipeline_id'],
                analysis_type=data['analysis_type'],
                parameters=data.get('parameters', {}),
                status='pending',
                metadata=data.get('metadata', {}),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            self.db_session.add(run)
            self.db_session.commit()
            return run

        except Exception as e:
            self.db_session.rollback()
            raise

    def update_run_status(self, run_id: UUID,
                          status: str,
                          results: Optional[Dict[str, Any]] = None,
                          error: Optional[str] = None) -> None:
        """Update advanced_analytics run status"""
        try:
            run = self.get_run(run_id)
            if run:
                run.status = status
                if results:
                    run.results = results
                if error:
                    run.error = error
                run.updated_at = datetime.utcnow()
                self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise

    def save_analytics_model(self, run_id: UUID, model_data: Dict[str, Any]) -> AnalyticsModel:
        """Save trained model information"""
        try:
            model = AnalyticsModel(
                run_id=run_id,
                model_type=model_data['model_type'],
                parameters=model_data.get('parameters', {}),
                metrics=model_data.get('metrics', {}),
                feature_importance=model_data.get('feature_importance', {}),
                created_at=datetime.utcnow()
            )
            self.db_session.add(model)
            self.db_session.commit()
            return model

        except Exception as e:
            self.db_session.rollback()
            raise

    def save_engineered_features(self, run_id: UUID, features: List[Dict[str, Any]]) -> List[AnalyticsFeature]:
        """Save engineered features"""
        try:
            feature_list = []
            for feature_data in features:
                feature = AnalyticsFeature(
                    run_id=run_id,
                    name=feature_data['name'],
                    description=feature_data.get('description'),
                    feature_type=feature_data['type'],
                    parameters=feature_data.get('parameters', {}),
                    metadata=feature_data.get('metadata', {}),
                    created_at=datetime.utcnow()
                )
                self.db_session.add(feature)
                feature_list.append(feature)

            self.db_session.commit()
            return feature_list

        except Exception as e:
            self.db_session.rollback()
            raise

    def save_analytics_results(self, run_id: UUID, results: Dict[str, Any]) -> AnalyticsResult:
        """Save advanced_analytics results"""
        try:
            result = AnalyticsResult(
                run_id=run_id,
                analysis_type=results['analysis_type'],
                metrics=results.get('metrics', {}),
                insights=results.get('insights', {}),
                predictions=results.get('predictions', {}),
                metadata=results.get('metadata', {}),
                created_at=datetime.utcnow()
            )
            self.db_session.add(result)
            self.db_session.commit()
            return result

        except Exception as e:
            self.db_session.rollback()
            raise

    def save_visualization(self, run_id: UUID, viz_data: Dict[str, Any]) -> AnalyticsVisualization:
        """Save visualization data"""
        try:
            visualization = AnalyticsVisualization(
                run_id=run_id,
                viz_type=viz_data['type'],
                config=viz_data.get('config', {}),
                data=viz_data['data'],
                metadata=viz_data.get('metadata', {}),
                created_at=datetime.utcnow()
            )
            self.db_session.add(visualization)
            self.db_session.commit()
            return visualization

        except Exception as e:
            self.db_session.rollback()
            raise

    def get_run(self, run_id: UUID) -> Optional[AnalyticsRun]:
        """Get advanced_analytics run by ID with related data"""
        return self.db_session.query(AnalyticsRun) \
            .options(
            joinedload(AnalyticsRun.models),
            joinedload(AnalyticsRun.features),
            joinedload(AnalyticsRun.results),
            joinedload(AnalyticsRun.visualizations)
        ) \
            .get(run_id)

    def list_runs(self, filters: Dict[str, Any],
                  page: int = 1,
                  page_size: int = 50) -> Tuple[List[AnalyticsRun], int]:
        """List advanced_analytics runs with filtering and pagination"""
        try:
            query = self.db_session.query(AnalyticsRun)

            # Apply filters
            if filters.get('pipeline_id'):
                query = query.filter(AnalyticsRun.pipeline_id == filters['pipeline_id'])
            if filters.get('analysis_type'):
                query = query.filter(AnalyticsRun.analysis_type == filters['analysis_type'])
            if filters.get('status'):
                query = query.filter(AnalyticsRun.status == filters['status'])

            # Get total count
            total = query.count()

            # Apply pagination
            runs = query.order_by(desc(AnalyticsRun.created_at)) \
                .offset((page - 1) * page_size) \
                .limit(page_size) \
                .all()

            return runs, total

        except Exception as e:
            raise

    def get_model_performance(self, run_id: UUID) -> Dict[str, Any]:
        """Get model performance metrics"""
        try:
            model = self.db_session.query(AnalyticsModel) \
                .filter(AnalyticsModel.run_id == run_id) \
                .first()

            if model:
                return {
                    'metrics': model.metrics,
                    'feature_importance': model.feature_importance
                }
            return {}

        except Exception as e:
            raise