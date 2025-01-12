# app/services/recommendations/decision_service.py
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from uuid import UUID
from sqlalchemy.orm import Session
from .....database.models.decision import (
    Decision,
    DecisionOption,
    DecisionComment,
    DecisionHistory
)
from .....database.models.pipeline import Pipeline

class DecisionService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.logger = logging.getLogger(__name__)

    def list_decisions(self, filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List all decisions with optional filtering."""
        try:
            query = self.db_session.query(Decision)
            
            if filters.get('status'):
                query = query.filter(Decision.status == filters['status'])
            if filters.get('priority'):
                query = query.filter(Decision.priority == filters['priority'])
            if filters.get('type'):
                query = query.filter(Decision.type == filters['type'])
            
            decisions = query.all()
            return [self._format_decision(decision) for decision in decisions]
        except Exception as e:
            self.logger.error(f"Error listing decisions: {str(e)}")
            raise

    def get_pending_decisions(self, pipeline_id: UUID) -> List[Dict[str, Any]]:
        """Get pending decisions for a pipeline."""
        try:
            decisions = self.db_session.query(Decision).filter(
                Decision.pipeline_id == pipeline_id,
                Decision.status == 'pending'
            ).order_by(
                Decision.priority.desc(),
                Decision.created_at.desc()
            ).all()
            
            return [self._format_decision(decision) for decision in decisions]
        except Exception as e:
            self.logger.error(f"Error getting pending decisions: {str(e)}")
            raise

    def make_decision(self, decision_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Make a decision."""
        try:
            decision = self.db_session.query(Decision).get(decision_id)
            if not decision:
                raise ValueError("Decision not found")
            
            if decision.status != 'pending':
                raise ValueError("Decision has already been made")
            
            # Update decision
            decision.status = data['status']  # approved/rejected
            decision.made_by = data['user_id']
            
            # Create history entry
            history = DecisionHistory(
                decision_id=decision_id,
                action='decision_made',
                previous_status='pending',
                new_status=data['status'],
                user_id=data['user_id'],
                metadata={
                    'reason': data.get('reason'),
                    'comments': data.get('comments')
                }
            )
            
            # Add comment if provided
            if data.get('comment'):
                comment = DecisionComment(
                    decision_id=decision_id,
                    user_id=data['user_id'],
                    content=data['comment']
                )
                self.db_session.add(comment)
            
            self.db_session.add(history)
            self.db_session.commit()
            
            return self._format_decision(decision)
        except Exception as e:
            self.logger.error(f"Error making decision: {str(e)}")
            self.db_session.rollback()
            raise

    def process_feedback(self, decision_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process feedback for a decision."""
        try:
            decision = self.db_session.query(Decision).get(decision_id)
            if not decision:
                raise ValueError("Decision not found")
            
            # Create feedback entry
            comment = DecisionComment(
                decision_id=decision_id,
                user_id=data['user_id'],
                content=data['feedback'],
                parent_id=data.get('parent_id')
            )
            
            self.db_session.add(comment)
            self.db_session.commit()
            
            return self._format_decision(decision)
        except Exception as e:
            self.logger.error(f"Error processing feedback: {str(e)}")
            self.db_session.rollback()
            raise

    def get_decision_history(self, pipeline_id: UUID, filters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Get decision history for a pipeline."""
        try:
            query = self.db_session.query(Decision).filter(
                Decision.pipeline_id == pipeline_id
            )
            
            if filters:
                if filters.get('status'):
                    query = query.filter(Decision.status == filters['status'])
                if filters.get('type'):
                    query = query.filter(Decision.type == filters['type'])
                    
            decisions = query.order_by(Decision.created_at.desc()).all()
            return [self._format_decision(decision) for decision in decisions]
        except Exception as e:
            self.logger.error(f"Error getting decision history: {str(e)}")
            raise

    def get_decision_impact(self, decision_id: UUID) -> Dict[str, Any]:
        """Get impact analysis for a decision."""
        try:
            decision = self.db_session.query(Decision).get(decision_id)
            if not decision:
                raise ValueError("Decision not found")
            
            return {
                'id': str(decision.id),
                'impact_analysis': decision.impact_analysis,
                'metrics': {
                    'quality_impact': self._calculate_quality_impact(decision),
                    'performance_impact': self._calculate_performance_impact(decision),
                    'cost_impact': self._calculate_cost_impact(decision)
                }
            }
        except Exception as e:
            self.logger.error(f"Error getting decision impact: {str(e)}")
            raise

    def _format_decision(self, decision: Decision) -> Dict[str, Any]:
        """Format decision for API response."""
        return {
            'id': str(decision.id),
            'pipeline_id': str(decision.pipeline_id),
            'type': decision.type,
            'status': decision.status,
            'priority': decision.priority,
            'deadline': decision.deadline.isoformat() if decision.deadline else None,
            'metadata': decision.metadata,
            'context': decision.context,
            'impact_analysis': decision.impact_analysis,
            'made_by': str(decision.made_by) if decision.made_by else None,
            'options': [
                {
                    'id': str(option.id),
                    'name': option.name,
                    'description': option.description,
                    'impact_score': option.impact_score,
                    'risks': option.risks,
                    'benefits': option.benefits,
                    'is_selected': option.is_selected
                }
                for option in decision.options
            ],
            'comments': [
                {
                    'id': str(comment.id),
                    'user_id': str(comment.user_id),
                    'content': comment.content,
                    'created_at': comment.created_at.isoformat()
                }
                for comment in decision.comments
            ],
            'created_at': decision.created_at.isoformat(),
            'updated_at': decision.updated_at.isoformat()
        }

    def _calculate_quality_impact(self, decision: Decision) -> float:
        """Calculate quality impact of a decision."""
        pass

    def _calculate_performance_impact(self, decision: Decision) -> float:
        """Calculate performance impact of a decision."""
        pass

    def _calculate_cost_impact(self, decision: Decision) -> Dict[str, float]:
        """Calculate cost impact of a decision."""
        pass