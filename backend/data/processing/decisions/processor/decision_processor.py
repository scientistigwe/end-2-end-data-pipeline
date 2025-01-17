# data_pipeline/decisions/processor/decision_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    DecisionContext,
    MessageMetadata
)
from core.staging.staging_manager import StagingManager

from ..types.decision_types import (
    DecisionSource,
    DecisionState,
    DecisionPhase,
    DecisionStatus,
    DecisionRequest,
    ComponentDecision,
    ComponentUpdate,
    DecisionValidation,
    DecisionImpact
)

logger = logging.getLogger(__name__)


class DecisionProcessor:
    """
    Processes and coordinates decisions across pipeline components.
    Handles decision validation, impact assessment, and state management.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.logger = logging.getLogger(__name__)

        # Active states
        self.active_states: Dict[str, DecisionState] = {}

    async def handle_component_request(
            self,
            pipeline_id: str,
            source: DecisionSource,
            request_data: Dict[str, Any],
            context: DecisionContext
    ) -> DecisionRequest:
        """Process decision request from component"""
        try:
            # Create decision request
            request = DecisionRequest(
                request_id=str(uuid.uuid4()),
                pipeline_id=pipeline_id,
                source=source,
                options=self._prepare_options(request_data.get('options', []), source),
                context=context.__dict__,
                priority=request_data.get('priority', 'medium'),
                requires_confirmation=request_data.get('requires_confirmation', True),
                metadata=request_data.get('metadata', {})
            )

            # Initialize or update state
            state = await self._get_or_create_state(pipeline_id)
            state.current_requests.append(request)
            state.status = DecisionStatus.AWAITING_INPUT
            state.phase = DecisionPhase.ANALYSIS
            self.active_states[pipeline_id] = state

            # Store in staging
            await self._store_request(pipeline_id, request)

            # Notify components about request
            await self._notify_components_of_request(request)

            return request

        except Exception as e:
            logger.error(f"Failed to handle component request: {str(e)}")
            raise

    async def process_decision(
            self,
            pipeline_id: str,
            decision: ComponentDecision
    ) -> Dict[str, Any]:
        """Process submitted decision"""
        try:
            state = self.active_states.get(pipeline_id)
            if not state:
                raise ValueError(f"No active state for pipeline: {pipeline_id}")

            # Validate decision
            validation = await self._validate_decision(decision, state)
            if not validation.passed:
                return {
                    'status': 'invalid',
                    'validation': validation.__dict__,
                    'errors': validation.issues
                }

            # Assess impact
            impact = await self._assess_decision_impact(decision, state)

            # Update state
            state.pending_decisions.append(decision)
            state.status = DecisionStatus.VALIDATING
            state.phase = DecisionPhase.VALIDATION

            # Store updated state
            await self._store_state(state)

            # Notify affected components
            await self._notify_affected_components(decision, impact)

            return {
                'status': 'valid',
                'decision': decision.__dict__,
                'validation': validation.__dict__,
                'impact': impact.__dict__
            }

        except Exception as e:
            logger.error(f"Failed to process decision: {str(e)}")
            raise

    async def handle_component_update(
            self,
            update: ComponentUpdate
    ) -> None:
        """Handle component update about decision impact"""
        try:
            state = self.active_states.get(update.pipeline_id)
            if not state:
                return

            # Find relevant decision
            decision = next(
                (d for d in state.pending_decisions
                 if d.decision_id == update.decision_id),
                None
            )

            if decision:
                # Update impact details
                decision.impacts[update.component] = update.impact_details

                # Check if all components updated
                if self._check_all_components_updated(decision, state):
                    # Move to completed
                    state.completed_decisions.append(decision)
                    state.pending_decisions.remove(decision)
                    state.status = DecisionStatus.COMPLETED

                # Store updated state
                await self._store_state(state)

                # If action required, notify
                if update.requires_action:
                    await self._notify_action_required(update)

        except Exception as e:
            logger.error(f"Failed to handle component update: {str(e)}")
            raise

    async def _validate_decision(
            self,
            decision: ComponentDecision,
            state: DecisionState
    ) -> DecisionValidation:
        """Validate decision against current state"""
        issues = []
        component_validations = {}

        # Validate request exists
        request = next(
            (r for r in state.current_requests
             if r.request_id == decision.request_id),
            None
        )
        if not request:
            issues.append("No matching request found")
            return DecisionValidation(
                decision_id=decision.decision_id,
                validation_type="request_validation",
                passed=False,
                issues=issues,
                component_validations={},
                metadata={'state': state.status.value}
            )

        # Validate option
        if not self._validate_option(decision.selected_option, request.options):
            issues.append("Invalid option selected")

        # Validate against each affected component
        for component, impact in decision.impacts.items():
            component_validations[component] = self._validate_component_impact(
                component,
                impact,
                request.context
            )

        return DecisionValidation(
            decision_id=decision.decision_id,
            validation_type="full_validation",
            passed=len(issues) == 0 and all(component_validations.values()),
            issues=issues,
            component_validations=component_validations,
            metadata={
                'state': state.status.value,
                'request_id': request.request_id
            }
        )

    async def _assess_decision_impact(
            self,
            decision: ComponentDecision,
            state: DecisionState
    ) -> DecisionImpact:
        """Assess impact of decision on components"""
        affected_components = {}
        cascading_effects = []
        requires_updates = []

        # Assess primary impacts
        for component, impact in decision.impacts.items():
            component_impact = await self._assess_component_impact(
                component,
                impact,
                decision
            )
            affected_components[component] = component_impact

            # Check for cascading effects
            if component_impact.get('cascading'):
                cascading_effects.extend(component_impact['cascading_effects'])
                requires_updates.append(component)

        return DecisionImpact(
            decision_id=decision.decision_id,
            affected_components=affected_components,
            cascading_effects=cascading_effects,
            requires_updates=requires_updates,
            metadata={
                'source': decision.source.value,
                'timestamp': datetime.now().isoformat()
            }
        )

    def _validate_option(
            self,
            selected_option: Dict[str, Any],
            available_options: List[Dict[str, Any]]
    ) -> bool:
        """Validate selected option against available options"""
        return any(
            opt['id'] == selected_option.get('id')
            for opt in available_options
        )

    def _validate_component_impact(
            self,
            component: str,
            impact: Dict[str, Any],
            context: Dict[str, Any]
    ) -> bool:
        """Validate impact on specific component"""
        # Implement component-specific validation
        return True

    async def _assess_component_impact(
            self,
            component: str,
            impact: Dict[str, Any],
            decision: ComponentDecision
    ) -> Dict[str, Any]:
        """Assess impact on specific component"""
        return {
            'level': impact.get('level', 'medium'),
            'type': impact.get('type', 'direct'),
            'requires_action': impact.get('requires_action', False),
            'cascading': impact.get('cascading', False),
            'cascading_effects': impact.get('cascading_effects', [])
        }

    async def _notify_components_of_request(
            self,
            request: DecisionRequest
    ) -> None:
        """Notify relevant components about decision request"""
        message = ProcessingMessage(
            message_type=MessageType.DECISION_REQUEST,
            content={
                'pipeline_id': request.pipeline_id,
                'request_id': request.request_id,
                'source': request.source.value,
                'options': request.options,
                'requires_confirmation': request.requires_confirmation
            },
            metadata=MessageMetadata(
                source_component="decision_processor",
                target_component="all",
                domain_type="decision"
            )
        )
        await self.message_broker.publish(message)

    async def _notify_affected_components(
            self,
            decision: ComponentDecision,
            impact: DecisionImpact
    ) -> None:
        """Notify affected components about decision"""
        for component in impact.affected_components:
            message = ProcessingMessage(
                message_type=MessageType.DECISION_IMPACT,
                content={
                    'pipeline_id': decision.pipeline_id,
                    'decision_id': decision.decision_id,
                    'impact': impact.affected_components[component],
                    'requires_update': component in impact.requires_updates
                },
                metadata=MessageMetadata(
                    source_component="decision_processor",
                    target_component=component,
                    domain_type="decision"
                )
            )
            await self.message_broker.publish(message)

    async def _notify_action_required(
            self,
            update: ComponentUpdate
    ) -> None:
        """Notify about required action"""
        message = ProcessingMessage(
            message_type=MessageType.DECISION_UPDATE,
            content={
                'pipeline_id': update.pipeline_id,
                'decision_id': update.decision_id,
                'component': update.component,
                'requires_action': True,
                'impact_details': update.impact_details
            },
            metadata=MessageMetadata(
                source_component="decision_processor",
                target_component="decision_manager",
                domain_type="decision"
            )
        )
        await self.message_broker.publish(message)

    async def _get_or_create_state(
            self,
            pipeline_id: str
    ) -> DecisionState:
        """Get existing state or create new one"""
        state = self.active_states.get(pipeline_id)
        if not state:
            state = DecisionState(
                pipeline_id=pipeline_id,
                current_requests=[],
                pending_decisions=[],
                completed_decisions=[],
                status=DecisionStatus.INITIALIZING,
                phase=DecisionPhase.INITIALIZATION
            )
        return state

    async def _store_state(self, state: DecisionState) -> None:
        """Store decision state"""
        await self.staging_manager.store_staged_data(
            state.pipeline_id,
            {
                'type': 'decision_state',
                'data': state.__dict__,
                'updated_at': datetime.now().isoformat()
            }
        )

    async def _store_request(
            self,
            pipeline_id: str,
            request: DecisionRequest
    ) -> None:
        """Store decision request"""
        await self.staging_manager.store_staged_data(
            pipeline_id,
            {
                'type': 'decision_request',
                'data': request.__dict__,
                'created_at': datetime.now().isoformat()
            }
        )

    def _check_all_components_updated(
            self,
            decision: ComponentDecision,
            state: DecisionState
    ) -> bool:
        """Check if all affected components have provided updates"""
        return all(
            component in decision.impacts
            for component in decision.impacts.keys()
        )