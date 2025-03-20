import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from dataclasses import dataclass
import pandas as pd
import numpy as np
import json
from pathlib import Path
import plotly.graph_objects as go
import plotly.express as px
from jinja2 import Environment, FileSystemLoader

from ...messaging.broker import MessageBroker
from ...messaging.event_types import (
    MessageType,
    ProcessingMessage,
    QualityContext,
    QualityState,
    QualityIssueType,
    ReportType,
    MessageMetadata,
    ComponentState
)
from ...config.settings import Settings
from ...utils.metrics import MetricsCollector
from ..base.base_service import BaseService

logger = logging.getLogger(__name__)

@dataclass
class ReportResult:
    """Result of a quality report generation"""
    report_id: str
    report_type: ReportType
    status: str
    content: Dict[str, Any]
    timestamp: datetime

class QualityReporter(BaseService):
    """Service for generating quality reports"""

    def __init__(
        self,
        message_broker: MessageBroker,
        settings: Settings,
        metrics_collector: MetricsCollector,
        component_name: str = "quality_reporter",
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

        # Report configuration
        self.report_config = settings.get("quality_reporting", {})
        self.max_retries = self.report_config.get("max_retries", 3)
        self.timeout_seconds = self.report_config.get("timeout_seconds", 300)
        self.report_dir = Path(self.report_config.get("report_dir", "reports"))
        self.template_dir = Path(self.report_config.get("template_dir", "templates"))
        
        # Report state tracking
        self.active_reports: Dict[str, Dict[str, Any]] = {}
        self.report_metrics: Dict[str, Any] = {
            "total_reports": 0,
            "completed_reports": 0,
            "failed_reports": 0,
            "average_report_time": 0.0
        }

        # Initialize report directory
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize template environment
        self.template_env = Environment(
            loader=FileSystemLoader(str(self.template_dir))
        )

    async def _initialize_service(self) -> None:
        """Initialize the quality reporter service"""
        try:
            # Set up message handlers
            await self._setup_message_handlers()
            
            # Initialize metrics
            await self._initialize_metrics()
            
            # Set service state
            self.state = ComponentState.ACTIVE
            
            logger.info(f"Quality Reporter initialized successfully: {self.component_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Quality Reporter: {str(e)}")
            self.state = ComponentState.ERROR
            raise

    async def _setup_message_handlers(self) -> None:
        """Set up message handlers for quality reporting operations"""
        # Core reporting handlers
        self.handlers.update({
            MessageType.QUALITY_REPORT_REQUEST: self._handle_report_request,
            MessageType.QUALITY_REPORT_START: self._handle_report_start,
            MessageType.QUALITY_REPORT_PROGRESS: self._handle_report_progress,
            MessageType.QUALITY_REPORT_COMPLETE: self._handle_report_complete,
            MessageType.QUALITY_REPORT_FAILED: self._handle_report_failed,
            
            # Report type handlers
            MessageType.QUALITY_REPORT_SUMMARY: self._handle_summary_report,
            MessageType.QUALITY_REPORT_DETAILED: self._handle_detailed_report,
            MessageType.QUALITY_REPORT_TREND: self._handle_trend_report,
            MessageType.QUALITY_REPORT_CUSTOM: self._handle_custom_report,
            
            # Status and reporting handlers
            MessageType.QUALITY_STATUS_REQUEST: self._handle_status_request,
            MessageType.QUALITY_REPORT_REQUEST: self._handle_report_request,
            
            # System operation handlers
            MessageType.QUALITY_CONFIG_UPDATE: self._handle_config_update,
            MessageType.QUALITY_RESOURCE_REQUEST: self._handle_resource_request
        })

    async def _handle_report_request(self, message: ProcessingMessage) -> None:
        """Handle report request"""
        try:
            pipeline_id = message.content.get("pipeline_id")
            if not pipeline_id:
                raise ValueError("Missing pipeline_id in request")

            # Create report context
            report_context = {
                "pipeline_id": pipeline_id,
                "state": QualityState.REPORTING,
                "start_time": datetime.now(),
                "report_types": message.content.get("report_types", []),
                "report_results": [],
                "retry_count": 0
            }
            
            # Store context
            self.active_reports[pipeline_id] = report_context
            
            # Update metrics
            self.report_metrics["total_reports"] += 1
            
            # Send success response
            await self._send_success_response(
                message=message,
                content={
                    "pipeline_id": pipeline_id,
                    "status": "report_started",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_REPORT_START
            )
            
            # Start report generation
            await self._generate_reports(pipeline_id)
            
        except Exception as e:
            logger.error(f"Error handling report request: {str(e)}")
            await self._send_error_response(
                message=message,
                error=str(e),
                response_type=MessageType.QUALITY_REPORT_FAILED
            )

    async def _generate_reports(self, pipeline_id: str) -> None:
        """Generate quality reports"""
        try:
            context = self.active_reports.get(pipeline_id)
            if not context:
                raise ValueError(f"No active context found for pipeline: {pipeline_id}")

            # Get quality data
            quality_data = await self._get_quality_data(pipeline_id)
            
            # Process each report type
            for report_type in context["report_types"]:
                # Generate report
                result = await self._generate_report(quality_data, report_type)
                
                # Store result
                context["report_results"].append(result)
                
                # Send progress update
                await self._send_success_response(
                    message=ProcessingMessage(
                        message_type=MessageType.QUALITY_REPORT_PROGRESS,
                        content={
                            "pipeline_id": pipeline_id,
                            "report_id": result.report_id,
                            "status": "completed",
                            "timestamp": datetime.now().isoformat()
                        }
                    ),
                    content={
                        "pipeline_id": pipeline_id,
                        "report_id": result.report_id,
                        "status": "completed",
                        "timestamp": datetime.now().isoformat()
                    },
                    response_type=MessageType.QUALITY_REPORT_PROGRESS
                )
            
            # Send completion message
            await self._send_success_response(
                message=ProcessingMessage(
                    message_type=MessageType.QUALITY_REPORT_COMPLETE,
                    content={
                        "pipeline_id": pipeline_id,
                        "report_results": context["report_results"],
                        "timestamp": datetime.now().isoformat()
                    }
                ),
                content={
                    "pipeline_id": pipeline_id,
                    "status": "report_complete",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_REPORT_COMPLETE
            )
            
            # Update metrics
            self.report_metrics["completed_reports"] += 1
            
            # Clean up
            await self._cleanup_report(pipeline_id)
            
        except Exception as e:
            logger.error(f"Error generating reports: {str(e)}")
            await self._handle_report_failed(pipeline_id, str(e))

    async def _generate_report(
        self,
        quality_data: Dict[str, Any],
        report_type: ReportType
    ) -> ReportResult:
        """Generate report based on report type"""
        try:
            report_id = str(uuid.uuid4())
            
            # Generate report based on type
            if report_type == ReportType.SUMMARY:
                content = await self._generate_summary_report(quality_data)
            elif report_type == ReportType.DETAILED:
                content = await self._generate_detailed_report(quality_data)
            elif report_type == ReportType.TREND:
                content = await self._generate_trend_report(quality_data)
            elif report_type == ReportType.CUSTOM:
                content = await self._generate_custom_report(quality_data)
            else:
                raise ValueError(f"Unsupported report type: {report_type}")
            
            # Create report result
            return ReportResult(
                report_id=report_id,
                report_type=report_type,
                status="completed",
                content=content,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            raise

    async def _generate_summary_report(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary quality report"""
        try:
            # Extract key metrics
            metrics = quality_data.get("metrics", {})
            issues = quality_data.get("issues", [])
            validations = quality_data.get("validations", [])
            
            # Calculate summary statistics
            total_issues = len(issues)
            resolved_issues = len([i for i in issues if i.get("status") == "resolved"])
            avg_quality_score = np.mean([v.get("score", 0) for v in validations])
            
            # Create summary content
            content = {
                "summary": {
                    "total_issues": total_issues,
                    "resolved_issues": resolved_issues,
                    "resolution_rate": resolved_issues / total_issues if total_issues > 0 else 0,
                    "average_quality_score": avg_quality_score,
                    "timestamp": datetime.now().isoformat()
                },
                "metrics": metrics,
                "charts": await self._generate_summary_charts(quality_data)
            }
            
            # Save report
            await self._save_report(content, "summary_report")
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating summary report: {str(e)}")
            raise

    async def _generate_detailed_report(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed quality report"""
        try:
            # Extract detailed data
            issues = quality_data.get("issues", [])
            validations = quality_data.get("validations", [])
            resolutions = quality_data.get("resolutions", [])
            
            # Create detailed content
            content = {
                "issues": {
                    "total": len(issues),
                    "by_type": self._group_by_type(issues),
                    "by_severity": self._group_by_severity(issues),
                    "by_status": self._group_by_status(issues)
                },
                "validations": {
                    "total": len(validations),
                    "by_type": self._group_by_type(validations),
                    "scores": [v.get("score", 0) for v in validations]
                },
                "resolutions": {
                    "total": len(resolutions),
                    "by_type": self._group_by_type(resolutions),
                    "by_status": self._group_by_status(resolutions)
                },
                "timestamp": datetime.now().isoformat(),
                "charts": await self._generate_detailed_charts(quality_data)
            }
            
            # Save report
            await self._save_report(content, "detailed_report")
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating detailed report: {str(e)}")
            raise

    async def _generate_trend_report(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trend quality report"""
        try:
            # Extract historical data
            historical_data = quality_data.get("historical", [])
            
            # Calculate trends
            trends = {
                "quality_scores": self._calculate_trend(historical_data, "quality_score"),
                "issue_counts": self._calculate_trend(historical_data, "issue_count"),
                "resolution_rates": self._calculate_trend(historical_data, "resolution_rate")
            }
            
            # Create trend content
            content = {
                "trends": trends,
                "historical_data": historical_data,
                "timestamp": datetime.now().isoformat(),
                "charts": await self._generate_trend_charts(historical_data)
            }
            
            # Save report
            await self._save_report(content, "trend_report")
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating trend report: {str(e)}")
            raise

    async def _generate_custom_report(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate custom quality report"""
        try:
            # Extract custom metrics
            custom_metrics = quality_data.get("custom_metrics", {})
            
            # Create custom content
            content = {
                "metrics": custom_metrics,
                "timestamp": datetime.now().isoformat(),
                "charts": await self._generate_custom_charts(quality_data)
            }
            
            # Save report
            await self._save_report(content, "custom_report")
            
            return content
            
        except Exception as e:
            logger.error(f"Error generating custom report: {str(e)}")
            raise

    async def _generate_summary_charts(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary charts"""
        try:
            # Create quality score chart
            quality_scores = quality_data.get("validations", [])
            score_fig = go.Figure()
            score_fig.add_trace(go.Bar(
                x=[v.get("type", "") for v in quality_scores],
                y=[v.get("score", 0) for v in quality_scores]
            ))
            score_fig.update_layout(
                title="Quality Scores by Type",
                xaxis_title="Validation Type",
                yaxis_title="Score"
            )
            
            # Create issue distribution chart
            issues = quality_data.get("issues", [])
            issue_fig = go.Figure()
            issue_fig.add_trace(go.Pie(
                labels=[i.get("type", "") for i in issues],
                values=[1] * len(issues)
            ))
            issue_fig.update_layout(title="Issue Distribution by Type")
            
            return {
                "quality_scores": score_fig.to_json(),
                "issue_distribution": issue_fig.to_json()
            }
            
        except Exception as e:
            logger.error(f"Error generating summary charts: {str(e)}")
            return {}

    async def _generate_detailed_charts(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate detailed charts"""
        try:
            # Create issue timeline chart
            issues = quality_data.get("issues", [])
            timeline_fig = go.Figure()
            timeline_fig.add_trace(go.Scatter(
                x=[i.get("timestamp", "") for i in issues],
                y=[1] * len(issues),
                mode="markers"
            ))
            timeline_fig.update_layout(
                title="Issue Timeline",
                xaxis_title="Time",
                yaxis_title="Issues"
            )
            
            # Create validation scores chart
            validations = quality_data.get("validations", [])
            validation_fig = go.Figure()
            validation_fig.add_trace(go.Box(
                y=[v.get("score", 0) for v in validations]
            ))
            validation_fig.update_layout(
                title="Validation Score Distribution",
                yaxis_title="Score"
            )
            
            return {
                "issue_timeline": timeline_fig.to_json(),
                "validation_scores": validation_fig.to_json()
            }
            
        except Exception as e:
            logger.error(f"Error generating detailed charts: {str(e)}")
            return {}

    async def _generate_trend_charts(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate trend charts"""
        try:
            # Create quality score trend chart
            trend_fig = go.Figure()
            trend_fig.add_trace(go.Scatter(
                x=[d.get("timestamp", "") for d in historical_data],
                y=[d.get("quality_score", 0) for d in historical_data],
                mode="lines+markers"
            ))
            trend_fig.update_layout(
                title="Quality Score Trend",
                xaxis_title="Time",
                yaxis_title="Score"
            )
            
            # Create issue count trend chart
            count_fig = go.Figure()
            count_fig.add_trace(go.Scatter(
                x=[d.get("timestamp", "") for d in historical_data],
                y=[d.get("issue_count", 0) for d in historical_data],
                mode="lines+markers"
            ))
            count_fig.update_layout(
                title="Issue Count Trend",
                xaxis_title="Time",
                yaxis_title="Count"
            )
            
            return {
                "quality_trend": trend_fig.to_json(),
                "issue_trend": count_fig.to_json()
            }
            
        except Exception as e:
            logger.error(f"Error generating trend charts: {str(e)}")
            return {}

    async def _generate_custom_charts(self, quality_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate custom charts"""
        try:
            # Create custom metrics chart
            custom_metrics = quality_data.get("custom_metrics", {})
            custom_fig = go.Figure()
            custom_fig.add_trace(go.Bar(
                x=list(custom_metrics.keys()),
                y=list(custom_metrics.values())
            ))
            custom_fig.update_layout(
                title="Custom Metrics",
                xaxis_title="Metric",
                yaxis_title="Value"
            )
            
            return {
                "custom_metrics": custom_fig.to_json()
            }
            
        except Exception as e:
            logger.error(f"Error generating custom charts: {str(e)}")
            return {}

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

    async def _save_report(self, content: Dict[str, Any], report_name: str) -> None:
        """Save report to file"""
        try:
            # Create report file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = self.report_dir / f"{report_name}_{timestamp}.json"
            
            # Save report content
            with open(report_path, "w") as f:
                json.dump(content, f, indent=2)
            
            logger.info(f"Report saved successfully: {report_path}")
            
        except Exception as e:
            logger.error(f"Error saving report: {str(e)}")
            raise

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

    def _group_by_severity(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group items by severity"""
        try:
            return {
                severity: len([i for i in items if i.get("severity") == severity])
                for severity in set(i.get("severity", "") for i in items)
            }
        except Exception as e:
            logger.error(f"Error grouping by severity: {str(e)}")
            return {}

    def _group_by_status(self, items: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group items by status"""
        try:
            return {
                status: len([i for i in items if i.get("status") == status])
                for status in set(i.get("status", "") for i in items)
            }
        except Exception as e:
            logger.error(f"Error grouping by status: {str(e)}")
            return {}

    def _calculate_trend(
        self,
        historical_data: List[Dict[str, Any]],
        metric: str
    ) -> Dict[str, float]:
        """Calculate trend for a metric"""
        try:
            if not historical_data:
                return {}
            
            # Extract metric values
            values = [d.get(metric, 0) for d in historical_data]
            
            # Calculate trend statistics
            return {
                "current": values[-1],
                "min": min(values),
                "max": max(values),
                "mean": np.mean(values),
                "std": np.std(values),
                "trend": (values[-1] - values[0]) / len(values) if len(values) > 1 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating trend: {str(e)}")
            return {}

    async def _handle_report_failed(self, pipeline_id: str, error: str) -> None:
        """Handle report failure"""
        try:
            # Update metrics
            self.report_metrics["failed_reports"] += 1
            
            # Send failure message
            await self._send_error_response(
                message=ProcessingMessage(
                    message_type=MessageType.QUALITY_REPORT_FAILED,
                    content={
                        "pipeline_id": pipeline_id,
                        "error": error,
                        "timestamp": datetime.now().isoformat()
                    }
                ),
                error=error,
                response_type=MessageType.QUALITY_REPORT_FAILED
            )
            
            # Clean up
            await self._cleanup_report(pipeline_id)
            
        except Exception as e:
            logger.error(f"Error handling report failure: {str(e)}")

    async def _cleanup_report(self, pipeline_id: str) -> None:
        """Clean up report resources"""
        try:
            if pipeline_id in self.active_reports:
                del self.active_reports[pipeline_id]
        except Exception as e:
            logger.error(f"Error cleaning up report: {str(e)}")

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