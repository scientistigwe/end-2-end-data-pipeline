"""
Enhanced QualityProcessor with message-based architecture and comprehensive quality management.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from core.messaging.broker import MessageBroker
from core.messaging.event_types import (
    QualityMessageType, QualityState, QualityCheckType,
    QualityIssueType, ResolutionType, QualityContext,
    QualityIssue, ResolutionResult, ModuleIdentifier,
    ComponentType, ProcessingMessage, MessageMetadata
)

from .analyzers import (
    basic_analyzer, address_analyzer, code_analyzer,
    datetime_analyzer, domain_analyzer, id_analyzer,
    numeric_analyzer, text_analyzer
)

from .detectors import (
    basic_data_validation, address_location,
    code_classification, date_time_processing,
    domain_specific_validation, duplication_management,
    identifier_processing, numeric_currency_processing,
    text_standardization
)

from .resolvers import (
    basic_resolver, address_resolver, code_resolver,
    datetime_resolver, domain_resolver, id_resolver,
    numeric_resolver, text_resolver
)

logger = logging.getLogger(__name__)


class QualityProcessor:
    """Enhanced quality processor with comprehensive quality management"""

    def __init__(self, message_broker: MessageBroker):
        self.message_broker = message_broker
        self.active_processes: Dict[str, QualityContext] = {}

        self.module_identifier = ModuleIdentifier(
            component_name="quality_processor",
            component_type=ComponentType.QUALITY_PROCESSOR,
            department="quality",
            role="processor"
        )

        self._initialize_registries()
        self._setup_subscriptions()

    def _initialize_registries(self) -> None:
        """Initialize comprehensive module registries"""
        self.detectors = {
            QualityCheckType.BASIC_VALIDATION: basic_data_validation,
            QualityCheckType.ADDRESS_LOCATION: address_location,
            QualityCheckType.CODE_CLASSIFICATION: code_classification,
            QualityCheckType.DATETIME_PROCESSING: date_time_processing,
            QualityCheckType.DOMAIN_VALIDATION: domain_specific_validation,
            QualityCheckType.IDENTIFIER_CHECK: identifier_processing,
            QualityCheckType.NUMERIC_CURRENCY: numeric_currency_processing,
            QualityCheckType.TEXT_STANDARD: text_standardization
        }

        self.analyzers = {
            QualityCheckType.BASIC_VALIDATION: basic_analyzer,
            QualityCheckType.ADDRESS_LOCATION: address_analyzer,
            QualityCheckType.CODE_CLASSIFICATION: code_analyzer,
            QualityCheckType.DATETIME_PROCESSING: datetime_analyzer,
            QualityCheckType.DOMAIN_VALIDATION: domain_analyzer,
            QualityCheckType.IDENTIFIER_CHECK: id_analyzer,
            QualityCheckType.NUMERIC_CURRENCY: numeric_analyzer,
            QualityCheckType.TEXT_STANDARD: text_analyzer
        }

        self.resolvers = {
            QualityCheckType.BASIC_VALIDATION: basic_resolver,
            QualityCheckType.ADDRESS_LOCATION: address_resolver,
            QualityCheckType.CODE_CLASSIFICATION: code_resolver,
            QualityCheckType.DATETIME_PROCESSING: datetime_resolver,
            QualityCheckType.DOMAIN_VALIDATION: domain_resolver,
            QualityCheckType.IDENTIFIER_CHECK: id_resolver,
            QualityCheckType.NUMERIC_CURRENCY: numeric_resolver,
            QualityCheckType.TEXT_STANDARD: text_resolver
        }

    async def _setup_subscriptions(self) -> None:
        """Setup comprehensive message subscriptions"""
        handlers = {
            # Core Process Flow
            QualityMessageType.QUALITY_PROCESS_START: self._handle_process_start,
            QualityMessageType.QUALITY_CONTEXT_ANALYZE_REQUEST: self._handle_context_analysis,

            # Detection and Analysis
            QualityMessageType.QUALITY_DETECTION_START: self._handle_detection_start,
            QualityMessageType.QUALITY_ISSUE_ANALYZE: self._handle_issue_analysis,

            # Resolution Management
            QualityMessageType.QUALITY_RESOLUTION_REQUEST: self._handle_resolution_request,
            QualityMessageType.QUALITY_RESOLUTION_APPLY: self._handle_resolution_apply,

            # Validation
            QualityMessageType.QUALITY_VALIDATE_REQUEST: self._handle_validation_request,

            # Reporting
            QualityMessageType.QUALITY_REPORT_GENERATE: self._handle_report_generation
        }

        for message_type, handler in handlers.items():
            await self.message_broker.subscribe(
                self.module_identifier,
                f"quality.{message_type.value}",
                handler
            )

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle quality process initialization"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = QualityContext(
                pipeline_id=pipeline_id,
                enabled_checks=message.content.get("enabled_checks", []),
                validation_rules=message.content.get("validation_rules", {})
            )
            self.active_processes[pipeline_id] = context

            await self._publish_status_update(
                pipeline_id,
                QualityState.INITIALIZING,
                "Starting quality analysis"
            )

            await self._initiate_context_analysis(pipeline_id, message.content)

        except Exception as e:
            logger.error(f"Process start failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_context_analysis(self, message: ProcessingMessage) -> None:
        """Handle data context analysis"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(QualityState.CONTEXT_ANALYSIS)

            # Profile data
            data = message.content.get("data")
            profile_results = await self._profile_data(data)
            context.column_profiles = profile_results

            # Identify relationships
            relationships = await self._identify_relationships(data)
            context.relationships = relationships

            # Determine required checks
            required_checks = self._determine_required_checks(context)
            context.enabled_checks.extend(required_checks)

            await self._initiate_quality_detection(pipeline_id, context)

        except Exception as e:
            logger.error(f"Context analysis failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_detection_start(self, message: ProcessingMessage) -> None:
        """Handle quality issue detection"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(QualityState.DETECTION)

            data = message.content.get("data")
            detected_issues = {}

            for check_type in context.enabled_checks:
                detector = self.detectors.get(check_type)
                if detector:
                    issues = await self._detect_issues(detector, data, check_type)
                    if issues:
                        detected_issues[check_type.value] = issues

            context.detected_issues = detected_issues

            if detected_issues:
                await self._initiate_issue_analysis(pipeline_id)
            else:
                await self._publish_completion(pipeline_id)

        except Exception as e:
            logger.error(f"Detection failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_issue_analysis(self, message: ProcessingMessage) -> None:
        """Handle analysis of detected issues"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(QualityState.ANALYSIS)

            analysis_results = {}
            for check_type_str, issues in context.detected_issues.items():
                check_type = QualityCheckType(check_type_str)
                analyzer = self.analyzers.get(check_type)
                if analyzer:
                    analysis = await analyzer.analyze(issues)
                    analysis_results[check_type_str] = analysis

            # Determine resolutions
            resolutions = await self._determine_resolutions(analysis_results)
            context.resolution_config = resolutions

            await self._initiate_resolution(pipeline_id)

        except Exception as e:
            logger.error(f"Issue analysis failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_resolution_apply(self, message: ProcessingMessage) -> None:
        """Handle resolution application"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(QualityState.RESOLUTION)

            data = message.content.get("data")
            resolution_results = []

            for check_type_str, resolutions in context.resolution_config.items():
                check_type = QualityCheckType(check_type_str)
                resolver = self.resolvers.get(check_type)
                if resolver:
                    result = await resolver.apply(data, resolutions)
                    resolution_results.append(result)

            context.applied_resolutions = resolution_results

            await self._initiate_validation(pipeline_id)

        except Exception as e:
            logger.error(f"Resolution application failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _handle_validation_request(self, message: ProcessingMessage) -> None:
        """Handle validation of applied resolutions"""
        pipeline_id = message.content["pipeline_id"]
        try:
            context = self.active_processes[pipeline_id]
            context.update_state(QualityState.VALIDATION)

            data = message.content.get("data")
            validation_results = await self._validate_resolutions(
                data, context.applied_resolutions
            )

            context.validation_results = validation_results

            if all(result["valid"] for result in validation_results):
                await self._publish_completion(pipeline_id)
            else:
                await self._handle_validation_failure(pipeline_id, validation_results)

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            await self._publish_error(pipeline_id, str(e))

    async def _publish_status_update(
            self,
            pipeline_id: str,
            state: QualityState,
            message: str
    ) -> None:
        """Publish quality status update"""
        status_message = ProcessingMessage(
            message_type=QualityMessageType.QUALITY_PROCESS_PROGRESS,
            content={
                "pipeline_id": pipeline_id,
                "state": state.value,
                "message": message,
                "timestamp": datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                correlation_id=pipeline_id,
                source_component=self.module_identifier.component_name
            ),
            source_identifier=self.module_identifier
        )
        await self.message_broker.publish(status_message)

    async def _publish_completion(self, pipeline_id: str) -> None:
        """Publish quality process completion"""
        context = self.active_processes[pipeline_id]
        message = ProcessingMessage(
            message_type=QualityMessageType.QUALITY_PROCESS_COMPLETE,
            content={
                "pipeline_id": pipeline_id,
                "summary": {
                    "total_issues": len(context.detected_issues),
                    "resolved_issues": len(context.applied_resolutions),
                    "validation_status": "passed" if context.validation_results else "failed"
                },
                "timestamp": datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                correlation_id=pipeline_id,
                source_component=self.module_identifier.component_name
            ),
            source_identifier=self.module_identifier
        )
        await self.message_broker.publish(message)

    async def _publish_error(self, pipeline_id: str, error: str) -> None:
        """Publish quality process error"""
        message = ProcessingMessage(
            message_type=QualityMessageType.QUALITY_PROCESS_FAILED,
            content={
                "pipeline_id": pipeline_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            },
            metadata=MessageMetadata(
                correlation_id=pipeline_id,
                source_component=self.module_identifier.component_name
            ),
            source_identifier=self.module_identifier
        )
        await self.message_broker.publish(message)

    async def cleanup(self) -> None:
        """Cleanup quality processor resources"""
        try:
            # Export any unfinished quality reports
            for context in self.active_processes.values():
                if context.detected_issues:
                    await self._handle_report_generation(
                        ProcessingMessage(
                            message_type=QualityMessageType.QUALITY_REPORT_GENERATE,
                            content={"pipeline_id": context.pipeline_id}
                        )
                    )

            # Clear active processes
            self.active_processes.clear()

        except Exception as e:
            logger.error(f"Quality processor cleanup failed: {str(e)}")
            raise