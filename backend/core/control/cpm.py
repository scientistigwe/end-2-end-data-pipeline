# backend/core/control/cpm.py

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid
from dataclasses import dataclass, field

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
    BaseContext,
    QualityContext,
    InsightContext,
    AnalyticsContext,
    DecisionContext,
    RecommendationContext,
    ReportContext,
    PipelineContext
)
from ..registry.component_registry import ComponentRegistry

logger = logging.getLogger(__name__)


@dataclass
class ControlPoint:
    """Control point representing a decision/transition point in processing"""
    stage: ProcessingStage
    department: str
    assigned_module: ModuleIdentifier
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ProcessingStatus = ProcessingStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    next_stages: List[ProcessingStage] = field(default_factory=list)
    requires_decision: bool = True
    staging_reference: Optional[str] = None
    pipeline_id: Optional[str] = None
    parent_control_point: Optional[str] = None
    timeout_minutes: int = 60


class ControlPointManager:
    """Enhanced Control Point Manager with complete processing chains"""

    def __init__(self, message_broker: MessageBroker):
        # Core components
        self.message_broker = message_broker
        self.component_registry = ComponentRegistry()

        # State management
        self.active_control_points: Dict[str, ControlPoint] = {}
        self.control_point_history: Dict[str, List[ControlPoint]] = {}
        self.department_chains: Dict[str, Dict[str, ModuleIdentifier]] = {}
        self.active_pipelines: Dict[str, PipelineContext] = {}

        # Process flow configuration
        self.stage_transitions = self._setup_stage_transitions()
        self.department_sequence = self._setup_department_sequence()

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="control_point_manager",
            component_type=ComponentType.ORCHESTRATOR,
            department="control",
            role="manager"
        )

        # Initialize
        self._initialize()

    def _setup_stage_transitions(self) -> Dict[ProcessingStage, List[ProcessingStage]]:
        """Define the possible stage transitions"""
        return {
            ProcessingStage.RECEPTION: [ProcessingStage.VALIDATION],
            ProcessingStage.VALIDATION: [ProcessingStage.QUALITY_CHECK],
            ProcessingStage.QUALITY_CHECK: [
                ProcessingStage.CONTEXT_ANALYSIS,
                ProcessingStage.USER_REVIEW  # If quality issues found
            ],
            ProcessingStage.CONTEXT_ANALYSIS: [
                ProcessingStage.INSIGHT_GENERATION,
                ProcessingStage.ADVANCED_ANALYTICS
            ],
            ProcessingStage.INSIGHT_GENERATION: [
                ProcessingStage.DECISION_MAKING,
                ProcessingStage.USER_REVIEW
            ],
            ProcessingStage.ADVANCED_ANALYTICS: [
                ProcessingStage.INSIGHT_GENERATION,
                ProcessingStage.DECISION_MAKING
            ],
            ProcessingStage.DECISION_MAKING: [
                ProcessingStage.RECOMMENDATION,
                ProcessingStage.REPORT_GENERATION
            ],
            ProcessingStage.RECOMMENDATION: [
                ProcessingStage.USER_REVIEW,
                ProcessingStage.REPORT_GENERATION
            ],
            ProcessingStage.REPORT_GENERATION: [
                ProcessingStage.USER_REVIEW,
                ProcessingStage.COMPLETION
            ],
            ProcessingStage.USER_REVIEW: [
                ProcessingStage.QUALITY_CHECK,  # For rework
                ProcessingStage.INSIGHT_GENERATION,  # For additional analysis
                ProcessingStage.REPORT_GENERATION,  # For report updates
                ProcessingStage.COMPLETION
            ]
        }

    def _setup_department_sequence(self) -> Dict[ProcessingStage, str]:
        """Map stages to responsible departments"""
        return {
            ProcessingStage.RECEPTION: "service",
            ProcessingStage.VALIDATION: "service",
            ProcessingStage.QUALITY_CHECK: "quality",
            ProcessingStage.CONTEXT_ANALYSIS: "insight",
            ProcessingStage.INSIGHT_GENERATION: "insight",
            ProcessingStage.ADVANCED_ANALYTICS: "analytics",
            ProcessingStage.DECISION_MAKING: "decision",
            ProcessingStage.RECOMMENDATION: "recommendation",
            ProcessingStage.REPORT_GENERATION: "report",
            ProcessingStage.USER_REVIEW: "service"
        }

    def _initialize(self):
        """Initialize CPM with all processing chains"""
        try:
            # Register with message broker
            asyncio.create_task(
                self.message_broker.subscribe(
                    self.module_identifier,
                    [
                        "control.*",
                        "*.complete",
                        "*.error",
                        "decision.required",
                        "quality.issues.detected",
                        "insight.generated",
                        "recommendation.ready"
                    ],
                    self._handle_control_message
                )
            )

            # Register department chains
            self._register_department_chains()

            logger.info("Control Point Manager initialized successfully")

        except Exception as e:
            logger.error(f"CPM initialization failed: {str(e)}")
            raise

    def _register_department_chains(self):
        """Register all department processing chains"""
        department_configs = {
            "quality": (
                ComponentType.QUALITY_MANAGER,
                ComponentType.QUALITY_HANDLER,
                ComponentType.QUALITY_PROCESSOR,
                QualityContext
            ),
            "insight": (
                ComponentType.INSIGHT_MANAGER,
                ComponentType.INSIGHT_HANDLER,
                ComponentType.INSIGHT_PROCESSOR,
                InsightContext
            ),
            "analytics": (
                ComponentType.ANALYTICS_MANAGER,
                ComponentType.ANALYTICS_HANDLER,
                ComponentType.ANALYTICS_PROCESSOR,
                AnalyticsContext
            ),
            "decision": (
                ComponentType.DECISION_MANAGER,
                ComponentType.DECISION_HANDLER,
                ComponentType.DECISION_PROCESSOR,
                DecisionContext
            ),
            "recommendation": (
                ComponentType.RECOMMENDATION_MANAGER,
                ComponentType.RECOMMENDATION_HANDLER,
                ComponentType.RECOMMENDATION_PROCESSOR,
                RecommendationContext
            ),
            "report": (
                ComponentType.REPORT_MANAGER,
                ComponentType.REPORT_HANDLER,
                ComponentType.REPORT_PROCESSOR,
                ReportContext
            )
        }

        for dept_name, (manager_type, handler_type, processor_type, context_type) in department_configs.items():
            chain_id = str(uuid.uuid4())

            # Create module identifiers
            manager = ModuleIdentifier.create_manager_identifier(
                manager_type, f"{dept_name}_manager"
            )
            handler = ModuleIdentifier.create_handler_identifier(
                handler_type, f"{dept_name}_handler"
            )
            processor = ModuleIdentifier(
                component_name=f"{dept_name}_processor",
                component_type=processor_type,
                department=dept_name,
                role="processor"
            )

            # Register chain
            self.department_chains[dept_name] = {
                'manager': manager,
                'handler': handler,
                'processor': processor,
                'context_type': context_type,
                'chain_id': chain_id
            }

            # Register with broker
            asyncio.create_task(
                self.message_broker.register_processing_chain(
                    chain_id, manager, handler, processor
                )
            )

    async def create_pipeline(
            self,
            pipeline_id: str,
            initial_metadata: Dict[str, Any]
    ) -> str:
        """Create a new processing pipeline"""
        context = PipelineContext(
            pipeline_id=pipeline_id,
            stage=ProcessingStage.RECEPTION,
            status=ProcessingStatus.PENDING,
            current_stage=ProcessingStage.RECEPTION.value,
            stage_sequence=[stage.value for stage in ProcessingStage],
            stage_dependencies=self._create_stage_dependencies(),
            stage_configs={},
            component_states={},
            progress={},
            error_handling_rules={},
            metadata=initial_metadata
        )

        self.active_pipelines[pipeline_id] = context
        return pipeline_id

    def _create_stage_dependencies(self) -> Dict[str, List[str]]:
        """Create stage dependencies map"""
        dependencies = {}
        for stage in ProcessingStage:
            dependencies[stage.value] = [
                prev_stage.value for prev_stage in ProcessingStage
                if stage in self.stage_transitions.get(prev_stage, [])
            ]
        return dependencies

    async def create_control_point(
            self,
            stage: ProcessingStage,
            pipeline_id: str,
            metadata: Dict[str, Any],
            staging_reference: Optional[str] = None,
            requires_decision: bool = True,
            parent_control_point: Optional[str] = None
    ) -> str:
        """Create a new control point"""
        try:
            department = self.department_sequence[stage]
            chain = self.department_chains.get(department)

            if not chain:
                raise ValueError(f"Unknown department: {department}")

            control_point = ControlPoint(
                stage=stage,
                department=department,
                assigned_module=chain['manager'],
                metadata=metadata,
                requires_decision=requires_decision,
                next_stages=self.stage_transitions.get(stage, []),
                staging_reference=staging_reference,
                pipeline_id=pipeline_id,
                parent_control_point=parent_control_point
            )

            self.active_control_points[control_point.id] = control_point

            # Update pipeline context
            if pipeline_id in self.active_pipelines:
                pipeline = self.active_pipelines[pipeline_id]
                pipeline.current_stage = stage.value
                pipeline.component_states[department] = ProcessingStatus.PENDING.value

            # Notify about new control point
            await self._notify_control_point_created(control_point)

            return control_point.id

        except Exception as e:
            logger.error(f"Control point creation failed: {str(e)}")
            raise

    async def _notify_control_point_created(
            self,
            control_point: ControlPoint
    ) -> None:
        """Notify about new control point creation"""
        message = ProcessingMessage(
            message_type=MessageType.CONTROL_POINT_REACHED,
            content={
                'control_point_id': control_point.id,
                'pipeline_id': control_point.pipeline_id,
                'stage': control_point.stage.value,
                'requires_decision': control_point.requires_decision,
                'metadata': control_point.metadata,
                'staging_reference': control_point.staging_reference
            },
            source_identifier=self.module_identifier,
            target_identifier=control_point.assigned_module,
            metadata=MessageMetadata(
                source_component="control_point_manager",
                target_component=control_point.assigned_module.component_name,
                domain_type=control_point.department,
                processing_stage=control_point.stage,
                correlation_id=control_point.pipeline_id
            )
        )

        await self.message_broker.publish(message)

    # backend/core/control/cpm.py [continued]

    async def process_decision(
            self,
            control_point_id: str,
            decision: Dict[str, Any]
    ) -> bool:
        """Process a decision and determine next actions"""
        try:
            control_point = self.active_control_points.get(control_point_id)
            if not control_point:
                logger.warning(f"Control point not found: {control_point_id}")
                return False

            # Record decision
            control_point.decisions.append(decision)
            control_point.updated_at = datetime.now()

            # Determine next action
            next_action = self._determine_next_action(control_point, decision)

            # Execute action
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

        decision_type = decision.get('type')

        if decision_type == 'approve':
            # Move to next logical stage
            next_stages = self.stage_transitions.get(control_point.stage, [])
            if next_stages:
                action['target_stage'] = next_stages[0]

        elif decision_type == 'rework':
            # Return to appropriate rework stage
            action['type'] = 'retry'
            action['target_stage'] = decision.get('rework_stage', control_point.stage)
            action['metadata']['rework_reason'] = decision.get('reason')

        elif decision_type == 'reject':
            action['type'] = 'reject'
            action['metadata']['rejection_reason'] = decision.get('reason')

        return action

    async def _execute_action(
            self,
            control_point: ControlPoint,
            action: Dict[str, Any]
    ) -> None:
        """Execute determined action"""
        try:
            if action['type'] == 'proceed':
                await self._proceed_to_stage(
                    control_point,
                    action['target_stage'],
                    action.get('metadata', {})
                )

            elif action['type'] == 'retry':
                await self._retry_stage(
                    control_point,
                    action['target_stage'],
                    action.get('metadata', {})
                )

            elif action['type'] == 'reject':
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

        # Update pipeline status
        if control_point.pipeline_id in self.active_pipelines:
            pipeline = self.active_pipelines[control_point.pipeline_id]
            pipeline.current_stage = target_stage.value

        # Create new control point for next stage
        new_cp_id = await self.create_control_point(
            stage=target_stage,
            pipeline_id=control_point.pipeline_id,
            metadata={
                **control_point.metadata,
                **metadata,
                'previous_control_point': control_point.id
            },
            staging_reference=control_point.staging_reference,
            parent_control_point=control_point.id
        )

        # Notify about stage progression
        await self._notify_stage_progression(control_point, new_cp_id, target_stage)

    async def _retry_stage(
            self,
            control_point: ControlPoint,
            target_stage: ProcessingStage,
            metadata: Dict[str, Any]
    ) -> None:
        """Handle stage retry"""
        # Archive current control point
        self._archive_control_point(control_point)

        # Create new control point for retry
        await self.create_control_point(
            stage=target_stage,
            pipeline_id=control_point.pipeline_id,
            metadata={
                **control_point.metadata,
                **metadata,
                'retry_of': control_point.id,
                'retry_count': len([
                    cp for cp in self.control_point_history.get(control_point.pipeline_id, [])
                    if cp.stage == target_stage
                ]) + 1
            },
            staging_reference=control_point.staging_reference,
            parent_control_point=control_point.id
        )

    async def _handle_rejection(
            self,
            control_point: ControlPoint,
            metadata: Dict[str, Any]
    ) -> None:
        """Handle rejected processing"""
        # Update control point status
        control_point.status = ProcessingStatus.REJECTED

        # Update pipeline status
        if control_point.pipeline_id in self.active_pipelines:
            pipeline = self.active_pipelines[control_point.pipeline_id]
            pipeline.status = ProcessingStatus.REJECTED

        # Notify about rejection
        await self._notify_rejection(control_point, metadata)

    def _archive_control_point(self, control_point: ControlPoint) -> None:
        """Archive a completed control point"""
        if control_point.pipeline_id:
            history = self.control_point_history.setdefault(
                control_point.pipeline_id, []
            )
            history.append(control_point)

        if control_point.id in self.active_control_points:
            del self.active_control_points[control_point.id]

    async def _handle_control_message(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle incoming control messages"""
        try:
            if message.message_type == MessageType.USER_DECISION_SUBMITTED:
                await self.process_decision(
                    message.content['control_point_id'],
                    message.content['decision']
                )

            elif message.message_type == MessageType.QUALITY_ISSUES_DETECTED:
                await self._handle_quality_issues(message)

            elif message.message_type == MessageType.FLOW_ERROR:
                await self._handle_flow_error(message)

            # Handle other message types...

        except Exception as e:
            logger.error(f"Message handling failed: {str(e)}")

    async def _handle_quality_issues(
            self,
            message: ProcessingMessage
    ) -> None:
        """Handle detected quality issues"""
        control_point_id = message.content.get('control_point_id')
        if not control_point_id or control_point_id not in self.active_control_points:
            return

        control_point = self.active_control_points[control_point_id]

        # Create user review control point
        await self.create_control_point(
            stage=ProcessingStage.USER_REVIEW,
            pipeline_id=control_point.pipeline_id,
            metadata={
                **control_point.metadata,
                'quality_issues': message.content.get('issues', []),
                'review_type': 'quality_review'
            },
            staging_reference=control_point.staging_reference,
            parent_control_point=control_point.id
        )

    def get_pipeline_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get complete pipeline status"""
        pipeline = self.active_pipelines.get(pipeline_id)
        if not pipeline:
            return None

        history = self.control_point_history.get(pipeline_id, [])
        active = [
            cp for cp in self.active_control_points.values()
            if cp.pipeline_id == pipeline_id
        ]

        return {
            'pipeline_id': pipeline_id,
            'current_stage': pipeline.current_stage,
            'status': pipeline.status.value,
            'history': [
                {
                    'control_point_id': cp.id,
                    'stage': cp.stage.value,
                    'department': cp.department,
                    'status': cp.status.value,
                    'created_at': cp.created_at.isoformat(),
                    'decisions': cp.decisions
                }
                for cp in history
            ],
            'active_control_points': [
                {
                    'control_point_id': cp.id,
                    'stage': cp.stage.value,
                    'department': cp.department,
                    'status': cp.status.value,
                    'created_at': cp.created_at.isoformat()
                }
                for cp in active
            ],
            'component_states': pipeline.component_states,
            'progress': pipeline.progress
        }