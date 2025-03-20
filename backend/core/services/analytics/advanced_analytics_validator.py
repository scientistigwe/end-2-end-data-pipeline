import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.preprocessing import StandardScaler

from core.messaging.message_broker import MessageBroker
from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage
from core.services.base_service import BaseService

class AdvancedAnalyticsValidator(BaseService):
    """Service for validating analytics results and models"""
    
    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker)
        self.active_validations: Dict[str, Dict[str, Any]] = {}
        self.validation_metrics: Dict[str, Dict[str, float]] = {}
        self.config = {
            "max_retries": 3,
            "timeout_seconds": 300,
            "batch_size": 1000,
            "max_concurrent_validations": 5,
            "validation_thresholds": {
                "accuracy": 0.8,
                "precision": 0.7,
                "recall": 0.7,
                "f1_score": 0.7,
                "r2_score": 0.6,
                "mae": 0.1,
                "rmse": 0.2
            },
            "cross_validation": {
                "n_splits": 5,
                "shuffle": True,
                "random_state": 42
            }
        }

    async def _initialize_service(self):
        """Initialize the validator service"""
        self._setup_message_handlers()
        self.logger.info("Advanced Analytics Validator initialized")

    def _setup_message_handlers(self):
        """Set up message handlers for the validator"""
        self.message_handlers = {
            MessageType.ANALYTICS_VALIDATION_REQUEST: self._handle_validation_request,
            MessageType.ANALYTICS_VALIDATION_START: self._handle_validation_start,
            MessageType.ANALYTICS_VALIDATION_PROGRESS: self._handle_validation_progress,
            MessageType.ANALYTICS_VALIDATION_COMPLETE: self._handle_validation_complete,
            MessageType.ANALYTICS_VALIDATION_FAILED: self._handle_validation_failed
        }

    async def _handle_validation_request(self, message: ProcessingMessage) -> ProcessingMessage:
        """Handle validation request message"""
        try:
            content = message.content
            validation_id = content.get("validation_id")
            analysis_id = content.get("analysis_id")
            data = pd.DataFrame(content.get("data", {}))
            model = content.get("model")
            validation_type = content.get("validation_type", "model")
            
            if not self._validate_validation_request(content):
                return ProcessingMessage(
                    message_type=MessageType.ANALYTICS_VALIDATION_FAILED,
                    content={
                        "validation_id": validation_id,
                        "error": "Invalid validation request",
                        "timestamp": datetime.now().isoformat()
                    }
                )

            # Create validation context
            validation_context = {
                "validation_id": validation_id,
                "analysis_id": analysis_id,
                "data": data,
                "model": model,
                "validation_type": validation_type,
                "start_time": datetime.now(),
                "status": "pending"
            }

            # Store validation context
            self.active_validations[validation_id] = validation_context

            # Start validation
            await self._start_validation(validation_id)

            return ProcessingMessage(
                message_type=MessageType.ANALYTICS_VALIDATION_START,
                content={
                    "validation_id": validation_id,
                    "status": "started",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling validation request: {str(e)}")
            return ProcessingMessage(
                message_type=MessageType.ANALYTICS_VALIDATION_FAILED,
                content={
                    "validation_id": content.get("validation_id"),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _start_validation(self, validation_id: str):
        """Start the validation process"""
        try:
            validation_context = self.active_validations[validation_id]
            validation_type = validation_context["validation_type"]
            data = validation_context["data"]
            model = validation_context["model"]

            if validation_type == "model":
                validation_results = await self._validate_model(data, model)
            elif validation_type == "results":
                validation_results = await self._validate_results(data)
            else:
                raise ValueError(f"Unsupported validation type: {validation_type}")

            # Update validation context
            validation_context["validation_results"] = validation_results
            validation_context["status"] = "completed"
            validation_context["end_time"] = datetime.now()

            # Update metrics
            await self._update_validation_metrics(validation_id)

            # Publish completion message
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_VALIDATION_COMPLETE,
                    content={
                        "validation_id": validation_id,
                        "validation_results": validation_results,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            )

        except Exception as e:
            self.logger.error(f"Error in validation process: {str(e)}")
            validation_context["status"] = "failed"
            validation_context["error"] = str(e)
            validation_context["end_time"] = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_VALIDATION_FAILED,
                    content={
                        "validation_id": validation_id,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            )

    async def _validate_model(self, data: pd.DataFrame, model: Any) -> Dict[str, Any]:
        """Validate a machine learning model"""
        try:
            # Prepare data
            X = data.drop(columns=["target"]) if "target" in data.columns else data
            y = data["target"] if "target" in data.columns else None

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y,
                test_size=0.2,
                random_state=self.config["cross_validation"]["random_state"]
            )

            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)

            # Train model
            model.fit(X_train_scaled, y_train)

            # Make predictions
            y_pred = model.predict(X_test_scaled)

            # Calculate metrics
            metrics = {
                "accuracy": accuracy_score(y_test, y_pred),
                "precision": precision_score(y_test, y_pred, average="weighted"),
                "recall": recall_score(y_test, y_pred, average="weighted"),
                "f1_score": f1_score(y_test, y_pred, average="weighted")
            }

            # Check thresholds
            validation_status = all(
                metrics[metric] >= self.config["validation_thresholds"][metric]
                for metric in metrics
            )

            return {
                "metrics": metrics,
                "validation_status": validation_status,
                "thresholds": self.config["validation_thresholds"],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error validating model: {str(e)}")
            raise

    async def _validate_results(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate analytics results"""
        try:
            validation_results = {
                "data_quality": await self._validate_data_quality(data),
                "statistical_validity": await self._validate_statistical_validity(data),
                "business_rules": await self._validate_business_rules(data),
                "timestamp": datetime.now().isoformat()
            }

            # Overall validation status
            validation_results["validation_status"] = all(
                result["status"] == "passed"
                for result in validation_results.values()
                if isinstance(result, dict) and "status" in result
            )

            return validation_results

        except Exception as e:
            self.logger.error(f"Error validating results: {str(e)}")
            raise

    async def _validate_data_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate data quality metrics"""
        try:
            quality_metrics = {
                "completeness": 1 - data.isnull().mean().mean(),
                "consistency": self._calculate_consistency(data),
                "accuracy": self._calculate_accuracy(data)
            }

            status = all(
                metric >= 0.8 for metric in quality_metrics.values()
            )

            return {
                "metrics": quality_metrics,
                "status": "passed" if status else "failed",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error validating data quality: {str(e)}")
            raise

    async def _validate_statistical_validity(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate statistical properties of the data"""
        try:
            statistical_metrics = {
                "normality": self._check_normality(data),
                "outliers": self._check_outliers(data),
                "correlation": self._check_correlation(data)
            }

            status = all(
                metric["status"] == "passed"
                for metric in statistical_metrics.values()
            )

            return {
                "metrics": statistical_metrics,
                "status": "passed" if status else "failed",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error validating statistical validity: {str(e)}")
            raise

    async def _validate_business_rules(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Validate business rules and constraints"""
        try:
            business_rules = {
                "value_ranges": self._check_value_ranges(data),
                "relationships": self._check_relationships(data),
                "constraints": self._check_constraints(data)
            }

            status = all(
                rule["status"] == "passed"
                for rule in business_rules.values()
            )

            return {
                "rules": business_rules,
                "status": "passed" if status else "failed",
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error validating business rules: {str(e)}")
            raise

    def _calculate_consistency(self, data: pd.DataFrame) -> float:
        """Calculate data consistency score"""
        try:
            # Check for duplicate rows
            duplicate_ratio = len(data[data.duplicated()]) / len(data)
            
            # Check for value consistency
            value_consistency = 1 - data.apply(
                lambda x: x.value_counts().max() / len(x)
            ).mean()

            return 1 - (duplicate_ratio + value_consistency) / 2

        except Exception as e:
            self.logger.error(f"Error calculating consistency: {str(e)}")
            return 0.0

    def _calculate_accuracy(self, data: pd.DataFrame) -> float:
        """Calculate data accuracy score"""
        try:
            # Check for obvious errors (e.g., negative values where not allowed)
            error_ratio = data.apply(
                lambda x: (x < 0).sum() / len(x)
            ).mean()

            return 1 - error_ratio

        except Exception as e:
            self.logger.error(f"Error calculating accuracy: {str(e)}")
            return 0.0

    def _check_normality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Check normality of numeric columns"""
        try:
            from scipy import stats

            normality_tests = {}
            for column in data.select_dtypes(include=[np.number]).columns:
                _, p_value = stats.normaltest(data[column])
                normality_tests[column] = {
                    "p_value": p_value,
                    "status": "passed" if p_value > 0.05 else "failed"
                }

            return {
                "tests": normality_tests,
                "status": "passed" if all(
                    test["status"] == "passed"
                    for test in normality_tests.values()
                ) else "failed"
            }

        except Exception as e:
            self.logger.error(f"Error checking normality: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _check_outliers(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Check for outliers in numeric columns"""
        try:
            outlier_checks = {}
            for column in data.select_dtypes(include=[np.number]).columns:
                z_scores = np.abs((data[column] - data[column].mean()) / data[column].std())
                outlier_ratio = (z_scores > 3).mean()
                outlier_checks[column] = {
                    "outlier_ratio": outlier_ratio,
                    "status": "passed" if outlier_ratio < 0.01 else "failed"
                }

            return {
                "checks": outlier_checks,
                "status": "passed" if all(
                    check["status"] == "passed"
                    for check in outlier_checks.values()
                ) else "failed"
            }

        except Exception as e:
            self.logger.error(f"Error checking outliers: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _check_correlation(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Check correlations between numeric columns"""
        try:
            numeric_data = data.select_dtypes(include=[np.number])
            correlation_matrix = numeric_data.corr()
            
            high_correlations = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i + 1, len(correlation_matrix.columns)):
                    if abs(correlation_matrix.iloc[i, j]) > 0.8:
                        high_correlations.append({
                            "column1": correlation_matrix.columns[i],
                            "column2": correlation_matrix.columns[j],
                            "correlation": correlation_matrix.iloc[i, j]
                        })

            return {
                "high_correlations": high_correlations,
                "status": "passed" if len(high_correlations) == 0 else "failed"
            }

        except Exception as e:
            self.logger.error(f"Error checking correlation: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _check_value_ranges(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Check if values are within expected ranges"""
        try:
            range_checks = {}
            for column in data.columns:
                if column in self.config.get("value_ranges", {}):
                    expected_range = self.config["value_ranges"][column]
                    violations = (
                        (data[column] < expected_range["min"]) |
                        (data[column] > expected_range["max"])
                    ).sum()
                    range_checks[column] = {
                        "violations": int(violations),
                        "status": "passed" if violations == 0 else "failed"
                    }

            return {
                "checks": range_checks,
                "status": "passed" if all(
                    check["status"] == "passed"
                    for check in range_checks.values()
                ) else "failed"
            }

        except Exception as e:
            self.logger.error(f"Error checking value ranges: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _check_relationships(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Check relationships between columns"""
        try:
            relationship_checks = {}
            for relationship in self.config.get("relationships", []):
                condition = relationship["condition"]
                violations = (~eval(condition, {"data": data})).sum()
                relationship_checks[condition] = {
                    "violations": int(violations),
                    "status": "passed" if violations == 0 else "failed"
                }

            return {
                "checks": relationship_checks,
                "status": "passed" if all(
                    check["status"] == "passed"
                    for check in relationship_checks.values()
                ) else "failed"
            }

        except Exception as e:
            self.logger.error(f"Error checking relationships: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _check_constraints(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Check business constraints"""
        try:
            constraint_checks = {}
            for constraint in self.config.get("constraints", []):
                condition = constraint["condition"]
                violations = (~eval(condition, {"data": data})).sum()
                constraint_checks[condition] = {
                    "violations": int(violations),
                    "status": "passed" if violations == 0 else "failed"
                }

            return {
                "checks": constraint_checks,
                "status": "passed" if all(
                    check["status"] == "passed"
                    for check in constraint_checks.values()
                ) else "failed"
            }

        except Exception as e:
            self.logger.error(f"Error checking constraints: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _validate_validation_request(self, content: Dict[str, Any]) -> bool:
        """Validate validation request content"""
        required_fields = ["validation_id", "analysis_id", "data"]
        return all(field in content for field in required_fields)

    async def _update_validation_metrics(self, validation_id: str):
        """Update validation metrics"""
        try:
            validation_context = self.active_validations[validation_id]
            start_time = validation_context["start_time"]
            end_time = validation_context["end_time"]
            duration = (end_time - start_time).total_seconds()

            self.validation_metrics[validation_id] = {
                "duration": duration,
                "status": validation_context["status"],
                "validation_type": validation_context["validation_type"],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error updating validation metrics: {str(e)}")

    async def _cleanup_resources(self):
        """Clean up service resources"""
        self.active_validations.clear()
        self.validation_metrics.clear()
        self.logger.info("Advanced Analytics Validator resources cleaned up") 