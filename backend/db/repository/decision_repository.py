# backend/db/repository/decision_repository.py

from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from uuid import UUID
from sqlalchemy import and_, or_, desc, func

# Import corresponding SQLAlchemy types
from backend.db.models.decision import (
    Decision,
    DecisionOption,
    DecisionComment,
    DecisionHistory,
    Recommendation
)
from backend.db.models.recommendation import Recommendation

class DecisionRepository:
    """
    Repository for decision-related db operations

    Manages db interactions for decisions,
    decision options, comments, and history
    """

    def __init__(self, db_session: Session):
        """
        Initialize repository with db session

        Args:
            db_session: SQLAlchemy db session
        """
        self.db_session = db_session

    def create_decision(self, data: Dict[str, Any]) -> Decision:
        """
        Create a new decision

        Args:
            data: Decision configuration data

        Returns:
            Created Decision instance
        """
        try:
            decision = Decision(
                pipeline_id=data['pipeline_id'],
                type=data.get('type'),
                status=data.get('status', 'pending'),
                priority=data.get('priority', 'medium'),
                deadline=data.get('deadline'),
                meta_info=data.get('meta_info', {}),
                context=data.get('context', {}),
                impact_analysis=data.get('impact_analysis', {}),
                risk_assessment=data.get('risk_assessment', {}),
                implementation_plan=data.get('implementation_plan', {}),
                confidence_score=data.get('confidence_score'),
                impact_score=data.get('impact_score'),
                risk_score=data.get('risk_score'),
                made_by=data.get('made_by'),
                recommendation_id=data.get('recommendation_id')
            )
            self.db_session.add(decision)
            self.db_session.commit()
            return decision

        except Exception as e:
            self.db_session.rollback()
            raise

    def update_decision(
            self,
            decision_id: UUID,
            data: Dict[str, Any]
    ) -> Decision:
        """
        Update an existing decision

        Args:
            decision_id: Unique identifier for the decision
            data: Update data

        Returns:
            Updated Decision instance
        """
        try:
            decision = self.db_session.query(Decision).get(decision_id)
            if not decision:
                raise ValueError(f"No decision found with ID {decision_id}")

            # Update decision attributes
            for key, value in data.items():
                if hasattr(decision, key):
                    setattr(decision, key, value)

            # Update decision status and timestamps
            if 'status' in data:
                decision.decision_made_at = datetime.utcnow()

            self.db_session.commit()
            return decision

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_decision_option(
            self,
            decision_id: UUID,
            option_data: Dict[str, Any]
    ) -> DecisionOption:
        """
        Create a decision option associated with a decision

        Args:
            decision_id: ID of the related decision
            option_data: Decision option configuration data

        Returns:
            Created DecisionOption instance
        """
        try:
            option = DecisionOption(
                decision_id=decision_id,
                name=option_data['name'],
                description=option_data.get('description'),
                impact_score=option_data.get('impact_score'),
                feasibility_score=option_data.get('feasibility_score'),
                risks=option_data.get('risks', {}),
                benefits=option_data.get('benefits', {}),
                costs=option_data.get('costs', {}),
                dependencies=option_data.get('dependencies', {}),
                is_selected=option_data.get('is_selected', False),
                implementation_complexity=option_data.get('implementation_complexity'),
                estimated_duration=option_data.get('estimated_duration')
            )
            self.db_session.add(option)
            self.db_session.commit()
            return option

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_decision_comment(
            self,
            decision_id: UUID,
            comment_data: Dict[str, Any]
    ) -> DecisionComment:
        """
        Create a comment for a decision

        Args:
            decision_id: ID of the related decision
            comment_data: Comment configuration data

        Returns:
            Created DecisionComment instance
        """
        try:
            comment = DecisionComment(
                decision_id=decision_id,
                user_id=comment_data['user_id'],
                content=comment_data['content'],
                parent_id=comment_data.get('parent_id'),
                comment_type=comment_data.get('comment_type'),
                attachments=comment_data.get('attachments', {}),
                is_internal=comment_data.get('is_internal', False)
            )
            self.db_session.add(comment)
            self.db_session.commit()
            return comment

        except Exception as e:
            self.db_session.rollback()
            raise

    def create_decision_history(
            self,
            decision_id: UUID,
            history_data: Dict[str, Any]
    ) -> DecisionHistory:
        """
        Create a history entry for a decision

        Args:
            decision_id: ID of the related decision
            history_data: History entry configuration data

        Returns:
            Created DecisionHistory instance
        """
        try:
            history = DecisionHistory(
                decision_id=decision_id,
                action=history_data['action'],
                previous_status=history_data.get('previous_status'),
                new_status=history_data.get('new_status'),
                user_id=history_data.get('user_id'),
                event_meta=history_data.get('event_meta', {}),
                change_reason=history_data.get('change_reason'),
                system_generated=history_data.get('system_generated', False)
            )
            self.db_session.add(history)
            self.db_session.commit()
            return history

        except Exception as e:
            self.db_session.rollback()
            raise

    def get_decision(self, decision_id: UUID) -> Optional[Decision]:
        """
        Retrieve a decision by ID with related data

        Args:
            decision_id: Unique identifier for the decision

        Returns:
            Decision instance with related options, comments, and history
        """
        return self.db_session.query(Decision) \
            .options(
            joinedload(Decision.options),
            joinedload(Decision.comments),
            joinedload(Decision.history)
        ) \
            .get(decision_id)

    def list_decisions(
            self,
            filters: Dict[str, Any],
            page: int = 1,
            page_size: int = 50
    ) -> Tuple[List[Decision], int]:
        """
        List decisions with filtering and pagination

        Args:
            filters: Dictionary of filter conditions
            page: Page number for pagination
            page_size: Number of items per page

        Returns:
            Tuple of (list of Decisions, total count)
        """
        try:
            query = self.db_session.query(Decision)

            # Apply filters
            if filters.get('pipeline_id'):
                query = query.filter(Decision.pipeline_id == filters['pipeline_id'])
            if filters.get('type'):
                query = query.filter(Decision.type == filters['type'])
            if filters.get('status'):
                query = query.filter(Decision.status == filters['status'])
            if filters.get('priority'):
                query = query.filter(Decision.priority == filters['priority'])

            # Get total count
            total = query.count()

            # Apply pagination
            decisions = query.order_by(desc(Decision.created_at)) \
                .offset((page - 1) * page_size) \
                .limit(page_size) \
                .all()

            return decisions, total

        except Exception as e:
            raise

    def get_decision_options(self, decision_id: UUID) -> List[DecisionOption]:
        """
        Retrieve decision options for a specific decision

        Args:
            decision_id: Unique identifier for the decision

        Returns:
            List of DecisionOption instances
        """
        return self.db_session.query(DecisionOption) \
            .filter(DecisionOption.decision_id == decision_id) \
            .order_by(desc(DecisionOption.impact_score)) \
            .all()

    def get_decision_comments(self, decision_id: UUID) -> List[DecisionComment]:
        """
        Retrieve comments for a specific decision

        Args:
            decision_id: Unique identifier for the decision

        Returns:
            List of DecisionComment instances
        """
        return self.db_session.query(DecisionComment) \
            .filter(DecisionComment.decision_id == decision_id) \
            .order_by(DecisionComment.created_at) \
            .all()

    def resolve_decision(
            self,
            decision_id: UUID,
            resolution_data: Dict[str, Any]
    ) -> Decision:
        """
        Resolve a specific decision

        Args:
            decision_id: Unique identifier for the decision
            resolution_data: Resolution details

        Returns:
            Updated Decision instance
        """
        try:
            decision = self.db_session.query(Decision).get(decision_id)
            if not decision:
                raise ValueError(f"No decision found with ID {decision_id}")

            # Update decision resolution details
            decision.status = resolution_data.get('status', 'resolved')
            decision.decision_made_at = datetime.utcnow()
            decision.implementation_date = resolution_data.get('implementation_date')

            # Create decision history entry
            history_entry = DecisionHistory(
                decision_id=decision_id,
                action='resolve',
                previous_status=decision.status,
                new_status=resolution_data.get('status', 'resolved'),
                user_id=resolution_data.get('user_id'),
                change_reason=resolution_data.get('reason')
            )
            self.db_session.add(history_entry)

            self.db_session.commit()
            return decision

        except Exception as e:
            self.db_session.rollback()
            raise

    def get_significant_recommendations(
            self,
            min_confidence: float = 0.7,
            min_impact: float = 0.6
    ) -> List[Recommendation]:
        """
        Retrieve significant recommendations

        Args:
            min_confidence: Minimum confidence threshold
            min_impact: Minimum impact threshold

        Returns:
            List of significant Recommendation instances
        """
        return self.db_session.query(Recommendation) \
            .filter(
            Recommendation.confidence >= min_confidence,
            Recommendation.impact >= min_impact
        ) \
            .order_by(
            desc(Recommendation.confidence),
            desc(Recommendation.impact)
        ) \
            .all()