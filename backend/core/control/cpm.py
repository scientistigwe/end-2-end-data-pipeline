# backend/core/control/cpm.py

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from dataclasses import dataclass, field

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    MessageMetadata
)
from ..registry.component_registry import ComponentRegistry, ComponentType

logger = logging.getLogger(__name__)


@dataclass
class ControlPoint:
    """Represents a control point in the processing flow"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    stage: ProcessingStage
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    next_stages: List[ProcessingStage] = field(default_factory=list)
    requires_decision: bool = True


class ControlPointManager:
    """Core Control Point Manager implementation"""

    def __init__(self, message_broker: MessageBroker):
        # Core components
        self.message_broker = message_broker
        self.component_registry = ComponentRegistry()

        # State management
        self.active_control_points: Dict[str, ControlPoint] = {}
        self.control_point_history: Dict[str, List[ControlPoint]] = {}

        # Flow tracking
        self.stage_transitions: Dict[ProcessingStage, List[ProcessingStage]] = {
            ProcessingStage.RECEPTION: [ProcessingStage.VALIDATION],
            ProcessingStage.VALIDATION: [ProcessingStage.QUALITY_CHECK],
            ProcessingStage.QUALITY_CHECK: [ProcessingStage.CONTEXT_ANALYSIS],
            ProcessingStage.CONTEXT_ANALYSIS: [ProcessingStage.INSIGHT_GENERATION],
            ProcessingStage.INSIGHT_GENERATION: [ProcessingStage.USER_REVIEW],
            ProcessingStage.USER_REVIEW: [ProcessingStage.COMPLETION]
        }

        # Component identification
        self.component_id = str(uuid.uuid4())

        # Initialize
        self._initialize()

    def _initialize(self):
        """Initialize CPM and register with system"""
        try:
            # Register with component registry
            self.component_registry.register_component(
                "control_point_manager",
                ComponentType.MANAGER,
                capabilities=["flow_control", "decision_management"]
            )

            # Subscribe to relevant message types
            self._setup_message_handlers()

            logger.info("Control Point Manager initialized successfully")

        except Exception as e:
            logger.error(f"CPM initialization failed: {str(e)}")
            raise

    async def create_control_point(
            self,
            stage: ProcessingStage,
            metadata: Dict[str, Any],
            requires_decision: bool = True
    ) -> str:
        """Create a new control point"""
        try:
            # Create control point
            control_point = ControlPoint(
                stage=stage,
                metadata=metadata,
                requires_decision=requires_decision,
                next_stages=self.stage_transitions.get(stage, [])
            )

            # Store control point
            self.active_control_points[control_point.id] = control_point

            # Notify about new control point
            await self._notify_control_point_created(control_point)

            return control_point.id

        except Exception as e:
            logger.error(f"Control point creation failed: {str(e)}")
            raise

    async def process_decision(
            self,
            control_point_id: str,
            decision: Dict[str, Any]
    ) -> bool:
        """Process a decision for a control point"""
        try:
            if control_point_id not in self.active_control_points:
                logger.warning(f"Control point not found: {control_point_id}")
                return False

            control_point = self.active_control_points[control_point_id]

            # Record decision
            control_point.decisions.append(decision)
            control_point.updated_at = datetime.now()

            # Determine next action
            next_action = self._determine_next_action(control_point, decision)

            # Execute next action
            await self._execute_action(control_point, next_action)

            return True

        except Exception as e:
            logger.error(f"Decision processing failed: {str(e)}")
            return False

    def _determine_next_action(
            self,
            control_point: ControlPoint,
            decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Determine next action based on decision"""
        action = {
            'type': 'proceed',
            'target_stage': None,
            'metadata': {}
        }

        # Get next stages
        next_stages = self.stage_transitions.get(control_point.stage, [])

        if decision.get('action') == 'proceed' and next_stages:
            action['target_stage'] = next_stages[0]
        elif decision.get('action') == 'retry':
            action['type'] = 'retry'
            action['target_stage'] = control_point.stage
        elif decision.get('action') == 'reject':
            action['type'] = 'reject'

        return action

    async def _execute_action(
            self,
            control_point: ControlPoint,
            action: Dict[str, Any]
    ) -> None:
        """Execute determined action"""
        try:
            if action['type'] == 'proceed':
                # Move to next stage
                await self._proceed_to_stage(
                    control_point,
                    action['target_stage'],
                    action.get('metadata', {})
                )
            elif action['type'] == 'retry':
                # Retry current stage
                await self._retry_stage(
                    control_point,
                    action.get('metadata', {})
                )
            elif action['type'] == 'reject':
                # Handle rejection
                await self._handle_rejection(
                    control_point,
                    action.get('metadata', {})
                )

        except Exception as e:
            logger.error(f"Action execution failed: {str(e)}")
            raise

    async def _proceed_to_stage(
            self,
            control_point: ControlPoint,
            target_stage: ProcessingStage,
            metadata: Dict[str, Any]
    ) -> None:
        """Handle progression to next stage"""
        # Archive current control point
        self._archive_control_point(control_point)

        # Create new control point for next stage
        new_cp_id = await self.create_control_point(
            stage=target_stage,
            metadata={
                **control_point.metadata,
                **metadata,
                'previous_control_point': control_point.id
            }
        )

        # Notify about stage progression
        await self._notify_stage_progression(control_point, new_cp_id, target_stage)

    def _archive_control_point(self, control_point: ControlPoint) -> None:
        """Archive a completed control point"""
        # Move to history
        if control_point.id in self.active_control_points:
            history = self.control_point_history.setdefault(
                control_point.metadata.get('pipeline_id', 'unknown'),
                []
            )
            history.append(control_point)
            del self.active_control_points[control_point.id]

    async def _notify_control_point_created(
            self,
            control_point: ControlPoint
    ) -> None:
        """Notify about new control point creation"""
        message = ProcessingMessage(
            message_type=MessageType.CONTROL_POINT_REACHED,
            content={
                'control_point_id': control_point.id,
                'stage': control_point.stage.value,
                'requires_decision': control_point.requires_decision,
                'metadata': control_point.metadata
            },
            metadata=MessageMetadata(
                source_component="control_point_manager",
                target_component="all"
            )
        )

        await self.message_broker.publish(message)

    async def _notify_stage_progression(
            self,
            old_control_point: ControlPoint,
            new_control_point_id: str,
            target_stage: ProcessingStage
    ) -> None:
        """Notify about stage progression"""
        message = ProcessingMessage(
            message_type=MessageType.STAGE_COMPLETE,
            content={
                'old_control_point_id': old_control_point.id,
                'new_control_point_id': new_control_point_id,
                'from_stage': old_control_point.stage.value,
                'to_stage': target_stage.value,
                'metadata': old_control_point.metadata
            },
            metadata=MessageMetadata(
                source_component="control_point_manager",
                target_component="all"
            )
        )

        await self.message_broker.publish(message)

    def _setup_message_handlers(self) -> None:
        """Setup message handlers for CPM"""
        self.message_broker.subscribe(
            self.component_id,
            "control.*",
            self._handle_control_message
        )

    async def _handle_control_message(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle incoming control messages"""
        try:
            if message.message_type == MessageType.USER_DECISION_SUBMITTED:
                await self._handle_user_decision(message)
            elif message.message_type == MessageType.FLOW_ERROR:
                await self._handle_flow_error(message)

        except Exception as e:
            logger.error(f"Message handling failed: {str(e)}")

    def get_control_point_status(
            self,
            control_point_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get status of a control point"""
        control_point = self.active_control_points.get(control_point_id)
        if not control_point:
            return None

        return {
            'id': control_point.id,
            'stage': control_point.stage.value,
            'status': control_point.status.value,
            'created_at': control_point.created_at.isoformat(),
            'updated_at': control_point.updated_at.isoformat(),
            'decisions': control_point.decisions,
            'requires_decision': control_point.requires_decision,
            'metadata': control_point.metadata
        }

    def get_pipeline_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get complete pipeline status"""
        history = self.control_point_history.get(pipeline_id, [])
        active = [
            cp for cp in self.active_control_points.values()
            if cp.metadata.get('pipeline_id') == pipeline_id
        ]

        if not history and not active:
            return None

        return {
            'pipeline_id': pipeline_id,
            'current_stage': active[0].stage.value if active else None,
            'history': [
                {
                    'stage': cp.stage.value,
                    'status': cp.status.value,
                    'decisions': cp.decisions
                }
                for cp in history
            ],
            'active_control_points': [
                self.get_control_point_status(cp.id)
                for cp in active
            ]
        }