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
    ValidationType,
    MessageMetadata,
    ComponentState
)
from ...config.settings import Settings
from ...utils.metrics import MetricsCollector
from ..base.base_service import BaseService

logger = logging.getLogger(__name__)

@dataclass
class ValidationResult:
    """Result of a quality validation"""
    validation_id: str
    validation_type: ValidationType
    status: str
    score: float
    details: Dict[str, Any]
    timestamp: datetime

class QualityValidator(BaseService):
    """Service for validating data quality"""

    def __init__(
        self,
        message_broker: MessageBroker,
        settings: Settings,
        metrics_collector: MetricsCollector,
        component_name: str = "quality_validator",
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

        # Validation configuration
        self.validation_config = settings.get("quality_validation", {})
        self.max_retries = self.validation_config.get("max_retries", 3)
        self.timeout_seconds = self.validation_config.get("timeout_seconds", 300)
        self.batch_size = self.validation_config.get("batch_size", 1000)
        self.min_quality_score = self.validation_config.get("min_quality_score", 0.8)
        
        # Validation state tracking
        self.active_validations: Dict[str, Dict[str, Any]] = {}
        self.validation_metrics: Dict[str, Any] = {
            "total_validations": 0,
            "passed_validations": 0,
            "failed_validations": 0,
            "average_validation_time": 0.0,
            "quality_scores": []
        }

    async def _initialize_service(self) -> None:
        """Initialize the quality validator service"""
        try:
            # Set up message handlers
            await self._setup_message_handlers()
            
            # Initialize metrics
            await self._initialize_metrics()
            
            # Set service state
            self.state = ComponentState.ACTIVE
            
            logger.info(f"Quality Validator initialized successfully: {self.component_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Quality Validator: {str(e)}")
            self.state = ComponentState.ERROR
            raise

    async def _setup_message_handlers(self) -> None:
        """Set up message handlers for quality validation operations"""
        # Core validation handlers
        self.handlers.update({
            MessageType.QUALITY_VALIDATION_REQUEST: self._handle_validation_request,
            MessageType.QUALITY_VALIDATION_START: self._handle_validation_start,
            MessageType.QUALITY_VALIDATION_PROGRESS: self._handle_validation_progress,
            MessageType.QUALITY_VALIDATION_COMPLETE: self._handle_validation_complete,
            MessageType.QUALITY_VALIDATION_FAILED: self._handle_validation_failed,
            
            # Validation type handlers
            MessageType.QUALITY_VALIDATE_COMPLETENESS: self._handle_completeness_validation,
            MessageType.QUALITY_VALIDATE_CONSISTENCY: self._handle_consistency_validation,
            MessageType.QUALITY_VALIDATE_ACCURACY: self._handle_accuracy_validation,
            MessageType.QUALITY_VALIDATE_TIMELINESS: self._handle_timeliness_validation,
            
            # Status and reporting handlers
            MessageType.QUALITY_STATUS_REQUEST: self._handle_status_request,
            MessageType.QUALITY_REPORT_REQUEST: self._handle_report_request,
            
            # System operation handlers
            MessageType.QUALITY_CONFIG_UPDATE: self._handle_config_update,
            MessageType.QUALITY_RESOURCE_REQUEST: self._handle_resource_request
        })

    async def _handle_validation_request(self, message: ProcessingMessage) -> None:
        """Handle validation request"""
        try:
            pipeline_id = message.content.get("pipeline_id")
            if not pipeline_id:
                raise ValueError("Missing pipeline_id in request")

            # Create validation context
            validation_context = {
                "pipeline_id": pipeline_id,
                "state": QualityState.VALIDATION,
                "start_time": datetime.now(),
                "validation_types": message.content.get("validation_types", []),
                "validation_results": [],
                "retry_count": 0
            }
            
            # Store context
            self.active_validations[pipeline_id] = validation_context
            
            # Update metrics
            self.validation_metrics["total_validations"] += 1
            
            # Send success response
            await self._send_success_response(
                message=message,
                content={
                    "pipeline_id": pipeline_id,
                    "status": "validation_started",
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_VALIDATION_START
            )
            
            # Start validation process
            await self._perform_validation(pipeline_id)
            
        except Exception as e:
            logger.error(f"Error handling validation request: {str(e)}")
            await self._send_error_response(
                message=message,
                error=str(e),
                response_type=MessageType.QUALITY_VALIDATION_FAILED
            )

    async def _perform_validation(self, pipeline_id: str) -> None:
        """Perform quality validation"""
        try:
            context = self.active_validations.get(pipeline_id)
            if not context:
                raise ValueError(f"No active context found for pipeline: {pipeline_id}")

            # Get data from staging
            data = await self._get_staging_data(pipeline_id)
            
            # Process each validation type
            for validation_type in context["validation_types"]:
                # Perform validation
                result = await self._validate_data(data, validation_type)
                
                # Store result
                context["validation_results"].append(result)
                
                # Send progress update
                await self._send_success_response(
                    message=ProcessingMessage(
                        message_type=MessageType.QUALITY_VALIDATION_PROGRESS,
                        content={
                            "pipeline_id": pipeline_id,
                            "validation_id": result.validation_id,
                            "status": "completed",
                            "timestamp": datetime.now().isoformat()
                        }
                    ),
                    content={
                        "pipeline_id": pipeline_id,
                        "validation_id": result.validation_id,
                        "status": "completed",
                        "timestamp": datetime.now().isoformat()
                    },
                    response_type=MessageType.QUALITY_VALIDATION_PROGRESS
                )
            
            # Calculate overall quality score
            overall_score = self._calculate_overall_score(context["validation_results"])
            
            # Send completion message
            await self._send_success_response(
                message=ProcessingMessage(
                    message_type=MessageType.QUALITY_VALIDATION_COMPLETE,
                    content={
                        "pipeline_id": pipeline_id,
                        "validation_results": context["validation_results"],
                        "overall_score": overall_score,
                        "timestamp": datetime.now().isoformat()
                    }
                ),
                content={
                    "pipeline_id": pipeline_id,
                    "status": "validation_complete",
                    "overall_score": overall_score,
                    "timestamp": datetime.now().isoformat()
                },
                response_type=MessageType.QUALITY_VALIDATION_COMPLETE
            )
            
            # Update metrics
            if overall_score >= self.min_quality_score:
                self.validation_metrics["passed_validations"] += 1
            else:
                self.validation_metrics["failed_validations"] += 1
            
            self.validation_metrics["quality_scores"].append(overall_score)
            
            # Clean up
            await self._cleanup_validation(pipeline_id)
            
        except Exception as e:
            logger.error(f"Error performing validation: {str(e)}")
            await self._handle_validation_failed(pipeline_id, str(e))

    async def _validate_data(
        self,
        data: pd.DataFrame,
        validation_type: ValidationType
    ) -> ValidationResult:
        """Validate data based on validation type"""
        try:
            validation_id = str(uuid.uuid4())
            
            # Perform validation based on type
            if validation_type == ValidationType.COMPLETENESS:
                result = await self._validate_completeness(data)
            elif validation_type == ValidationType.CONSISTENCY:
                result = await self._validate_consistency(data)
            elif validation_type == ValidationType.ACCURACY:
                result = await self._validate_accuracy(data)
            elif validation_type == ValidationType.TIMELINESS:
                result = await self._validate_timeliness(data)
            else:
                raise ValueError(f"Unsupported validation type: {validation_type}")
            
            # Create validation result
            return ValidationResult(
                validation_id=validation_id,
                validation_type=validation_type,
                status="completed",
                score=result["score"],
                details=result["details"],
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error validating data: {str(e)}")
            raise

    async def _validate_completeness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate data completeness"""
        try:
            # Calculate completeness metrics
            total_rows = len(data)
            missing_counts = data.isna().sum()
            completeness_scores = 1 - (missing_counts / total_rows)
            
            # Calculate overall completeness score
            overall_score = completeness_scores.mean()
            
            # Identify columns with low completeness
            low_completeness = completeness_scores[completeness_scores < 0.9]
            
            return {
                "score": overall_score,
                "details": {
                    "total_rows": total_rows,
                    "missing_counts": missing_counts.to_dict(),
                    "completeness_scores": completeness_scores.to_dict(),
                    "low_completeness_columns": low_completeness.index.tolist(),
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating completeness: {str(e)}")
            raise

    async def _validate_consistency(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate data consistency"""
        try:
            # Check data type consistency
            type_consistency = data.dtypes.astype(str).value_counts()
            
            # Check value range consistency
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            range_stats = {}
            for col in numeric_cols:
                range_stats[col] = {
                    "min": data[col].min(),
                    "max": data[col].max(),
                    "mean": data[col].mean(),
                    "std": data[col].std()
                }
            
            # Calculate consistency score
            type_score = 1 - (len(type_consistency) / len(data.columns))
            range_score = 1 - (len(range_stats) / len(numeric_cols))
            overall_score = (type_score + range_score) / 2
            
            return {
                "score": overall_score,
                "details": {
                    "type_consistency": type_consistency.to_dict(),
                    "range_stats": range_stats,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating consistency: {str(e)}")
            raise

    async def _validate_accuracy(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate data accuracy"""
        try:
            # Check for statistical anomalies
            numeric_cols = data.select_dtypes(include=[np.number]).columns
            anomaly_stats = {}
            
            for col in numeric_cols:
                # Calculate z-scores
                z_scores = np.abs((data[col] - data[col].mean()) / data[col].std())
                
                # Identify anomalies
                anomalies = z_scores[z_scores > 3]
                
                anomaly_stats[col] = {
                    "anomaly_count": len(anomalies),
                    "anomaly_percentage": len(anomalies) / len(data),
                    "max_zscore": z_scores.max()
                }
            
            # Calculate accuracy score
            anomaly_scores = [
                1 - stats["anomaly_percentage"]
                for stats in anomaly_stats.values()
            ]
            overall_score = np.mean(anomaly_scores) if anomaly_scores else 1.0
            
            return {
                "score": overall_score,
                "details": {
                    "anomaly_stats": anomaly_stats,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating accuracy: {str(e)}")
            raise

    async def _validate_timeliness(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate data timeliness"""
        try:
            # Check for timestamp columns
            timestamp_cols = data.select_dtypes(include=['datetime64']).columns
            
            timeliness_stats = {}
            for col in timestamp_cols:
                # Calculate time differences
                time_diffs = data[col].diff()
                
                # Check for gaps
                gaps = time_diffs[time_diffs > pd.Timedelta(hours=1)]
                
                timeliness_stats[col] = {
                    "gap_count": len(gaps),
                    "max_gap": gaps.max().total_seconds() / 3600 if not gaps.empty else 0,
                    "avg_gap": gaps.mean().total_seconds() / 3600 if not gaps.empty else 0
                }
            
            # Calculate timeliness score
            if timeliness_stats:
                gap_scores = [
                    1 - (stats["gap_count"] / len(data))
                    for stats in timeliness_stats.values()
                ]
                overall_score = np.mean(gap_scores)
            else:
                overall_score = 1.0
            
            return {
                "score": overall_score,
                "details": {
                    "timeliness_stats": timeliness_stats,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Error validating timeliness: {str(e)}")
            raise

    def _calculate_overall_score(self, results: List[ValidationResult]) -> float:
        """Calculate overall quality score from validation results"""
        try:
            if not results:
                return 0.0
            
            # Calculate weighted average of scores
            weights = {
                ValidationType.COMPLETENESS: 0.3,
                ValidationType.CONSISTENCY: 0.2,
                ValidationType.ACCURACY: 0.3,
                ValidationType.TIMELINESS: 0.2
            }
            
            weighted_scores = [
                result.score * weights.get(result.validation_type, 0.25)
                for result in results
            ]
            
            return sum(weighted_scores)
            
        except Exception as e:
            logger.error(f"Error calculating overall score: {str(e)}")
            return 0.0

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

    async def _handle_validation_failed(self, pipeline_id: str, error: str) -> None:
        """Handle validation failure"""
        try:
            # Update metrics
            self.validation_metrics["failed_validations"] += 1
            
            # Send failure message
            await self._send_error_response(
                message=ProcessingMessage(
                    message_type=MessageType.QUALITY_VALIDATION_FAILED,
                    content={
                        "pipeline_id": pipeline_id,
                        "error": error,
                        "timestamp": datetime.now().isoformat()
                    }
                ),
                error=error,
                response_type=MessageType.QUALITY_VALIDATION_FAILED
            )
            
            # Clean up
            await self._cleanup_validation(pipeline_id)
            
        except Exception as e:
            logger.error(f"Error handling validation failure: {str(e)}")

    async def _cleanup_validation(self, pipeline_id: str) -> None:
        """Clean up validation resources"""
        try:
            if pipeline_id in self.active_validations:
                del self.active_validations[pipeline_id]
        except Exception as e:
            logger.error(f"Error cleaning up validation: {str(e)}")

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