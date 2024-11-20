# core/staging/staging_area.py

from dataclasses import dataclass, field, replace
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
import uuid
import logging

from backend.core.metrics.metrics_manager import MetricsManager
from backend.core.messaging.broker import MessageBroker
from backend.core.messaging.types import (
    ModuleIdentifier,
    ProcessingMessage,
    MessageType,
    ProcessingStatus
)


@dataclass
class DataQualityCheck:
    """Comprehensive data quality check configuration"""
    name: str
    check_function: Callable[[Any], bool]
    severity: str = 'warning'
    description: Optional[str] = None
    last_run: Optional[datetime] = None
    failures: int = 0


@dataclass
class StagingMetadata:
    """Enhanced metadata for staged data with quality tracking"""
    source_module: ModuleIdentifier
    stage_id: str
    data_type: str
    format: str
    size_bytes: int
    row_count: Optional[int]
    columns: Optional[List[str]]
    tags: Dict[str, str]
    quality_score: float = 1.0
    processing_chain: List[str] = field(default_factory=list)
    quality_checks: List[DataQualityCheck] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    retention_period: Optional[timedelta] = field(default_factory=lambda: timedelta(days=7))




class EnhancedStagingArea:
    """
    Advanced staging area with comprehensive data management,
    quality checks, and intelligent routing
    """

    def __init__(self, message_broker: MessageBroker):
        # Core staging storage
        self.staging_area: Dict[str, Dict[str, Any]] = {}

        # Messaging and tracking
        self.message_broker = message_broker

        # Create module identifiers for registration
        self.module_id = ModuleIdentifier("StagingArea", "manage_data")
        self.data_staged_module = ModuleIdentifier("StagingArea", "data_staged")
        self.quality_check_module = ModuleIdentifier("StagingArea", "quality_check")

        # Logging and monitoring
        self.logger = logging.getLogger(__name__)

        # Quality and performance metrics
        self.metrics_manager = MetricsManager()

        # Register modules with message broker
        self.message_broker.register_module(self.module_id)
        self.message_broker.register_module(self.data_staged_module)
        self.message_broker.register_module(self.quality_check_module)

        # Setup message subscriptions
        self._setup_message_subscriptions()


    def _setup_message_subscriptions(self):
        """Set up message subscriptions for staging area events"""
        subscriptions = [
            (self.data_staged_module.get_tag(), self._handle_data_staged),
            (self.quality_check_module.get_tag(), self._run_quality_checks)
        ]

        for tag, handler in subscriptions:
            self.message_broker.subscribe_to_module(tag, handler)


    def stage_data(self, data: Any, metadata: StagingMetadata) -> str:
        """
        Stage data with comprehensive quality checks and tracking

        Returns:
            Staging ID for the staged data
        """
        # Generate unique staging ID
        staging_id = metadata.stage_id or str(uuid.uuid4())

        # Run initial quality checks
        quality_checks = self._setup_quality_checks(metadata)
        metadata = replace(metadata, quality_checks=quality_checks)

        # Run quality checks
        quality_results = self._run_quality_checks(data, metadata)

        # Update metadata with quality results
        metadata.quality_score = quality_results['overall_score']

        # Store staged data
        self.staging_area[staging_id] = {
            "data": data,
            "metadata": metadata,
            "status": ProcessingStatus.STAGED
        }

        # Update metrics
        self.metrics_manager.increment_metric('total_staged_data')
        self.metrics_manager.update_average_metric(
            'data_quality_avg_score',
            overall_score,
            self.metrics_manager.get_metric('total_staged_data', 1)
        )

        # Publish staging message
        staging_message = ProcessingMessage(
            source_identifier=self.module_id,
            message_type=MessageType.STATUS_UPDATE,
            content={
                'staging_id': staging_id,
                'quality_score': metadata.quality_score,
                'data_type': metadata.data_type
            }
        )
        self.message_broker.publish(staging_message)

        return staging_id


    def _setup_quality_checks(self, metadata: StagingMetadata) -> List[DataQualityCheck]:
        """
        Configure default and custom quality checks based on data type
        """
        default_checks = [
            DataQualityCheck(
                name='size_check',
                check_function=lambda data: metadata.size_bytes > 0,
                description='Ensure data is not empty'
            ),
            DataQualityCheck(
                name='type_check',
                check_function=lambda data: isinstance(data, type(data)),
                description='Verify data type consistency'
            )
        ]

        # TODO: Add more specific checks based on data_type and format

        return default_checks


    def _run_quality_checks(self, data: Any, metadata: StagingMetadata) -> Dict[str, Any]:
        """
        Run comprehensive data quality checks

        Args:
            data: Data to be checked
            metadata: Metadata associated with the data

        Returns:
            Detailed quality check results with overall score and individual check details
        """
        check_results = []
        failed_checks = []
        check_scores = []

        # Run default quality checks
        for quality_check in metadata.quality_checks:
            try:
                # Execute the quality check
                check_passed = quality_check.check_function(data)

                # Determine check score based on severity
                if check_passed:
                    check_score = 1.0
                    check_status = 'PASSED'
                else:
                    # Different severity levels impact scoring
                    if quality_check.severity == 'critical':
                        check_score = 0.0
                    elif quality_check.severity == 'warning':
                        check_score = 0.5
                    else:
                        check_score = 0.75

                    check_status = 'FAILED'
                    failed_checks.append(quality_check)

                    # Log the failure
                    self.logger.warning(
                        f"Quality check failed: {quality_check.name} - "
                        f"Severity: {quality_check.severity}"
                    )

                # Compile check result
                check_result = {
                    'name': quality_check.name,
                    'passed': check_passed,
                    'status': check_status,
                    'severity': quality_check.severity,
                    'description': quality_check.description,
                    'score': check_score
                }
                check_results.append(check_result)
                check_scores.append(check_score)

                # Update check metadata
                quality_check.last_run = datetime.now()
                if not check_passed:
                    quality_check.failures += 1

            except Exception as e:
                # Handle unexpected errors during quality check
                error_result = {
                    'name': quality_check.name,
                    'passed': False,
                    'status': 'ERROR',
                    'severity': 'critical',
                    'description': f"Check execution failed: {str(e)}",
                    'score': 0.0
                }
                check_results.append(error_result)
                failed_checks.append(quality_check)

                self.logger.error(
                    f"Quality check {quality_check.name} failed with error: {e}"
                )

        # Calculate overall quality score
        total_checks = len(metadata.quality_checks)
        overall_score = (
            sum(check_scores) / total_checks
            if total_checks > 0
            else 1.0
        )

        # Update global metrics
        self.metrics['quality_check_failures'] += len(failed_checks)
        self.metrics['data_quality_avg_score'] = (
                                                         self.metrics['data_quality_avg_score'] *
                                                         (self.metrics['total_staged_data'] - 1) /
                                                         self.metrics['total_staged_data']
                                                 ) + (overall_score / self.metrics['total_staged_data'])

        # Prepare comprehensive results
        quality_results = {
            'overall_score': overall_score,
            'total_checks': total_checks,
            'passed_checks': total_checks - len(failed_checks),
            'failed_checks': len(failed_checks),
            'check_results': check_results,
            'failed_check_details': [
                {
                    'name': check.name,
                    'severity': check.severity,
                    'description': check.description
                } for check in failed_checks
            ]
        }

        return quality_results


    def update_staging_status(self, staging_id: str, status: ProcessingStatus,
                              additional_metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Update the status of staged data and broadcast status change

        Args:
            staging_id: Unique identifier for staged data
            status: New processing status
            additional_metadata: Optional additional metadata to update
        """
        if staging_id not in self.staging_area:
            self.logger.error(f"Staging ID {staging_id} not found")
            return

        # Retrieve current staging entry
        staging_entry = self.staging_area[staging_id]
        metadata = staging_entry['metadata']

        # Update metadata
        if additional_metadata:
            metadata = replace(metadata, **additional_metadata)

        # Update status
        staging_entry['status'] = status
        staging_entry['metadata'] = metadata

        # Broadcast status change message
        status_message = ProcessingMessage(
            source_identifier=self.module_id,
            message_type=MessageType.STATUS_UPDATE,
            content={
                'staging_id': staging_id,
                'status': status,
                'metadata': metadata.__dict__
            }
        )
        self.message_broker.publish(status_message)


    def get_staged_data(self, staging_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve staged data by its staging ID

        Args:
            staging_id: Unique identifier for staged data

        Returns:
            Dictionary containing staged data and metadata, or None if not found
        """
        return self.staging_area.get(staging_id)


    def cleanup_expired_data(self) -> None:
        """
        Remove staged data that has exceeded its retention period
        """
        current_time = datetime.now()
        expired_ids = [
            sid for sid, entry in self.staging_area.items()
            if current_time - entry['metadata'].created_at > entry['metadata'].retention_period
        ]

        for staging_id in expired_ids:
            del self.staging_area[staging_id]
            self.metrics['total_staged_data'] -= 1

            # Log cleanup
            self.logger.info(f"Removed expired staging data: {staging_id}")


    def _handle_data_staged(self, message: ProcessingMessage) -> None:
        """
        Handle incoming data staging events from message broker
        """
        try:
            # Extract staging details from message
            staging_data = message.content

            # Validate incoming data
            if not all(key in staging_data for key in ['data', 'metadata']):
                raise ValueError("Invalid staging message format")

            # Stage the data
            self.stage_data(
                data=staging_data['data'],
                metadata=staging_data['metadata']
            )
        except Exception as e:
            self.logger.error(f"Error handling staged data: {e}")
            # Optionally, publish an error message
            error_message = ProcessingMessage(
                source_identifier=self.module_id,
                message_type=MessageType.ERROR,
                content={'error': str(e)}
            )
            self.message_broker.publish(error_message)
