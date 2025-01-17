# backend/data_pipeline/advanced_analytics/types/model_types.py

from typing import Dict, Any, List, Optional, Protocol, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from .analytics_types import ModelMetricType, FeatureType, AnalyticsDataType


class ModelType(Enum):
    """Types of analytical models"""
    REGRESSION = "regression"
    CLASSIFICATION = "classification"
    CLUSTERING = "clustering"
    DIMENSIONALITY_REDUCTION = "dimensionality_reduction"
    TIME_SERIES = "time_series"
    CUSTOM = "custom"


class ModelFramework(Enum):
    """Supported modeling frameworks"""
    SKLEARN = "sklearn"
    TENSORFLOW = "tensorflow"
    PYTORCH = "pytorch"
    XGBOOST = "xgboost"
    CUSTOM = "custom"


class ModelStage(Enum):
    """Model lifecycle stages"""
    INITIALIZED = "initialized"
    TRAINED = "trained"
    VALIDATED = "validated"
    TUNED = "tuned"
    DEPLOYED = "deployed"
    ARCHIVED = "archived"


@dataclass
class FeatureDefinition:
    """Definition of a model feature"""
    name: str
    feature_type: FeatureType
    data_type: AnalyticsDataType
    importance: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelDefinition:
    """Definition of an analytical model"""
    model_id: str
    model_type: ModelType
    framework: ModelFramework
    features: List[FeatureDefinition]
    hyperparameters: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_id: str
    metrics: Dict[ModelMetricType, float]
    validation_results: Dict[str, Any]
    feature_importance: Dict[str, float]
    prediction_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ModelArtifact:
    """Model artifact information"""
    model_id: str
    staged_id: str
    artifact_type: str
    location: str
    size: int
    metadata: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)


class ModelInterface(Protocol):
    """Protocol defining required model interface"""

    def fit(self, X: Any, y: Any, **kwargs) -> None:
        """Fit model to data"""
        ...

    def predict(self, X: Any) -> Any:
        """Generate predictions"""
        ...

    def get_params(self) -> Dict[str, Any]:
        """Get model parameters"""
        ...

    def set_params(self, **params) -> None:
        """Set model parameters"""
        ...

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance scores"""
        ...


@dataclass
class ModelVersion:
    """Model version information"""
    model_id: str
    version: str
    parent_version: Optional[str]
    changes: Dict[str, Any]
    performance_delta: Dict[ModelMetricType, float]
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ModelExperiment:
    """Model experiment tracking"""
    experiment_id: str
    model_id: str
    hypothesis: str
    parameters: Dict[str, Any]
    results: Dict[str, Any]
    conclusions: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "running"


@dataclass
class HyperparameterTrial:
    """Results from a hyperparameter optimization trial"""
    trial_id: str
    parameters: Dict[str, Any]
    metrics: Dict[ModelMetricType, float]
    duration: float
    status: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# Type aliases for common model types
ModelParams = Dict[str, Any]
ModelPrediction = Union[List[float], List[int], List[str]]
FeatureImportance = Dict[str, float]
ModelMetrics = Dict[ModelMetricType, float]


class ModelRegistry:
    """Interface for model registration and tracking"""

    def register_model(self, definition: ModelDefinition) -> str:
        """Register a new model"""
        ...

    def get_model(self, model_id: str) -> Optional[ModelDefinition]:
        """Get model definition"""
        ...

    def update_performance(self, performance: ModelPerformance) -> None:
        """Update model performance metrics"""
        ...

    def get_performance(self, model_id: str) -> Optional[ModelPerformance]:
        """Get model performance metrics"""
        ...

    def list_models(self,
                    model_type: Optional[ModelType] = None,
                    framework: Optional[ModelFramework] = None) -> List[ModelDefinition]:
        """List registered models with optional filtering"""
        ...

    def delete_model(self, model_id: str) -> bool:
        """Delete model registration"""
        ...