# backend/core/control/cpm.py

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime
import uuid
from dataclasses import dataclass, field
from collections import defaultdict

from ..messaging.broker import MessageBroker
from ..managers.staging_manager import StagingManager
from ..messaging.event_types import (
    MessageType, ProcessingStage, ProcessingStatus, ProcessingMessage,
    MessageMetadata, ModuleIdentifier, ComponentType,
    QualityContext, InsightContext, AnalyticsContext,
    DecisionContext, RecommendationContext, ReportContext,
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
    cp_metadata: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    next_stages: List[ProcessingStage] = field(default_factory=list)
    requires_decision: bool = True
    staging_reference: Optional[str] = None
    pipeline_id: Optional[str] = None
    parent_control_point: Optional[str] = None
    timeout_minutes: int = 60
    user_id: Optional[str] = None

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
            'parent_control_point': self.parent_control_point,
            'user_id': self.user_id
        }


@dataclass
class FrontendRequest:
    """Track frontend request information"""
    request_id: str
    user_id: str
    pipeline_id: str
    request_type: str
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"
    metadata: Dict[str, Any] = field(default_factory=dict)


class ControlPointManager:
    """
    Control Point Manager:
    1. Direct frontend interface
    2. Backend pub/sub orchestration
    3. Process management
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        # Core components
        self.message_broker = message_broker
        self.staging_manager = staging_manager
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
            component_type=ComponentType.MANAGER,
            department="control",
            role="manager"
        )

        # Background tasks
        self.tasks: List[asyncio.Task] = []

    async def initialize(self):
        """Initialize CPM asynchronously"""
        try:
            # Register message handlers
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=[
                    "control.*",
                    "*.complete",
                    "*.error",
                    "decision.required",
                    "quality.issues.detected",
                    "insight.generated",
                    "recommendation.ready"
                ],
                callback=self._handle_control_message
            )

            # Register processing chains
            await self._register_department_chains()

            # Start background monitoring tasks
            self.tasks.extend([
                asyncio.create_task(self._monitor_process_timeouts()),
                asyncio.create_task(self._monitor_resource_usage()),
                asyncio.create_task(self._monitor_component_health())
            ])

            logger.info("Control Point Manager initialized successfully")

        except Exception as e:
            logger.error(f"CPM initialization failed: {str(e)}")
            raise

    async def _monitor_process_timeouts(self):
        """Monitor processes for timeouts"""
        while True:
            try:
                # Check active control points for timeouts
                current_time = datetime.now()
                for cp in list(self.active_control_points.values()):
                    elapsed_minutes = (current_time - cp.created_at).total_seconds() / 60
                    if elapsed_minutes > cp.timeout_minutes:
                        await self._handle_process_timeout(cp)

                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Process timeout monitoring failed: {str(e)}")
                await asyncio.sleep(60)  # Retry after error

    async def _monitor_resource_usage(self):
        """Monitor system resource usage"""
        while True:
            try:
                # Check CPU, memory usage etc.
                await self._check_resource_metrics()
                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Resource monitoring failed: {str(e)}")
                await asyncio.sleep(30)

    async def _monitor_component_health(self):
        """Monitor health of connected components"""
        while True:
            try:
                await self._check_component_health()
                await self._check_broker_connection()
                await self._check_processing_health()
                await asyncio.sleep(60)  # Check every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health monitoring failed: {str(e)}")
                await asyncio.sleep(60)

    async def cleanup(self):
        """Cleanup CPM resources"""
        try:
            # Cancel all background tasks
            for task in self.tasks:
                task.cancel()
            await asyncio.gather(*self.tasks, return_exceptions=True)
            self.tasks.clear()

            # Cleanup active pipelines
            for pipeline_id in list(self.active_pipelines.keys()):
                await self._cleanup_pipeline(pipeline_id)

            # Clear state
            self.active_control_points.clear()
            self.control_point_history.clear()
            self.active_pipelines.clear()
            self.department_chains.clear()

            logger.info("CPM cleanup completed successfully")

        except Exception as e:
            logger.error(f"CPM cleanup failed: {str(e)}")
    # -------------------------------------------------------------------------
    # FRONTEND INTERFACE
    # -------------------------------------------------------------------------

    async def handle_frontend_request(
            self,
            request_type: str,
            metadata: Dict[str, Any],
            user_id: str
    ) -> Dict[str, Any]:
        """Handle incoming frontend request"""
        try:
            # Generate IDs
            request_id = str(uuid.uuid4())
            pipeline_id = str(uuid.uuid4())

            # Create frontend request tracking
            frontend_request = FrontendRequest(
                request_id=request_id,
                user_id=user_id,
                pipeline_id=pipeline_id,
                request_type=request_type,
                metadata=metadata
            )
            self.frontend_requests[request_id] = frontend_request

            # Track user session
            self.user_sessions[user_id].add(pipeline_id)

            # Create pipeline and control point
            await self.create_pipeline(
                pipeline_id=pipeline_id,
                initial_metadata={
                    'request_type': request_type,
                    'user_id': user_id,
                    'request_id': request_id,
                    **metadata
                }
            )

            return {
                'status': 'success',
                'request_id': request_id,
                'pipeline_id': pipeline_id,
                'tracking_url': f'/api/pipeline/{pipeline_id}/status'
            }

        except Exception as e:
            logger.error(f"Frontend request failed: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            }

    async def get_frontend_status(
            self,
            pipeline_id: str,
            user_id: str
    ) -> Dict[str, Any]:
        """Get status for frontend"""
        try:
            # Validate user access
            if pipeline_id not in self.user_sessions.get(user_id, set()):
                return {'status': 'unauthorized'}

            # Get pipeline status
            status = self.get_pipeline_status(pipeline_id)
            if not status:
                return {'status': 'not_found'}

            # Get pending notifications
            notifications = self.user_notifications[user_id]
            self.user_notifications[user_id] = []  # Clear after retrieval

            return {
                'pipeline_id': pipeline_id,
                'current_stage': status['current_stage'],
                'progress': status['progress'],
                'requires_decision': self._needs_user_decision(status),
                'available_actions': self._get_user_actions(status),
                'notifications': notifications,
                'component_states': status['component_states']
            }

        except Exception as e:
            logger.error(f"Status retrieval failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    async def handle_user_decision(
            self,
            pipeline_id: str,
            decision: Dict[str, Any],
            user_id: str
    ) -> Dict[str, Any]:
        """Handle user decision from frontend"""
        try:
            # Validate user access
            if pipeline_id not in self.user_sessions.get(user_id, set()):
                return {'status': 'unauthorized'}

            # Find active control point
            active_cp = next(
                (cp for cp in self.active_control_points.values()
                 if cp.pipeline_id == pipeline_id and
                 cp.status == ProcessingStatus.AWAITING_DECISION),
                None
            )

            if not active_cp:
                return {
                    'status': 'error',
                    'error': 'No decision pending'
                }

            # Record user with decision
            decision['user_id'] = user_id
            decision['timestamp'] = datetime.utcnow().isoformat()

            # Process decision
            await self.process_decision(active_cp.id, decision)

            return {
                'status': 'success',
                'pipeline_id': pipeline_id
            }

        except Exception as e:
            logger.error(f"Decision handling failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    async def list_user_pipelines(
            self,
            user_id: str
    ) -> Dict[str, Any]:
        """List all pipelines for user"""
        try:
            pipeline_ids = self.user_sessions.get(user_id, set())
            pipelines = []

            for pid in pipeline_ids:
                status = self.get_pipeline_status(pid)
                if status:
                    pipelines.append({
                        'pipeline_id': pid,
                        'status': status['status'],
                        'current_stage': status['current_stage'],
                        'progress': status['progress'].get('overall', 0),
                        'created_at': status['history'][0]['created_at']
                        if status['history'] else None
                    })

            return {
                'status': 'success',
                'pipelines': pipelines
            }

        except Exception as e:
            logger.error(f"Pipeline listing failed: {str(e)}")
            return {'status': 'error', 'error': str(e)}

    def _needs_user_decision(self, status: Dict[str, Any]) -> bool:
        """Check if user decision is needed"""
        active_points = status.get('active_control_points', [])
        return any(
            cp.get('status') == ProcessingStatus.AWAITING_DECISION.value
            for cp in active_points
        )

    def _get_user_actions(self, status: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get available user actions"""
        actions = []

        if self._needs_user_decision(status):
            active_cp = next(
                cp for cp in status['active_control_points']
                if cp['status'] == ProcessingStatus.AWAITING_DECISION.value
            )

            # Get stage-specific options
            stage = ProcessingStage(active_cp['stage'])
            options = self._prepare_decision_options(stage)

            actions.extend([
                {
                    'type': 'decision',
                    'control_point_id': active_cp['id'],
                    'options': options
                }
            ])

        return actions

    # -------------------------------------------------------------------------
    # BACKEND PUB/SUB INTERFACE
    # -------------------------------------------------------------------------

    async def _initialize(self):
        """Initialize CPM with message handlers"""
        try:
            # Setup message handlers
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=[
                    # Core flow
                    "control.*",
                    "*.complete",
                    "*.error",
                    "decision.required",

                    # Component outputs
                    "quality.*.complete",
                    "insight.*.complete",
                    "analytics.*.complete",
                    "decision.*.complete",

                    # Staging notifications
                    "staging.data.stored",
                    "staging.output.stored",
                    "staging.access.*",

                    # User interactions
                    "user.decision.*",
                    "user.action.*"
                ],
                callback=self._handle_control_message
            )

            # Register processing chains
            await self._register_department_chains()

            logger.info("CPM initialized successfully")

        except Exception as e:
            logger.error(f"CPM initialization failed: {str(e)}")
            raise

    async def _handle_control_message(self, message: ProcessingMessage) -> None:
        """Handle incoming control messages"""
        try:
            handlers = {
                # Pipeline Control
                MessageType.CONTROL_POINT_CREATED: self._handle_control_point_created,
                MessageType.PIPELINE_STAGE_COMPLETE: self._handle_stage_complete,
                MessageType.PIPELINE_STAGE_ERROR: self._handle_stage_error,
                # Component Interactions
                MessageType.QUALITY_ISSUE_DETECTED: self._handle_quality_issues,
                MessageType.INSIGHT_GENERATE_COMPLETE: self._handle_insight_generated,
                MessageType.RECOMMENDATION_GENERATE_COMPLETE: self._handle_recommendation_ready,

                # Staging Interactions
                MessageType.STAGING_STORE_COMPLETE: self._handle_staged_data,
                MessageType.STAGING_RETRIEVE_COMPLETE: self._handle_staged_output,

                # User Interactions
                MessageType.DECISION_VALIDATE_COMPLETE: self._handle_user_decision,
                MessageType.USER_INTERVENTION_REQUEST: self._handle_user_action
            }
            handler = handlers.get(message.message_type)
            if handler:
                await handler(message)
            else:
                logger.warning(f"Unhandled message type: {message.message_type}")

        except Exception as e:
            logger.error(f"Message handling failed: {str(e)}")
            await self._handle_flow_error(message, error=e)

    async def _handle_quality_issues(self, message: ProcessingMessage) -> None:
        """Handle detected quality issues"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            issues = message.content.get('issues', [])

            # Find relevant control point
            control_point = next(
                (cp for cp in self.active_control_points.values()
                 if cp.pipeline_id == pipeline_id and
                 cp.stage == ProcessingStage.QUALITY_CHECK),
                None
            )

            if control_point:
                # Update control point
                control_point.metadata['quality_issues'] = issues
                control_point.requires_decision = True
                control_point.status = ProcessingStatus.AWAITING_DECISION

                # Notify frontend
                await self._notify_frontend(
                    pipeline_id=pipeline_id,
                    notification_type='quality_issues',
                    data={
                        'issues': issues,
                        'requires_action': True
                    }
                )

        except Exception as e:
            logger.error(f"Quality issues handling failed: {str(e)}")
            await self._handle_flow_error(message, error=e)

    async def _handle_insight_generated(self, message: ProcessingMessage) -> None:
        """Handle generated insights"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            insights = message.content.get('insights', [])

            # Find relevant control point
            control_point = next(
                (cp for cp in self.active_control_points.values()
                 if cp.pipeline_id == pipeline_id and
                 cp.stage == ProcessingStage.INSIGHT_GENERATION),
                None
            )

            if control_point:
                # Update control point
                control_point.metadata['insights'] = insights
                control_point.requires_decision = True
                control_point.status = ProcessingStatus.AWAITING_DECISION

                # Notify frontend
                await self._notify_frontend(
                    pipeline_id=pipeline_id,
                    notification_type='insights_ready',
                    data={
                        'insights': insights,
                        'requires_review': True
                    }
                )

        except Exception as e:
            logger.error(f"Insight handling failed: {str(e)}")
            await self._handle_flow_error(message, error=e)

    async def _handle_recommendation_ready(self, message: ProcessingMessage) -> None:
        """Handle ready recommendations"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            recommendations = message.content.get('recommendations', [])

            # Find relevant control point
            control_point = next(
                (cp for cp in self.active_control_points.values()
                 if cp.pipeline_id == pipeline_id and
                 cp.stage == ProcessingStage.RECOMMENDATION),
                None
            )

            if control_point:
                # Update control point
                control_point.metadata['recommendations'] = recommendations
                control_point.requires_decision = True
                control_point.status = ProcessingStatus.AWAITING_DECISION

                # Notify frontend
                await self._notify_frontend(
                    pipeline_id=pipeline_id,
                    notification_type='recommendations_ready',
                    data={
                        'recommendations': recommendations,
                        'requires_review': True
                    }
                )

        except Exception as e:
            logger.error(f"Recommendation handling failed: {str(e)}")
            await self._handle_flow_error(message, error=e)

    # -------------------------------------------------------------------------
    # FRONTEND NOTIFICATION HANDLING
    # -------------------------------------------------------------------------

    async def _notify_frontend(
            self,
            pipeline_id: str,
            notification_type: str,
            data: Dict[str, Any]
    ) -> None:
        """Send notification to frontend"""
        try:
            # Get pipeline status
            status = self.get_pipeline_status(pipeline_id)
            if not status:
                return

            # Get user ID from metadata
            user_id = status['metadata'].get('user_id')
            if not user_id:
                return

            # Create notification
            notification = {
                'type': notification_type,
                'pipeline_id': pipeline_id,
                'timestamp': datetime.utcnow().isoformat(),
                'data': data
            }

            # Store for next status check
            self.user_notifications[user_id].append(notification)

        except Exception as e:
            logger.error(f"Frontend notification failed: {str(e)}")

    # -------------------------------------------------------------------------
    # PROCESS MANAGEMENT
    # -------------------------------------------------------------------------

    async def create_pipeline(
            self,
            pipeline_id: str,
            initial_metadata: Dict[str, Any]
    ) -> str:
        """Create new processing pipeline"""
        try:
            # Create pipeline context
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
                metadata=initial_metadata,
                requires_decision=False  # Initial point doesn't need decision
            )

            return pipeline_id

        except Exception as e:
            logger.error(f"Pipeline creation failed: {str(e)}")
            raise

    def _setup_stage_transitions(self) -> Dict[ProcessingStage, List[ProcessingStage]]:
        """
        Define the possible stage transitions in the data processing pipeline.

        Represents a directed graph of stage progression, determining valid
        transitions between different processing stages.

        Returns:
            Dict mapping each processing stage to its possible next stages
        """
        return {
            ProcessingStage.RECEPTION: [ProcessingStage.VALIDATION],
            ProcessingStage.VALIDATION: [ProcessingStage.QUALITY_CHECK],
            ProcessingStage.QUALITY_CHECK: [
                ProcessingStage.CONTEXT_ANALYSIS,
                ProcessingStage.USER_REVIEW  # If quality issues are found
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
                ProcessingStage.QUALITY_CHECK,  # Rework needed
                ProcessingStage.INSIGHT_GENERATION,  # Additional analysis
                ProcessingStage.REPORT_GENERATION,  # Report updates
                ProcessingStage.COMPLETION
            ]
        }

    def _setup_department_sequence(self) -> Dict[ProcessingStage, str]:
        """
        Map processing stages to responsible departments.

        Provides a mapping of which organizational department or
        functional unit is responsible for processing each stage.

        Returns:
            Dict mapping processing stages to department names
        """
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

    def _create_stage_dependencies(self) -> Dict[str, List[str]]:
        """
        Create a map of stage dependencies ensuring correct processing order.

        Returns dependencies that must be completed before a stage can begin.
        This helps ensure sequential and logical processing of stages.

        Returns:
            Dict mapping stage names to their prerequisite stages
        """
        dependencies = {}
        for stage in ProcessingStage:
            dependencies[stage.value] = [
                prev_stage.value for prev_stage in ProcessingStage
                if stage in self.stage_transitions.get(prev_stage, [])
            ]
        return dependencies

    async def _start_stage_processing(self, control_point: ControlPoint) -> None:
        """Start processing for a stage"""
        try:
            # Get department chain
            chain = self.department_chains.get(control_point.department)
            if not chain:
                raise ValueError(f"No chain for department: {control_point.department}")

            # Create stage start message
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

            # Update pipeline progress
            if control_point.pipeline_id:
                await self._update_pipeline_progress(
                    pipeline_id=control_point.pipeline_id,
                    stage=control_point.stage,
                    progress=0.0
                )

            # Notify frontend
            await self._notify_frontend(
                pipeline_id=control_point.pipeline_id,
                notification_type='stage_started',
                data={
                    'stage': control_point.stage.value,
                    'department': control_point.department
                }
            )

            # Start processing
            await self.message_broker.publish(message)

        except Exception as e:
            logger.error(f"Stage start failed: {str(e)}")
            await self._handle_stage_error(control_point, str(e))

    async def _handle_stage_completion(self, control_point: ControlPoint) -> None:
        """Handle stage completion"""
        try:
            # Update statuses
            control_point.status = ProcessingStatus.COMPLETED
            control_point.updated_at = datetime.utcnow()

            # Update pipeline progress
            if control_point.pipeline_id:
                await self._update_pipeline_progress(
                    pipeline_id=control_point.pipeline_id,
                    stage=control_point.stage,
                    progress=1.0
                )

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

            # Notify frontend
            await self._notify_frontend(
                pipeline_id=control_point.pipeline_id,
                notification_type='stage_completed',
                data={
                    'stage': control_point.stage.value,
                    'requires_decision': control_point.requires_decision,
                    'next_stage': next_stage.value if next_stage else None
                }
            )

        except Exception as e:
            logger.error(f"Stage completion failed: {str(e)}")
            await self._handle_stage_error(control_point, str(e))

    async def _handle_pipeline_completion(self, control_point: ControlPoint) -> None:
        """Handle pipeline completion"""
        try:
            pipeline = self.active_pipelines.get(control_point.pipeline_id)
            if not pipeline:
                return

            # Update pipeline status
            pipeline.status = ProcessingStatus.COMPLETED

            # Create completion summary
            summary = self._create_pipeline_summary(pipeline)

            # Create completion message
            message = ProcessingMessage(
                message_type=MessageType.PIPELINE_CREATE_COMPLETE,
                content={
                    'pipeline_id': control_point.pipeline_id,
                    'final_stage': control_point.stage.value,
                    'completion_time': datetime.utcnow().isoformat(),
                    'summary': summary
                },
                source_identifier=self.module_identifier
            )

            # Notify completion
            await self.message_broker.publish(message)

            # Notify frontend
            await self._notify_frontend(
                pipeline_id=control_point.pipeline_id,
                notification_type='pipeline_completed',
                data={'summary': summary}
            )

            # Start cleanup
            await self._cleanup_pipeline(control_point.pipeline_id)

        except Exception as e:
            logger.error(f"Pipeline completion failed: {str(e)}")
            await self._handle_flow_error(
                ProcessingMessage(content={'pipeline_id': control_point.pipeline_id}),
                error=e
            )

    async def _register_department_chains(self):
        """
        Register processing department chains with unique module identifiers.

        Each department has a manager, handler, and processor that work together
        to process data through a specific stage of the pipeline.
        """
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
            await self.message_broker.register_processing_chain(
                chain_id, manager, handler, processor
            )

    # -------------------------------------------------------------------------
    # ERROR HANDLING & CLEANUP
    # -------------------------------------------------------------------------

    async def _handle_flow_error(
            self,
            message: ProcessingMessage,
            error: Optional[Exception] = None
    ) -> None:
        """Handle flow-level errors"""
        try:
            pipeline_id = message.content.get('pipeline_id')

            # Find affected control point
            control_point = next(
                (cp for cp in self.active_control_points.values()
                 if cp.pipeline_id == pipeline_id),
                None
            )

            if control_point:
                # Update control point status
                control_point.status = ProcessingStatus.FAILED
                control_point.metadata['error'] = {
                    'message': str(error) if error else "Flow error",
                    'timestamp': datetime.utcnow().isoformat()
                }

                # Update pipeline status
                pipeline = self.active_pipelines.get(pipeline_id)
                if pipeline:
                    pipeline.status = ProcessingStatus.FAILED

                # Notify frontend
                await self._notify_frontend(
                    pipeline_id=pipeline_id,
                    notification_type='error',
                    data={
                        'error': str(error) if error else "Flow error",
                        'stage': control_point.stage.value,
                        'recoverable': self._is_error_recoverable(error)
                    }
                )

        except Exception as e:
            logger.error(f"Error handling failed: {str(e)}")

    #..................................................................................................
    # Helper Methods
    #..................................................................................................
    # 1. Stage management
    def _determine_next_stage(
            self,
            control_point: ControlPoint
    ) -> Optional[ProcessingStage]:
        """Determine next stage in pipeline"""
        try:
            current_stage = control_point.stage
            next_stages = self.stage_transitions.get(current_stage, [])

            if not next_stages:
                return None

            # Consider stage dependencies
            pipeline = self.active_pipelines.get(control_point.pipeline_id)
            if not pipeline:
                return next_stages[0]

            dependencies = pipeline.stage_dependencies

            for stage in next_stages:
                stage_deps = dependencies.get(stage.value, [])
                if all(dep in pipeline.completed_stages for dep in stage_deps):
                    return stage

            return next_stages[0]

        except Exception as e:
            logger.error(f"Next stage determination failed: {str(e)}")
            return None

    async def _proceed_to_stage(
            self,
            control_point: ControlPoint,
            next_stage: ProcessingStage,
            metadata: Dict[str, Any]
    ) -> None:
        """Proceed to next stage"""
        try:
            # Archive current control point
            await self._archive_control_point(control_point)

            # Create control point for next stage
            await self.create_control_point(
                stage=next_stage,
                pipeline_id=control_point.pipeline_id,
                metadata={
                    **control_point.metadata,
                    **metadata,
                    'previous_stage': control_point.stage.value
                },
                staging_reference=control_point.staging_reference,
                parent_control_point=control_point.id
            )

        except Exception as e:
            logger.error(f"Stage transition failed: {str(e)}")
            raise

    # 2. Control Point Management
    async def _retry_stage(
            self,
            control_point: ControlPoint,
            target_stage: ProcessingStage,
            metadata: Dict[str, Any]
    ) -> None:
        """Retry a specific stage"""
        try:
            # Archive current control point
            await self._archive_control_point(control_point)

            # Count previous retries
            retry_count = sum(
                1 for cp in self.control_point_history.get(control_point.pipeline_id, [])
                if cp.stage == target_stage
            )

            # Create new control point for retry
            await self.create_control_point(
                stage=target_stage,
                pipeline_id=control_point.pipeline_id,
                metadata={
                    **control_point.metadata,
                    **metadata,
                    'retry_count': retry_count + 1,
                    'retry_reason': metadata.get('reason', 'User requested retry')
                },
                staging_reference=control_point.staging_reference,
                parent_control_point=control_point.id
            )

        except Exception as e:
            logger.error(f"Stage retry failed: {str(e)}")
            raise

    async def _archive_control_point(self, control_point: ControlPoint) -> None:
        """Archive a control point"""
        try:
            # Add to history
            if control_point.pipeline_id:
                history = self.control_point_history.setdefault(
                    control_point.pipeline_id, []
                )
                history.append(control_point)

            # Remove from active
            if control_point.id in self.active_control_points:
                del self.active_control_points[control_point.id]

            # Update pipeline
            pipeline = self.active_pipelines.get(control_point.pipeline_id)
            if pipeline:
                pipeline.completed_stages.append(control_point.stage.value)

        except Exception as e:
            logger.error(f"Control point archival failed: {str(e)}")
            raise

    def _is_error_recoverable(self, error: Optional[Exception]) -> bool:
        """Determine if error is recoverable"""
        if not error:
            return False

        # List of recoverable error types
        recoverable_errors = (
            TimeoutError,
            ConnectionError,
            asyncio.TimeoutError
        )

        return isinstance(error, recoverable_errors)

    # 3. Pipeline Management
    def _create_pipeline_summary(self, pipeline: PipelineContext) -> Dict[str, Any]:
        """Create detailed pipeline summary"""
        try:
            current_time = datetime.utcnow()
            duration = (current_time - pipeline.created_at).total_seconds()

            # Gather stage statistics
            stage_stats = {}
            for cp in self.control_point_history.get(pipeline.pipeline_id, []):
                stage_stats[cp.stage.value] = {
                    'attempts': stage_stats.get(cp.stage.value, {}).get('attempts', 0) + 1,
                    'duration': cp.updated_at - cp.created_at,
                    'decisions': len(cp.decisions)
                }

            return {
                'pipeline_id': pipeline.pipeline_id,
                'status': pipeline.status.value,
                'duration_seconds': duration,
                'stages_completed': pipeline.completed_stages,
                'stage_statistics': stage_stats,
                'total_decisions': sum(
                    stats.get('decisions', 0)
                    for stats in stage_stats.values()
                ),
                'component_states': pipeline.component_states,
                'final_progress': pipeline.progress,
                'error_count': len([
                    cp for cp in self.control_point_history.get(pipeline.pipeline_id, [])
                    if cp.status == ProcessingStatus.FAILED
                ])
            }

        except Exception as e:
            logger.error(f"Pipeline summary creation failed: {str(e)}")
            return {
                'pipeline_id': pipeline.pipeline_id,
                'status': 'error',
                'error': str(e)
            }

    async def _cleanup_pipeline(self, pipeline_id: str) -> None:
        """Clean up pipeline resources"""
        try:
            # Archive all active control points
            active_points = [
                cp for cp in self.active_control_points.values()
                if cp.pipeline_id == pipeline_id
            ]
            for cp in active_points:
                await self._archive_control_point(cp)

            # Clear from active pipelines
            if pipeline_id in self.active_pipelines:
                pipeline = self.active_pipelines.pop(pipeline_id)

                # Clear user session if exists
                if 'user_id' in pipeline.metadata:
                    user_id = pipeline.metadata['user_id']
                    if pipeline_id in self.user_sessions.get(user_id, set()):
                        self.user_sessions[user_id].remove(pipeline_id)

            # Notify cleanup
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_CLEANUP_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

            # Add this new block to indicate cleanup completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_CLEANUP_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'timestamp': datetime.utcnow().isoformat(),
                        'status': 'success'
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Pipeline cleanup failed: {str(e)}")
            raise

    # 4. Progress Tracking
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
            completed_stages = len(pipeline.completed_stages)
            current_progress = progress if stage.value not in pipeline.completed_stages else 1.0

            overall_progress = (
                (completed_stages + current_progress) / total_stages
                if total_stages > 0 else 0
            )

            pipeline.progress['overall'] = overall_progress

            # Notify progress update
            await self._notify_frontend(
                pipeline_id=pipeline_id,
                notification_type='progress_update',
                data={
                    'stage': stage.value,
                    'stage_progress': progress,
                    'overall_progress': overall_progress
                }
            )

        except Exception as e:
            logger.error(f"Progress update failed: {str(e)}")

    async def create_control_point(
            self,
            stage: ProcessingStage,
            pipeline_id: str,
            metadata: Dict[str, Any],
            staging_reference: Optional[str] = None,
            requires_decision: bool = True,
            parent_control_point: Optional[str] = None
    ) -> str:
        """Create a new control point in the processing pipeline"""
        try:
            # Get department for this stage
            department = self.department_sequence.get(stage, 'service')

            # Get processing chain for department
            chain = self.department_chains.get(department)
            if not chain:
                raise ValueError(f"No processing chain found for department: {department}")

            # Create a new control point
            control_point = ControlPoint(
                stage=stage,
                department=department,
                assigned_module=chain['manager'],
                pipeline_id=pipeline_id,
                metadata=metadata,
                staging_reference=staging_reference,
                requires_decision=requires_decision,
                parent_control_point=parent_control_point,
                next_stages=self.stage_transitions.get(stage, [])
            )

            # Add to active control points
            self.active_control_points[control_point.id] = control_point

            # Start stage processing
            await self._start_stage_processing(control_point)

            # Publish control point creation event
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.CONTROL_POINT_CREATED,
                    content={
                        'control_point_id': control_point.id,
                        'pipeline_id': pipeline_id,
                        'stage': stage.value,
                        'department': department
                    },
                    source_identifier=self.module_identifier
                )
            )

            return control_point.id

        except Exception as e:
            logger.error(f"Control point creation failed: {str(e)}")
            raise

    def _prepare_decision_options(self, stage: ProcessingStage) -> List[Dict[str, Any]]:
        """
        Prepare decision options based on processing stage

        Args:
            stage (ProcessingStage): Current processing stage

        Returns:
            List of decision options with metadata
        """
        stage_decision_map = {
            ProcessingStage.QUALITY_CHECK: [
                {
                    'type': 'approve',
                    'label': 'Proceed with Data',
                    'description': 'No significant quality issues found'
                },
                {
                    'type': 'rework',
                    'label': 'Request Data Correction',
                    'description': 'Quality issues require resolution'
                }
            ],
            ProcessingStage.INSIGHT_GENERATION: [
                {
                    'type': 'approve',
                    'label': 'Accept Insights',
                    'description': 'Insights look valid and actionable'
                },
                {
                    'type': 'retry',
                    'label': 'Regenerate Insights',
                    'description': 'Current insights need refinement'
                }
            ],
            ProcessingStage.RECOMMENDATION: [
                {
                    'type': 'approve',
                    'label': 'Accept Recommendations',
                    'description': 'Recommendations seem appropriate'
                },
                {
                    'type': 'modify',
                    'label': 'Adjust Recommendations',
                    'description': 'Need slight modifications'
                },
                {
                    'type': 'reject',
                    'label': 'Reject Recommendations',
                    'description': 'Recommendations do not meet requirements'
                }
            ],
            ProcessingStage.USER_REVIEW: [
                {
                    'type': 'continue',
                    'label': 'Continue Processing',
                    'description': 'No further changes needed'
                },
                {
                    'type': 'restart',
                    'label': 'Restart Pipeline',
                    'description': 'Restart entire processing pipeline'
                }
            ]
        }

        return stage_decision_map.get(stage, [
            {
                'type': 'proceed',
                'label': 'Default Proceed',
                'description': 'Continue to next stage'
            }
        ])

    async def _handle_control_point_created(self, message: ProcessingMessage) -> None:
        """Handle control point creation event"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            control_point_id = message.content.get('control_point_id')
            stage = ProcessingStage(message.content.get('stage'))
            department = message.content.get('department')

            # Validate message
            if not all([pipeline_id, control_point_id, stage, department]):
                logger.warning("Incomplete control point creation message")
                return

            # Find the control point
            control_point = self.active_control_points.get(control_point_id)
            if not control_point:
                logger.warning(f"Control point not found: {control_point_id}")
                return

            # Update pipeline progress tracking
            pipeline = self.active_pipelines.get(pipeline_id)
            if pipeline:
                pipeline.component_states[department] = ProcessingStatus.PENDING.value

            logger.info(f"Control point created: {control_point_id} at stage {stage}")

        except Exception as e:
            logger.error(f"Control point creation handling failed: {str(e)}")

    async def _handle_stage_complete(self, message: ProcessingMessage) -> None:
        """Handle stage completion event"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            control_point_id = message.content.get('control_point_id')
            stage = ProcessingStage(message.content.get('stage'))

            # Find control point
            control_point = next(
                (cp for cp in self.active_control_points.values()
                 if cp.id == control_point_id and cp.pipeline_id == pipeline_id),
                None
            )

            if not control_point:
                logger.warning(f"No matching control point for completion: {control_point_id}")
                return

            # Handle stage completion
            await self._handle_stage_completion(control_point)

        except Exception as e:
            logger.error(f"Stage completion handling failed: {str(e)}")

    async def _handle_stage_error(
            self,
            control_point: ControlPoint,
            error_message: str
    ) -> None:
        """Handle stage processing errors"""
        try:
            # Update control point status
            control_point.status = ProcessingStatus.FAILED
            control_point.metadata['error'] = {
                'message': error_message,
                'timestamp': datetime.utcnow().isoformat()
            }

            # Update pipeline status
            pipeline = self.active_pipelines.get(control_point.pipeline_id)
            if pipeline:
                pipeline.status = ProcessingStatus.FAILED

            # Notify frontend about error
            await self._notify_frontend(
                pipeline_id=control_point.pipeline_id,
                notification_type='stage_error',
                data={
                    'stage': control_point.stage.value,
                    'error': error_message,
                    'recoverable': self._is_error_recoverable(Exception(error_message))
                }
            )

            # Attempt error recovery or rollback
            if self._is_error_recoverable(Exception(error_message)):
                await self._retry_stage(
                    control_point,
                    control_point.stage,
                    {'error_recovery': True, 'original_error': error_message}
                )

        except Exception as e:
            logger.error(f"Stage error handling failed: {str(e)}")

    async def _handle_staged_data(self, message: ProcessingMessage) -> None:
        """Handle data staging event"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            staging_reference = message.content.get('staging_reference')
            data_details = message.content.get('data_details', {})

            # Update staging metadata for pipeline
            pipeline = self.active_pipelines.get(pipeline_id)
            if pipeline:
                pipeline.metadata['staged_data'] = {
                    'reference': staging_reference,
                    'details': data_details
                }

            # Create a control point for next processing stage
            await self.create_control_point(
                stage=ProcessingStage.VALIDATION,
                pipeline_id=pipeline_id,
                metadata={'staged_data': data_details},
                staging_reference=staging_reference
            )

        except Exception as e:
            logger.error(f"Staged data handling failed: {str(e)}")

    async def _handle_staged_output(self, message: ProcessingMessage) -> None:
        """Handle output staging event"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            staging_reference = message.content.get('staging_reference')
            output_details = message.content.get('output_details', {})

            # Update pipeline metadata with staged output
            pipeline = self.active_pipelines.get(pipeline_id)
            if pipeline:
                pipeline.metadata['staged_output'] = {
                    'reference': staging_reference,
                    'details': output_details
                }

            # Optional: trigger next processing stage or notify completion
            logger.info(f"Output staged for pipeline {pipeline_id}")

        except Exception as e:
            logger.error(f"Staged output handling failed: {str(e)}")

    async def _handle_user_decision(self, message: ProcessingMessage) -> None:
        """Process user decision submitted through message broker"""
        try:
            control_point_id = message.content.get('control_point_id')
            decision = message.content.get('decision')
            user_id = message.content.get('user_id')

            if not all([control_point_id, decision, user_id]):
                logger.warning("Incomplete user decision message")
                return

            # Process the decision
            await self.process_decision(control_point_id, decision)

        except Exception as e:
            logger.error(f"User decision handling failed: {str(e)}")

    async def _handle_user_action(self, message: ProcessingMessage) -> None:
        """Handle generic user action request"""
        try:
            action_type = message.content.get('action_type')
            pipeline_id = message.content.get('pipeline_id')
            user_id = message.content.get('user_id')
            action_details = message.content.get('details', {})

            if not all([action_type, pipeline_id, user_id]):
                logger.warning("Incomplete user action message")
                return

            # Map actions to specific handlers
            action_handlers = {
                'retry_stage': self._retry_stage,
                'modify_recommendation': self._modify_recommendation,
                'escalate_issue': self._escalate_issue
            }

            handler = action_handlers.get(action_type)
            if handler:
                await handler(pipeline_id, user_id, action_details)
            else:
                logger.warning(f"Unhandled user action: {action_type}")

        except Exception as e:
            logger.error(f"User action handling failed: {str(e)}")

    async def _modify_recommendation(
            self,
            pipeline_id: str,
            user_id: str,
            action_details: Dict[str, Any]
    ) -> None:
        """
        Modify recommendations for a specific pipeline

        Args:
            pipeline_id (str): Identifier of the pipeline
            user_id (str): User initiating the modification
            action_details (Dict[str, Any]): Details of modification
        """
        try:
            # Validate user access
            if pipeline_id not in self.user_sessions.get(user_id, set()):
                logger.warning(f"Unauthorized recommendation modification attempt by user {user_id}")
                return

            # Find the active recommendation control point
            control_point = next(
                (cp for cp in self.active_control_points.values()
                 if cp.pipeline_id == pipeline_id and
                 cp.stage == ProcessingStage.RECOMMENDATION),
                None
            )

            if not control_point:
                logger.warning(f"No active recommendation stage found for pipeline {pipeline_id}")
                return

            # Extract current recommendations
            current_recommendations = control_point.metadata.get('recommendations', [])

            # Apply modifications based on action details
            modified_recommendations = self._apply_recommendation_modifications(
                current_recommendations,
                action_details
            )

            # Update control point metadata
            control_point.metadata['recommendations'] = modified_recommendations
            control_point.metadata['modification_history'] = {
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'original_recommendations': current_recommendations,
                'modification_details': action_details
            }

            # Notify recommendation service about modifications
            modification_message = ProcessingMessage(
                message_type=MessageType.RECOMMENDATION_VALIDATE_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'modified_recommendations': modified_recommendations,
                    'modification_details': action_details,
                    'user_id': user_id
                },
                source_identifier=self.module_identifier
            )

            await self.message_broker.publish(modification_message)

            # Notify frontend
            await self._notify_frontend(
                pipeline_id=pipeline_id,
                notification_type='recommendation_modified',
                data={
                    'original_count': len(current_recommendations),
                    'modified_count': len(modified_recommendations),
                    'modification_type': action_details.get('type', 'unknown')
                }
            )

            logger.info(f"Recommendations modified for pipeline {pipeline_id} by user {user_id}")

        except Exception as e:
            logger.error(f"Recommendation modification failed: {str(e)}")
            await self._handle_flow_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                error=e
            )

    def _apply_recommendation_modifications(
            self,
            recommendations: List[Dict[str, Any]],
            modification_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply modifications to recommendations

        Args:
            recommendations (List[Dict[str, Any]]): Original recommendations
            modification_details (Dict[str, Any]): Modification instructions

        Returns:
            List[Dict[str, Any]]: Modified recommendations
        """
        modification_type = modification_details.get('type', 'default')

        modification_strategies = {
            'filter': self._filter_recommendations,
            'prioritize': self._prioritize_recommendations,
            'remove': self._remove_recommendations,
            'add': self._add_recommendations,
            'default': lambda r, d: r  # No modification
        }

        strategy = modification_strategies.get(modification_type, modification_strategies['default'])
        return strategy(recommendations, modification_details)


    def _filter_recommendations(
            self,
            recommendations: List[Dict[str, Any]],
            filter_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Filter recommendations based on criteria

        Args:
            recommendations (List[Dict[str, Any]]): Original recommendations
            filter_details (Dict[str, Any]): Filtering criteria

        Returns:
            List[Dict[str, Any]]: Filtered recommendations
        """
        criteria = filter_details.get('criteria', {})

        def matches_criteria(recommendation: Dict[str, Any]) -> bool:
            return all(
                recommendation.get(key) == value
                for key, value in criteria.items()
            )

        return [r for r in recommendations if matches_criteria(r)]


    def _prioritize_recommendations(
            self,
            recommendations: List[Dict[str, Any]],
            prioritization_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Prioritize recommendations based on specified criteria

        Args:
            recommendations (List[Dict[str, Any]]): Original recommendations
            prioritization_details (Dict[str, Any]): Prioritization instructions

        Returns:
            List[Dict[str, Any]]: Prioritized recommendations
        """
        sort_key = prioritization_details.get('sort_by', 'score')
        reverse = prioritization_details.get('order', 'descending') == 'descending'

        return sorted(
            recommendations,
            key=lambda r: r.get(sort_key, 0),
            reverse=reverse
        )


    def _remove_recommendations(
            self,
            recommendations: List[Dict[str, Any]],
            removal_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Remove specific recommendations

        Args:
            recommendations (List[Dict[str, Any]]): Original recommendations
            removal_details (Dict[str, Any]): Removal instructions

        Returns:
            List[Dict[str, Any]]: Recommendations after removal
        """
        removal_criteria = removal_details.get('criteria', {})

        def should_remove(recommendation: Dict[str, Any]) -> bool:
            return all(
                recommendation.get(key) == value
                for key, value in removal_criteria.items()
            )

        return [r for r in recommendations if not should_remove(r)]


    def _add_recommendations(
            self,
            recommendations: List[Dict[str, Any]],
            addition_details: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Add new recommendations

        Args:
            recommendations (List[Dict[str, Any]]): Original recommendations
            addition_details (Dict[str, Any]): Addition instructions

        Returns:
            List[Dict[str, Any]]: Recommendations after addition
        """
        new_recommendations = addition_details.get('recommendations', [])
        return recommendations + new_recommendations


    async def _escalate_issue(
            self,
            pipeline_id: str,
            user_id: str,
            escalation_details: Dict[str, Any]
    ) -> None:
        """
        Escalate an issue in the pipeline

        Args:
            pipeline_id (str): Identifier of the pipeline
            user_id (str): User initiating the escalation
            escalation_details (Dict[str, Any]): Escalation information
        """
        try:
            # Validate user access
            if pipeline_id not in self.user_sessions.get(user_id, set()):
                logger.warning(f"Unauthorized issue escalation attempt by user {user_id}")
                return

            # Find the current control point
            current_control_point = next(
                (cp for cp in self.active_control_points.values()
                 if cp.pipeline_id == pipeline_id),
                None
            )

            if not current_control_point:
                logger.warning(f"No active control point found for pipeline {pipeline_id}")
                return

            # Create escalation message
            escalation_message = ProcessingMessage(
                message_type=MessageType.USER_INTERVENTION_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'stage': current_control_point.stage.value,
                    'escalation_details': escalation_details,
                    'user_id': user_id
                },
                source_identifier=self.module_identifier
            )

            # Publish escalation message
            await self.message_broker.publish(escalation_message)

            # Notify frontend
            await self._notify_frontend(
                pipeline_id=pipeline_id,
                notification_type='issue_escalated',
                data={
                    'stage': current_control_point.stage.value,
                    'escalation_type': escalation_details.get('type', 'general'),
                    'escalation_reason': escalation_details.get('reason', 'Unspecified')
                }
            )

            logger.info(f"Issue escalated for pipeline {pipeline_id} by user {user_id}")

        except Exception as e:
            logger.error(f"Issue escalation failed: {str(e)}")
            await self._handle_flow_error(
                ProcessingMessage(content={'pipeline_id': pipeline_id}),
                error=e
            )

    async def process_decision(
            self,
            control_point_id: str,
            decision: Dict[str, Any]
    ) -> bool:
        """
        Process a decision for a specific control point

        Args:
            control_point_id (str): Identifier of the control point
            decision (Dict[str, Any]): Decision details

        Returns:
            bool: Whether the decision was processed successfully
        """
        try:
            # Find the control point
            control_point = self.active_control_points.get(control_point_id)
            if not control_point:
                logger.warning(f"Control point not found: {control_point_id}")
                return False

            # Validate decision
            if not self._validate_decision(control_point, decision):
                logger.warning(f"Invalid decision for control point: {control_point_id}")
                return False

            # Record the decision
            control_point.decisions.append(decision)
            control_point.updated_at = datetime.utcnow()

            # Determine next action based on decision
            next_action = self._determine_decision_action(control_point, decision)

            # Execute the action
            await self._execute_decision_action(control_point, next_action)

            return True

        except Exception as e:
            logger.error(f"Decision processing failed: {str(e)}")
            await self._handle_flow_error(
                ProcessingMessage(content={'pipeline_id': control_point.pipeline_id}),
                error=e
            )
            return False


    def _validate_decision(
            self,
            control_point: ControlPoint,
            decision: Dict[str, Any]
    ) -> bool:
        """
        Validate the decision against control point constraints

        Args:
            control_point (ControlPoint): Current control point
            decision (Dict[str, Any]): Decision to validate

        Returns:
            bool: Whether the decision is valid
        """
        # Check if decision type is valid for the stage
        valid_decision_types = {
            ProcessingStage.QUALITY_CHECK: ['approve', 'rework'],
            ProcessingStage.INSIGHT_GENERATION: ['approve', 'retry'],
            ProcessingStage.RECOMMENDATION: ['approve', 'modify', 'reject'],
            ProcessingStage.USER_REVIEW: ['continue', 'restart']
        }

        decision_type = decision.get('type')
        allowed_types = valid_decision_types.get(control_point.stage, [])

        return (
                decision_type in allowed_types and
                control_point.status == ProcessingStatus.AWAITING_DECISION
        )


    def _determine_decision_action(
            self,
            control_point: ControlPoint,
            decision: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Determine the next action based on the decision

        Args:
            control_point (ControlPoint): Current control point
            decision (Dict[str, Any]): Decision details

        Returns:
            Dict[str, Any]: Action to take
        """
        decision_type = decision.get('type')

        # Default action is to proceed to next stage
        action = {
            'type': 'proceed',
            'target_stage': None,
            'metadata': {}
        }

        # Map decision types to specific actions
        decision_actions = {
            'approve': lambda: action,
            'rework': lambda: {
                'type': 'retry',
                'target_stage': ProcessingStage.QUALITY_CHECK,
                'metadata': {'reason': 'Rework required'}
            },
            'retry': lambda: {
                'type': 'retry',
                'target_stage': ProcessingStage.INSIGHT_GENERATION,
                'metadata': {'reason': 'Regenerate insights'}
            },
            'modify': lambda: {
                'type': 'modify',
                'target_stage': ProcessingStage.RECOMMENDATION,
                'metadata': {'modification_details': decision.get('details', {})}
            },
            'reject': lambda: {
                'type': 'reject',
                'metadata': {'reason': 'Recommendations rejected'}
            },
            'continue': lambda: action,
            'restart': lambda: {
                'type': 'restart',
                'target_stage': ProcessingStage.RECEPTION,
                'metadata': {'reason': 'Pipeline restart'}
            }
        }

        action_func = decision_actions.get(decision_type, lambda: action)
        return action_func()


    async def _execute_decision_action(
            self,
            control_point: ControlPoint,
            action: Dict[str, Any]
    ) -> None:
        """
        Execute the determined action for a decision

        Args:
            control_point (ControlPoint): Current control point
            action (Dict[str, Any]): Action to execute
        """
        try:
            action_type = action.get('type')

            if action_type == 'proceed':
                # Automatically proceed to next stage
                next_stage = self._determine_next_stage(control_point)
                if next_stage:
                    await self._proceed_to_stage(
                        control_point,
                        next_stage,
                        action.get('metadata', {})
                    )
                else:
                    await self._handle_pipeline_completion(control_point)

            elif action_type == 'retry':
                # Retry a specific stage
                target_stage = action.get('target_stage', control_point.stage)
                await self._retry_stage(
                    control_point,
                    target_stage,
                    action.get('metadata', {})
                )

            elif action_type == 'modify':
                # Handle recommendation modification
                await self._modify_recommendation(
                    control_point.pipeline_id,
                    control_point.user_id,
                    action.get('metadata', {})
                )

            elif action_type == 'reject':
                # Handle rejection (could trigger specific workflow)
                await self._handle_pipeline_rejection(control_point)

            elif action_type == 'restart':
                # Restart the entire pipeline
                await self.create_pipeline(
                    pipeline_id=control_point.pipeline_id,
                    initial_metadata=control_point.metadata
                )

        except Exception as e:
            logger.error(f"Decision action execution failed: {str(e)}")
            await self._handle_flow_error(
                ProcessingMessage(content={'pipeline_id': control_point.pipeline_id}),
                error=e
            )


    async def _handle_pipeline_rejection(self, control_point: ControlPoint) -> None:
        """
        Handle pipeline rejection

        Args:
            control_point (ControlPoint): Current control point
        """
        try:
            # Update pipeline status
            pipeline = self.active_pipelines.get(control_point.pipeline_id)
            if pipeline:
                pipeline.status = ProcessingStatus.CANCELLED

            # Notify frontend
            await self._notify_frontend(
                pipeline_id=control_point.pipeline_id,
                notification_type='pipeline_rejected',
                data={
                    'stage': control_point.stage.value,
                    'reason': control_point.metadata.get('rejection_reason', 'Unspecified')
                }
            )

            # Cleanup pipeline
            await self._cleanup_pipeline(control_point.pipeline_id)

        except Exception as e:
            logger.error(f"Pipeline rejection handling failed: {str(e)}")
            await self._handle_flow_error(
                ProcessingMessage(content={'pipeline_id': control_point.pipeline_id}),
                error=e
            )