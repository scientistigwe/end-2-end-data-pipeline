# data/processing/decisions/modules/decision_coordinator.py

import logging
from typing import Dict, Any, List
from datetime import datetime

from ..types.decision_types import (
    DecisionType,
    DecisionStatus,
    DecisionContext
)

logger = logging.getLogger(__name__)

class DecisionCoordinator:
    """
    Coordinates decisions between different pipeline components.
    Handles inter-component communication and decision flow.
    """

    def __init__(self, message_broker):
        self.message_broker = message_broker
        self.logger = logging.getLogger(__name__)
        self.active_contexts: Dict[str, Dict[str, Any]] = {}

    async def handle_component_request(
        self,
        pipeline_id: str,
        component: str,
        request_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle decision request from a pipeline component"""
        try:
            # Store component context
            self.active_contexts[pipeline_id] = {
                'component': component,
                'request': request_data,
                'timestamp': datetime.now().isoformat()
            }

            # Format decision options
            options = self._format_decision_options(
                request_data.get('options', []),
                component
            )

            # Notify other relevant components
            await self._notify_components(
                pipeline_id,
                component,
                'decision_requested',
                request_data
            )

            return {
                'context': self.active_contexts[pipeline_id],
                'options': options
            }

        except Exception as e:
            logger.error(f"Failed to handle component request: {str(e)}")
            raise

    async def process_decision(
        self,
        pipeline_id: str,
        decision: Dict[str, Any]
    ) -> None:
        """Process decision and coordinate with components"""
        try:
            context = self.active_contexts.get(pipeline_id)
            if not context:
                raise ValueError(f"No active context for pipeline: {pipeline_id}")

            # Notify requesting component
            await self._notify_component(
                context['component'],
                pipeline_id,
                'decision_made',
                decision
            )

            # Notify affected components
            affected_components = self._get_affected_components(
                context['component'],
                decision
            )

            for component in affected_components:
                await self._notify_component(
                    component,
                    pipeline_id,
                    'decision_impact',
                    {
                        'origin_component': context['component'],
                        'decision': decision
                    }
                )

        except Exception as e:
            logger.error(f"Failed to process decision: {str(e)}")
            raise

    def _format_decision_options(
        self,
        options: List[Dict[str, Any]],
        component: str
    ) -> List[Dict[str, Any]]:
        """Format component-specific options for user presentation"""
        formatted_options = []
        for option in options:
            formatted_options.append({
                'id': option.get('id'),
                'component': component,
                'title': option.get('title'),
                'description': option.get('description'),
                'impact': self._assess_cross_component_impact(option, component),
                'requires_confirmation': option.get('requires_confirmation', False)
            })
        return formatted_options

    def _assess_cross_component_impact(
        self,
        option: Dict[str, Any],
        source_component: str
    ) -> Dict[str, Any]:
        """Assess impact of decision across components"""
        impact = {
            'source': source_component,
            'components': {}
        }

        # Assess impact on quality
        if source_component != 'quality' and option.get('affects_quality'):
            impact['components']['quality'] = {
                'level': 'high',
                'type': 'direct'
            }

        # Assess impact on insights
        if source_component != 'insights' and option.get('affects_insights'):
            impact['components']['insights'] = {
                'level': 'medium',
                'type': 'indirect'
            }

        return impact

    async def _notify_component(
        self,
        component: str,
        pipeline_id: str,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Notify specific component about decision event"""
        message = {
            'pipeline_id': pipeline_id,
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }

        await self.message_broker.publish(
            f"{component}.decision.{event_type}",
            message
        )

    def _get_affected_components(
        self,
        source_component: str,
        decision: Dict[str, Any]
    ) -> List[str]:
        """Determine which components are affected by a decision"""
        affected = set()

        # Add components based on decision impact
        if decision.get('affects_quality'):
            affected.add('quality')
        if decision.get('affects_insights'):
            affected.add('insights')
        if decision.get('affects_analytics'):
            affected.add('advanced_analytics')

        # Remove source component
        affected.discard(source_component)

        return list(affected)