import uuid
from typing import Dict, List, Any, Optional, Callable, Tuple, Type
from enum import Enum
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import logging
import traceback
import time
import threading
import functools


# Third-party imports
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor

# Local imports (assumed to be defined in respective modules)
from backend.core.messaging.broker import MessageBroker
from backend.core.metrics.performance_tracker import PerformanceTracker
from backend.core.messaging.types import (
    ProcessingMessage,
    MessageType,
    ProcessingStatus,
    ModuleIdentifier
)
from backend.core.orchestration.conductor import DataConductor
from backend.core.staging.staging_area import EnhancedStagingArea
from backend.core.config.data_processing_enums import ProcessingModule, DataIssueType, build_routing_graph

# Import managers and handlers
from backend.data_pipeline.source.file.file_manager import FileManager
from backend.data_pipeline.source.api.api_manager import ApiManager
from backend.data_pipeline.source.cloud.s3_data_manager import S3DataManager
from backend.data_pipeline.source.database.db_data_manager import DBDataManager
from backend.data_pipeline.source.stream.stream_manager import StreamManager
from backend.core.output.handlers import (
    DatabaseOutputHandler,
    FileOutputHandler,
    APIOutputHandler,
    StreamOutputHandler
)

import logging
from typing import Dict, List, Any, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
import uuid
import traceback


