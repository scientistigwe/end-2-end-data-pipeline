import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
from dataclasses import dataclass
import pandas as pd
import numpy as np
from pathlib import Path
import json

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    QualityContext,
    QualityState,
    QualityIssueType,
    MessageMetadata,
    ComponentState
)
from ...config.settings import Settings
from ...utils.metrics import MetricsCollector
from ..base.base_service import BaseService

logger = logging.getLogger(__name__)

@dataclass
class MonitoringResult:
    """Result of a quality monitoring check"""
    check_id: str
    timestamp: datetime
    status: str
    metrics: Dict[str, Any]
    alerts: List[Dict[str, Any]]

class QualityMonitor(BaseService):
    """Service for monitoring data quality in real-time"""

    def __init__(
        self,
        message_broker: MessageBroker,
        settings: Settings,
        metrics_collector: MetricsCollector,
        component_name: str = "quality_monitor",
        domain_type: str = "quality"
    ):
        # Call base class initialization first
        super().__init__(
            message_broker=message_broker,
            settings=settings,
            metrics_collector=metrics_collector,
            component_name=component_name,
            domain_type=domain_type
        )

        # Monitor configuration
        self.monitor_config = settings.get("quality_monitoring", {})
        self.check_interval = self.monitor_config.get("check_interval", 300)  # 5 minutes
        self.alert_thresholds = self.monitor_config.get("alert_thresholds", {})
        self.max_retries = self.monitor_config.get("max_retries", 3)
        self.timeout_seconds = self.monitor_config.get("timeout_seconds", 60)
        
        # Monitor state tracking
        self.active_monitors: Dict[str, Dict[str, Any]] = {}
        self.monitoring_metrics: Dict[str, Any] = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "total_alerts": 0,
            "active_alerts": 0
        }

        # Initialize monitoring tasks
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}

    async def _initialize_service(self) -> None:
        """Initialize the quality monitor service"""
        try:
            # Set up message handlers
            await self._setup_message_handlers()
            
            # Initialize metrics
            await self._initialize_metrics()
            
            # Set service state
            self.state = ComponentState.ACTIVE
            
            logger.info(f"Quality Monitor initialized successfully: {self.component_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Quality Monitor: {str(e)}")
            self.state = ComponentState.ERROR
            raise

    async def _setup_message_handlers(self) -> None:
        """Set up message handlers for quality monitoring operations"""
        # Core monitoring handlers
        self.handlers.update({
            MessageType.QUALITY_MONITOR_START: self._handle_monitor_start,
            MessageType.QUALITY_MONITOR_STOP: self._handle_monitor_stop,
            MessageType.QUALITY_MONITOR_STATUS: self._handle_monitor_status,
            MessageType.QUALITY_MONITOR_UPDATE: self._handle_monitor_update,
            
            # Alert handlers
            MessageType.QUALITY_ALERT_CREATE: self._handle_alert_create,
            MessageType.QUALITY_ALERT_RESOLVE: self._handle_alert_resolve,
            MessageType.QUALITY_ALERT_UPDATE: self._handle_alert_update,
            
            # Status and reporting handlers
            MessageType.QUALITY_STATUS_REQUEST: self._handle_status_request,
            
            # System operation handlers
            MessageType.QUALITY_CONFIG_UPDATE: self._handle_config_update,
            MessageType.QUALITY_RESOURCE_REQUEST: self._handle_resource_request
        })

    async def _handle_monitor_start(self, message: ProcessingMessage) -> None:
        """Handle monitor start request"""
        try:
            pipeline_id = message.content.get("pipeline_id")
            if not pipeline_id:
                raise ValueError("Missing pipeline_id in request")

            # Create monitor context
            monitor_context = {
                "pipeline_id": pipeline_id,
                "state": QualityState.MONITORING,
                "start_time": datetime.now(),
                "check_interval": message.content.get("check_interval", self.check_interval),
                "alert_thresholds": message.content.get("alert_thresholds", self.alert_thresholds),
                "active_alerts": [],
                "retry_count": 0
            }
            
            # Store context
            self.active_monitors[pipeline_id] = monitor_context
            
            # Start monitoring task
            self.monitoring_tasks[pipeline_id] = asyncio.create_task(
                self._monitor_pipeline(pipeline_id)
            )
            
            # Send success response
            await self._send_success_response(
                message=message,
                content={
                    "pipeline_id": pipeline_id,
                    "status": "monitoring_started",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_MONITOR_STATUS
            )
            
        except Exception as e:
            logger.error(f"Error starting monitor: {str(e)}")
            await self._send_error_response(
                message=message,
                error=str(e),
                response_type=MessageType.QUALITY_MONITOR_STATUS
            )

    async def _handle_monitor_stop(self, message: ProcessingMessage) -> None:
        """Handle monitor stop request"""
        try:
            pipeline_id = message.content.get("pipeline_id")
            if not pipeline_id:
                raise ValueError("Missing pipeline_id in request")

            # Stop monitoring task
            if pipeline_id in self.monitoring_tasks:
                self.monitoring_tasks[pipeline_id].cancel()
                del self.monitoring_tasks[pipeline_id]
            
            # Clean up monitor context
            if pipeline_id in self.active_monitors:
                del self.active_monitors[pipeline_id]
            
            # Send success response
            await self._send_success_response(
                message=message,
                content={
                    "pipeline_id": pipeline_id,
                    "status": "monitoring_stopped",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_MONITOR_STATUS
            )
            
        except Exception as e:
            logger.error(f"Error stopping monitor: {str(e)}")
            await self._send_error_response(
                message=message,
                error=str(e),
                response_type=MessageType.QUALITY_MONITOR_STATUS
            )

    async def _monitor_pipeline(self, pipeline_id: str) -> None:
        """Monitor pipeline quality"""
        try:
            context = self.active_monitors.get(pipeline_id)
            if not context:
                raise ValueError(f"No active context found for pipeline: {pipeline_id}")

            while True:
                try:
                    # Perform quality check
                    result = await self._perform_quality_check(pipeline_id)
                    
                    # Update metrics
                    self.monitoring_metrics["total_checks"] += 1
                    if result.status == "passed":
                        self.monitoring_metrics["passed_checks"] += 1
                    else:
                        self.monitoring_metrics["failed_checks"] += 1
                    
                    # Process alerts
                    await self._process_alerts(pipeline_id, result)
                    
                    # Send status update
                    await self._send_success_response(
                        message=ProcessingMessage(
                            message_type=MessageType.QUALITY_MONITOR_UPDATE,
                            content={
                                "pipeline_id": pipeline_id,
                                "check_id": result.check_id,
                                "status": result.status,
                                "timestamp": datetime.now().isoformat()
                            }
                        ),
                        content={
                            "pipeline_id": pipeline_id,
                            "check_id": result.check_id,
                            "status": result.status,
                            "metrics": result.metrics,
                            "alerts": result.alerts,
                            "timestamp": datetime.now().isoformat()
                        },
                        response_type=MessageType.QUALITY_MONITOR_UPDATE
                    )
                    
                    # Wait for next check
                    await asyncio.sleep(context["check_interval"])
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {str(e)}")
                    await asyncio.sleep(5)  # Wait before retry
                    
        except Exception as e:
            logger.error(f"Error monitoring pipeline: {str(e)}")
            await self._handle_monitor_failed(pipeline_id, str(e))

    async def _perform_quality_check(self, pipeline_id: str) -> MonitoringResult:
        """Perform quality check"""
        try:
            check_id = str(uuid.uuid4())
            
            # Get quality data
            quality_data = await self._get_quality_data(pipeline_id)
            
            # Calculate metrics
            metrics = await self._calculate_metrics(quality_data)
            
            # Check thresholds
            alerts = await self._check_thresholds(pipeline_id, metrics)
            
            # Determine status
            status = "passed" if not alerts else "failed"
            
            return MonitoringResult(
                check_id=check_id,
                timestamp=datetime.now(),
                status=status,
                metrics=metrics,
                alerts=alerts
            )
            
        except Exception as e:
            logger.error(f"Error performing quality check: {str(e)}")
            raise

    async def _calculate_metrics(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate monitoring metrics"""
        try:
            # Extract data
            issues = quality_data.get("issues", [])
            validations = quality_data.get("validations", [])
            resolutions = quality_data.get("resolutions", [])
            
            # Calculate metrics
            return {
                "total_issues": len(issues),
                "active_issues": len([i for i in issues if i.get("status") == "active"]),
                "resolution_rate": len(resolutions) / len(issues) if issues else 0,
                "avg_quality_score": np.mean([v.get("score", 0) for v in validations]),
                "issue_types": self._group_by_type(issues),
                "validation_scores": [v.get("score", 0) for v in validations]
            }
            
        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return {}

    async def _check_thresholds(
        self,
        pipeline_id: str,
        metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Check metrics against thresholds"""
        try:
            alerts = []
            context = self.active_monitors.get(pipeline_id, {})
            thresholds = context.get("alert_thresholds", self.alert_thresholds)
            
            # Check total issues threshold
            if metrics["total_issues"] > thresholds.get("max_total_issues", 100):
                alerts.append({
                    "type": "high_issue_count",
                    "severity": "high",
                    "metric": "total_issues",
                    "value": metrics["total_issues"],
                    "threshold": thresholds["max_total_issues"]
                })
            
            # Check active issues threshold
            if metrics["active_issues"] > thresholds.get("max_active_issues", 50):
                alerts.append({
                    "type": "high_active_issues",
                    "severity": "medium",
                    "metric": "active_issues",
                    "value": metrics["active_issues"],
                    "threshold": thresholds["max_active_issues"]
                })
            
            # Check resolution rate threshold
            if metrics["resolution_rate"] < thresholds.get("min_resolution_rate", 0.8):
                alerts.append({
                    "type": "low_resolution_rate",
                    "severity": "medium",
                    "metric": "resolution_rate",
                    "value": metrics["resolution_rate"],
                    "threshold": thresholds["min_resolution_rate"]
                })
            
            # Check quality score threshold
            if metrics["avg_quality_score"] < thresholds.get("min_quality_score", 0.8):
                alerts.append({
                    "type": "low_quality_score",
                    "severity": "high",
                    "metric": "avg_quality_score",
                    "value": metrics["avg_quality_score"],
                    "threshold": thresholds["min_quality_score"]
                })
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking thresholds: {str(e)}")
            return []

    async def _process_alerts(
        self,
        pipeline_id: str,
        result: MonitoringResult
    ) -> None:
        """Process monitoring alerts"""
        try:
            context = self.active_monitors.get(pipeline_id)
            if not context:
                return
            
            # Update active alerts
            context["active_alerts"] = result.alerts
            
            # Update metrics
            self.monitoring_metrics["total_alerts"] += len(result.alerts)
            self.monitoring_metrics["active_alerts"] = len(result.alerts)
            
            # Send alert notifications
            for alert in result.alerts:
                await self._send_alert_notification(pipeline_id, alert)
            
        except Exception as e:
            logger.error(f"Error processing alerts: {str(e)}")

    async def _send_alert_notification(
        self,
        pipeline_id: str,
        alert: Dict[str, Any]
    ) -> None:
        """Send alert notification"""
        try:
            # Create alert message
            alert_message = ProcessingMessage(
                message_type=MessageType.QUALITY_ALERT_CREATE,
                content={
                    "pipeline_id": pipeline_id,
                    "alert": alert,
                    "timestamp": datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=str(uuid.uuid4()),
                    source_component=self.component_name,
                    target_component="quality_manager"
                )
            )
            
            # Send alert
            await self.message_broker.publish(alert_message)
            
        except Exception as e:
            logger.error(f"Error sending alert notification: {str(e)}")

    async def _handle_alert_resolve(self, message: ProcessingMessage) -> None:
        """Handle alert resolution"""
        try:
            pipeline_id = message.content.get("pipeline_id")
            alert_id = message.content.get("alert_id")
            
            if not pipeline_id or not alert_id:
                raise ValueError("Missing pipeline_id or alert_id in request")
            
            # Update active alerts
            context = self.active_monitors.get(pipeline_id)
            if context:
                context["active_alerts"] = [
                    a for a in context["active_alerts"]
                    if a.get("id") != alert_id
                ]
                self.monitoring_metrics["active_alerts"] = len(context["active_alerts"])
            
            # Send success response
            await self._send_success_response(
                message=message,
                content={
                    "pipeline_id": pipeline_id,
                    "alert_id": alert_id,
                    "status": "resolved",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_ALERT_UPDATE
            )
            
        except Exception as e:
            logger.error(f"Error resolving alert: {str(e)}")
            await self._send_error_response(
                message=message,
                error=str(e),
                response_type=MessageType.QUALITY_ALERT_UPDATE
            )

    async def _get_quality_data(self, pipeline_id: str) -> Dict[str, Any]:
        """Get quality data from quality manager"""
        try:
            # Create request message
            request_message = ProcessingMessage(
                message_type=MessageType.QUALITY_DATA_REQUEST,
                content={
                    "pipeline_id": pipeline_id,
                    "timestamp": datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=str(uuid.uuid4()),
                    source_component=self.component_name,
                    target_component="quality_manager"
                )
            )
            
            # Send request and wait for response
            response = await self.message_broker.request(request_message)
            
            # Extract data from response
            return response.content.get("data", {})
            
        except Exception as e:
            logger.error(f"Error getting quality data: {str(e)}")
            raise

    async def _handle_monitor_failed(self, pipeline_id: str, error: str) -> None:
        """Handle monitor failure"""
        try:
            # Stop monitoring task
            if pipeline_id in self.monitoring_tasks:
                self.monitoring_tasks[pipeline_id].cancel()
                del self.monitoring_tasks[pipeline_id]
            
            # Clean up monitor context
            if pipeline_id in self.active_monitors:
                del self.active_monitors[pipeline_id]
            
            # Send failure message
            await self._send_error_response(
                message=ProcessingMessage(
                    message_type=MessageType.QUALITY_MONITOR_STATUS,
                    content={
                        "pipeline_id": pipeline_id,
                        "error": error,
                        "timestamp": datetime.now().isoformat()
                    }
                ),
                error=error,
                response_type=MessageType.QUALITY_MONITOR_STATUS
            )
            
        except Exception as e:
            logger.error(f"Error handling monitor failure: {str(e)}")

    def _group_by_type(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group items by type"""
        try:
            return {
                item_type: len([i for i in items if i.get("type") == item_type])
                for item_type in set(i.get("type", "") for i in items)
            }
        except Exception as e:
            logger.error(f"Error grouping by type: {str(e)}")
            return {}

    async def _send_success_response(
        self,
        message: ProcessingMessage,
        content: Dict[str, Any],
        response_type: MessageType
    ) -> None:
        """Send success response message"""
        response = message.create_response(response_type, content)
        await self.message_broker.publish(response)

    async def _send_error_response(
        self,
        message: ProcessingMessage,
        error: str,
        response_type: MessageType
    ) -> None:
        """Send error response message"""
        content = {
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        response = message.create_response(response_type, content)
        await self.message_broker.publish(response) 