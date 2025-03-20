import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
from dataclasses import dataclass
import pandas as pd
import numpy as np
from scipy import stats

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
class ColumnProfile:
    """Profile information for a data column"""
    name: str
    data_type: str
    total_rows: int
    unique_values: int
    missing_count: int
    missing_percentage: float
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    mean_value: Optional[float] = None
    std_value: Optional[float] = None
    distinct_values: Optional[List[Any]] = None
    value_counts: Optional[Dict[str, int]] = None

class QualityAnalyzer(BaseService):
    """Service for analyzing data quality"""

    def __init__(
        self,
        message_broker: MessageBroker,
        settings: Settings,
        metrics_collector: MetricsCollector,
        component_name: str = "quality_analyzer",
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

        # Quality analysis configuration
        self.analysis_config = settings.get("quality_analysis", {})
        self.max_rows_per_batch = self.analysis_config.get("max_rows_per_batch", 10000)
        self.sample_size = self.analysis_config.get("sample_size", 1000)
        self.anomaly_threshold = self.analysis_config.get("anomaly_threshold", 3.0)
        self.missing_threshold = self.analysis_config.get("missing_threshold", 0.1)
        self.duplicate_threshold = self.analysis_config.get("duplicate_threshold", 0.05)
        
        # Analysis state tracking
        self.active_analyses: Dict[str, Dict[str, Any]] = {}
        self.analysis_metrics: Dict[str, Any] = {
            "total_analyses": 0,
            "completed_analyses": 0,
            "failed_analyses": 0,
            "average_analysis_time": 0.0
        }

    async def _initialize_service(self) -> None:
        """Initialize the quality analyzer service"""
        try:
            # Set up message handlers
            await self._setup_message_handlers()
            
            # Initialize metrics
            await self._initialize_metrics()
            
            # Set service state
            self.state = ComponentState.ACTIVE
            
            logger.info(f"Quality Analyzer initialized successfully: {self.component_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Quality Analyzer: {str(e)}")
            self.state = ComponentState.ERROR
            raise

    async def _setup_message_handlers(self) -> None:
        """Set up message handlers for quality analysis operations"""
        # Core analysis handlers
        self.handlers.update({
            MessageType.QUALITY_CONTEXT_ANALYZE_REQUEST: self._handle_context_analysis_request,
            MessageType.QUALITY_ANALYSE_REQUEST: self._handle_analysis_request,
            MessageType.QUALITY_ANALYSE_START: self._handle_analysis_start,
            MessageType.QUALITY_ANALYSE_PROGRESS: self._handle_analysis_progress,
            MessageType.QUALITY_ANALYSE_COMPLETE: self._handle_analysis_complete,
            
            # Advanced analysis handlers
            MessageType.QUALITY_ANOMALY_DETECT: self._handle_anomaly_detection,
            MessageType.QUALITY_PATTERN_RECOGNIZE: self._handle_pattern_recognition,
            
            # Status and reporting handlers
            MessageType.QUALITY_STATUS_REQUEST: self._handle_status_request,
            MessageType.QUALITY_REPORT_REQUEST: self._handle_report_request,
            
            # System operation handlers
            MessageType.QUALITY_CONFIG_UPDATE: self._handle_config_update,
            MessageType.QUALITY_RESOURCE_REQUEST: self._handle_resource_request
        })

    async def _handle_context_analysis_request(self, message: ProcessingMessage) -> None:
        """Handle context analysis request"""
        try:
            pipeline_id = message.content.get("pipeline_id")
            if not pipeline_id:
                raise ValueError("Missing pipeline_id in request")

            # Create analysis context
            analysis_context = {
                "pipeline_id": pipeline_id,
                "state": QualityState.CONTEXT_ANALYSIS,
                "start_time": datetime.now(),
                "column_profiles": {},
                "relationships": {},
                "total_rows": 0,
                "total_columns": 0
            }
            
            # Store context
            self.active_analyses[pipeline_id] = analysis_context
            
            # Update metrics
            self.analysis_metrics["total_analyses"] += 1
            
            # Send success response
            await self._send_success_response(
                message=message,
                content={
                    "pipeline_id": pipeline_id,
                    "status": "context_analysis_started",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_CONTEXT_ANALYZE_PROGRESS
            )
            
            # Start context analysis
            await self._perform_context_analysis(pipeline_id)
            
        except Exception as e:
            logger.error(f"Error handling context analysis request: {str(e)}")
            await self._send_error_response(
                message=message,
                error=str(e),
                response_type=MessageType.QUALITY_PROCESS_FAILED
            )

    async def _perform_context_analysis(self, pipeline_id: str) -> None:
        """Perform context analysis for a pipeline"""
        try:
            context = self.active_analyses.get(pipeline_id)
            if not context:
                raise ValueError(f"No active context found for pipeline: {pipeline_id}")

            # Get data from staging
            data = await self._get_staging_data(pipeline_id)
            
            # Analyze columns
            for column in data.columns:
                profile = await self._analyze_column(data[column])
                context["column_profiles"][column] = profile
            
            # Analyze relationships
            context["relationships"] = await self._analyze_relationships(data)
            
            # Update totals
            context["total_rows"] = len(data)
            context["total_columns"] = len(data.columns)
            
            # Send completion message
            await self._send_success_response(
                message=ProcessingMessage(
                    message_type=MessageType.QUALITY_CONTEXT_ANALYZE_COMPLETE,
                    content={
                        "pipeline_id": pipeline_id,
                        "column_profiles": context["column_profiles"],
                        "relationships": context["relationships"],
                        "total_rows": context["total_rows"],
                        "total_columns": context["total_columns"],
                        "timestamp": datetime.now().isoformat()
                    }
                ),
                content={
                    "pipeline_id": pipeline_id,
                    "status": "context_analysis_complete",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_CONTEXT_ANALYZE_COMPLETE
            )

        except Exception as e:
            logger.error(f"Error performing context analysis: {str(e)}")
            await self._handle_analysis_failed(pipeline_id, str(e))

    async def _analyze_column(self, column_data: pd.Series) -> ColumnProfile:
        """Analyze a single column of data"""
        try:
            # Basic statistics
            total_rows = len(column_data)
            missing_count = column_data.isna().sum()
            missing_percentage = missing_count / total_rows if total_rows > 0 else 0
            unique_values = column_data.nunique()
            
            # Create profile
            profile = ColumnProfile(
                name=column_data.name,
                data_type=str(column_data.dtype),
                total_rows=total_rows,
                unique_values=unique_values,
                missing_count=missing_count,
                missing_percentage=missing_percentage
            )
            
            # Numeric statistics
            if pd.api.types.is_numeric_dtype(column_data):
                profile.min_value = float(column_data.min())
                profile.max_value = float(column_data.max())
                profile.mean_value = float(column_data.mean())
                profile.std_value = float(column_data.std())
            
            # Categorical statistics
            if pd.api.types.is_string_dtype(column_data):
                profile.distinct_values = column_data.unique().tolist()
                profile.value_counts = column_data.value_counts().to_dict()
            
            return profile
            
        except Exception as e:
            logger.error(f"Error analyzing column {column_data.name}: {str(e)}")
            raise

    async def _analyze_relationships(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze relationships between columns"""
        try:
            relationships = {}
            
            # Correlation analysis for numeric columns
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            if len(numeric_columns) > 1:
                correlations = data[numeric_columns].corr()
                relationships["correlations"] = correlations.to_dict()
            
            # Cardinality analysis
            cardinality = {}
            for column in data.columns:
                cardinality[column] = data[column].nunique()
            relationships["cardinality"] = cardinality
            
            # Functional dependencies
            relationships["functional_dependencies"] = await self._detect_functional_dependencies(data)
            
            return relationships
            
        except Exception as e:
            logger.error(f"Error analyzing relationships: {str(e)}")
            raise

    async def _detect_functional_dependencies(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect functional dependencies between columns"""
        try:
            dependencies = []
            
            # Check for potential key columns
            for column in data.columns:
                if data[column].nunique() == len(data):
                    # This column might be a key
                    for other_column in data.columns:
                        if other_column != column:
                            # Check if other_column is functionally dependent
                            if data.groupby(column)[other_column].nunique().max() == 1:
                                dependencies.append({
                                    "determinant": column,
                                    "dependent": other_column,
                                    "strength": "strong"
                                })
            
            return dependencies
            
        except Exception as e:
            logger.error(f"Error detecting functional dependencies: {str(e)}")
            raise

    async def _handle_analysis_request(self, message: ProcessingMessage) -> None:
        """Handle quality analysis request"""
        try:
            pipeline_id = message.content.get("pipeline_id")
            if not pipeline_id:
                raise ValueError("Missing pipeline_id in request")

            # Get analysis context
            context = self.active_analyses.get(pipeline_id)
            if not context:
                raise ValueError(f"No active context found for pipeline: {pipeline_id}")

            # Update state
            context["state"] = QualityState.ANALYSIS
            
            # Send success response
            await self._send_success_response(
                message=message,
                content={
                    "pipeline_id": pipeline_id,
                    "status": "analysis_started",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_ANALYSE_START
            )
            
            # Start analysis
            await self._perform_quality_analysis(pipeline_id)
            
        except Exception as e:
            logger.error(f"Error handling analysis request: {str(e)}")
            await self._send_error_response(
                message=message,
                error=str(e),
                response_type=MessageType.QUALITY_PROCESS_FAILED
            )

    async def _perform_quality_analysis(self, pipeline_id: str) -> None:
        """Perform quality analysis"""
        try:
            context = self.active_analyses.get(pipeline_id)
            if not context:
                raise ValueError(f"No active context found for pipeline: {pipeline_id}")

            # Get data from staging
            data = await self._get_staging_data(pipeline_id)
            
            # Initialize analysis results
            analysis_results = {
                "issues": [],
                "metrics": {},
                "recommendations": []
            }
            
            # Check for missing values
            await self._check_missing_values(data, analysis_results)
            
            # Check for duplicates
            await self._check_duplicates(data, analysis_results)
            
            # Check for anomalies
            await self._check_anomalies(data, analysis_results)
            
            # Check for data type consistency
            await self._check_data_types(data, analysis_results)
            
            # Check for value constraints
            await self._check_value_constraints(data, analysis_results)
            
            # Update context with results
            context["analysis_results"] = analysis_results
            
            # Send completion message
            await self._send_success_response(
                message=ProcessingMessage(
                    message_type=MessageType.QUALITY_ANALYSE_COMPLETE,
                    content={
                        "pipeline_id": pipeline_id,
                        "analysis_results": analysis_results,
                        "timestamp": datetime.now().isoformat()
                    }
                ),
                content={
                    "pipeline_id": pipeline_id,
                    "status": "analysis_complete",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_ANALYSE_COMPLETE
            )
            
            # Update metrics
            self.analysis_metrics["completed_analyses"] += 1
            
        except Exception as e:
            logger.error(f"Error performing quality analysis: {str(e)}")
            await self._handle_analysis_failed(pipeline_id, str(e))

    async def _check_missing_values(self, data: pd.DataFrame, results: Dict[str, Any]) -> None:
        """Check for missing values in the data"""
        try:
            for column in data.columns:
                missing_count = data[column].isna().sum()
                missing_percentage = missing_count / len(data)
                
                if missing_percentage > self.missing_threshold:
                    results["issues"].append({
                        "type": QualityIssueType.MISSING_VALUES,
                        "column": column,
                        "severity": "high" if missing_percentage > 0.5 else "medium",
                        "details": {
                            "missing_count": int(missing_count),
                            "missing_percentage": float(missing_percentage)
                        }
                    })
                    
                    results["recommendations"].append({
                        "type": "missing_values",
                        "column": column,
                        "action": "investigate_missing_values",
                        "priority": "high" if missing_percentage > 0.5 else "medium"
                    })
                    
        except Exception as e:
            logger.error(f"Error checking missing values: {str(e)}")
            raise

    async def _check_duplicates(self, data: pd.DataFrame, results: Dict[str, Any]) -> None:
        """Check for duplicate records in the data"""
        try:
            duplicate_count = len(data) - len(data.drop_duplicates())
            duplicate_percentage = duplicate_count / len(data)
            
            if duplicate_percentage > self.duplicate_threshold:
                results["issues"].append({
                    "type": QualityIssueType.DUPLICATES,
                    "severity": "high" if duplicate_percentage > 0.1 else "medium",
                    "details": {
                        "duplicate_count": int(duplicate_count),
                        "duplicate_percentage": float(duplicate_percentage)
                    }
                })
                
                results["recommendations"].append({
                    "type": "duplicates",
                    "action": "remove_duplicates",
                    "priority": "high" if duplicate_percentage > 0.1 else "medium"
                })
                
        except Exception as e:
            logger.error(f"Error checking duplicates: {str(e)}")
            raise

    async def _check_anomalies(self, data: pd.DataFrame, results: Dict[str, Any]) -> None:
        """Check for anomalies in numeric columns"""
        try:
            numeric_columns = data.select_dtypes(include=[np.number]).columns
            
            for column in numeric_columns:
                # Calculate z-scores
                z_scores = np.abs(stats.zscore(data[column].dropna()))
                
                # Find anomalies
                anomalies = z_scores > self.anomaly_threshold
                anomaly_count = anomalies.sum()
                
                if anomaly_count > 0:
                    results["issues"].append({
                        "type": QualityIssueType.ANOMALIES,
                        "column": column,
                        "severity": "medium",
                        "details": {
                            "anomaly_count": int(anomaly_count),
                            "anomaly_percentage": float(anomaly_count / len(data))
                        }
                    })
                    
                    results["recommendations"].append({
                        "type": "anomalies",
                        "column": column,
                        "action": "investigate_anomalies",
                        "priority": "medium"
                    })
                    
        except Exception as e:
            logger.error(f"Error checking anomalies: {str(e)}")
            raise

    async def _check_data_types(self, data: pd.DataFrame, results: Dict[str, Any]) -> None:
        """Check for data type consistency"""
        try:
            for column in data.columns:
                # Check for mixed types
                if data[column].dtype == "object":
                    type_counts = data[column].apply(type).value_counts()
                    if len(type_counts) > 1:
                        results["issues"].append({
                            "type": QualityIssueType.MIXED_TYPES,
                            "column": column,
                            "severity": "medium",
                            "details": {
                                "type_counts": type_counts.to_dict()
                            }
                        })
                        
                        results["recommendations"].append({
                            "type": "mixed_types",
                            "column": column,
                            "action": "standardize_data_types",
                            "priority": "medium"
                        })
                        
        except Exception as e:
            logger.error(f"Error checking data types: {str(e)}")
            raise

    async def _check_value_constraints(self, data: pd.DataFrame, results: Dict[str, Any]) -> None:
        """Check for value constraints violations"""
        try:
            for column in data.columns:
                # Check for negative values in non-negative columns
                if pd.api.types.is_numeric_dtype(data[column]):
                    negative_count = (data[column] < 0).sum()
                    if negative_count > 0:
                        results["issues"].append({
                            "type": QualityIssueType.CONSTRAINT_VIOLATION,
                            "column": column,
                            "severity": "low",
                            "details": {
                                "negative_count": int(negative_count),
                                "constraint": "non_negative"
                            }
                        })
                        
                        results["recommendations"].append({
                            "type": "constraint_violation",
                            "column": column,
                            "action": "validate_value_constraints",
                            "priority": "low"
                        })
                        
        except Exception as e:
            logger.error(f"Error checking value constraints: {str(e)}")
            raise

    async def _get_staging_data(self, pipeline_id: str) -> pd.DataFrame:
        """Get data from staging area"""
        try:
            # Create request message
            request_message = ProcessingMessage(
                message_type=MessageType.STAGING_DATA_REQUEST,
                content={
                    "pipeline_id": pipeline_id,
                    "timestamp": datetime.now().isoformat()
                },
                metadata=MessageMetadata(
                    correlation_id=str(uuid.uuid4()),
                    source_component=self.component_name,
                    target_component="staging_manager"
                )
            )
            
            # Send request and wait for response
            response = await self.message_broker.request(request_message)
            
            # Extract data from response
            data = pd.DataFrame(response.content.get("data", []))
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting staging data: {str(e)}")
            raise

    async def _handle_analysis_failed(self, pipeline_id: str, error: str) -> None:
        """Handle analysis failure"""
        try:
            # Update metrics
            self.analysis_metrics["failed_analyses"] += 1
            
            # Send failure message
            await self._send_error_response(
                message=ProcessingMessage(
                    message_type=MessageType.QUALITY_PROCESS_FAILED,
                    content={
                        "pipeline_id": pipeline_id,
                        "error": error,
                        "timestamp": datetime.now().isoformat()
                    }
                ),
                error=error,
                response_type=MessageType.QUALITY_PROCESS_FAILED
            )
            
            # Clean up
            if pipeline_id in self.active_analyses:
                del self.active_analyses[pipeline_id]
                
        except Exception as e:
            logger.error(f"Error handling analysis failure: {str(e)}")

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