def retry_decorator(max_attempts=3, base_delay=1, backoff_factor=2, allowed_exceptions=(Exception,)):
    """
    A flexible retry decorator that can be used on instance methods and functions

    Args:
        max_attempts (int): Maximum number of retry attempts
        base_delay (float): Base delay between retries
        backoff_factor (float): Exponential backoff multiplier
        allowed_exceptions (tuple): Exceptions that trigger a retry
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    result = func(self, *args, **kwargs)
                    if attempt > 1:
                        self.logger.info(f"Operation succeeded on attempt {attempt}")
                    return result

                except allowed_exceptions as e:
                    last_exception = e
                    delay = base_delay * (backoff_factor ** (attempt - 1))
                    self.logger.warning(
                        f"Attempt {attempt} failed. Retrying in {delay:.2f} seconds. "
                        f"Error: {str(e)}"
                    )
                    time.sleep(delay)

            raise RetryExhaustedError(f"Failed after {max_attempts} attempts") from last_exception

        return wrapper

    return decorator


class OrchestratorError(Exception):
    """Base exception for orchestrator errors"""
    pass


class RetryExhaustedError(OrchestratorError):
    """Exception raised when all retry attempts are exhausted"""
    pass


@dataclass
class RetryConfig:
    """Configuration for retry mechanism

    Attributes:
        max_attempts (int): Maximum number of retry attempts
        base_delay (float): Initial delay between retries in seconds
        backoff_factor (float): Multiplier for exponential backoff
        allowed_exceptions (Tuple[Type[Exception], ...]): Exception types eligible for retry
    """
    max_attempts: int = 3
    base_delay: float = 1.0
    backoff_factor: float = 2.0
    allowed_exceptions: Tuple[Type[Exception], ...] = (OrchestratorError,)


@dataclass
class PipelineMetadata:
    """Tracks comprehensive pipeline execution data

    Attributes:
        pipeline_id (str): Unique identifier for the pipeline
        source_type (str): Type of data source
        start_time (datetime): Pipeline start timestamp
        end_time (Optional[datetime]): Pipeline completion timestamp
        status (ProcessingStatus): Current pipeline status
        data_size (int): Size of processed data
        stages_completed (List[str]): List of completed processing stages
        user_decisions (List[Dict[str, Any]]): Record of user decisions
        performance_metrics (Dict[str, Any]): Performance tracking metrics
        recommendations (List[str]): System-generated recommendations
    """
    pipeline_id: str
    source_type: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: ProcessingStatus = ProcessingStatus.PENDING
    data_size: int = 0
    stages_completed: List[str] = field(default_factory=list)
    user_decisions: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class TrafficMetadata:
    """Tracks data movement between pipeline components

    Attributes:
        traffic_id (str): Unique identifier for the traffic instance
        source_module (str): Origin module name
        destination_module (str): Target module name
        timestamp (datetime): Traffic occurrence timestamp
        payload_type (str): Type of data being transferred
        processing_stage (str): Current processing stage
        user_decision_required (bool): Flag for required user intervention
        processing_history (List[Dict[str, Any]]): Historical processing records
    """
    traffic_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_module: str = ''
    destination_module: str = ''
    timestamp: datetime = field(default_factory=datetime.now)
    payload_type: str = ''
    processing_stage: str = 'initial'
    user_decision_required: bool = False
    processing_history: List[Dict[str, Any]] = field(default_factory=list)


class DataOrchestrator:
    """Main orchestrator for data processing pipelines

    Coordinates data flow, manages processing stages, and handles system resources
    while maintaining operational metrics and error handling.
    """
    def __init__(self,
                 message_broker: Optional[MessageBroker] = None,
                 data_conductor: Optional[DataConductor] = None,
                 staging_area: Optional[EnhancedStagingArea] = None,
                 logger: Optional[logging.Logger] = None):
        """Initialize orchestrator with enhanced message handling"""

        # Core components
        self.message_broker = message_broker
        self.conductor = data_conductor
        self.staging_area = staging_area

        # Enhanced logging setup
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        # Performance and metrics
        self.performance_tracker = PerformanceTracker()

        # Configuration with UUID-based instance identification
        self.instance_id = str(uuid.uuid4())
        self.module_id = ModuleIdentifier("DataOrchestrator", "manage_pipeline", self.instance_id)
        self.retry_config = RetryConfig()

        # Enhanced tracking with timestamps
        self.active_pipelines: Dict[str, PipelineMetadata] = {}
        self.active_traffic: Dict[str, TrafficMetadata] = {}

        # Resource management with proper cleanup
        self.source_managers: Dict[str, Any] = {}
        self.output_handlers: Dict[str, Callable] = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

        # Tracking
        self.active_pipelines: Dict[str, PipelineMetadata] = {}
        self.active_traffic: Dict[str, TrafficMetadata] = {}

        # Resource management
        self.source_managers: Dict[str, Any] = {}
        self.output_handlers: Dict[str, Callable] = {}
        self.thread_pool = ThreadPoolExecutor(max_workers=4)

        # Register all potential modules BEFORE setup
        self._register_all_potential_modules()

        # Message handling setup
        self._setup_routing_graph()
        self._setup_message_subscriptions()

        # Routing configuration
        self.routing_graph = build_routing_graph()
        self.initial_routing = {'default': 'data_quality_module'}

        # Initialization sequence
        self._initialize_components()


    def _initialize_components(self):
        """Initialize components in correct sequence with error handling"""
        try:
            # Register orchestrator first
            self._register_orchestrator()

            # Register all modules
            registration_result = self._register_all_potential_modules()

            # Setup message handling only after successful registration
            if registration_result.get('failed', []):
                failed_modules = registration_result['failed']
                self.logger.warning(f"Some modules failed registration: {failed_modules}")

            # Setup routing and subscriptions
            self._setup_routing_graph()
            self._setup_message_subscriptions()

            # Verify setup
            self._verify_initialization()

        except Exception as e:
            self.logger.error(f"Initialization failed: {str(e)}")
            raise RuntimeError(f"Orchestrator initialization failed: {str(e)}")

    def _register_orchestrator(self):
        """Register the orchestrator itself with the message broker"""
        try:
            self.message_broker.register_module(self.module_id)
            self.logger.info(f"Orchestrator registered with ID: {self.instance_id}")
        except Exception as e:
            self.logger.error(f"Failed to register orchestrator: {str(e)}")
            raise

    def _register_all_potential_modules(self) -> Dict[str, List[ModuleIdentifier]]:
        """Register all potential modules with enhanced error handling and tracking"""
        if not self.message_broker:
            raise ValueError("Message broker must be initialized before module registration")

        # Define all module categories with instance IDs
        module_categories = {
            'source': [
                ModuleIdentifier("source_data", "ingest", self.instance_id),
                ModuleIdentifier("file_source", "read", self.instance_id),
                ModuleIdentifier("api_source", "fetch", self.instance_id),
                ModuleIdentifier("s3_source", "retrieve", self.instance_id),
                ModuleIdentifier("db_source", "query", self.instance_id),
                ModuleIdentifier("stream_source", "process", self.instance_id)
            ],
            'output': [
                ModuleIdentifier("output_handler", "process", self.instance_id),
                ModuleIdentifier("db_output", "write", self.instance_id),
                ModuleIdentifier("file_output", "save", self.instance_id),
                ModuleIdentifier("api_output", "send", self.instance_id),
                ModuleIdentifier("stream_output", "publish", self.instance_id)
            ],
            'pipeline': [
                ModuleIdentifier("pipeline_status", "update", self.instance_id),
                ModuleIdentifier("user_decision", "handle", self.instance_id),
                ModuleIdentifier("error_handler", "manage", self.instance_id),
                ModuleIdentifier("logging", "record", self.instance_id),
                ModuleIdentifier("performance_tracker", "monitor", self.instance_id)
            ],
            'processing': [
                ModuleIdentifier(module.value, "process", self.instance_id)
                for module in ProcessingModule
            ],
            'orchestrator': [
                self.module_id,
                ModuleIdentifier("data_conductor", "coordinate", self.instance_id),  # Fixed typo here
                ModuleIdentifier("staging_area", "manage", self.instance_id),  # Fixed typo here
            ]
        }

        registered = []
        failed = []

        # Register modules with enhanced error handling
        for category, modules in module_categories.items():
            for module in modules:
                try:
                    self.message_broker.register_module(module)
                    registered.append(module)
                    self.logger.info(f"Registered {category} module: {module.get_tag()}")
                except Exception as e:
                    failed.append(module)
                    self.logger.error(f"Failed to register {category} module {module.get_tag()}: {str(e)}")

        # Log registration summary
        self._log_registration_summary(registered, failed)

        return {
            'registered': registered,
            'failed': failed
        }

    def _log_registration_summary(self, registered: List[ModuleIdentifier], failed: List[ModuleIdentifier]) -> None:
        """Log a summary of module registration results"""
        total = len(registered) + len(failed)
        success_rate = (len(registered) / total * 100) if total > 0 else 0

        self.logger.info(f"Module registration summary:")
        self.logger.info(f"Total modules: {total}")
        self.logger.info(f"Successfully registered: {len(registered)} ({success_rate:.1f}%)")
        self.logger.info(f"Failed to register: {len(failed)}")

        if failed:
            self.logger.warning("Failed modules:")
            for module in failed:
                self.logger.warning(f"  - {module.get_tag()}")

    def _setup_routing_graph(self):
        """
        Setup the routing graph for pipeline module routing
        This method initializes the routing configuration based on issue types and processing modules
        """
        # Use the build_routing_graph() function to create the routing configuration
        self.routing_graph = build_routing_graph()

        # Set a default initial routing if not already set
        if not hasattr(self, 'initial_routing'):
            self.initial_routing = {'default': 'data_quality_module'}

        self.logger.info("Routing graph successfully configured")

    def _generate_error_recommendation(self, exception: Exception) -> str:
        """Generate context-aware error recommendations

        Args:
            exception (Exception): Caught exception

        Returns:
            str: Recommended action based on error type
        """
        error_recommendations = {
            FileNotFoundError: "Verify file path and permissions",
            PermissionError: "Check file/resource access rights",
            ConnectionError: "Validate network connectivity and endpoint",
        }
        return error_recommendations.get(
            type(exception),
            "Review error details and system configuration"
        )

    def register_source_manager(self, source_type: str, manager: Any):
        """Register data source manager

        Args:
            source_type (str): Type of data source
            manager (Any): Manager instance for the source type
        """
        self.source_managers[source_type] = manager

    def register_output_handler(self, destination: str, handler: Callable):
        """Register output destination handler

        Args:
            destination (str): Output destination type
            handler (Callable): Handler function for the destination
        """
        self.output_handlers[destination] = handler

    @retry_decorator(max_attempts=3, base_delay=1)
    def handle_source_data(self, message: ProcessingMessage) -> str:
        """Process incoming source data with enhanced error handling and retry logic"""
        try:
            pipeline_id = str(uuid.uuid4())
            source_type = message.source_identifier.module_name.lower()

            # Extract and validate data
            source_data = message.content.get('data')
            if not source_data:
                raise ValueError("No data provided in message")

            metadata = message.content.get('metadata', {})

            # Create pipeline metadata with enhanced tracking
            pipeline_metadata = PipelineMetadata(
                pipeline_id=pipeline_id,
                source_type=source_type,
                data_size=len(str(source_data)),
                creation_time=datetime.now(),
                source_message_id=message.message_id
            )

            # Track performance and stage data
            self.performance_tracker.track_pipeline_start(pipeline_id, message)
            staging_id = self.staging_area.stage_data(source_data, metadata)

            # Update pipeline status
            pipeline_metadata.stages_completed.append("Staged")
            self.active_pipelines[pipeline_id] = pipeline_metadata

            # Create and publish ingestion message
            ingestion_message = self._create_ingestion_message(pipeline_id, staging_id)
            self.message_broker.publish(ingestion_message)

            self.logger.info(f"Pipeline {pipeline_id} initiated for {source_type} data")
            return pipeline_id

        except Exception as e:
            self._handle_pipeline_error(pipeline_id, e)
            raise

    def _setup_message_subscriptions(self):
        """Setup message subscriptions with enhanced error handling and verification"""
        self.logger.info("Setting up message subscriptions...")

        # Define critical subscriptions
        critical_subscriptions = [
            (self.module_id.get_tag(), self._handle_internal_message),
            (f"pipeline_status.update.{self.instance_id}", self._update_pipeline_status),
            (f"user_decision.handle.{self.instance_id}", self._handle_user_decision),
            (f"source_data.ingest.{self.instance_id}", self.handle_source_data),
        ]

        successful_subscriptions = []
        failed_subscriptions = []

        for module_tag, callback in critical_subscriptions:
            try:
                # Attempt subscription with enhanced error handling
                self.message_broker.subscribe_to_module(module_tag, callback)
                successful_subscriptions.append(module_tag)
                self.logger.info(f"Successfully subscribed to {module_tag}")
            except Exception as e:
                failed_subscriptions.append((module_tag, str(e)))
                self.logger.error(f"Failed to subscribe to {module_tag}: {str(e)}")

        # Verify critical subscriptions
        self._verify_subscriptions(successful_subscriptions, failed_subscriptions)

    def _verify_subscriptions(self, successful: List[str], failed: List[tuple]):
        """Verify critical subscriptions and handle failures"""
        if failed:
            critical_failures = [tag for tag, _ in failed if "source_data" in tag or "pipeline_status" in tag]
            if critical_failures:
                raise RuntimeError(f"Critical subscription failures: {critical_failures}")
            else:
                self.logger.warning(f"Non-critical subscription failures: {failed}")

    def _verify_initialization(self):
        """Verify complete initialization of all components"""
        # Check message broker status
        broker_status = self.message_broker.get_subscription_status()

        # Verify critical modules are registered
        critical_modules = {
            f"source_data.ingest.{self.instance_id}",
            f"pipeline_status.update.{self.instance_id}",
            self.module_id.get_tag()
        }

        registered_modules = set(broker_status['registered_modules'])
        missing_critical = critical_modules - registered_modules

        if missing_critical:
            raise RuntimeError(f"Critical modules not registered: {missing_critical}")

        self.logger.info("Orchestrator initialization verified successfully")

    def _handle_internal_message(self, message: ProcessingMessage):
        """Process internal orchestrator messages

        Args:
            message (ProcessingMessage): Internal message
        """
        pass  # Implement internal message handling logic

    def _update_pipeline_status(self, message: ProcessingMessage):
        """Update pipeline status and tracking information

        Args:
            message (ProcessingMessage): Status update message
        """
        pipeline_id = message.content.get('pipeline_id')
        if pipeline_id in self.active_pipelines:
            pipeline = self.active_pipelines[pipeline_id]
            current_stage = message.source_identifier.get_tag()
            pipeline.stages_completed.append(current_stage)

            if 'status' in message.content:
                pipeline.status = message.content['status']

            if pipeline.status == ProcessingStatus.COMPLETED:
                pipeline.end_time = datetime.now()
                self.performance_tracker.finalize_pipeline_metrics(
                    pipeline_id,
                    'success'
                )

    def _handle_user_decision(self, message: ProcessingMessage):
        """Process user intervention decisions

        Args:
            message (ProcessingMessage): User decision message
        """
        pipeline_id = message.content.get('pipeline_id')
        if pipeline_id in self.active_pipelines:
            pipeline = self.active_pipelines[pipeline_id]
            decision = message.content.get('decision', {})

            pipeline.user_decisions.append(decision)

            if decision.get('proceed', False):
                next_module = self.conductor.get_next_module(pipeline_id)
                if next_module:
                    self._route_to_module(pipeline_id, next_module)
            else:
                self.logger.info(f"Pipeline {pipeline_id} paused for review")

        def _route_to_module(self, pipeline_id: str, current_module: ProcessingModule,
                             detected_issues: List[DataIssueType] = None):
            """Route pipeline to next appropriate module based on current state and issues

            Args:
                pipeline_id (str): Pipeline identifier
                current_module (ProcessingModule): Current processing module
                detected_issues (List[DataIssueType], optional): List of detected data issues
            """
            if not detected_issues:
                # Default routing path
                next_module = self.routing_graph.get(current_module, {}).get(None)
                if next_module:
                    self._publish_routing_message(pipeline_id, next_module)
                    return

            # Issue-based routing
            if detected_issues:
                for issue in detected_issues:
                    next_module = self.routing_graph.get(current_module, {}).get(issue)
                    if next_module:
                        self._publish_routing_message(pipeline_id, next_module)
                        return

            # Log warning if no routing found
            self.logger.warning(
                f"No specific routing found for module {current_module} with issues: {detected_issues}"
            )

        def _publish_routing_message(self, pipeline_id: str, destination_module: ProcessingModule):
            """Publish message to route pipeline to next module

            Args:
                pipeline_id (str): Pipeline identifier
                destination_module (ProcessingModule): Target processing module
            """
            routing_message = ProcessingMessage(
                source_identifier=self.module_id,
                message_type=MessageType.ACTION,
                content={
                    'pipeline_id': pipeline_id,
                    'destination_module': destination_module.value,
                    'action': 'route_pipeline'
                }
            )
            self.message_broker.publish(routing_message)

        def monitor_pipeline_progress(self, pipeline_id: str) -> Dict[str, Any]:
            """Monitor and report pipeline execution progress

            Args:
                pipeline_id (str): Pipeline identifier

            Returns:
                Dict[str, Any]: Current pipeline status and progress metrics
            """
            if pipeline_id not in self.active_pipelines:
                return {'error': 'Pipeline not found'}

            pipeline = self.active_pipelines[pipeline_id]

            return {
                'pipeline_id': pipeline_id,
                'status': pipeline.status,
                'stages_completed': pipeline.stages_completed,
                'start_time': pipeline.start_time,
                'current_duration': (datetime.now() - pipeline.start_time).total_seconds(),
                'data_size': pipeline.data_size,
                'user_decisions': pipeline.user_decisions,
                'recommendations': pipeline.recommendations
            }

        def handle_pipeline_error(self, pipeline_id: str, error: Exception) -> None:
            """Process pipeline errors and initiate recovery actions

            Args:
                pipeline_id (str): Pipeline identifier
                error (Exception): Encountered error
            """
            if pipeline_id not in self.active_pipelines:
                self.logger.error(f"Error in unknown pipeline: {pipeline_id}")
                return

            pipeline = self.active_pipelines[pipeline_id]

            # Record error details
            error_details = {
                'timestamp': datetime.now(),
                'error_type': type(error).__name__,
                'error_message': str(error),
                'stage': pipeline.stages_completed[-1] if pipeline.stages_completed else 'unknown'
            }

            # Generate recovery recommendation
            recommendation = self._generate_error_recommendation(error)
            pipeline.recommendations.append(recommendation)

            # Update pipeline status
            pipeline.status = ProcessingStatus.ERROR

            # Publish error notification
            error_message = ProcessingMessage(
                source_identifier=self.module_id,
                message_type=MessageType.ERROR,
                content={
                    'pipeline_id': pipeline_id,
                    'error_details': error_details,
                    'recommendations': [recommendation]
                }
            )
            self.message_broker.publish(error_message)

            self.logger.error(f"Pipeline {pipeline_id} encountered error: {str(error)}")

        def cleanup_completed_pipelines(self, age_threshold: timedelta = timedelta(hours=24)) -> None:
            """Remove completed pipelines from active tracking

            Args:
                age_threshold (timedelta, optional): Age threshold for cleanup
            """
            current_time = datetime.now()
            pipelines_to_remove = []

            for pipeline_id, pipeline in self.active_pipelines.items():
                if pipeline.end_time and (current_time - pipeline.end_time) > age_threshold:
                    pipelines_to_remove.append(pipeline_id)

            for pipeline_id in pipelines_to_remove:
                del self.active_pipelines[pipeline_id]
                self.logger.info(f"Cleaned up completed pipeline: {pipeline_id}")

        def get_pipeline_metrics(self, pipeline_id: str) -> Dict[str, Any]:
            """Retrieve detailed metrics for specific pipeline

            Args:
                pipeline_id (str): Pipeline identifier

            Returns:
                Dict[str, Any]: Comprehensive pipeline metrics
            """
            if pipeline_id not in self.active_pipelines:
                return {'error': 'Pipeline not found'}

            pipeline = self.active_pipelines[pipeline_id]

            metrics = {
                'pipeline_id': pipeline_id,
                'source_type': pipeline.source_type,
                'status': pipeline.status,
                'execution_time': None,
                'stages': pipeline.stages_completed,
                'data_size': pipeline.data_size,
                'decisions': len(pipeline.user_decisions),
                'start_time': pipeline.start_time
            }

            if pipeline.end_time:
                metrics['execution_time'] = (pipeline.end_time - pipeline.start_time).total_seconds()

            return metrics

        def get_performance_summary(self) -> Dict[str, Any]:
            """Generate comprehensive system performance report

            Returns:
                Dict[str, Any]: System-wide performance metrics
            """
            return self.performance_tracker.get_performance_summary()

        def __del__(self):
            """Cleanup resources on orchestrator deletion"""
            self.thread_pool.shutdown(wait=True)

        def create_data_orchestrator(
                message_broker: MessageBroker,
                data_conductor: DataConductor,
                staging_area: EnhancedStagingArea
        ) -> DataOrchestrator:
            """Factory function to create and configure DataOrchestrator

            Args:
                message_broker (MessageBroker): Message routing system
                data_conductor (DataConductor): Data flow controller
                staging_area (EnhancedStagingArea): Temporary data storage

            Returns:
                DataOrchestrator: Configured orchestrator instance
            """
            orchestrator = DataOrchestrator(message_broker, data_conductor, staging_area)

            # Register source managers
            source_managers = {
                "file": FileManager(message_broker),
                "api": ApiManager(message_broker),
                "cloud": S3DataManager(message_broker),
                "database": DBDataManager(message_broker),
                "stream": StreamManager(message_broker)
            }

            for source_type, manager in source_managers.items():
                orchestrator.register_source_manager(source_type, manager)

            # Register output handlers
            output_handlers = {
                "database": DatabaseOutputHandler().handle_output,
                "file": FileOutputHandler().handle_output,
                "api": APIOutputHandler().handle_output,
                "stream": StreamOutputHandler().handle_output
            }

            for destination, handler in output_handlers.items():
                orchestrator.register_output_handler(destination, handler)

            return orchestrator

    def _create_ingestion_message(self, pipeline_id: str, staging_id: str) -> ProcessingMessage:
        """Create standardized ingestion message"""
        return ProcessingMessage(
            source_identifier=self.module_id,
            message_type=MessageType.ACTION,
            content={
                'pipeline_id': pipeline_id,
                'staging_id': staging_id,
                'action': 'start_ingestion',
                'timestamp': datetime.now().isoformat()
            }
        )

    def _log_registration_summary(self, registered: List[ModuleIdentifier], failed: List[ModuleIdentifier]):
        """Log comprehensive registration summary"""
        total = len(registered) + len(failed)
        success_rate = (len(registered) / total) * 100 if total > 0 else 0

        self.logger.info(f"""
Module Registration Summary:
Total Attempted: {total}
Successfully Registered: {len(registered)} ({success_rate:.1f}%)
Failed Registrations: {len(failed)}
""")

        if failed:
            self.logger.error("Failed Modules:")
            for module in failed:
                self.logger.error(f"- {module.get_tag()}")

    def __del__(self):
        """Enhanced cleanup with logging"""
        try:
            self.thread_pool.shutdown(wait=True)
            self.logger.info("Orchestrator resources cleaned up successfully")
        except Exception as e:
            self.logger.error(f"Error during orchestrator cleanup: {str(e)}")