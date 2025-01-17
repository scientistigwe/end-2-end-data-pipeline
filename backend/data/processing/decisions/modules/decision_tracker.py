# data/processing/decisions/modules/decision_tracker.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


class DecisionTracker:
    """
    Tracks decision states and progress across the pipeline.
    Maintains decision history and relationships.
    """

    def __init__(self):
        self.active_decisions: Dict[str, Dict[str, Any]] = {}
        self.decision_history: Dict[str, List[Dict[str, Any]]] = {}
        self.logger = logging.getLogger(__name__)

    def track_request(
            self,
            pipeline_id: str,
            context: Dict[str, Any]
    ) -> None:
        """Track new decision request"""
        if pipeline_id not in self.decision_history:
            self.decision_history[pipeline_id] = []

        self.active_decisions[pipeline_id] = {
            'context': context,
            'status': 'pending',
            'requested_at': datetime.now().isoformat(),
            'updates': []
        }

    def track_decision(
            self,
            pipeline_id: str,
            decision: Dict[str, Any]
    ) -> None:
        """Track made decision"""
        if pipeline_id in self.active_decisions:
            active = self.active_decisions[pipeline_id]
            active['decision'] = decision
            active['decided_at'] = datetime.now().isoformat()
            active['status'] = 'decided'

    def track_validation(
            self,
            pipeline_id: str,
            validation_result: Dict[str, Any]
    ) -> None:
        """Track decision validation"""
        if pipeline_id in self.active_decisions:
            active = self.active_decisions[pipeline_id]
            active['validation'] = validation_result
            active['validated_at'] = datetime.now().isoformat()
            active['status'] = 'validated'

    def track_completion(
            self,
            pipeline_id: str,
            result: Dict[str, Any]
    ) -> None:
        """Track decision completion"""
        if pipeline_id in self.active_decisions:
            active = self.active_decisions[pipeline_id]
            active['result'] = result
            active['completed_at'] = datetime.now().isoformat()
            active['status'] = 'completed'

            # Move to history
            self.decision_history[pipeline_id].append(active)
            del self.active_decisions[pipeline_id]

    def get_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get current decision status"""
        active = self.active_decisions.get(pipeline_id)
        if active:
            return {
                'pipeline_id': pipeline_id,
                'status': active['status'],
                'timeline': {
                    'requested_at': active.get('requested_at'),
                    'decided_at': active.get('decided_at'),
                    'validated_at': active.get('validated_at'),
                    'completed_at': active.get('completed_at')
                },
                'context': active.get('context'),
                'decision': active.get('decision'),
                'validation': active.get('validation'),
                'result': active.get('result')
            }
        return None

    def get_history(
            self,
            pipeline_id: str
    ) -> List[Dict[str, Any]]:
        """Get decision history for pipeline"""
        return self.decision_history.get(pipeline_id, [])