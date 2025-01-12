from sqlalchemy.orm import Session, joinedload
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy import and_, or_, desc, func

from backend.database.models.data_quality_model import (
    QualityRun,
    DataProfile,
    QualityValidation,
    QualityMetric
)


class QualityRepository:
    """Repository for quality-related database operations"""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def create_quality_run(self, data: Dict[str, Any]) -> QualityRun:
        """Create new quality run"""
        try:
            run = QualityRun(
                name=data['name'],
                description=data.get('description'),
                pipeline_id=data['pipeline_id'],
                dataset_id=data.get('dataset_id'),
                check_type=data.get('check_type', 'validation'),
                configuration=data.get('configuration', {}),
                rules=data.get('rules', {}),
                thresholds=data.get('thresholds', {}),
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
        """Update quality run status"""
        try:
            run = self.get_quality_run(run_id)
            if run:
                run.status = status
                if progress is not None:
                    run.progress = progress
                if results:
                    self._update_quality_metrics(run.id, results)
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

    def create_data_profile(self, run_id: UUID, profile_data: Dict[str, Any]) -> DataProfile:
        """Create data profile"""
        try:
            profile = DataProfile(
                quality_run_id=run_id,
                profile_type=profile_data['profile_type'],
                target_name=profile_data['target_name'],
                row_count=profile_data.get('row_count'),
                null_count=profile_data.get('null_count'),
                unique_count=profile_data.get('unique_count'),
                data_type=profile_data.get('data_type'),
                distribution_type=profile_data.get('distribution_type'),
                distribution_params=profile_data.get('distribution_params', {}),
                quantiles=profile_data.get('quantiles', {}),
                histogram=profile_data.get('histogram', {}),
                numeric_stats=profile_data.get('numeric_stats', {}),
                categorical_stats=profile_data.get('categorical_stats', {}),
                text_stats=profile_data.get('text_stats', {}),
                temporal_stats=profile_data.get('temporal_stats', {}),
                quality_issues=profile_data.get('quality_issues', {}),
                recommendations=profile_data.get('recommendations', {})
            )
            self.db_session.add(profile)
            self.db_session.commit()
            return profile

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_validation(self, run_id: UUID, validation_data: Dict[str, Any]) -> QualityValidation:
        """Create validation result"""
        try:
            validation = QualityValidation(
                quality_run_id=run_id,
                validation_type=validation_data['validation_type'],
                name=validation_data['name'],
                description=validation_data.get('description'),
                rule_id=validation_data.get('rule_id'),
                rule_config=validation_data.get('rule_config', {}),
                parameters=validation_data.get('parameters', {}),
                status=validation_data['status'],
                result=validation_data.get('result', {}),
                failed_rows=validation_data.get('failed_rows', 0),
                impact_score=validation_data.get('impact_score'),
                context=validation_data.get('context', {}),
                affected_columns=validation_data.get('affected_columns', {}),
                suggestions=validation_data.get('suggestions', {})
            )
            self.db_session.add(validation)
            self.db_session.commit()
            return validation

        except Exception as e:
            self.db_session.rollback()
            raise

    def _update_quality_metrics(self, run_id: UUID, results: Dict[str, Any]) -> None:
        """Update quality metrics from results"""
        try:
            # Calculate summary metrics
            total_checks = len(results.get('validations', []))
            passed_checks = len([v for v in results.get('validations', [])
                                 if v.get('status') == 'passed'])
            failed_checks = total_checks - passed_checks

            # Update run with metrics
            run = self.get_quality_run(run_id)
            if run:
                run.total_checks = total_checks
                run.passed_checks = passed_checks
                run.failed_checks = failed_checks
                run.quality_score = (passed_checks / total_checks * 100) if total_checks > 0 else 0

            self.db_session.commit()

        except Exception as e:
            self.db_session.rollback()
            raise

    def get_quality_run(self, run_id: UUID) -> Optional[QualityRun]:
        """Get quality run by ID with related data"""
        return self.db_session.query(QualityRun) \
            .options(
            joinedload(QualityRun.profiles),
            joinedload(QualityRun.validations),
            joinedload(QualityRun.metrics)
        ) \
            .get(run_id)

    def list_quality_runs(
            self,
            filters: Dict[str, Any],
            page: int = 1,
            page_size: int = 50
    ) -> Tuple[List[QualityRun], int]:
        """List quality runs with filtering and pagination"""
        try:
            query = self.db_session.query(QualityRun)

            # Apply filters
            if filters.get('pipeline_id'):
                query = query.filter(QualityRun.pipeline_id == filters['pipeline_id'])
            if filters.get('dataset_id'):
                query = query.filter(QualityRun.dataset_id == filters['dataset_id'])
            if filters.get('status'):
                query = query.filter(QualityRun.status == filters['status'])
            if filters.get('check_type'):
                query = query.filter(QualityRun.check_type == filters['check_type'])
            if filters.get('min_quality_score'):
                query = query.filter(QualityRun.quality_score >= filters['min_quality_score'])

            # Get total count
            total = query.count()

            # Apply pagination
            runs = query.order_by(desc(QualityRun.created_at)) \
                .offset((page - 1) * page_size) \
                .limit(page_size) \
                .all()

            return runs, total

        except Exception as e:
            raise

    def get_profile_by_target(
            self,
            run_id: UUID,
            target_name: str
    ) -> Optional[DataProfile]:
        """Get data profile for specific target"""
        return self.db_session.query(DataProfile) \
            .filter(
            DataProfile.quality_run_id == run_id,
            DataProfile.target_name == target_name
        ) \
            .first()

    def get_validations(
            self,
            run_id: UUID,
            status: Optional[str] = None
    ) -> List[QualityValidation]:
        """Get validations for a run"""
        query = self.db_session.query(QualityValidation) \
            .filter(QualityValidation.quality_run_id == run_id)

        if status:
            query = query.filter(QualityValidation.status == status)

        return query.order_by(desc(QualityValidation.impact_score)).all()

    def get_quality_summary(self, run_id: UUID) -> Dict[str, Any]:
        """Get quality summary metrics"""
        run = self.get_quality_run(run_id)
        if not run:
            return {}

        return {
            'total_checks': run.total_checks,
            'passed_checks': run.passed_checks,
            'failed_checks': run.failed_checks,
            'quality_score': run.quality_score,
            'status': run.status,
            'execution_time': run.execution_time,
            'started_at': run.started_at.isoformat() if run.started_at else None,
            'completed_at': run.completed_at.isoformat() if run.completed_at else None
        }

    def get_quality_metrics(self, run_id: UUID) -> List[QualityMetric]:
        """Get detailed quality metrics"""
        return self.db_session.query(QualityMetric) \
            .filter(QualityMetric.quality_run_id == run_id) \
            .order_by(QualityMetric.category, QualityMetric.name) \
            .all()