# backend/core/control/cpm.py

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid
from dataclasses import dataclass, field

from ..messaging.broker import MessageBroker
from ..managers.staging_manager import StagingManager
from ..messaging.event_types import (
    MessageType,
    ProcessingStage,
    ProcessingStatus,
    ProcessingMessage,
    MessageMetadata,
    ModuleIdentifier,
    ComponentType,
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
    """Represents a decision/transition point in processing"""
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert control point to dictionary"""
        return {
            'id': self.id,
            'stage': self.stage.value,
            'department': self.department,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'metadata': self.metadata,
            'decisions': self.decisions,
            'requires_decision': self.requires_decision,
            'staging_reference': self.staging_reference,
            'pipeline_id': self.pipeline_id,
            'parent_control_point': self.parent_control_point
        }

class ControlPointManager:
    """Control Point Manager orchestrates the processing flow"""

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        # Core components
        self.message_broker = message_broker
        self.component_registry = ComponentRegistry()
        self.staging_manager = staging_manager


        # State management
        self.active_control_points: Dict[str, ControlPoint] = {}
        self.control_point_history: Dict[str, List[ControlPoint]] = {}
        self.department_chains: Dict[str, Dict[str, ModuleIdentifier]] = {}
        self.active_pipelines: Dict[str, PipelineContext] = {}

        # Module identification
        self.module_identifier = ModuleIdentifier(
            component_name="control_point_manager",
            component_type=ComponentType.MANAGER,
            department="control",
            role="manager"
        )

        # Process flow configuration
        self.stage_transitions = self._setup_stage_transitions()
        self.department_sequence = self._setup_department_sequence()

        # Initialize
        self._initialize()

    def initialize(self):
        """Public method to trigger initialization"""
        return self._initialize()  # Call the private method

    async def _initialize(self):
        """Initialize CPM with all processing chains"""
        try:
            # Setup message handlers with event loop management
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # Message patterns to subscribe to
            # Register message patterns
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns = [
                    "control.*",
                    "*.complete",
                    "*.error",
                    "decision.required",
                    "quality.issues.detected",
                    "insight.generated",
                    "recommendation.ready",
                    "staging.data.stored",
                    "staging.output.stored",
                    "staging.access.granted",
                    "staging.access.denied"
                ],
                callback=self._handle_control_message
            )

            # Perform other initialization tasks
            self._register_department_chains()

            logger.info("Control Point Manager initialized successfully")

        except Exception as e:
            logger.error(f"CPM initialization failed: {str(e)}")
            raise

    def _setup_stage_transitions(self) -> Dict[ProcessingStage, List[ProcessingStage]]:
        """Define stage transitions"""
        return {
            ProcessingStage.RECEPTION: [ProcessingStage.VALIDATION],
            ProcessingStage.VALIDATION: [ProcessingStage.QUALITY_CHECK],
            ProcessingStage.QUALITY_CHECK: [
                ProcessingStage.CONTEXT_ANALYSIS,
                ProcessingStage.USER_REVIEW
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
                ProcessingStage.QUALITY_CHECK,
                ProcessingStage.INSIGHT_GENERATION,
                ProcessingStage.REPORT_GENERATION,
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

        loop = asyncio.get_event_loop()
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
            loop.create_task(
                self.message_broker.register_processing_chain(
                    chain_id, manager, handler, processor
                )
            )

    async def _handle_control_message(self, message: ProcessingMessage) -> None:
        """Handle incoming control messages"""
        try:
            handlers = {
                MessageType.USER_DECISION_SUBMITTED: self._handle_decision_submitted,
                MessageType.QUALITY_ISSUES_DETECTED: self._handle_quality_issues,
                MessageType.STAGING_DATA_STORED: self._handle_staged_data,
                MessageType.STAGING_OUTPUT_STORED: self._handle_staged_output,
                MessageType.COMPONENT_OUTPUT_READY: self._handle_component_output,
                MessageType.FLOW_ERROR: self._handle_flow_error
            }

            handler = handlers.get(message.message_type)
            if handler:
                await handler(message)
            else:
                logger.warning(f"Unhandled message type: {message.message_type}")

        except Exception as e:
            logger.error(f"Message handling failed: {str(e)}")
            await self._handle_flow_error(message, error=e)

    async def create_pipeline(
            self,
            pipeline_id: str,
            initial_metadata: Dict[str, Any]
    ) -> str:
        """Create new processing pipeline"""
        try:
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
                metadata=initial_metadata
            )

            self.active_pipelines[pipeline_id] = context

            # Create initial control point
            await self.create_control_point(
                stage=ProcessingStage.RECEPTION,
                pipeline_id=pipeline_id,
                metadata=initial_metadata
            )

            return pipeline_id

        except Exception as e:
            logger.error(f"Pipeline creation failed: {str(e)}")
            raise

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
        """Create new control point"""
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
        try:
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

        except Exception as e:
            logger.error(f"Control point notification failed: {str(e)}")
            raise

    async def _handle_staged_data(self, message: ProcessingMessage) -> None:
        """Handle notification of newly staged data"""
        try:
            content = message.content
            reference_id = content.get('reference_id')
            pipeline_id = content.get('pipeline_id')
            component_type = content.get('component_type')

            # Update relevant control point
            active_cp = next(
                (cp for cp in self.active_control_points.values()
                 if cp.pipeline_id == pipeline_id and
                 cp.stage.value == content.get('stage')),
                None
            )

            if active_cp:
                active_cp.staging_reference = reference_id
                active_cp.metadata.update({
                    'staged_data': {
                        'reference_id': reference_id,
                        'component_type': component_type,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                })
                await self._check_stage_readiness(active_cp)

        except Exception as e:
            logger.error(f"Staged data handling error: {str(e)}")

    async def _handle_component_output(self, message: ProcessingMessage) -> None:
        """Handle component output notification"""
        try:
            content = message.content
            reference_id = content.get('reference_id')
            component_type = content.get('component_type')
            output_data = content.get('output_data')

            # Find control point by staging reference
            control_point = next(
                (cp for cp in self.active_control_points.values()
                 if cp.staging_reference == reference_id),
                None
            )

            if control_point:
                # Update control point with output information
                output_key = f"{component_type.lower()}_output"
                control_point.metadata[output_key] = output_data
                await self._check_stage_completion(control_point)

        except Exception as e:
            logger.error(f"Component output handling error: {str(e)}")

    async def _check_stage_readiness(self, control_point: ControlPoint) -> None:
        """Check if stage is ready to begin processing"""
        try:
            stage_requirements = {
                ProcessingStage.QUALITY_CHECK: {'staged_data'},
                ProcessingStage.CONTEXT_ANALYSIS: {'quality_output'},
                ProcessingStage.INSIGHT_GENERATION: {'context_analysis_output'},
                # Add other stage requirements
            }

            required = stage_requirements.get(control_point.stage, set())
            available = set(control_point.metadata.keys())

            if required.issubset(available):
                await self._start_stage_processing(control_point)

        except Exception as e:
            logger.error(f"Stage readiness check error: {str(e)}")

    async def _start_stage_processing(self, control_point: ControlPoint) -> None:
        """Start processing for a stage"""
        try:
            # Get department chain
            chain = self.department_chains.get(control_point.department)
            if not chain:
                raise ValueError(f"No chain for department: {control_point.department}")

            # Create processing message
            message = ProcessingMessage(
                message_type=MessageType.STAGE_PROCESSING_START,
                content={
                    'control_point_id': control_point.id,
                    'pipeline_id': control_point.pipeline_id,
                    'stage': control_point.stage.value,
                    'staging_reference': control_point.staging_reference,
                    'metadata': control_point.metadata
                },
                source_identifier=self.module_identifier,
                target_identifier=chain['manager']
            )

            # Update status
            control_point.status = ProcessingStatus.IN_PROGRESS

            # Notify processing start
            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Stage processing start error: {str(e)}")
            await self._handle_stage_error(control_point, str(e))

    async def _check_stage_completion(self, control_point: ControlPoint) -> None:
        """Check if stage processing is complete"""
        try:
            stage_outputs = {
                ProcessingStage.QUALITY_CHECK: {'quality_output'},
                ProcessingStage.CONTEXT_ANALYSIS: {'context_output'},
                ProcessingStage.INSIGHT_GENERATION: {'insight_output'},
                ProcessingStage.ADVANCED_ANALYTICS: {'analytics_output'},
                ProcessingStage.DECISION_MAKING: {'decision_output'},
                ProcessingStage.RECOMMENDATION: {'recommendation_output'},
                ProcessingStage.REPORT_GENERATION: {'report_output'}
            }

            required_outputs = stage_outputs.get(control_point.stage, set())
            available_outputs = {
                key for key in control_point.metadata.keys()
                if key.endswith('_output')
            }

            if required_outputs.issubset(available_outputs):
                await self._handle_stage_completion(control_point)

        except Exception as e:
            logger.error(f"Stage completion check error: {str(e)}")

    async def _handle_stage_completion(self, control_point: ControlPoint) -> None:
        """Handle stage completion"""
        try:
            # Update status
            control_point.status = ProcessingStatus.COMPLETED
            control_point.updated_at = datetime.utcnow()

            # Determine next action
            if control_point.requires_decision:
                await self._request_stage_decision(control_point)
            else:
                # Auto-proceed to next stage
                next_stage = self._determine_next_stage(control_point)
                if next_stage:
                    await self._proceed_to_stage(
                        control_point,
                        next_stage,
                        {'auto_transition': True}
                    )
                else:
                    await self._handle_pipeline_completion(control_point)

        except Exception as e:
            logger.error(f"Stage completion handling error: {str(e)}")

    async def _request_stage_decision(self, control_point: ControlPoint) -> None:
        """Request decision for stage completion"""
        try:
            # Prepare decision options based on stage
            options = self._prepare_decision_options(control_point)

            # Create decision request message
            message = ProcessingMessage(
                message_type=MessageType.DECISION_REQUEST,
                content={
                    'control_point_id': control_point.id,
                    'pipeline_id': control_point.pipeline_id,
                    'stage': control_point.stage.value,
                    'options': options,
                    'metadata': control_point.metadata,
                    'stage_outputs': {
                        k: v for k, v in control_point.metadata.items()
                        if k.endswith('_output')
                    }
                },
                source_identifier=self.module_identifier,
                target_identifier=None  # Broadcast to decision handlers
            )

            # Update status
            control_point.status = ProcessingStatus.AWAITING_DECISION

            # Send request
            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Decision request failed: {str(e)}")
            await self._handle_stage_error(control_point, str(e))

    def _prepare_decision_options(self, control_point: ControlPoint) -> List[Dict[str, Any]]:
        """Prepare decision options based on stage and context"""
        base_options = [
            {
                'type': 'approve',
                'label': 'Approve and Continue',
                'requires_comment': False
            },
            {
                'type': 'reject',
                'label': 'Reject',
                'requires_comment': True
            }
        ]

        # Add stage-specific options
        if control_point.stage == ProcessingStage.QUALITY_CHECK:
            base_options.append({
                'type': 'rework',
                'label': 'Request Rework',
                'requires_comment': True,
                'target_stage': ProcessingStage.VALIDATION
            })

        elif control_point.stage == ProcessingStage.INSIGHT_GENERATION:
            base_options.append({
                'type': 'more_analysis',
                'label': 'Request Additional Analysis',
                'requires_comment': True,
                'target_stage': ProcessingStage.ADVANCED_ANALYTICS
            })

        return base_options

    async def _handle_decision_submitted(self, message: ProcessingMessage) -> None:
        """Handle submitted decision"""
        try:
            content = message.content
            control_point_id = content.get('control_point_id')
            decision = content.get('decision')

            control_point = self.active_control_points.get(control_point_id)
            if not control_point:
                logger.warning(f"Control point not found: {control_point_id}")
                return

            # Record decision
            control_point.decisions.append({
                **decision,
                'timestamp': datetime.utcnow().isoformat(),
                'decision_maker': message.source_identifier.component_name
            })

            # Process decision
            await self.process_decision(control_point_id, decision)

        except Exception as e:
            logger.error(f"Decision handling error: {str(e)}")

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

        elif decision_type == 'more_analysis':
            action['type'] = 'proceed'
            action['target_stage'] = ProcessingStage.ADVANCED_ANALYTICS
            action['metadata']['analysis_request'] = decision.get('reason')

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

    async def _handle_pipeline_completion(self, control_point: ControlPoint) -> None:
        """Handle pipeline completion"""
        try:
            pipeline = self.active_pipelines.get(control_point.pipeline_id)
            if not pipeline:
                return

            # Update pipeline status
            pipeline.status = ProcessingStatus.COMPLETED

            # Create completion message
            message = ProcessingMessage(
                message_type=MessageType.PIPELINE_COMPLETE,
                content={
                    'pipeline_id': control_point.pipeline_id,
                    'final_stage': control_point.stage.value,
                    'completion_time': datetime.utcnow().isoformat(),
                    'summary': self._create_pipeline_summary(pipeline)
                },
                source_identifier=self.module_identifier
            )

            # Notify completion
            await self.message_broker.publish(message)

            # Cleanup
            await self._cleanup_pipeline(control_point.pipeline_id)

        except Exception as e:
            logger.error(f"Pipeline completion handling error: {str(e)}")

    def _create_pipeline_summary(self, pipeline: PipelineContext) -> Dict[str, Any]:
        """Create pipeline execution summary"""
        return {
            'pipeline_id': pipeline.pipeline_id,
            'status': pipeline.status.value,
            'stages_completed': pipeline.stage_sequence,
            'total_time': (datetime.utcnow() - pipeline.created_at).total_seconds(),
            'component_states': pipeline.component_states,
            'progress': pipeline.progress
        }

    async def _handle_stage_error(
            self,
            control_point: ControlPoint,
            error: str,
            error_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Handle stage processing errors"""
        try:
            # Update control point status
            control_point.status = ProcessingStatus.FAILED
            control_point.metadata['error'] = {
                'message': error,
                'context': error_context or {},
                'timestamp': datetime.utcnow().isoformat()
            }

            # Update pipeline status
            pipeline = self.active_pipelines.get(control_point.pipeline_id)
            if pipeline:
                pipeline.status = ProcessingStatus.FAILED
                pipeline.component_states[control_point.department] = ProcessingStatus.FAILED.value

            # Create error message
            message = ProcessingMessage(
                message_type=MessageType.FLOW_ERROR,
                content={
                    'control_point_id': control_point.id,
                    'pipeline_id': control_point.pipeline_id,
                    'stage': control_point.stage.value,
                    'department': control_point.department,
                    'error': error,
                    'error_context': error_context,
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier
            )

            # Notify error
            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    async def _handle_flow_error(
            self,
            message: ProcessingMessage,
            error: Optional[Exception] = None
    ) -> None:
        """Handle flow-level errors"""
        try:
            content = message.content
            pipeline_id = content.get('pipeline_id')
            control_point_id = content.get('control_point_id')

            # Find affected control point
            control_point = None
            if control_point_id:
                control_point = self.active_control_points.get(control_point_id)
            elif pipeline_id:
                control_point = next(
                    (cp for cp in self.active_control_points.values()
                     if cp.pipeline_id == pipeline_id),
                    None
                )

            if control_point:
                await self._handle_stage_error(
                    control_point,
                    str(error) if error else "Flow error",
                    content.get('error_context')
                )

        except Exception as e:
            logger.error(f"Flow error handling failed: {str(e)}")

    async def _cleanup_pipeline(self, pipeline_id: str) -> None:
        """Clean up pipeline resources"""
        try:
            # Archive control points
            control_points = [
                cp for cp in self.active_control_points.values()
                if cp.pipeline_id == pipeline_id
            ]
            for cp in control_points:
                self._archive_control_point(cp)

            # Remove from active pipelines
            if pipeline_id in self.active_pipelines:
                del self.active_pipelines[pipeline_id]

            # Notify cleanup
            message = ProcessingMessage(
                message_type=MessageType.PIPELINE_CLEANUP,
                content={
                    'pipeline_id': pipeline_id,
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier
            )
            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Pipeline cleanup failed: {str(e)}")

    def get_pipeline_status(
            self,
            pipeline_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get complete pipeline status"""
        pipeline = self.active_pipelines.get(pipeline_id)
        if not pipeline:
            return None

        history = self.control_point_history.get(pipeline_id, [])
        active_points = [
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
                cp.to_dict() for cp in active_points
            ],
            'component_states': pipeline.component_states,
            'progress': pipeline.progress
        }

    async def _update_pipeline_progress(
            self,
            pipeline_id: str,
            stage: ProcessingStage,
            progress: float
    ) -> None:
        """Update pipeline progress"""
        try:
            pipeline = self.active_pipelines.get(pipeline_id)
            if not pipeline:
                return

            # Update stage progress
            pipeline.progress[stage.value] = progress

            # Calculate overall progress
            total_stages = len(ProcessingStage)
            completed_stages = len([
                s for s in pipeline.stage_sequence
                if s in pipeline.progress
            ])
            current_progress = pipeline.progress.get(stage.value, 0)

            overall_progress = (
                (completed_stages - 1 + current_progress) / total_stages
                if total_stages > 0 else 0
            )

            pipeline.progress['overall'] = overall_progress

            # Notify progress update
            await self._notify_progress_update(pipeline_id, overall_progress)

        except Exception as e:
            logger.error(f"Progress update failed: {str(e)}")

    async def _notify_progress_update(
            self,
            pipeline_id: str,
            progress: float
    ) -> None:
        """Notify about pipeline progress update"""
        try:
            message = ProcessingMessage(
                message_type=MessageType.PIPELINE_PROGRESS,
                content={
                    'pipeline_id': pipeline_id,
                    'progress': progress,
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier
            )
            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Progress notification failed: {str(e)}")

    async def cleanup(self) -> None:
        """Cleanup CPM resources"""
        try:
            # Cleanup active pipelines
            for pipeline_id in list(self.active_pipelines.keys()):
                await self._cleanup_pipeline(pipeline_id)

            # Clear all state
            self.active_control_points.clear()
            self.control_point_history.clear()
            self.active_pipelines.clear()
            self.department_chains.clear()

            logger.info("CPM cleanup completed successfully")

        except Exception as e:
            logger.error(f"CPM cleanup failed: {str(e)}")