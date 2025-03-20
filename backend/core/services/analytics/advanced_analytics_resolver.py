import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest

from core.messaging.message_broker import MessageBroker
from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage
from core.services.base_service import BaseService

class AdvancedAnalyticsResolver(BaseService):
    """Service for resolving issues identified in analytics analysis"""
    
    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker)
        self.active_resolutions: Dict[str, Dict[str, Any]] = {}
        self.resolution_metrics: Dict[str, Dict[str, float]] = {}
        self.config = {
            "max_retries": 3,
            "timeout_seconds": 300,
            "batch_size": 1000,
            "max_concurrent_resolutions": 5,
            "resolution_strategies": {
                "missing_values": {
                    "strategy": "mean",
                    "fill_value": None
                },
                "outliers": {
                    "threshold": 3.0,
                    "method": "isolation_forest"
                },
                "inconsistencies": {
                    "threshold": 0.95,
                    "method": "statistical"
                }
            }
        }

    async def _initialize_service(self):
        """Initialize the resolver service"""
        self._setup_message_handlers()
        self.logger.info("Advanced Analytics Resolver initialized")

    def _setup_message_handlers(self):
        """Set up message handlers for the resolver"""
        self.message_handlers = {
            MessageType.ANALYTICS_RESOLUTION_REQUEST: self._handle_resolution_request,
            MessageType.ANALYTICS_RESOLUTION_START: self._handle_resolution_start,
            MessageType.ANALYTICS_RESOLUTION_PROGRESS: self._handle_resolution_progress,
            MessageType.ANALYTICS_RESOLUTION_COMPLETE: self._handle_resolution_complete,
            MessageType.ANALYTICS_RESOLUTION_FAILED: self._handle_resolution_failed
        }

    async def _handle_resolution_request(self, message: ProcessingMessage) -> ProcessingMessage:
        """Handle resolution request message"""
        try:
            content = message.content
            resolution_id = content.get("resolution_id")
            analysis_id = content.get("analysis_id")
            issues = content.get("issues", [])
            data = pd.DataFrame(content.get("data", {}))
            
            if not self._validate_resolution_request(content):
                return ProcessingMessage(
                    message_type=MessageType.ANALYTICS_RESOLUTION_FAILED,
                    content={
                        "resolution_id": resolution_id,
                        "error": "Invalid resolution request",
                        "timestamp": datetime.now().isoformat()
                    }
                )

            # Create resolution context
            resolution_context = {
                "resolution_id": resolution_id,
                "analysis_id": analysis_id,
                "issues": issues,
                "data": data,
                "start_time": datetime.now(),
                "status": "pending"
            }

            # Store resolution context
            self.active_resolutions[resolution_id] = resolution_context

            # Start resolution
            await self._start_resolution(resolution_id)

            return ProcessingMessage(
                message_type=MessageType.ANALYTICS_RESOLUTION_START,
                content={
                    "resolution_id": resolution_id,
                    "status": "started",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling resolution request: {str(e)}")
            return ProcessingMessage(
                message_type=MessageType.ANALYTICS_RESOLUTION_FAILED,
                content={
                    "resolution_id": content.get("resolution_id"),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _start_resolution(self, resolution_id: str):
        """Start the resolution process"""
        try:
            resolution_context = self.active_resolutions[resolution_id]
            issues = resolution_context["issues"]
            data = resolution_context["data"]

            # Resolve each issue
            resolved_data = data.copy()
            resolution_results = []

            for issue in issues:
                issue_type = issue.get("type")
                resolution_result = await self._resolve_issue(resolved_data, issue)
                resolved_data = resolution_result["resolved_data"]
                resolution_results.append(resolution_result)

            # Update resolution context
            resolution_context["resolved_data"] = resolved_data
            resolution_context["resolution_results"] = resolution_results
            resolution_context["status"] = "completed"
            resolution_context["end_time"] = datetime.now()

            # Update metrics
            await self._update_resolution_metrics(resolution_id)

            # Publish completion message
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_RESOLUTION_COMPLETE,
                    content={
                        "resolution_id": resolution_id,
                        "resolved_data": resolved_data.to_dict(),
                        "resolution_results": resolution_results,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            )

        except Exception as e:
            self.logger.error(f"Error in resolution process: {str(e)}")
            resolution_context["status"] = "failed"
            resolution_context["error"] = str(e)
            resolution_context["end_time"] = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_RESOLUTION_FAILED,
                    content={
                        "resolution_id": resolution_id,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            )

    async def _resolve_issue(self, data: pd.DataFrame, issue: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a specific issue in the data"""
        try:
            issue_type = issue.get("type")
            affected_columns = issue.get("affected_columns", [])
            resolution_strategy = self.config["resolution_strategies"].get(issue_type, {})

            if issue_type == "missing_values":
                result = await self._resolve_missing_values(data, affected_columns, resolution_strategy)
            elif issue_type == "outliers":
                result = await self._resolve_outliers(data, affected_columns, resolution_strategy)
            elif issue_type == "inconsistencies":
                result = await self._resolve_inconsistencies(data, affected_columns, resolution_strategy)
            else:
                raise ValueError(f"Unsupported issue type: {issue_type}")

            return {
                "issue_type": issue_type,
                "affected_columns": affected_columns,
                "resolution_strategy": resolution_strategy,
                "resolved_data": result["resolved_data"],
                "resolution_metrics": result["metrics"],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error resolving issue: {str(e)}")
            raise

    async def _resolve_missing_values(
        self,
        data: pd.DataFrame,
        affected_columns: List[str],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve missing values in the data"""
        try:
            resolved_data = data.copy()
            metrics = {}

            for column in affected_columns:
                # Calculate missing value statistics
                missing_count = resolved_data[column].isnull().sum()
                missing_ratio = missing_count / len(resolved_data)
                metrics[f"{column}_missing_ratio"] = missing_ratio

                # Apply imputation strategy
                imputer = SimpleImputer(strategy=strategy["strategy"])
                resolved_data[column] = imputer.fit_transform(resolved_data[[column]])

            return {
                "resolved_data": resolved_data,
                "metrics": metrics
            }

        except Exception as e:
            self.logger.error(f"Error resolving missing values: {str(e)}")
            raise

    async def _resolve_outliers(
        self,
        data: pd.DataFrame,
        affected_columns: List[str],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve outliers in the data"""
        try:
            resolved_data = data.copy()
            metrics = {}

            for column in affected_columns:
                # Calculate outlier statistics
                z_scores = np.abs((resolved_data[column] - resolved_data[column].mean()) / resolved_data[column].std())
                outlier_mask = z_scores > strategy["threshold"]
                outlier_count = outlier_mask.sum()
                outlier_ratio = outlier_count / len(resolved_data)
                metrics[f"{column}_outlier_ratio"] = outlier_ratio

                if strategy["method"] == "isolation_forest":
                    # Use Isolation Forest to detect and handle outliers
                    iso_forest = IsolationForest(contamination=outlier_ratio)
                    outlier_labels = iso_forest.fit_predict(resolved_data[[column]])
                    resolved_data[column] = np.where(
                        outlier_labels == -1,
                        resolved_data[column].median(),
                        resolved_data[column]
                    )

            return {
                "resolved_data": resolved_data,
                "metrics": metrics
            }

        except Exception as e:
            self.logger.error(f"Error resolving outliers: {str(e)}")
            raise

    async def _resolve_inconsistencies(
        self,
        data: pd.DataFrame,
        affected_columns: List[str],
        strategy: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resolve inconsistencies in the data"""
        try:
            resolved_data = data.copy()
            metrics = {}

            for column in affected_columns:
                # Calculate consistency metrics
                value_counts = resolved_data[column].value_counts()
                most_common = value_counts.index[0]
                consistency_ratio = value_counts[0] / len(resolved_data)
                metrics[f"{column}_consistency_ratio"] = consistency_ratio

                if consistency_ratio < strategy["threshold"]:
                    # Replace inconsistent values with most common value
                    resolved_data[column] = resolved_data[column].replace(
                        value_counts.index[1:],
                        most_common
                    )

            return {
                "resolved_data": resolved_data,
                "metrics": metrics
            }

        except Exception as e:
            self.logger.error(f"Error resolving inconsistencies: {str(e)}")
            raise

    def _validate_resolution_request(self, content: Dict[str, Any]) -> bool:
        """Validate resolution request content"""
        required_fields = ["resolution_id", "analysis_id", "issues", "data"]
        return all(field in content for field in required_fields)

    async def _update_resolution_metrics(self, resolution_id: str):
        """Update resolution metrics"""
        try:
            resolution_context = self.active_resolutions[resolution_id]
            start_time = resolution_context["start_time"]
            end_time = resolution_context["end_time"]
            duration = (end_time - start_time).total_seconds()

            self.resolution_metrics[resolution_id] = {
                "duration": duration,
                "status": resolution_context["status"],
                "issues_resolved": len(resolution_context["issues"]),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error updating resolution metrics: {str(e)}")

    async def _cleanup_resources(self):
        """Clean up service resources"""
        self.active_resolutions.clear()
        self.resolution_metrics.clear()
        self.logger.info("Advanced Analytics Resolver resources cleaned up") 