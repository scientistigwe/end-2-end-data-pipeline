# backend/db/repository/recommendation_repository.py

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.orm import Session, joinedload

# Import corresponding SQLAlchemy types
from backend.db.models.recommendation import (
    Recommendation,
    RecommendationFeedback
)


class RecommendationRepository:
    """
    Repository for recommendation-related db operations

    Manages db interactions for recommendations
    and recommendation feedback
    """

    def __init__(self, db_session: Session):
        """
        Initialize repository with db session

        Args:
            db_session: SQLAlchemy db session
        """
        self.db_session = db_session

    def create_recommendation(self, data: Dict[str, Any]) -> Recommendation:
        """
        Create a new recommendation

        Args:
            data: Recommendation configuration data

        Returns:
            Created Recommendation instance
        """
        try:
            recommendation = Recommendation(
                pipeline_id=data['pipeline_id'],
                type=data.get('type'),
                status=data.get('status', 'pending'),
                priority=data.get('priority', 0),
                confidence=data.get('confidence'),
                impact=data.get('impact'),
                description=data['description'],
                rationale=data.get('rationale'),
                action_details=data.get('action_details', {}),
                recommendation_meta=data.get('recommendation_meta', {}),
                category=data.get('category'),
                cost_estimate=data.get('cost_estimate'),
                benefit_estimate=data.get('benefit_estimate'),
                implementation_complexity=data.get('implementation_complexity'),
                dependencies=data.get('dependencies', {}),
                required_resources=data.get('required_resources', {}),
                validation_rules=data.get('validation_rules', {})
            )
            self.db_session.add(recommendation)
            self.db_session.commit()
            return recommendation

        except Exception as e:
            self.db_session.rollback()
            raise

    def update_recommendation(
            self,
            recommendation_id: UUID,
            data: Dict[str, Any]
    ) -> Recommendation:
        """
        Update an existing recommendation

        Args:
            recommendation_id: Unique identifier for the recommendation
            data: Update data

        Returns:
            Updated Recommendation instance
        """
        try:
            recommendation = self.db_session.query(Recommendation).get(recommendation_id)
            if not recommendation:
                raise ValueError(f"No recommendation found with ID {recommendation_id}")

            # Update recommendation attributes
            for key, value in data.items():
                if hasattr(recommendation, key):
                    setattr(recommendation, key, value)

            # Update status-related timestamps
            if data.get('status') == 'applied':
                recommendation.applied_at = datetime.utcnow()
            elif data.get('status') == 'dismissed':
                recommendation.dismissed_at = datetime.utcnow()

            self.db_session.commit()
            return recommendation

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_recommendation_feedback(
            self,
            recommendation_id: UUID,
            feedback_data: Dict[str, Any]
    ) -> RecommendationFeedback:
        """
        Create feedback for a recommendation

        Args:
            recommendation_id: ID of the related recommendation
            feedback_data: Feedback configuration data

        Returns:
            Created RecommendationFeedback instance
        """
        try:
            feedback = RecommendationFeedback(
                recommendation_id=recommendation_id,
                user_id=feedback_data['user_id'],
                rating=feedback_data.get('rating'),
                comment=feedback_data.get('comment'),
                feedback_meta=feedback_data.get('feedback_meta', {}),
                sentiment=feedback_data.get('sentiment'),
                impact_assessment=feedback_data.get('impact_assessment'),
                implementation_feedback=feedback_data.get('implementation_feedback'),
                suggestions=feedback_data.get('suggestions', {}),
                is_anonymous=feedback_data.get('is_anonymous', False)
            )
            self.db_session.add(feedback)
            self.db_session.commit()
            return feedback

        except Exception as e:
            self.db_session.rollback()
            raise

    def get_recommendation(self, recommendation_id: UUID) -> Optional[Recommendation]:
        """
        Retrieve a recommendation by ID with related data

        Args:
            recommendation_id: Unique identifier for the recommendation

        Returns:
            Recommendation instance with related feedback
        """
        return self.db_session.query(Recommendation) \
            .options(joinedload(Recommendation.feedback)) \
            .get(recommendation_id)

    def list_recommendations(
            self,
            filters: Dict[str, Any],
            page: int = 1,
            page_size: int = 50
    ) -> Tuple[List[Recommendation], int]:
        """
        List recommendations with filtering and pagination

        Args:
            filters: Dictionary of filter conditions
            page: Page number for pagination
            page_size: Number of items per page

        Returns:
            Tuple of (list of Recommendations, total count)
        """
        try:
            query = self.db_session.query(Recommendation)

            # Apply filters
            if filters.get('pipeline_id'):
                query = query.filter(Recommendation.pipeline_id == filters['pipeline_id'])
            if filters.get('type'):
                query = query.filter(Recommendation.type == filters['type'])
            if filters.get('status'):
                query = query.filter(Recommendation.status == filters['status'])
            if filters.get('category'):
                query = query.filter(Recommendation.category == filters['category'])

            # Get total count
            total = query.count()

            # Apply pagination
            recommendations = query.order_by(
                desc(Recommendation.priority),
                desc(Recommendation.confidence)
            ) \
                .offset((page - 1) * page_size) \
                .limit(page_size) \
                .all()

            return recommendations, total

        except Exception as e:
            raise

    def get_recommendation_feedback(
            self,
            recommendation_id: UUID
    ) -> List[RecommendationFeedback]:
        """
        Retrieve feedback for a specific recommendation

        Args:
            recommendation_id: Unique identifier for the recommendation

        Returns:
            List of RecommendationFeedback instances
        """
        return self.db_session.query(RecommendationFeedback) \
            .filter(RecommendationFeedback.recommendation_id == recommendation_id) \
            .order_by(RecommendationFeedback.created_at) \
            .all()

    def get_significant_recommendations(
            self,
            min_confidence: float = 0.7,
            min_impact: float = 0.6,
            status: Optional[str] = 'pending'
    ) -> List[Recommendation]:
        """
        Retrieve significant recommendations

        Args:
            min_confidence: Minimum confidence threshold
            min_impact: Minimum impact threshold
            status: Optional status filter

        Returns:
            List of significant Recommendation instances
        """
        query = self.db_session.query(Recommendation) \
            .filter(
            Recommendation.confidence >= min_confidence,
            Recommendation.impact >= min_impact
        )

        if status:
            query = query.filter(Recommendation.status == status)

        return query.order_by(
            desc(Recommendation.confidence),
            desc(Recommendation.impact)
        ) \
            .all()

    def apply_recommendation(
            self,
            recommendation_id: UUID,
            application_data: Dict[str, Any]
    ) -> Recommendation:
        """
        Apply a recommendation

        Args:
            recommendation_id: Unique identifier for the recommendation
            application_data: Details of recommendation application

        Returns:
            Updated Recommendation instance
        """
        try:
            recommendation = self.db_session.query(Recommendation).get(recommendation_id)
            if not recommendation:
                raise ValueError(f"No recommendation found with ID {recommendation_id}")

            # Update recommendation status and application details
            recommendation.status = 'applied'
            recommendation.applied_at = datetime.utcnow()
            recommendation.applied_by = application_data.get('applied_by')

            # Add any additional application metadata
            recommendation.action_details.update(
                application_data.get('action_details', {})
            )

            self.db_session.commit()
            return recommendation

        except Exception as e:
            self.db_session.rollback()
            raise

    def dismiss_recommendation(
            self,
            recommendation_id: UUID,
            dismissal_data: Dict[str, Any]
    ) -> Recommendation:
        """
        Dismiss a recommendation

        Args:
            recommendation_id: Unique identifier for the recommendation
            dismissal_data: Details of recommendation dismissal

        Returns:
            Updated Recommendation instance
        """
        try:
            recommendation = self.db_session.query(Recommendation).get(recommendation_id)
            if not recommendation:
                raise ValueError(f"No recommendation found with ID {recommendation_id}")

            # Update recommendation status and dismissal details
            recommendation.status = 'dismissed'
            recommendation.dismissed_at = datetime.utcnow()
            recommendation.dismissed_by = dismissal_data.get('dismissed_by')
            recommendation.dismiss_reason = dismissal_data.get('reason')

            self.db_session.commit()
            return recommendation

        except Exception as e:
            self.db_session.rollback()
            raise