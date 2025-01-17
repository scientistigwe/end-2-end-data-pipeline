# data/processing/decisions/modules/decision_validator.py

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..types.decision_types import DecisionValidation

logger = logging.getLogger(__name__)


class DecisionValidator:
    """
    Validates decisions across components.
    Ensures decisions maintain system consistency.
    """

    def validate_decision(
            self,
            decision: Dict[str, Any],
            context: Dict[str, Any]
    ) -> DecisionValidation:
        """Validate decision against context and dependencies"""
        try:
            validation_results = []

            # Validate format and completeness
            format_result = self._validate_format(decision)
            validation_results.append(format_result)

            # Validate against component context
            context_result = self._validate_context(decision, context)
            validation_results.append(context_result)

            # Validate cross-component dependencies
            dependency_result = self._validate_dependencies(decision, context)
            validation_results.append(dependency_result)

            # Overall validation status
            is_valid = all(result['valid'] for result in validation_results)

            return DecisionValidation(
                decision_id=decision.get('id'),
                validation_type='cross_component',
                passed=is_valid,
                score=self._calculate_validation_score(validation_results),
                issues=[issue for r in validation_results for issue in r.get('issues', [])],
                metadata={'validation_results': validation_results}
            )

        except Exception as e:
            logger.error(f"Decision validation failed: {str(e)}")
            raise

    def _validate_format(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Validate decision format and required fields"""
        issues = []

        # Required fields
        required_fields = ['id', 'type', 'action', 'component']
        for field in required_fields:
            if field not in decision:
                issues.append(f"Missing required field: {field}")

        # Field format validation
        if 'impact' in decision and not isinstance(decision['impact'], dict):
            issues.append("Impact must be a dictionary")

        return {
            'valid': len(issues) == 0,
            'type': 'format',
            'issues': issues
        }

    def _validate_context(
            self,
            decision: Dict[str, Any],
            context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate decision against component context"""
        issues = []

        # Validate component match
        if decision.get('component') != context.get('source_component'):
            issues.append("Decision component doesn't match context")

        # Validate decision type
        if context.get('allowed_types'):
            if decision.get('type') not in context['allowed_types']:
                issues.append(f"Invalid decision type for context")

        # Validate against context constraints
        if context.get('constraints'):
            for constraint in context['constraints']:
                if not self._check_constraint(decision, constraint):
                    issues.append(f"Failed constraint: {constraint['name']}")

        return {
            'valid': len(issues) == 0,
            'type': 'context',
            'issues': issues
        }

    def _validate_dependencies(
            self,
            decision: Dict[str, Any],
            context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate cross-component dependencies"""
        issues = []

        # Check component dependencies
        if decision.get('affects_quality') and not self._check_quality_dependency(decision):
            issues.append("Invalid quality impact")

        if decision.get('affects_insights') and not self._check_insight_dependency(decision):
            issues.append("Invalid insight impact")

        return {
            'valid': len(issues) == 0,
            'type': 'dependencies',
            'issues': issues
        }

    def _calculate_validation_score(
            self,
            results: List[Dict[str, Any]]
    ) -> float:
        """Calculate overall validation score"""
        weights = {
            'format': 0.3,
            'context': 0.4,
            'dependencies': 0.3
        }

        score = 0.0
        for result in results:
            if result['valid']:
                score += weights.get(result['type'], 0)

        return score