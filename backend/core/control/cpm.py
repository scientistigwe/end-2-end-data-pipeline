# backend/core/control/cpm.py

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Tuple
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


from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import asyncio
import psutil
import logging


class AlertSeverity(Enum):
    """Severity levels for monitoring alerts"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class MonitoringAlert:
    """Structure for monitoring alerts"""
    alert_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    severity: AlertSeverity = AlertSeverity.INFO
    source: str = "system_monitor"
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary representation"""
        return {
            'alert_id': self.alert_id,
            'severity': self.severity.value,
            'source': self.source,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context
        }

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
        
        # Frontend communication tracking
        self.frontend_sessions: Dict[str, FrontendCPMContext] = {}
        self.pending_commands: Dict[str, List[Dict[str, Any]]] = {}
        
        # Processor tracking
        self.registered_processors: Dict[str, ProcessorContext] = {}
        self.processor_capabilities: Dict[str, Set[str]] = {}

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
            # Register message handlers for all domains
            await self.message_broker.subscribe(
                module_identifier=self.module_identifier,
                message_patterns=[
                    "control.*",
                    "*.complete",
                    "*.error",
                    "decision.required",
                    "quality.issues.detected",
                    "insight.generated",
                    "recommendation.ready",
                    "frontend.cpm.*",  # Frontend direct communication
                    "processor.*"      # Processor communication
                ],
                callback=self._handle_control_message
            )

            # Register processing chains
            await self._register_department_chains()

            # Start background monitoring tasks
            self.tasks.extend([
                asyncio.create_task(self._monitor_process_timeouts()),
                asyncio.create_task(self._monitor_resource_usage()),
                asyncio.create_task(self._monitor_component_health()),
                asyncio.create_task(self._monitor_frontend_sessions()),
                asyncio.create_task(self._monitor_processor_health())
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

    async def _check_resource_metrics(self):
        """
        Monitor system resource usage and publish alerts if thresholds are exceeded.
        """
        try:
            # Collect system resource metrics
            cpu_usage = psutil.cpu_percent()
            memory_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage('/').percent

            # Create metrics object
            metrics = {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage
            }

            # Create alerts for critical thresholds
            alerts = []
            if cpu_usage > 90:
                alerts.append(MonitoringAlert(
                    severity=AlertSeverity.CRITICAL,
                    source='system_monitor',
                    message=f'High CPU usage detected: {cpu_usage}%',
                    context={'cpu_usage': cpu_usage}
                ))

            if memory_usage > 90:
                alerts.append(MonitoringAlert(
                    severity=AlertSeverity.CRITICAL,
                    source='system_monitor',
                    message=f'High memory usage detected: {memory_usage}%',
                    context={'memory_usage': memory_usage}
                ))

            if disk_usage > 90:
                alerts.append(MonitoringAlert(
                    severity=AlertSeverity.CRITICAL,
                    source='system_monitor',
                    message=f'High disk usage detected: {disk_usage}%',
                    context={'disk_usage': disk_usage}
                ))

            # Publish alerts (assuming self.message_broker exists)
            for alert in alerts:
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_ALERT_GENERATE,
                        content={
                            'alert': alert.to_dict(),
                            'timestamp': datetime.utcnow().isoformat()
                        },
                        source_identifier=self.module_identifier
                    )
                )

            # Log metrics
            logger.info(f"System Resource Metrics: {metrics}")

        except Exception as e:
            logger.error(f"Resource metrics check failed: {str(e)}")

    async def _check_component_health(self):
        """
        Check health of registered components across different departments.
        """
        try:
            # Track health check results
            health_status = {}

            # Iterate through registered department chains
            for dept, chain in self.department_chains.items():
                # Prepare health check message
                health_check_message = ProcessingMessage(
                    message_type=MessageType.MONITORING_HEALTH_CHECK,
                    content={
                        'department': dept,
                        'components': [
                            chain['manager'].component_name,
                            chain['handler'].component_name,
                            chain['processor'].component_name
                        ]
                    },
                    source_identifier=self.module_identifier,
                    target_identifier=chain['manager']
                )

                try:
                    # Send health check request
                    response = await self.message_broker.request_response(health_check_message)

                    # Interpret health status
                    status = response.get('status', 'unknown')
                    details = response.get('details', {})

                    health_status[dept] = {
                        'overall_status': status,
                        'component_details': details
                    }

                except Exception as component_error:
                    # Handle individual component health check failure
                    health_status[dept] = {
                        'overall_status': 'error',
                        'error': str(component_error)
                    }
                    logger.error(f"Health check failed for {dept} department: {component_error}")

            # Identify and log critical health issues
            critical_components = [
                dept for dept, status in health_status.items()
                if status['overall_status'] != 'healthy'
            ]

            if critical_components:
                # Publish system alert for critical health issues
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_HEALTH_ALERT,
                        content={
                            'critical_components': critical_components,
                            'health_status': health_status,
                            'timestamp': datetime.utcnow().isoformat()
                        },
                        source_identifier=self.module_identifier
                    )
                )

            # Log overall health status
            logger.info(f"Component Health Status: {health_status}")

        except Exception as e:
            logger.error(f"Component health check failed: {str(e)}")

    async def _check_broker_connection(self):
        """
        Verify message broker connectivity and system communication channels.
        """
        try:
            # Generate a unique correlation ID for tracking
            correlation_id = str(uuid.uuid4())

            # Create a ping message
            ping_message = ProcessingMessage(
                message_type=MessageType.GLOBAL_HEALTH_CHECK,
                content={
                    'correlation_id': correlation_id,
                    'timestamp': datetime.utcnow().isoformat(),
                    'source': self.module_identifier.component_name
                },
                source_identifier=self.module_identifier,
                metadata=MessageMetadata(
                    correlation_id=correlation_id,
                    requires_response=True,
                    timeout_seconds=10  # 10-second timeout
                )
            )

            try:
                # Attempt to send and receive a response
                response = await self.message_broker.request_response(
                    ping_message,
                    timeout=10  # 10-second timeout
                )

                # Verify response integrity
                if (response and
                        response.get('correlation_id') == correlation_id and
                        response.get('status') == 'ok'):
                    logger.info("Message broker connection verified successfully")
                else:
                    raise ValueError("Invalid broker response")

            except asyncio.TimeoutError:
                # Handle timeout scenario
                await self._handle_broker_disconnection("Broker ping timed out")

        except Exception as e:
            # Handle connection verification failure
            await self._handle_broker_disconnection(str(e))

    async def _handle_broker_disconnection(self, error_message: str):
        """
        Handle message broker disconnection scenarios.
        """
        try:
            # Create a critical alert
            disconnection_alert = MonitoringAlert(
                severity=AlertSeverity.CRITICAL,
                source='broker_monitor',
                message=f'Message broker connection lost: {error_message}',
                context={'error': error_message}
            )

            # Publish disconnection alert
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_ALERT_GENERATE,
                    content={
                        'alert': disconnection_alert.to_dict(),
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

            # Log the disconnection
            logger.critical(f"Message broker disconnection detected: {error_message}")

        except Exception as recovery_error:
            logger.error(f"Broker disconnection handling failed: {recovery_error}")

    async def _handle_process_timeout(self, control_point: ControlPoint) -> None:
        """
        Handle timeout for a specific control point in the processing pipeline

        Args:
            control_point (ControlPoint): The control point that has timed out
        """
        try:
            # Update control point status to timeout
            control_point.status = ProcessingStatus.DECISION_TIMEOUT
            control_point.updated_at = datetime.utcnow()

            # Find the associated pipeline
            pipeline = self.active_pipelines.get(control_point.pipeline_id)
            if not pipeline:
                logger.warning(f"No pipeline found for timed-out control point: {control_point.id}")
                return

            # Create timeout alert
            timeout_alert = ProcessingMessage(
                message_type=MessageType.PIPELINE_STAGE_ERROR,
                content={
                    'pipeline_id': control_point.pipeline_id,
                    'control_point_id': control_point.id,
                    'stage': control_point.stage.value,
                    'error_type': 'timeout',
                    'timeout_duration': control_point.timeout_minutes,
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier,
                metadata=MessageMetadata(
                    correlation_id=str(uuid.uuid4()),
                    priority=3  # High priority
                )
            )

            # Publish timeout alert
            await self.message_broker.publish(timeout_alert)

            # Determine next action based on stage and timeout
            recovery_action = self._determine_timeout_recovery_action(control_point)

            # Execute recovery action
            if recovery_action == 'retry':
                await self._retry_stage(
                    control_point,
                    control_point.stage,
                    {
                        'reason': 'stage_timeout',
                        'original_timeout_duration': control_point.timeout_minutes
                    }
                )
            elif recovery_action == 'escalate':
                await self._escalate_timeout(control_point)
            elif recovery_action == 'cancel':
                await self._cancel_pipeline(control_point)

            # Notify frontend about timeout
            await self._notify_frontend(
                pipeline_id=control_point.pipeline_id,
                notification_type='stage_timeout',
                data={
                    'stage': control_point.stage.value,
                    'timeout_duration': control_point.timeout_minutes,
                    'recovery_action': recovery_action
                }
            )

        except Exception as e:
            logger.error(f"Process timeout handling failed: {str(e)}")
            await self._handle_flow_error(
                ProcessingMessage(content={'pipeline_id': control_point.pipeline_id}),
                error=e
            )

    def _determine_timeout_recovery_action(self, control_point: ControlPoint) -> str:
        """
        Determine the appropriate recovery action for a timed-out control point

        Args:
            control_point (ControlPoint): The control point that has timed out

        Returns:
            str: Recovery action ('retry', 'escalate', or 'cancel')
        """
        # Define timeout recovery strategies for different stages
        timeout_strategies = {
            ProcessingStage.RECEPTION: 'retry',
            ProcessingStage.VALIDATION: 'retry',
            ProcessingStage.QUALITY_CHECK: 'escalate',
            ProcessingStage.CONTEXT_ANALYSIS: 'retry',
            ProcessingStage.INSIGHT_GENERATION: 'escalate',
            ProcessingStage.ADVANCED_ANALYTICS: 'escalate',
            ProcessingStage.DECISION_MAKING: 'escalate',
            ProcessingStage.RECOMMENDATION: 'escalate',
            ProcessingStage.REPORT_GENERATION: 'retry',
            ProcessingStage.USER_REVIEW: 'escalate'
        }

        # Get retry count to prevent infinite retries
        retry_count = sum(
            1 for cp in self.control_point_history.get(control_point.pipeline_id, [])
            if cp.stage == control_point.stage
        )

        # Determine action based on stage and retry count
        action = timeout_strategies.get(control_point.stage, 'cancel')

        # Limit retries to prevent infinite loops
        if action == 'retry' and retry_count >= 3:
            action = 'escalate'

        # If escalation is not possible, default to cancel
        if action == 'escalate' and retry_count >= 2:
            action = 'cancel'

        return action

    async def _escalate_timeout(self, control_point: ControlPoint) -> None:
        """
        Escalate a timed-out control point

        Args:
            control_point (ControlPoint): The control point to escalate
        """
        try:
            # Create escalation message
            escalation_message = ProcessingMessage(
                message_type=MessageType.USER_INTERVENTION_REQUEST,
                content={
                    'pipeline_id': control_point.pipeline_id,
                    'control_point_id': control_point.id,
                    'stage': control_point.stage.value,
                    'escalation_type': 'timeout',
                    'timeout_details': {
                        'duration': control_point.timeout_minutes,
                        'stage': control_point.stage.value
                    },
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier
            )

            # Publish escalation request
            await self.message_broker.publish(escalation_message)

            # Log escalation
            logger.warning(f"Timeout escalated for pipeline {control_point.pipeline_id} at stage {control_point.stage}")

        except Exception as e:
            logger.error(f"Timeout escalation failed: {str(e)}")

    async def _cancel_pipeline(self, control_point: ControlPoint) -> None:
        """
        Cancel the entire pipeline due to repeated timeouts

        Args:
            control_point (ControlPoint): The control point that triggered cancellation
        """
        try:
            # Update pipeline status
            pipeline = self.active_pipelines.get(control_point.pipeline_id)
            if pipeline:
                pipeline.status = ProcessingStatus.CANCELLED

            # Create cancellation message
            cancellation_message = ProcessingMessage(
                message_type=MessageType.PIPELINE_CANCEL_REQUEST,
                content={
                    'pipeline_id': control_point.pipeline_id,
                    'reason': 'repeated_timeouts',
                    'stage': control_point.stage.value,
                    'timestamp': datetime.utcnow().isoformat()
                },
                source_identifier=self.module_identifier
            )

            # Publish cancellation request
            await self.message_broker.publish(cancellation_message)

            # Cleanup pipeline resources
            await self._cleanup_pipeline(control_point.pipeline_id)

            # Log cancellation
            logger.error(f"Pipeline {control_point.pipeline_id} cancelled due to repeated timeouts")

        except Exception as e:
            logger.error(f"Pipeline cancellation failed: {str(e)}")

    async def _check_processing_health(self):
        """
        Comprehensive health check for processing components and pipelines

        Performs in-depth analysis of system processing health, tracking:
        - Active pipeline status
        - Component performance
        - Resource utilization
        - Processing bottlenecks
        """
        try:
            # Initialize health metrics container
            processing_health = {
                'overall_status': 'healthy',
                'active_pipelines': 0,
                'pipeline_states': {},
                'component_performance': {},
                'bottlenecks': [],
                'resource_constraints': {},
                'processing_issues': []
            }

            # Analyze active pipelines
            for pipeline_id, pipeline in self.active_pipelines.items():
                processing_health['active_pipelines'] += 1

                # Track pipeline state details
                processing_health['pipeline_states'][pipeline_id] = {
                    'current_stage': pipeline.current_stage.value if pipeline.current_stage else None,
                    'status': pipeline.status.value,
                    'progress': pipeline.progress.get('overall', 0),
                    'duration': (datetime.now() - pipeline.created_at).total_seconds()
                }

                # Identify potential bottlenecks
                if (pipeline.status == ProcessingStatus.IN_PROGRESS and
                        pipeline.progress.get('overall', 0) < 0.1):
                    processing_health['bottlenecks'].append({
                        'pipeline_id': pipeline_id,
                        'stage': pipeline.current_stage.value if pipeline.current_stage else 'unknown',
                        'duration_seconds': processing_health['pipeline_states'][pipeline_id]['duration']
                    })

            # Check component health across different departments
            for dept, chain in self.department_chains.items():
                try:
                    # Send health check request to each department
                    health_check_message = ProcessingMessage(
                        message_type=MessageType.MONITORING_HEALTH_CHECK,
                        content={
                            'department': dept,
                            'components': [
                                chain['manager'].component_name,
                                chain['handler'].component_name,
                                chain['processor'].component_name
                            ]
                        },
                        source_identifier=self.module_identifier,
                        target_identifier=chain['manager']
                    )

                    # Request component health details
                    response = await self.message_broker.request_response(
                        health_check_message,
                        timeout=10  # 10-second timeout
                    )

                    # Parse component performance
                    component_performance = response.get('performance', {})
                    processing_health['component_performance'][dept] = {
                        'status': response.get('status', 'unknown'),
                        'processing_time': component_performance.get('avg_processing_time'),
                        'error_rate': component_performance.get('error_rate', 0),
                        'throughput': component_performance.get('throughput')
                    }

                    # Identify performance issues
                    if (component_performance.get('error_rate', 0) > 0.1 or
                            component_performance.get('avg_processing_time', 0) > 5):
                        processing_health['processing_issues'].append({
                            'department': dept,
                            'issue_type': 'performance_degradation',
                            'details': component_performance
                        })

                except Exception as component_error:
                    processing_health['processing_issues'].append({
                        'department': dept,
                        'issue_type': 'health_check_failure',
                        'error': str(component_error)
                    })

            # Assess overall system health
            processing_health['overall_status'] = self._evaluate_processing_health(processing_health)

            # Publish health assessment
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.MONITORING_PROCESS_PROGRESS,
                    content={
                        'processing_health': processing_health,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

            # Generate alerts for critical issues
            await self._generate_processing_health_alerts(processing_health)

            # Log processing health
            logger.info(f"Processing Health Assessment: {processing_health}")

        except Exception as e:
            logger.error(f"Processing health check failed: {str(e)}")

    def _evaluate_processing_health(self, health_data: Dict[str, Any]) -> str:
        """
        Evaluate overall system processing health

        Args:
            health_data (Dict[str, Any]): Comprehensive health check data

        Returns:
            str: Overall health status ('healthy', 'degraded', 'critical')
        """
        # Criteria for health assessment
        if len(health_data.get('processing_issues', [])) > 3:
            return 'critical'

        if len(health_data.get('bottlenecks', [])) > 2:
            return 'degraded'

        # Check component performance
        for dept_performance in health_data.get('component_performance', {}).values():
            if (dept_performance.get('error_rate', 0) > 0.1 or
                    dept_performance.get('avg_processing_time', 0) > 5):
                return 'degraded'

        return 'healthy'

    async def _generate_processing_health_alerts(self, health_data: Dict[str, Any]) -> None:
        """
        Generate alerts based on processing health assessment

        Args:
            health_data (Dict[str, Any]): Comprehensive health check data
        """
        try:
            # Generate alerts for critical issues
            alerts = []

            # Alert for processing bottlenecks
            for bottleneck in health_data.get('bottlenecks', []):
                alerts.append(MonitoringAlert(
                    severity=AlertSeverity.HIGH,
                    source='processing_monitor',
                    message=f"Processing bottleneck detected in pipeline {bottleneck['pipeline_id']}",
                    context=bottleneck
                ))

            # Alert for performance issues
            for issue in health_data.get('processing_issues', []):
                severity = (
                    AlertSeverity.CRITICAL if issue['issue_type'] == 'health_check_failure'
                    else AlertSeverity.HIGH
                )
                alerts.append(MonitoringAlert(
                    severity=severity,
                    source='processing_monitor',
                    message=f"Performance issue in {issue.get('department', 'unknown')} department",
                    context=issue
                ))

            # Publish alerts
            for alert in alerts:
                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.MONITORING_ALERT_GENERATE,
                        content={
                            'alert': alert.to_dict(),
                            'timestamp': datetime.utcnow().isoformat()
                        },
                        source_identifier=self.module_identifier
                    )
                )

        except Exception as e:
            logger.error(f"Processing health alert generation failed: {str(e)}")

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

    async def _monitor_frontend_sessions(self):
        """Monitor frontend session health"""
        while True:
            try:
                current_time = datetime.now()
                for session_id, session in list(self.frontend_sessions.items()):
                    # Check for stale sessions
                    if (current_time - session.last_heartbeat).total_seconds() > 300:  # 5 minutes
                        await self._handle_stale_session(session_id)
                    
                    # Process pending commands
                    if session_id in self.pending_commands:
                        await self._process_pending_commands(session_id)

                await asyncio.sleep(30)  # Check every 30 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Frontend session monitoring failed: {str(e)}")
                await asyncio.sleep(30)

    async def _monitor_processor_health(self):
        """Monitor registered processors"""
        while True:
            try:
                current_time = datetime.now()
                for processor_id, context in list(self.registered_processors.items()):
                    # Check for stale processors
                    if (current_time - context.last_heartbeat).total_seconds() > 60:  # 1 minute
                        await self._handle_stale_processor(processor_id)
                    
                    # Check processor queue size
                    if context.message_queue_size > 1000:
                        await self._handle_processor_backpressure(processor_id)

                await asyncio.sleep(15)  # Check every 15 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Processor health monitoring failed: {str(e)}")
                await asyncio.sleep(15)

    async def _handle_stale_session(self, session_id: str) -> None:
        """Handle stale frontend session"""
        try:
            session = self.frontend_sessions[session_id]
            # Notify frontend about session timeout
            await self._notify_frontend(
                session.pipeline_id,
                "session_timeout",
                {"session_id": session_id}
            )
            # Cleanup session
            del self.frontend_sessions[session_id]
            if session_id in self.pending_commands:
                del self.pending_commands[session_id]
        except Exception as e:
            logger.error(f"Failed to handle stale session {session_id}: {str(e)}")

    async def _handle_stale_processor(self, processor_id: str) -> None:
        """Handle stale processor"""
        try:
            context = self.registered_processors[processor_id]
            # Notify about processor timeout
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PROCESSOR_ERROR_NOTIFY,
                    content={
                        "processor_id": processor_id,
                        "error": "Processor heartbeat timeout",
                        "last_heartbeat": context.last_heartbeat.isoformat()
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="system_monitor"
                    )
                )
            )
            # Unregister processor
            await self.unregister_processor(processor_id)
        except Exception as e:
            logger.error(f"Failed to handle stale processor {processor_id}: {str(e)}")

    async def _handle_processor_backpressure(self, processor_id: str) -> None:
        """Handle processor backpressure"""
        try:
            context = self.registered_processors[processor_id]
            # Notify about backpressure
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PROCESSOR_ERROR_NOTIFY,
                    content={
                        "processor_id": processor_id,
                        "error": "Processor queue size exceeded",
                        "queue_size": context.message_queue_size
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="system_monitor"
                    )
                )
            )
            # Implement backpressure handling logic
            await self._apply_backpressure_measures(processor_id)
        except Exception as e:
            logger.error(f"Failed to handle processor backpressure {processor_id}: {str(e)}")

    async def register_processor(
            self,
            processor_id: str,
            capabilities: List[str],
            max_queue_size: int = 1000
    ) -> None:
        """Register a new processor"""
        try:
            # Create processor context
            context = ProcessorContext(
                processor_id=processor_id,
                capabilities=capabilities,
                status="active",
                last_heartbeat=datetime.now(),
                message_queue_size=0,
                active_tasks=0,
                error_count=0
            )
            
            # Register with broker
            await self.message_broker.register_processor(
                processor_id=processor_id,
                capabilities=capabilities,
                max_queue_size=max_queue_size
            )
            
            # Update local state
            self.registered_processors[processor_id] = context
            self.processor_capabilities[processor_id] = set(capabilities)
            
            logger.info(f"Processor {processor_id} registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register processor {processor_id}: {str(e)}")
            raise

    async def unregister_processor(self, processor_id: str) -> None:
        """Unregister a processor"""
        try:
            # Remove from broker
            await self.message_broker.unregister_processor(processor_id)
            
            # Cleanup local state
            if processor_id in self.registered_processors:
                del self.registered_processors[processor_id]
            if processor_id in self.processor_capabilities:
                del self.processor_capabilities[processor_id]
                
            logger.info(f"Processor {processor_id} unregistered successfully")
            
        except Exception as e:
            logger.error(f"Failed to unregister processor {processor_id}: {str(e)}")
            raise

    async def _process_pending_commands(self, session_id: str) -> None:
        """Process pending commands for a frontend session"""
        try:
            commands = self.pending_commands[session_id]
            for command in commands:
                # Process command based on type
                if command["type"] == "status_request":
                    await self._handle_status_request(session_id, command)
                elif command["type"] == "command_request":
                    await self._handle_command_request(session_id, command)
                elif command["type"] == "config_update":
                    await self._handle_config_update(session_id, command)
            
            # Clear processed commands
            self.pending_commands[session_id] = []
            
        except Exception as e:
            logger.error(f"Failed to process pending commands for session {session_id}: {str(e)}")

    async def _handle_status_request(self, session_id: str, command: Dict[str, Any]) -> None:
        """Handle frontend status request"""
        try:
            session = self.frontend_sessions[session_id]
            pipeline_id = command.get('pipeline_id', session.pipeline_id)
            
            # Get detailed pipeline status
            status = await self.get_frontend_status(pipeline_id, session.user_id)
            
            # Add additional metrics
            status.update({
                'resource_usage': await self._get_pipeline_resource_usage(pipeline_id),
                'processing_metrics': await self._get_processing_metrics(pipeline_id),
                'component_health': await self._get_component_health(pipeline_id)
            })
            
            # Send response
            await self._send_frontend_response(
                session_id,
                'status_response',
                status
            )
            
        except Exception as e:
            logger.error(f"Status request handling failed: {str(e)}")
            await self._send_frontend_error(session_id, str(e))

    async def _handle_command_request(self, session_id: str, command: Dict[str, Any]) -> None:
        """Handle frontend command request"""
        try:
            session = self.frontend_sessions[session_id]
            command_type = command.get('command_type')
            pipeline_id = command.get('pipeline_id', session.pipeline_id)
            
            # Validate command
            if not self._validate_frontend_command(command_type, pipeline_id):
                raise ValueError(f"Invalid command type: {command_type}")
            
            # Process command based on type
            command_handlers = {
                'pause_pipeline': self._handle_pause_pipeline,
                'resume_pipeline': self._handle_resume_pipeline,
                'cancel_pipeline': self._handle_cancel_pipeline,
                'retry_stage': self._handle_retry_stage,
                'modify_config': self._handle_modify_config,
                'request_help': self._handle_request_help,
                'escalate_issue': self._handle_escalate_issue
            }
            
            handler = command_handlers.get(command_type)
            if handler:
                result = await handler(pipeline_id, command.get('params', {}))
                await self._send_frontend_response(session_id, f'{command_type}_response', result)
            else:
                raise ValueError(f"Unsupported command type: {command_type}")
                
        except Exception as e:
            logger.error(f"Command request handling failed: {str(e)}")
            await self._send_frontend_error(session_id, str(e))

    async def _handle_config_update(self, session_id: str, command: Dict[str, Any]) -> None:
        """Handle frontend configuration update"""
        try:
            session = self.frontend_sessions[session_id]
            pipeline_id = command.get('pipeline_id', session.pipeline_id)
            config_updates = command.get('config', {})
            
            # Validate config updates
            if not self._validate_config_updates(config_updates):
                raise ValueError("Invalid configuration updates")
            
            # Apply config updates
            result = await self._apply_config_updates(pipeline_id, config_updates)
            
            # Notify relevant components
            await self._notify_config_change(pipeline_id, config_updates)
            
            # Send response
            await self._send_frontend_response(
                session_id,
                'config_update_response',
                result
            )
            
        except Exception as e:
            logger.error(f"Config update handling failed: {str(e)}")
            await self._send_frontend_error(session_id, str(e))

    async def _handle_pause_pipeline(self, pipeline_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pipeline pause request"""
        try:
            pipeline = self.active_pipelines.get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            
            # Update pipeline status
            pipeline.status = ProcessingStatus.PAUSED
            
            # Pause active control points
            for cp in self.active_control_points.values():
                if cp.pipeline_id == pipeline_id:
                    cp.status = ProcessingStatus.PAUSED
            
            # Notify components
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_PAUSE_REQUEST,
                    content={'pipeline_id': pipeline_id},
                    source_identifier=self.module_identifier
                )
            )
            
            return {'status': 'success', 'message': 'Pipeline paused successfully'}
            
        except Exception as e:
            logger.error(f"Pipeline pause failed: {str(e)}")
            raise

    async def _handle_resume_pipeline(self, pipeline_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pipeline resume request"""
        try:
            pipeline = self.active_pipelines.get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            
            # Update pipeline status
            pipeline.status = ProcessingStatus.IN_PROGRESS
            
            # Resume active control points
            for cp in self.active_control_points.values():
                if cp.pipeline_id == pipeline_id:
                    cp.status = ProcessingStatus.IN_PROGRESS
            
            # Notify components
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_RESUME_REQUEST,
                    content={'pipeline_id': pipeline_id},
                    source_identifier=self.module_identifier
                )
            )
            
            return {'status': 'success', 'message': 'Pipeline resumed successfully'}
            
        except Exception as e:
            logger.error(f"Pipeline resume failed: {str(e)}")
            raise

    async def _handle_cancel_pipeline(self, pipeline_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pipeline cancellation request"""
        try:
            pipeline = self.active_pipelines.get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            
            # Update pipeline status
            pipeline.status = ProcessingStatus.CANCELLED
            
            # Cancel active control points
            for cp in self.active_control_points.values():
                if cp.pipeline_id == pipeline_id:
                    cp.status = ProcessingStatus.CANCELLED
            
            # Notify components
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PIPELINE_CANCEL_REQUEST,
                    content={'pipeline_id': pipeline_id},
                    source_identifier=self.module_identifier
                )
            )
            
            # Cleanup pipeline
            await self._cleanup_pipeline(pipeline_id)
            
            return {'status': 'success', 'message': 'Pipeline cancelled successfully'}
            
        except Exception as e:
            logger.error(f"Pipeline cancellation failed: {str(e)}")
            raise

    async def _handle_retry_stage(self, pipeline_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle stage retry request"""
        try:
            stage = ProcessingStage(params.get('stage'))
            if not stage:
                raise ValueError("Invalid stage specified")
            
            # Find active control point
            control_point = next(
                (cp for cp in self.active_control_points.values()
                 if cp.pipeline_id == pipeline_id),
                None
            )
            
            if not control_point:
                raise ValueError(f"No active control point found for pipeline: {pipeline_id}")
            
            # Retry stage
            await self._retry_stage(
                control_point,
                stage,
                {'reason': 'User requested retry'}
            )
            
            return {'status': 'success', 'message': f'Stage {stage.value} retry initiated'}
            
        except Exception as e:
            logger.error(f"Stage retry failed: {str(e)}")
            raise

    async def _handle_modify_config(self, pipeline_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle configuration modification request"""
        try:
            config_updates = params.get('config', {})
            
            # Validate updates
            if not self._validate_config_updates(config_updates):
                raise ValueError("Invalid configuration updates")
            
            # Apply updates
            result = await self._apply_config_updates(pipeline_id, config_updates)
            
            # Notify components
            await self._notify_config_change(pipeline_id, config_updates)
            
            return {'status': 'success', 'message': 'Configuration updated successfully'}
            
        except Exception as e:
            logger.error(f"Config modification failed: {str(e)}")
            raise

    async def _handle_request_help(self, pipeline_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle help request"""
        try:
            help_type = params.get('help_type')
            context = params.get('context', {})
            
            # Generate help response
            help_response = await self._generate_help_response(help_type, context)
            
            return {
                'status': 'success',
                'help_content': help_response
            }
            
        except Exception as e:
            logger.error(f"Help request handling failed: {str(e)}")
            raise

    async def _handle_escalate_issue(self, pipeline_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle issue escalation request"""
        try:
            issue_type = params.get('issue_type')
            description = params.get('description')
            priority = params.get('priority', 'medium')
            
            # Create escalation
            escalation_id = await self._create_escalation(
                pipeline_id,
                issue_type,
                description,
                priority
            )
            
            return {
                'status': 'success',
                'escalation_id': escalation_id,
                'message': 'Issue escalated successfully'
            }
            
        except Exception as e:
            logger.error(f"Issue escalation failed: {str(e)}")
            raise

    async def _send_frontend_response(
            self,
            session_id: str,
            response_type: str,
            data: Dict[str, Any]
    ) -> None:
        """Send response to frontend"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.FRONTEND_RESPONSE,
                    content={
                        'session_id': session_id,
                        'response_type': response_type,
                        'data': data
                    },
                    metadata=MessageMetadata(
                        source_component=self.module_identifier.component_name,
                        target_component="frontend"
                    )
                )
            )
        except Exception as e:
            logger.error(f"Failed to send frontend response: {str(e)}")

    async def _send_frontend_error(self, session_id: str, error_message: str) -> None:
        """Send error response to frontend"""
        try:
            await self._send_frontend_response(
                session_id,
                'error',
                {'error': error_message}
            )
        except Exception as e:
            logger.error(f"Failed to send frontend error: {str(e)}")

    def _validate_frontend_command(self, command_type: str, pipeline_id: str) -> bool:
        """Validate frontend command"""
        valid_commands = {
            'pause_pipeline',
            'resume_pipeline',
            'cancel_pipeline',
            'retry_stage',
            'modify_config',
            'request_help',
            'escalate_issue'
        }
        
        return (
            command_type in valid_commands and
            pipeline_id in self.active_pipelines
        )

    def _validate_config_updates(self, config_updates: Dict[str, Any]) -> bool:
        """Validate configuration updates"""
        required_fields = {'stage', 'department', 'parameters'}
        return all(field in config_updates for field in required_fields)

    async def _apply_config_updates(self, pipeline_id: str, config_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Apply configuration updates"""
        try:
            pipeline = self.active_pipelines.get(pipeline_id)
            if not pipeline:
                raise ValueError(f"Pipeline not found: {pipeline_id}")
            
            # Update pipeline configuration
            pipeline.stage_configs.update(config_updates)
            
            # Update component states
            pipeline.component_states[config_updates['department']] = ProcessingStatus.PENDING.value
            
            return {
                'status': 'success',
                'updated_config': pipeline.stage_configs
            }
            
        except Exception as e:
            logger.error(f"Config update application failed: {str(e)}")
            raise

    async def _notify_config_change(self, pipeline_id: str, config_updates: Dict[str, Any]) -> None:
        """Notify components about configuration changes"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.CONFIG_UPDATE_NOTIFY,
                    content={
                        'pipeline_id': pipeline_id,
                        'config_updates': config_updates
                    },
                    source_identifier=self.module_identifier
                )
            )
        except Exception as e:
            logger.error(f"Config change notification failed: {str(e)}")

    async def _generate_help_response(self, help_type: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate help response based on type and context"""
        help_responses = {
            'stage_help': self._generate_stage_help,
            'error_help': self._generate_error_help,
            'decision_help': self._generate_decision_help,
            'config_help': self._generate_config_help
        }
        
        generator = help_responses.get(help_type)
        if not generator:
            raise ValueError(f"Unsupported help type: {help_type}")
            
        return await generator(context)

    async def _create_escalation(
            self,
            pipeline_id: str,
            issue_type: str,
            description: str,
            priority: str
    ) -> str:
        """Create new escalation"""
        try:
            escalation_id = str(uuid.uuid4())
            
            # Create escalation record
            escalation = {
                'id': escalation_id,
                'pipeline_id': pipeline_id,
                'issue_type': issue_type,
                'description': description,
                'priority': priority,
                'status': 'open',
                'created_at': datetime.utcnow().isoformat()
            }
            
            # Store escalation
            self.escalations[escalation_id] = escalation
            
            # Notify escalation service
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ESCALATION_CREATE,
                    content=escalation,
                    source_identifier=self.module_identifier
                )
            )
            
            return escalation_id
            
        except Exception as e:
            logger.error(f"Escalation creation failed: {str(e)}")
            raise

    async def _apply_backpressure_measures(self, processor_id: str) -> None:
        """Apply backpressure measures to handle processor overload"""
        try:
            context = self.registered_processors[processor_id]
            
            # Calculate backpressure level
            backpressure_level = self._calculate_backpressure_level(context)
            
            # Apply measures based on level
            if backpressure_level == 'high':
                await self._apply_high_backpressure(processor_id)
            elif backpressure_level == 'medium':
                await self._apply_medium_backpressure(processor_id)
            else:
                await self._apply_low_backpressure(processor_id)
                
            # Monitor effectiveness
            await self._monitor_backpressure_effectiveness(processor_id)
            
        except Exception as e:
            logger.error(f"Backpressure measures application failed: {str(e)}")

    def _calculate_backpressure_level(self, context: ProcessorContext) -> str:
        """Calculate backpressure level based on processor metrics"""
        queue_size = context.message_queue_size
        active_tasks = context.active_tasks
        error_rate = context.error_count / max(1, context.total_tasks)
        
        # Define thresholds
        thresholds = {
            'high': {
                'queue_size': 1000,
                'active_tasks': 50,
                'error_rate': 0.1
            },
            'medium': {
                'queue_size': 500,
                'active_tasks': 25,
                'error_rate': 0.05
            }
        }
        
        # Check high threshold
        if (queue_size >= thresholds['high']['queue_size'] or
                active_tasks >= thresholds['high']['active_tasks'] or
                error_rate >= thresholds['high']['error_rate']):
            return 'high'
            
        # Check medium threshold
        if (queue_size >= thresholds['medium']['queue_size'] or
                active_tasks >= thresholds['medium']['active_tasks'] or
                error_rate >= thresholds['medium']['error_rate']):
            return 'medium'
            
        return 'low'

    async def _apply_high_backpressure(self, processor_id: str) -> None:
        """Apply high-level backpressure measures"""
        try:
            # Pause new task assignment
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PROCESSOR_PAUSE_REQUEST,
                    content={'processor_id': processor_id},
                    metadata=MessageMetadata(priority=MessagePriority.HIGH)
                )
            )
            
            # Request task redistribution
            await self._redistribute_tasks(processor_id)
            
            # Increase monitoring frequency
            await self._adjust_monitoring_frequency(processor_id, 'high')
            
            # Notify system monitor
            await self._notify_backpressure_status(processor_id, 'high')
            
        except Exception as e:
            logger.error(f"High backpressure application failed: {str(e)}")

    async def _apply_medium_backpressure(self, processor_id: str) -> None:
        """Apply medium-level backpressure measures"""
        try:
            # Reduce task assignment rate
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PROCESSOR_THROTTLE_REQUEST,
                    content={'processor_id': processor_id},
                    metadata=MessageMetadata(priority=MessagePriority.NORMAL)
                )
            )
            
            # Adjust task prioritization
            await self._adjust_task_prioritization(processor_id)
            
            # Increase monitoring frequency
            await self._adjust_monitoring_frequency(processor_id, 'medium')
            
            # Notify system monitor
            await self._notify_backpressure_status(processor_id, 'medium')
            
        except Exception as e:
            logger.error(f"Medium backpressure application failed: {str(e)}")

    async def _apply_low_backpressure(self, processor_id: str) -> None:
        """Apply low-level backpressure measures"""
        try:
            # Adjust task scheduling
            await self._adjust_task_scheduling(processor_id)
            
            # Monitor queue growth
            await self._monitor_queue_growth(processor_id)
            
            # Notify system monitor
            await self._notify_backpressure_status(processor_id, 'low')
            
        except Exception as e:
            logger.error(f"Low backpressure application failed: {str(e)}")

    async def _monitor_backpressure_effectiveness(self, processor_id: str) -> None:
        """Monitor effectiveness of backpressure measures"""
        try:
            context = self.registered_processors[processor_id]
            
            # Track metrics over time
            metrics_history = context.metrics_history
            
            # Calculate effectiveness
            effectiveness = self._calculate_backpressure_effectiveness(metrics_history)
            
            # Adjust measures if needed
            if effectiveness < 0.5:  # Less than 50% effective
                await self._escalate_backpressure_measures(processor_id)
                
            # Update monitoring configuration
            await self._update_monitoring_config(processor_id, effectiveness)
            
        except Exception as e:
            logger.error(f"Backpressure effectiveness monitoring failed: {str(e)}")

    def _calculate_backpressure_effectiveness(self, metrics_history: List[Dict[str, Any]]) -> float:
        """Calculate effectiveness of backpressure measures"""
        if not metrics_history:
            return 0.0
            
        # Calculate queue size reduction
        queue_reduction = (
            metrics_history[0]['queue_size'] - metrics_history[-1]['queue_size']
        ) / max(1, metrics_history[0]['queue_size'])
        
        # Calculate error rate reduction
        error_reduction = (
            metrics_history[0]['error_rate'] - metrics_history[-1]['error_rate']
        ) / max(1, metrics_history[0]['error_rate'])
        
        # Calculate processing rate improvement
        processing_improvement = (
            metrics_history[-1]['processing_rate'] - metrics_history[0]['processing_rate']
        ) / max(1, metrics_history[0]['processing_rate'])
        
        # Weighted average of improvements
        effectiveness = (
            0.4 * queue_reduction +
            0.3 * error_reduction +
            0.3 * processing_improvement
        )
        
        return max(0.0, min(1.0, effectiveness))

    async def _escalate_backpressure_measures(self, processor_id: str) -> None:
        """Escalate backpressure measures if current measures are ineffective"""
        try:
            context = self.registered_processors[processor_id]
            current_level = self._calculate_backpressure_level(context)
            
            # Determine next level
            escalation_map = {
                'low': 'medium',
                'medium': 'high'
            }
            
            next_level = escalation_map.get(current_level)
            if next_level:
                # Apply next level measures
                measure_handlers = {
                    'medium': self._apply_medium_backpressure,
                    'high': self._apply_high_backpressure
                }
                
                handler = measure_handlers.get(next_level)
                if handler:
                    await handler(processor_id)
                    
                # Log escalation
                logger.warning(
                    f"Backpressure measures escalated to {next_level} for processor {processor_id}"
                )
                
        except Exception as e:
            logger.error(f"Backpressure escalation failed: {str(e)}")

    async def _redistribute_tasks(self, processor_id: str) -> None:
        """Redistribute tasks from overloaded processor"""
        try:
            context = self.registered_processors[processor_id]
            
            # Find available processors
            available_processors = [
                pid for pid, ctx in self.registered_processors.items()
                if (pid != processor_id and
                    ctx.status == 'active' and
                    ctx.message_queue_size < 500)
            ]
            
            if not available_processors:
                logger.warning(f"No available processors for task redistribution from {processor_id}")
                return
                
            # Calculate redistribution amount
            redistribution_amount = min(
                context.message_queue_size // 2,
                context.active_tasks // 2
            )
            
            # Redistribute tasks
            for _ in range(redistribution_amount):
                target_processor = available_processors[0]  # Simple round-robin
                await self._move_task(processor_id, target_processor)
                
            logger.info(
                f"Redistributed {redistribution_amount} tasks from processor {processor_id}"
            )
            
        except Exception as e:
            logger.error(f"Task redistribution failed: {str(e)}")

    async def _move_task(self, source_processor: str, target_processor: str) -> None:
        """Move a task from one processor to another"""
        try:
            # Get task from source processor
            task = await self.message_broker.get_next_task(source_processor)
            if not task:
                return
                
            # Forward task to target processor
            await self.message_broker.forward_task(
                task,
                target_processor,
                metadata=MessageMetadata(
                    priority=MessagePriority.HIGH,
                    source_processor=source_processor
                )
            )
            
            # Update processor contexts
            self.registered_processors[source_processor].message_queue_size -= 1
            self.registered_processors[target_processor].message_queue_size += 1
            
        except Exception as e:
            logger.error(f"Task movement failed: {str(e)}")

    async def _adjust_task_prioritization(self, processor_id: str) -> None:
        """Adjust task prioritization for processor using advanced algorithms"""
        try:
            # Get current queue and processor context
            queue = await self.message_broker.get_processor_queue(processor_id)
            context = self.registered_processors[processor_id]
            
            # Calculate priority scores for each task
            prioritized_tasks = await self._calculate_task_priorities(queue, context)
            
            # Apply priority-based sorting with additional factors
            sorted_tasks = self._sort_tasks_by_priority(prioritized_tasks)
            
            # Apply fairness adjustments
            adjusted_tasks = self._apply_fairness_adjustments(sorted_tasks, context)
            
            # Requeue tasks in priority order
            await self.message_broker.reorder_processor_queue(
                processor_id,
                adjusted_tasks
            )
            
            # Update processor metrics
            await self._update_processor_metrics(processor_id, adjusted_tasks)
            
        except Exception as e:
            logger.error(f"Task prioritization adjustment failed: {str(e)}")

    async def _calculate_task_priorities(self, queue: List[ProcessingMessage], context: ProcessorContext) -> List[Tuple[ProcessingMessage, float]]:
        """Calculate priority scores for tasks using multiple factors"""
        prioritized_tasks = []
        
        for task in queue:
            # Base priority from message metadata
            base_priority = task.metadata.priority.value
            
            # Calculate urgency score
            urgency_score = self._calculate_urgency_score(task)
            
            # Calculate resource impact score
            resource_score = self._calculate_resource_impact(task, context)
            
            # Calculate dependency score
            dependency_score = self._calculate_dependency_score(task)
            
            # Calculate fairness score
            fairness_score = self._calculate_fairness_score(task, context)
            
            # Weighted combination of scores
            total_score = (
                0.3 * base_priority +
                0.25 * urgency_score +
                0.2 * resource_score +
                0.15 * dependency_score +
                0.1 * fairness_score
            )
            
            prioritized_tasks.append((task, total_score))
            
        return prioritized_tasks

    def _calculate_urgency_score(self, task: ProcessingMessage) -> float:
        """Calculate urgency score based on deadlines and dependencies"""
        deadline = task.metadata.deadline
        if not deadline:
            return 0.5
            
        # Calculate time until deadline
        time_until_deadline = (deadline - datetime.utcnow()).total_seconds()
        
        # Normalize to 0-1 range
        if time_until_deadline <= 0:
            return 1.0
        elif time_until_deadline > 3600:  # More than 1 hour
            return 0.2
        else:
            return 1.0 - (time_until_deadline / 3600)

    def _calculate_resource_impact(self, task: ProcessingMessage, context: ProcessorContext) -> float:
        """Calculate resource impact score based on task requirements"""
        # Get task resource requirements
        requirements = task.metadata.resource_requirements or {}
        
        # Calculate resource utilization impact
        cpu_impact = requirements.get('cpu', 0) / context.max_cpu
        memory_impact = requirements.get('memory', 0) / context.max_memory
        io_impact = requirements.get('io_operations', 0) / context.max_io_ops
        
        # Weighted average of resource impacts
        return (0.4 * cpu_impact + 0.3 * memory_impact + 0.3 * io_impact)

    def _calculate_dependency_score(self, task: ProcessingMessage) -> float:
        """Calculate dependency score based on task dependencies"""
        dependencies = task.metadata.dependencies or []
        if not dependencies:
            return 0.5
            
        # Count blocked dependencies
        blocked_count = sum(1 for dep in dependencies if not dep.get('completed', False))
        
        # Normalize score
        return min(1.0, blocked_count / len(dependencies))

    def _calculate_fairness_score(self, task: ProcessingMessage, context: ProcessorContext) -> float:
        """Calculate fairness score to prevent starvation"""
        # Get task source and age
        source = task.metadata.source_component
        age = (datetime.utcnow() - task.metadata.created_at).total_seconds()
        
        # Calculate waiting time ratio
        wait_ratio = min(1.0, age / context.max_wait_time)
        
        # Get source-specific waiting time
        source_wait_time = context.source_wait_times.get(source, 0)
        source_ratio = min(1.0, source_wait_time / context.max_source_wait_time)
        
        # Combine factors
        return 0.6 * wait_ratio + 0.4 * source_ratio

    def _sort_tasks_by_priority(self, prioritized_tasks: List[Tuple[ProcessingMessage, float]]) -> List[ProcessingMessage]:
        """Sort tasks by priority score with tie-breaking"""
        # Sort by priority score
        sorted_tasks = sorted(prioritized_tasks, key=lambda x: x[1], reverse=True)
        
        # Apply tie-breaking rules
        final_order = []
        current_score = None
        current_group = []
        
        for task, score in sorted_tasks:
            if current_score is None:
                current_score = score
                current_group.append(task)
            elif abs(score - current_score) < 0.01:  # Consider scores equal if difference is small
                current_group.append(task)
            else:
                # Sort current group by tie-breaking rules
                final_order.extend(self._apply_tie_breaking(current_group))
                current_score = score
                current_group = [task]
                
        # Handle last group
        if current_group:
            final_order.extend(self._apply_tie_breaking(current_group))
            
        return final_order

    def _apply_tie_breaking(self, tasks: List[ProcessingMessage]) -> List[ProcessingMessage]:
        """Apply tie-breaking rules to tasks with equal priority scores"""
        # Sort by multiple criteria in order of importance
        return sorted(
            tasks,
            key=lambda t: (
                t.metadata.priority.value,  # Message priority
                t.metadata.deadline or datetime.max,  # Deadline
                t.metadata.created_at,  # Creation time
                t.metadata.source_component  # Source component
            )
        )

    def _apply_fairness_adjustments(self, tasks: List[ProcessingMessage], context: ProcessorContext) -> List[ProcessingMessage]:
        """Apply fairness adjustments to prevent starvation"""
        # Group tasks by source
        source_groups = {}
        for task in tasks:
            source = task.metadata.source_component
            if source not in source_groups:
                source_groups[source] = []
            source_groups[source].append(task)
            
        # Calculate fair distribution
        fair_distribution = self._calculate_fair_distribution(tasks, source_groups)
        
        # Apply distribution while maintaining priority order within groups
        adjusted_tasks = []
        for source, count in fair_distribution.items():
            source_tasks = source_groups.get(source, [])
            adjusted_tasks.extend(source_tasks[:count])
            
        return adjusted_tasks

    def _calculate_fair_distribution(self, tasks: List[ProcessingMessage], source_groups: Dict[str, List[ProcessingMessage]]) -> Dict[str, int]:
        """Calculate fair distribution of tasks across sources"""
        total_tasks = len(tasks)
        num_sources = len(source_groups)
        
        # Calculate base fair share
        base_share = total_tasks // num_sources
        remainder = total_tasks % num_sources
        
        # Initialize distribution
        distribution = {}
        for source in source_groups:
            distribution[source] = base_share
            
        # Distribute remainder based on source priority
        if remainder > 0:
            # Sort sources by priority (can be customized based on business rules)
            priority_sources = sorted(
                source_groups.keys(),
                key=lambda s: self._get_source_priority(s)
            )
            
            # Distribute remainder to highest priority sources
            for source in priority_sources[:remainder]:
                distribution[source] += 1
                
        return distribution

    def _get_source_priority(self, source: str) -> int:
        """Get priority for a source component"""
        # Define source priorities (can be customized)
        source_priorities = {
            'data_import': 1,
            'data_transform': 2,
            'data_validate': 3,
            'data_export': 4,
            'quality_check': 5,
            'analytics': 6
        }
        return source_priorities.get(source, 0)

    async def _update_processor_metrics(self, processor_id: str, tasks: List[ProcessingMessage]) -> None:
        """Update processor metrics with detailed performance analytics"""
        try:
            context = self.registered_processors[processor_id]
            
            # Calculate comprehensive metrics
            metrics = {
                'queue_metrics': self._calculate_queue_metrics(tasks),
                'performance_metrics': self._calculate_performance_metrics(context),
                'resource_metrics': self._calculate_resource_metrics(tasks, context),
                'dependency_metrics': self._calculate_dependency_metrics(tasks),
                'health_metrics': self._calculate_health_metrics(context),
                'efficiency_metrics': self._calculate_efficiency_metrics(context),
                'visualization_data': self._prepare_visualization_data(context)
            }
            
            # Update context metrics
            context.metrics_history.append(metrics)
            if len(context.metrics_history) > 100:  # Keep last 100 measurements
                context.metrics_history.pop(0)
                
            # Update current metrics
            context.current_metrics = metrics
            
            # Notify monitoring system with enhanced data
            await self._notify_processor_metrics_update(processor_id, metrics)
            
        except Exception as e:
            logger.error(f"Processor metrics update failed: {str(e)}")

    def _calculate_queue_metrics(self, tasks: List[ProcessingMessage]) -> Dict[str, Any]:
        """Calculate detailed queue metrics"""
        if not tasks:
            return {
                'size': 0,
                'growth_rate': 0,
                'priority_distribution': {},
                'source_distribution': {},
                'average_wait_time': 0,
                'max_wait_time': 0,
                'wait_time_distribution': {},
                'bottleneck_analysis': {}
            }
            
        # Calculate basic metrics
        queue_size = len(tasks)
        wait_times = [(datetime.utcnow() - task.metadata.created_at).total_seconds() for task in tasks]
        max_wait = max(wait_times)
        avg_wait = sum(wait_times) / queue_size
        
        # Calculate wait time distribution
        wait_distribution = {
            '0-5min': sum(1 for t in wait_times if t <= 300),
            '5-15min': sum(1 for t in wait_times if 300 < t <= 900),
            '15-30min': sum(1 for t in wait_times if 900 < t <= 1800),
            '30min+': sum(1 for t in wait_times if t > 1800)
        }
        
        # Analyze bottlenecks
        bottlenecks = self._analyze_queue_bottlenecks(tasks)
        
        return {
            'size': queue_size,
            'growth_rate': self._calculate_queue_growth_rate(tasks),
            'priority_distribution': self._calculate_priority_distribution(tasks),
            'source_distribution': self._calculate_source_distribution(tasks),
            'average_wait_time': avg_wait,
            'max_wait_time': max_wait,
            'wait_time_distribution': wait_distribution,
            'bottleneck_analysis': bottlenecks
        }

    def _calculate_performance_metrics(self, context: ProcessorContext) -> Dict[str, Any]:
        """Calculate detailed performance metrics"""
        if not context.metrics_history:
            return {
                'processing_rate': 0,
                'error_rate': 0,
                'average_processing_time': 0,
                'throughput': 0,
                'latency': 0,
                'efficiency': 0,
                'trends': {}
            }
            
        # Calculate processing metrics
        recent_metrics = context.metrics_history[-5:]  # Last 5 measurements
        processing_times = [m.get('processing_time', 0) for m in recent_metrics]
        error_counts = [m.get('error_count', 0) for m in recent_metrics]
        total_tasks = [m.get('total_tasks', 0) for m in recent_metrics]
        
        # Calculate trends
        trends = self._calculate_performance_trends(context.metrics_history)
        
        return {
            'processing_rate': sum(total_tasks) / len(total_tasks),
            'error_rate': sum(error_counts) / max(1, sum(total_tasks)),
            'average_processing_time': sum(processing_times) / len(processing_times),
            'throughput': self._calculate_throughput(context),
            'latency': self._calculate_latency(context),
            'efficiency': self._calculate_processing_efficiency(context),
            'trends': trends
        }

    def _calculate_resource_metrics(self, tasks: List[ProcessingMessage], context: ProcessorContext) -> Dict[str, Any]:
        """Calculate detailed resource utilization metrics"""
        # Calculate current resource usage
        current_usage = self._calculate_resource_utilization(tasks, context)
        
        # Calculate resource trends
        resource_trends = self._calculate_resource_trends(context)
        
        # Calculate resource efficiency
        efficiency = self._calculate_resource_efficiency(context)
        
        # Calculate resource bottlenecks
        bottlenecks = self._identify_resource_bottlenecks(context)
        
        return {
            'current_usage': current_usage,
            'trends': resource_trends,
            'efficiency': efficiency,
            'bottlenecks': bottlenecks,
            'recommendations': self._generate_resource_recommendations(context)
        }

    def _calculate_dependency_metrics(self, tasks: List[ProcessingMessage]) -> Dict[str, Any]:
        """Calculate detailed dependency metrics"""
        # Calculate basic dependency metrics
        basic_metrics = self._calculate_dependency_complexity(tasks)
        
        # Calculate dependency chains
        chains = self._analyze_dependency_chains(tasks)
        
        # Calculate critical paths
        critical_paths = self._identify_critical_paths(tasks)
        
        # Calculate dependency health
        health = self._calculate_dependency_health(tasks)
        
        return {
            **basic_metrics,
            'chains': chains,
            'critical_paths': critical_paths,
            'health': health,
            'recommendations': self._generate_dependency_recommendations(tasks)
        }

    def _calculate_health_metrics(self, context: ProcessorContext) -> Dict[str, Any]:
        """Calculate detailed health metrics"""
        return {
            'status': context.status,
            'uptime': self._calculate_uptime(context),
            'error_rate': self._calculate_error_rate(context),
            'recovery_rate': self._calculate_recovery_rate(context),
            'stability_score': self._calculate_stability_score(context),
            'health_trends': self._calculate_health_trends(context),
            'alerts': self._get_active_alerts(context)
        }

    def _calculate_efficiency_metrics(self, context: ProcessorContext) -> Dict[str, Any]:
        """Calculate detailed efficiency metrics"""
        return {
            'resource_efficiency': self._calculate_resource_efficiency(context),
            'processing_efficiency': self._calculate_processing_efficiency(context),
            'queue_efficiency': self._calculate_queue_efficiency(context),
            'overall_efficiency': self._calculate_overall_efficiency(context),
            'optimization_opportunities': self._identify_optimization_opportunities(context)
        }

    def _prepare_visualization_data(self, context: ProcessorContext) -> Dict[str, Any]:
        """Prepare data for visualization"""
        return {
            'time_series': self._prepare_time_series_data(context),
            'resource_usage': self._prepare_resource_usage_data(context),
            'performance_charts': self._prepare_performance_charts(context),
            'health_status': self._prepare_health_status_data(context),
            'dependency_graph': self._prepare_dependency_graph(context),
            'bottleneck_analysis': self._prepare_bottleneck_analysis(context)
        }

    def _prepare_time_series_data(self, context: ProcessorContext) -> Dict[str, List[Dict[str, Any]]]:
        """Prepare time series data for visualization"""
        if not context.metrics_history:
            return {}
            
        return {
            'queue_size': [
                {'timestamp': m.get('timestamp'), 'value': m.get('queue_size', 0)}
                for m in context.metrics_history
            ],
            'processing_rate': [
                {'timestamp': m.get('timestamp'), 'value': m.get('processing_rate', 0)}
                for m in context.metrics_history
            ],
            'error_rate': [
                {'timestamp': m.get('timestamp'), 'value': m.get('error_rate', 0)}
                for m in context.metrics_history
            ],
            'resource_usage': [
                {'timestamp': m.get('timestamp'), 'value': m.get('resource_usage', {})}
                for m in context.metrics_history
            ]
        }

    def _prepare_resource_usage_data(self, context: ProcessorContext) -> Dict[str, Any]:
        """Prepare resource usage data for visualization"""
        if not context.metrics_history:
            return {}
            
        latest_metrics = context.metrics_history[-1]
        resource_usage = latest_metrics.get('resource_metrics', {}).get('current_usage', {})
        
        return {
            'current': {
                'cpu': resource_usage.get('cpu', 0),
                'memory': resource_usage.get('memory', 0),
                'io': resource_usage.get('io', 0)
            },
            'limits': {
                'cpu': context.max_cpu,
                'memory': context.max_memory,
                'io': context.max_io_ops
            },
            'trends': self._calculate_resource_trends(context)
        }

    def _prepare_performance_charts(self, context: ProcessorContext) -> Dict[str, Any]:
        """Prepare performance chart data"""
        if not context.metrics_history:
            return {}
            
        return {
            'throughput': self._calculate_throughput_chart_data(context),
            'latency': self._calculate_latency_chart_data(context),
            'error_rate': self._calculate_error_rate_chart_data(context),
            'efficiency': self._calculate_efficiency_chart_data(context)
        }

    def _prepare_health_status_data(self, context: ProcessorContext) -> Dict[str, Any]:
        """Prepare health status data for visualization"""
        health_metrics = self._calculate_health_metrics(context)
        
        return {
            'status': health_metrics['status'],
            'score': health_metrics['stability_score'],
            'trends': health_metrics['health_trends'],
            'alerts': health_metrics['alerts'],
            'recommendations': self._generate_health_recommendations(health_metrics)
        }

    def _prepare_dependency_graph(self, context: ProcessorContext) -> Dict[str, Any]:
        """Prepare dependency graph data for visualization"""
        if not context.current_tasks:
            return {}
            
        return {
            'nodes': self._get_dependency_nodes(context.current_tasks),
            'edges': self._get_dependency_edges(context.current_tasks),
            'critical_paths': self._identify_critical_paths(context.current_tasks),
            'bottlenecks': self._identify_dependency_bottlenecks(context.current_tasks)
        }

    def _prepare_bottleneck_analysis(self, context: ProcessorContext) -> Dict[str, Any]:
        """Prepare bottleneck analysis data for visualization"""
        return {
            'resource_bottlenecks': self._identify_resource_bottlenecks(context),
            'processing_bottlenecks': self._identify_processing_bottlenecks(context),
            'queue_bottlenecks': self._analyze_queue_bottlenecks(context.current_tasks),
            'dependency_bottlenecks': self._identify_dependency_bottlenecks(context.current_tasks),
            'recommendations': self._generate_bottleneck_recommendations(context)
        }

    def _analyze_queue_bottlenecks(self, tasks: List[ProcessingMessage]) -> Dict[str, Any]:
        """Analyze queue bottlenecks"""
        if not tasks:
            return {}
            
        # Group tasks by source and priority
        source_groups = {}
        priority_groups = {}
        
        for task in tasks:
            source = task.metadata.source_component
            priority = task.metadata.priority.value
            
            if source not in source_groups:
                source_groups[source] = []
            if priority not in priority_groups:
                priority_groups[priority] = []
                
            source_groups[source].append(task)
            priority_groups[priority].append(task)
            
        # Calculate bottleneck metrics
        bottlenecks = {
            'source_bottlenecks': self._identify_source_bottlenecks(source_groups),
            'priority_bottlenecks': self._identify_priority_bottlenecks(priority_groups),
            'wait_time_bottlenecks': self._identify_wait_time_bottlenecks(tasks),
            'resource_bottlenecks': self._identify_resource_bottlenecks_from_tasks(tasks)
        }
        
        return bottlenecks

    def _identify_source_bottlenecks(self, source_groups: Dict[str, List[ProcessingMessage]]) -> List[Dict[str, Any]]:
        """Identify bottlenecks by source"""
        bottlenecks = []
        total_tasks = sum(len(tasks) for tasks in source_groups.values())
        
        for source, tasks in source_groups.items():
            task_count = len(tasks)
            percentage = (task_count / total_tasks) * 100
            
            if percentage > 30:  # Source with more than 30% of tasks
                bottlenecks.append({
                    'source': source,
                    'task_count': task_count,
                    'percentage': percentage,
                    'recommendation': f"Consider distributing tasks from {source} more evenly"
                })
                
        return bottlenecks

    def _identify_priority_bottlenecks(self, priority_groups: Dict[int, List[ProcessingMessage]]) -> List[Dict[str, Any]]:
        """Identify bottlenecks by priority"""
        bottlenecks = []
        total_tasks = sum(len(tasks) for tasks in priority_groups.values())
        
        for priority, tasks in priority_groups.items():
            task_count = len(tasks)
            percentage = (task_count / total_tasks) * 100
            
            if priority == MessagePriority.HIGH.value and percentage > 40:
                bottlenecks.append({
                    'priority': priority,
                    'task_count': task_count,
                    'percentage': percentage,
                    'recommendation': "High priority tasks may be blocking lower priority tasks"
                })
                
        return bottlenecks

    def _identify_wait_time_bottlenecks(self, tasks: List[ProcessingMessage]) -> List[Dict[str, Any]]:
        """Identify bottlenecks based on wait times"""
        bottlenecks = []
        
        for task in tasks:
            wait_time = (datetime.utcnow() - task.metadata.created_at).total_seconds()
            
            if wait_time > 3600:  # More than 1 hour
            return 0.0
            
        recent_metrics = context.metrics_history[-5:]  # Last 5 measurements
        if len(recent_metrics) < 2:
            return 0.0
            
        # Calculate average growth rate
        growth_rates = []
        for i in range(1, len(recent_metrics)):
            rate = (
                recent_metrics[i]['queue_size'] - recent_metrics[i-1]['queue_size']
            ) / max(1, recent_metrics[i-1]['queue_size'])
            growth_rates.append(rate)
            
        return sum(growth_rates) / len(growth_rates)

    async def _notify_queue_growth_alert(self, processor_id: str, growth_rate: float) -> None:
        """Notify about accelerating queue growth"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PROCESSOR_QUEUE_ALERT,
                    content={
                        'processor_id': processor_id,
                        'growth_rate': growth_rate,
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        priority=MessagePriority.HIGH,
                        source_component=self.module_identifier.component_name
                    )
                )
            )
        except Exception as e:
            logger.error(f"Queue growth alert notification failed: {str(e)}")

    async def _adjust_monitoring_frequency(self, processor_id: str, level: str) -> None:
        """Adjust monitoring frequency based on backpressure level"""
        try:
            monitoring_intervals = {
                'high': 5,    # 5 seconds
                'medium': 15, # 15 seconds
                'low': 30     # 30 seconds
            }
            
            interval = monitoring_intervals.get(level, 30)
            
            # Update monitoring configuration
            await self.message_broker.update_processor_config(
                processor_id,
                {'monitoring_interval': interval}
            )
            
        except Exception as e:
            logger.error(f"Monitoring frequency adjustment failed: {str(e)}")

    async def _update_monitoring_config(self, processor_id: str, effectiveness: float) -> None:
        """Update monitoring configuration based on effectiveness"""
        try:
            # Adjust thresholds based on effectiveness
            thresholds = {
                'queue_size': int(1000 * (1 - effectiveness)),
                'active_tasks': int(50 * (1 - effectiveness)),
                'error_rate': 0.1 * (1 - effectiveness)
            }
            
            # Update processor configuration
            await self.message_broker.update_processor_config(
                processor_id,
                {'monitoring_thresholds': thresholds}
            )
            
        except Exception as e:
            logger.error(f"Monitoring config update failed: {str(e)}")

    async def _notify_backpressure_status(self, processor_id: str, level: str) -> None:
        """Notify about backpressure status"""
        try:
            context = self.registered_processors[processor_id]
            
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.PROCESSOR_BACKPRESSURE_STATUS,
                    content={
                        'processor_id': processor_id,
                        'level': level,
                        'metrics': {
                            'queue_size': context.message_queue_size,
                            'active_tasks': context.active_tasks,
                            'error_rate': context.error_count / max(1, context.total_tasks)
                        },
                        'timestamp': datetime.utcnow().isoformat()
                    },
                    metadata=MessageMetadata(
                        priority=MessagePriority.HIGH,
                        source_component=self.module_identifier.component_name
                    )
                )
            )
        except Exception as e:
            logger.error(f"Backpressure status notification failed: {str(e)}")