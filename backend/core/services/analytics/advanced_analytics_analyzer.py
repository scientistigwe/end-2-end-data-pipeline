import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

from core.messaging.message_broker import MessageBroker
from core.messaging.message_types import MessageType
from core.messaging.processing_message import ProcessingMessage
from core.services.base_service import BaseService

class AdvancedAnalyticsAnalyzer(BaseService):
    """Service for performing advanced analytics analysis on data"""
    
    def __init__(self, message_broker: MessageBroker):
        super().__init__(message_broker)
        self.active_analyses: Dict[str, Dict[str, Any]] = {}
        self.analysis_metrics: Dict[str, Dict[str, float]] = {}
        self.config = {
            "max_retries": 3,
            "timeout_seconds": 300,
            "batch_size": 1000,
            "max_concurrent_analyses": 5,
            "model_params": {
                "random_forest": {
                    "n_estimators": 100,
                    "max_depth": 10
                },
                "kmeans": {
                    "n_clusters": 5,
                    "max_iter": 300
                },
                "pca": {
                    "n_components": 2
                }
            }
        }

    async def _initialize_service(self):
        """Initialize the analyzer service"""
        self._setup_message_handlers()
        self.logger.info("Advanced Analytics Analyzer initialized")

    def _setup_message_handlers(self):
        """Set up message handlers for the analyzer"""
        self.message_handlers = {
            MessageType.ANALYTICS_ANALYSIS_REQUEST: self._handle_analysis_request,
            MessageType.ANALYTICS_ANALYSIS_START: self._handle_analysis_start,
            MessageType.ANALYTICS_ANALYSIS_PROGRESS: self._handle_analysis_progress,
            MessageType.ANALYTICS_ANALYSIS_COMPLETE: self._handle_analysis_complete,
            MessageType.ANALYTICS_ANALYSIS_FAILED: self._handle_analysis_failed
        }

    async def _handle_analysis_request(self, message: ProcessingMessage) -> ProcessingMessage:
        """Handle analysis request message"""
        try:
            content = message.content
            analysis_id = content.get("analysis_id")
            analysis_type = content.get("analysis_type")
            data = pd.DataFrame(content.get("data", {}))
            
            if not self._validate_analysis_request(content):
                return ProcessingMessage(
                    message_type=MessageType.ANALYTICS_ANALYSIS_FAILED,
                    content={
                        "analysis_id": analysis_id,
                        "error": "Invalid analysis request",
                        "timestamp": datetime.now().isoformat()
                    }
                )

            # Create analysis context
            analysis_context = {
                "analysis_id": analysis_id,
                "analysis_type": analysis_type,
                "data": data,
                "start_time": datetime.now(),
                "status": "pending"
            }

            # Store analysis context
            self.active_analyses[analysis_id] = analysis_context

            # Start analysis
            await self._start_analysis(analysis_id)

            return ProcessingMessage(
                message_type=MessageType.ANALYTICS_ANALYSIS_START,
                content={
                    "analysis_id": analysis_id,
                    "status": "started",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            self.logger.error(f"Error handling analysis request: {str(e)}")
            return ProcessingMessage(
                message_type=MessageType.ANALYTICS_ANALYSIS_FAILED,
                content={
                    "analysis_id": content.get("analysis_id"),
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _start_analysis(self, analysis_id: str):
        """Start the analysis process"""
        try:
            analysis_context = self.active_analyses[analysis_id]
            analysis_type = analysis_context["analysis_type"]
            data = analysis_context["data"]

            # Perform analysis based on type
            if analysis_type == "comprehensive":
                result = await self._perform_comprehensive_analysis(data)
            elif analysis_type == "statistical":
                result = await self._perform_statistical_analysis(data)
            elif analysis_type == "predictive":
                result = await self._perform_predictive_analysis(data)
            elif analysis_type == "clustering":
                result = await self._perform_clustering_analysis(data)
            else:
                raise ValueError(f"Invalid analysis type: {analysis_type}")

            # Update analysis context
            analysis_context["result"] = result
            analysis_context["status"] = "completed"
            analysis_context["end_time"] = datetime.now()

            # Update metrics
            await self._update_analysis_metrics(analysis_id)

            # Publish completion message
            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_ANALYSIS_COMPLETE,
                    content={
                        "analysis_id": analysis_id,
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            )

        except Exception as e:
            self.logger.error(f"Error in analysis process: {str(e)}")
            analysis_context["status"] = "failed"
            analysis_context["error"] = str(e)
            analysis_context["end_time"] = datetime.now()

            await self.message_broker.publish(
                ProcessingMessage(
                    message_type=MessageType.ANALYTICS_ANALYSIS_FAILED,
                    content={
                        "analysis_id": analysis_id,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
                )
            )

    async def _perform_comprehensive_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Perform comprehensive analysis including all analysis types"""
        try:
            # Perform statistical analysis
            statistical_result = await self._perform_statistical_analysis(data)
            
            # Perform predictive analysis
            predictive_result = await self._perform_predictive_analysis(data)
            
            # Perform clustering analysis
            clustering_result = await self._perform_clustering_analysis(data)

            return {
                "statistical_analysis": statistical_result,
                "predictive_analysis": predictive_result,
                "clustering_analysis": clustering_result,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error in comprehensive analysis: {str(e)}")
            raise

    async def _perform_statistical_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Perform statistical analysis on the data"""
        try:
            # Calculate basic statistics
            basic_stats = {
                "mean": data.mean().to_dict(),
                "std": data.std().to_dict(),
                "min": data.min().to_dict(),
                "max": data.max().to_dict(),
                "median": data.median().to_dict()
            }

            # Calculate correlation matrix
            correlation_matrix = data.corr().to_dict()

            # Calculate distribution statistics
            distribution_stats = {
                "skew": data.skew().to_dict(),
                "kurtosis": data.kurtosis().to_dict()
            }

            return {
                "basic_stats": basic_stats,
                "correlation_matrix": correlation_matrix,
                "distribution_stats": distribution_stats,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error in statistical analysis: {str(e)}")
            raise

    async def _perform_predictive_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Perform predictive analysis on the data"""
        try:
            # Prepare data
            X = data.drop("target", axis=1)
            y = data["target"]

            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # Train model
            model = RandomForestRegressor(
                n_estimators=self.config["model_params"]["random_forest"]["n_estimators"],
                max_depth=self.config["model_params"]["random_forest"]["max_depth"]
            )
            model.fit(X_train, y_train)

            # Make predictions
            predictions = model.predict(X_test)

            # Calculate performance metrics
            performance_metrics = {
                "mse": mean_squared_error(y_test, predictions),
                "r2": r2_score(y_test, predictions)
            }

            # Get feature importance
            feature_importance = dict(zip(X.columns, model.feature_importances_))

            return {
                "feature_importance": feature_importance,
                "model_performance": performance_metrics,
                "predictions": predictions.tolist(),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error in predictive analysis: {str(e)}")
            raise

    async def _perform_clustering_analysis(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Perform clustering analysis on the data"""
        try:
            # Prepare data
            X = data.drop("target", axis=1)
            scaler = StandardScaler()
            X_scaled = scaler.fit_transform(X)

            # Apply PCA
            pca = PCA(n_components=self.config["model_params"]["pca"]["n_components"])
            X_pca = pca.fit_transform(X_scaled)

            # Perform clustering
            kmeans = KMeans(
                n_clusters=self.config["model_params"]["kmeans"]["n_clusters"],
                max_iter=self.config["model_params"]["kmeans"]["max_iter"]
            )
            cluster_labels = kmeans.fit_predict(X_pca)

            # Calculate cluster metrics
            cluster_metrics = {
                "inertia": kmeans.inertia_,
                "n_iterations": kmeans.n_iter_,
                "cluster_centers": kmeans.cluster_centers_.tolist()
            }

            return {
                "cluster_labels": cluster_labels.tolist(),
                "cluster_centers": kmeans.cluster_centers_.tolist(),
                "cluster_metrics": cluster_metrics,
                "pca_explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error in clustering analysis: {str(e)}")
            raise

    def _validate_analysis_request(self, content: Dict[str, Any]) -> bool:
        """Validate analysis request content"""
        required_fields = ["analysis_id", "analysis_type", "data"]
        return all(field in content for field in required_fields)

    async def _update_analysis_metrics(self, analysis_id: str):
        """Update analysis metrics"""
        try:
            analysis_context = self.active_analyses[analysis_id]
            start_time = analysis_context["start_time"]
            end_time = analysis_context["end_time"]
            duration = (end_time - start_time).total_seconds()

            self.analysis_metrics[analysis_id] = {
                "duration": duration,
                "status": analysis_context["status"],
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error updating analysis metrics: {str(e)}")

    async def _cleanup_resources(self):
        """Clean up service resources"""
        self.active_analyses.clear()
        self.analysis_metrics.clear()
        self.logger.info("Advanced Analytics Analyzer resources cleaned up") 