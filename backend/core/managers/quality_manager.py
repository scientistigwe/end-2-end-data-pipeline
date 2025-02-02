import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import asyncio

from ..messaging.broker import MessageBroker
from ..messaging.event_types import (
    MessageType,
    ProcessingMessage,
    ProcessingStage,
    ProcessingStatus,
    MessageMetadata,
    QualityContext,
    QualityState,
    ManagerState,
    QualityMetrics,
    ComponentType,
    ModuleIdentifier,
    QualityIssue,
    ResolutionResult
)
from .base.base_manager import BaseManager

logger = logging.getLogger(__name__)


class QualityManager(BaseManager):
    """
    Quality Manager that coordinates quality workflow through message broker.
    Maintains state and manages transitions through message-based communication.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            component_name: str = "quality_manager",
            domain_type: str = "quality"
    ):
        super().__init__(message_broker, component_name, domain_type)

        # Quality configuration
        self.quality_thresholds = {
            "missing_data": 0.1,
            "invalid_format": 0.05,
            "duplicate_entries": 0.01,
            "anomaly_score": 0.8
        }

    async def _setup_domain_handlers(self) -> None:
        """Setup quality-specific message handlers"""
        handlers = {
            # Core Process Flow
            MessageType.QUALITY_PROCESS_START: self._handle_process_start,
            MessageType.QUALITY_PROCESS_PROGRESS: self._handle_process_progress,
            MessageType.QUALITY_PROCESS_COMPLETE: self._handle_process_complete,
            MessageType.QUALITY_PROCESS_FAILED: self._handle_process_failed,

            # Quality Analysis Flow
            MessageType.QUALITY_CONTEXT_ANALYZE_REQUEST: self._handle_context_analysis,
            MessageType.QUALITY_DETECTION_REQUEST: self._handle_detection_request,
            MessageType.QUALITY_ANALYSE_REQUEST: self._handle_analysis_request,
            MessageType.QUALITY_RESOLUTION_REQUEST: self._handle_resolution_request,

            # Validation Flow
            MessageType.QUALITY_VALIDATE_REQUEST: self._handle_validation_request,
            MessageType.QUALITY_VALIDATE_COMPLETE: self._handle_validation_complete,
            MessageType.QUALITY_VALIDATE_REJECT: self._handle_validation_reject,

            # Issue Management
            MessageType.QUALITY_ISSUE_DETECTED: self._handle_issues_detected,
            MessageType.QUALITY_RESOLUTION_SUGGEST: self._handle_resolution_suggest,
            MessageType.QUALITY_RESOLUTION_APPLY: self._handle_resolution_apply,

            # Status and Control
            MessageType.QUALITY_STATUS_REQUEST: self._handle_status_request,
            MessageType.QUALITY_CONFIG_UPDATE: self._handle_config_update,
            MessageType.QUALITY_CLEANUP_REQUEST: self._handle_cleanup_request
        }

        for message_type, handler in handlers.items():
            await self.register_message_handler(message_type, handler)

    async def start(self) -> None:
        """Initialize and start quality manager"""
        try:
            await super().start()  # Call base start first

            # Start quality-specific monitoring
            self._start_background_task(
                self._monitor_quality_metrics(),
                "quality_metrics_monitor"
            )

        except Exception as e:
            self.logger.error(f"Quality manager start failed: {str(e)}")
            raise

    async def _monitor_quality_metrics(self) -> None:
        """Monitor quality metrics trends"""
        while not self._shutting_down:
            try:
                for pipeline_id, context in list(self.active_processes.items()):
                    quality_trends = self._calculate_quality_trends(context)
                    if self._has_concerning_trends(quality_trends):
                        await self._handle_quality_trends(pipeline_id, quality_trends)

                await asyncio.sleep(300)  # Check every 5 minutes

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Quality monitoring failed: {str(e)}")
                if not self._shutting_down:
                    await asyncio.sleep(60)

    async def _manager_specific_cleanup(self) -> None:
        """Quality-specific cleanup"""
        try:
            # Clean up any active quality processes
            for pipeline_id in list(self.active_processes.keys()):
                context = self.active_processes[pipeline_id]
                if context.state not in [QualityState.COMPLETED, QualityState.FAILED]:
                    await self._handle_process_failed(ProcessingMessage(
                        message_type=MessageType.QUALITY_PROCESS_FAILED,
                        content={
                            'pipeline_id': pipeline_id,
                            'error': 'Cleanup initiated'
                        }
                    ))
        except Exception as e:
            self.logger.error(f"Quality specific cleanup failed: {str(e)}")

    async def _handle_process_start(self, message: ProcessingMessage) -> None:
        """Handle quality process start request"""
        try:
            pipeline_id = message.content.get('pipeline_id')
            context = QualityContext(
                pipeline_id=pipeline_id,
                correlation_id=str(uuid.uuid4()),
                state=QualityState.INITIALIZING,
                stage=ProcessingStage.QUALITY_CHECK,
                metrics=QualityMetrics()
            )

            self.active_processes[pipeline_id] = context

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_CONTEXT_ANALYZE_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': message.content.get('config', {})
                    },
                    metadata=MessageMetadata(
                        source_component=self.context.component_name,
                        target_component='quality_service',
                        domain_type=self.context.domain_type
                    )
                )
            )

        except Exception as e:
            await self._handle_error(message, str(e))

    async def _handle_process_progress(self, message: ProcessingMessage) -> None:
        """Handle quality process progress updates"""
        pipeline_id = message.content.get('pipeline_id')
        progress = message.content.get('progress', 0)
        status = message.content.get('status', '')

        try:
            context = self.active_processes.get(pipeline_id)
            if not context:
                return

            # Update context progress
            context.progress = progress
            context.status = status
            context.updated_at = datetime.now()

            # Notify progress
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_PROCESS_STATE_UPDATE,
                    content={
                        'pipeline_id': pipeline_id,
                        'progress': progress,
                        'status': status
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Progress update failed: {str(e)}")

    async def _handle_context_analysis(self, message: ProcessingMessage) -> None:
        """Handle quality context analysis request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = QualityState.CONTEXT_ANALYSIS
            context.updated_at = datetime.now()

            # Begin detection phase
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_DETECTION_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'context': context.to_dict()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Context analysis failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_detection_request(self, message: ProcessingMessage) -> None:
        """Handle quality detection request"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = QualityState.DETECTION
            context.updated_at = datetime.now()

            # Request quality detection
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_DETECTION_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'thresholds': self.quality_thresholds
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Detection request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_issues_detected(self, message: ProcessingMessage) -> None:
        """Handle detected quality issues"""
        pipeline_id = message.content.get('pipeline_id')
        issues: List[QualityIssue] = message.content.get('issues', [])
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context with issues
            context.detected_issues.extend(issues)
            context.updated_at = datetime.now()

            # Check if manual intervention needed
            if self._requires_manual_intervention(issues):
                await self._request_manual_review(pipeline_id, issues)
            else:
                # Auto-resolve if possible
                await self._attempt_auto_resolution(pipeline_id, issues)

        except Exception as e:
            logger.error(f"Issues handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _requires_manual_intervention(self, issues: List[QualityIssue]) -> bool:
        """Determine if issues require manual intervention"""
        if not issues:
            return False

        critical_issues = [
            issue for issue in issues
            if issue.severity == 'critical' or not issue.auto_resolvable
        ]
        return len(critical_issues) > 0

    async def _attempt_auto_resolution(self, pipeline_id: str, issues: List[QualityIssue]) -> None:
        """Attempt automatic resolution of quality issues"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.QUALITY_RESOLUTION_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'issues': [issue.__dict__ for issue in issues],
                    'auto_resolve': True
                },
                source_identifier=self.module_identifier
            )
        )

    async def _request_manual_review(self, pipeline_id: str, issues: List[QualityIssue]) -> None:
        """Request manual review for quality issues"""
        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.CONTROL_POINT_DECISION_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'issues': [issue.__dict__ for issue in issues],
                    'requires_review': True
                },
                source_identifier=self.module_identifier
            )
        )

    async def _handle_resolution_suggest(self, message: ProcessingMessage) -> None:
        """Handle resolution suggestions for quality issues"""
        pipeline_id = message.content.get('pipeline_id')
        suggestions = message.content.get('suggestions', [])
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context
            context.resolution_suggestions = suggestions
            context.updated_at = datetime.now()

            # Request resolution application
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_RESOLUTION_APPLY,
                    content={
                        'pipeline_id': pipeline_id,
                        'suggestions': suggestions
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Resolution suggestion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_resolution_apply(self, message: ProcessingMessage) -> None:
        """Handle resolution application results"""
        pipeline_id = message.content.get('pipeline_id')
        results: List[ResolutionResult] = message.content.get('results', [])
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context with resolution results
            context.applied_resolutions.extend(results)
            context.updated_at = datetime.now()

            # Check if all issues resolved
            if self._all_issues_resolved(context):
                await self._complete_quality_check(pipeline_id)
            else:
                # Request further validation
                await self._request_validation(pipeline_id)

        except Exception as e:
            logger.error(f"Resolution application handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    def _all_issues_resolved(self, context: QualityContext) -> bool:
        """Check if all quality issues are resolved"""
        return len(context.detected_issues) == len(context.applied_resolutions)

    async def _complete_quality_check(self, pipeline_id: str) -> None:
        """Complete quality check process"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        try:
            # Update context state
            context.state = QualityState.COMPLETED
            context.completed_at = datetime.now()

            # Notify completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_PROCESS_COMPLETE,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': context.metrics.__dict__,
                        'results': {
                            'issues_detected': len(context.detected_issues),
                            'issues_resolved': len(context.applied_resolutions),
                            'completion_time': context.completed_at.isoformat()
                        }
                    },
                    source_identifier=self.module_identifier
                )
            )

            # Cleanup process
            await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Quality check completion failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _request_resolution(self, pipeline_id: str, validation_results: Dict[str, Any]) -> None:
        """Request resolution based on validation results"""
        context = self.active_processes.get(pipeline_id)
        if not context:
            return

        await self.message_broker.publish(
            ProcessingMessage(
                message_type=MessageType.QUALITY_RESOLUTION_REQUEST,
                content={
                    'pipeline_id': pipeline_id,
                    'validation_results': validation_results,
                    'context': context.to_dict()
                },
                source_identifier=self.module_identifier
            )
        )

    async def _handle_cleanup_request(self, message: ProcessingMessage) -> None:
        """Handle cleanup requests for quality processes"""
        pipeline_id = message.content.get('pipeline_id')

        try:
            await self._cleanup_process(pipeline_id)

            # Notify cleanup completion
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_CLEANUP_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': 'completed',
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Cleanup request failed: {str(e)}")

    async def _handle_config_update(self, message: ProcessingMessage) -> None:
        """Handle quality configuration updates"""
        config_updates = message.content.get('config', {})

        try:
            # Update quality thresholds
            if thresholds := config_updates.get('thresholds'):
                self.quality_thresholds.update(thresholds)

            # Notify config update
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_CONFIG_UPDATE,
                    content={
                        'status': 'completed',
                        'updates': config_updates,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Config update failed: {str(e)}")

    async def _handle_status_request(self, message: ProcessingMessage) -> None:
        """Handle status requests for quality processes"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        try:
            if context:
                status_info = {
                    'state': context.state.value,
                    'progress': context.progress,
                    'metrics': context.metrics.__dict__,
                    'issues_count': len(context.detected_issues),
                    'resolutions_count': len(context.applied_resolutions),
                    'last_updated': context.updated_at.isoformat()
                }
            else:
                status_info = {
                    'state': 'not_found',
                    'error': f'No active process for pipeline {pipeline_id}'
                }

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_STATUS_REQUEST,
                    content={
                        'pipeline_id': pipeline_id,
                        'status': status_info,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_identifier=self.module_identifier
                )
            )

        except Exception as e:
            logger.error(f"Status request failed: {str(e)}")

    def _exceeds_resource_limits(self, metrics: Dict[str, float]) -> bool:
        """Check if resource metrics exceed limits"""
        return any([
            metrics.get('cpu_percent', 0) > 90,
            metrics.get('memory_percent', 0) > 85
        ])

    async def _handle_resource_violation(self, pipeline_id: str, metrics: Dict[str, float]) -> None:
        """Handle resource limit violations"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_RESOURCE_ALERT,
                    content={
                        'pipeline_id': pipeline_id,
                        'metrics': metrics,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_component=self.component_name
                )
            )
        except Exception as e:
            logger.error(f"Resource violation handling failed: {str(e)}")

    def _calculate_quality_trends(self, context: QualityContext) -> Dict[str, Any]:
        """Calculate trends in quality metrics"""
        return {
            'issue_rate': len(context.detected_issues) / max(1, context.metrics.total_issues),
            'resolution_rate': len(context.applied_resolutions) / max(1, len(context.detected_issues)),
            'validation_rate': context.metrics.validation_rate,
            'average_severity': context.metrics.average_severity
        }

    def _has_concerning_trends(self, trends: Dict[str, Any]) -> bool:
        """Check for concerning quality trends"""
        return any([
            trends.get('issue_rate', 0) > 0.3,  # More than 30% issues
            trends.get('resolution_rate', 1) < 0.7,  # Less than 70% resolution
            trends.get('validation_rate', 1) < 0.8  # Less than 80% validation
        ])

    async def _handle_quality_trends(self, pipeline_id: str, trends: Dict[str, Any]) -> None:
        """Handle concerning quality trends"""
        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_ALERT_NOTIFY,
                    content={
                        'pipeline_id': pipeline_id,
                        'trends': trends,
                        'timestamp': datetime.now().isoformat()
                    },
                    source_component=self.component_name
                )
            )
        except Exception as e:
            logger.error(f"Quality trends handling failed: {str(e)}")

    async def _handle_validation_request(self, message: ProcessingMessage) -> None:
        """Handle validation request for quality checks"""
        pipeline_id = message.content.get('pipeline_id')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            # Update context state
            context.state = QualityState.VALIDATION
            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_VALIDATE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'context': context.to_dict()
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component='quality_service'
                    )
                )
            )

        except Exception as e:
            logger.error(f"Validation request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validation_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of validation process"""
        pipeline_id = message.content.get('pipeline_id')
        validation_results = message.content.get('results', {})
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            if validation_results.get('passed', False):
                await self._complete_quality_check(pipeline_id)
            else:
                await self._request_resolution(pipeline_id, validation_results)

        except Exception as e:
            logger.error(f"Validation completion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_validation_reject(self, message: ProcessingMessage) -> None:
        """Handle validation rejection"""
        pipeline_id = message.content.get('pipeline_id')
        rejection_reason = message.content.get('reason', '')
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            context.updated_at = datetime.now()
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_PROCESS_FAILED,
                    content={
                        'pipeline_id': pipeline_id,
                        'error': f"Validation rejected: {rejection_reason}"
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component='quality_service'
                    )
                )
            )

        except Exception as e:
            logger.error(f"Validation rejection handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_analysis_request(self, message: ProcessingMessage) -> None:
        """Handle quality analysis request"""
        pipeline_id = message.content.get('pipeline_id')
        analysis_config = message.content.get('config', {})
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            context.state = QualityState.ANALYSIS
            context.updated_at = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_ANALYSE_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'config': analysis_config
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component='quality_service'
                    )
                )
            )

        except Exception as e:
            logger.error(f"Analysis request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_resolution_request(self, message: ProcessingMessage) -> None:
        """Handle resolution request for quality issues"""
        pipeline_id = message.content.get('pipeline_id')
        resolution_data = message.content.get('resolution', {})
        context = self.active_processes.get(pipeline_id)

        if not context:
            return

        try:
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.QUALITY_RESOLUTION_START,
                    content={
                        'pipeline_id': pipeline_id,
                        'resolution': resolution_data
                    },
                    metadata=MessageMetadata(
                        source_component=self.component_name,
                        target_component='quality_service'
                    )
                )
            )

        except Exception as e:
            logger.error(f"Resolution request failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_process_complete(self, message: ProcessingMessage) -> None:
        """Handle completion of quality process"""
        pipeline_id = message.content.get('pipeline_id')

        try:
            context = self.active_processes.get(pipeline_id)
            if context:
                context.state = QualityState.COMPLETED
                context.completed_at = datetime.now()

                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.QUALITY_PROCESS_COMPLETE,
                        content={
                            'pipeline_id': pipeline_id,
                            'status': 'success',
                            'completion_time': context.completed_at.isoformat()
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component='pipeline_manager'
                        )
                    )
                )

                await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Process completion handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

    async def _handle_process_failed(self, message: ProcessingMessage) -> None:
        """Handle quality process failure"""
        pipeline_id = message.content.get('pipeline_id')
        error_details = message.content.get('error', 'Unknown error')

        try:
            context = self.active_processes.get(pipeline_id)
            if context:
                context.state = QualityState.FAILED
                context.error = error_details

                await self.message_broker.publish(
                    ProcessingMessage(
                        message_type=MessageType.QUALITY_PROCESS_FAILED,
                        content={
                            'pipeline_id': pipeline_id,
                            'error': error_details,
                            'timestamp': datetime.now().isoformat()
                        },
                        metadata=MessageMetadata(
                            source_component=self.component_name,
                            target_component='pipeline_manager'
                        )
                    )
                )

                await self._cleanup_process(pipeline_id)

        except Exception as e:
            logger.error(f"Process failure handling failed: {str(e)}")
            await self._handle_error(pipeline_id, str(e))

