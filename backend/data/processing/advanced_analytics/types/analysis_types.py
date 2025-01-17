# backend/data_pipeline/advanced_analytics/types/analytics_types.py

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List, Union

class AnalyticsPhase(Enum):
    """Advanced analytics processing phases"""
    DATA_PREPARATION = "data_preparation"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_TRAINING = "model_training"
    MODEL_EVALUATION = "model_evaluation"
    VISUALIZATION = "visualization"

class AnalyticsDataType(Enum):
    """Types of data handled in analytics"""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEMPORAL = "temporal"
    TEXT = "text"
    BINARY = "binary"
    IMAGE = "image"
    MIXED = "mixed"

class FeatureType(Enum):
    """Types of engineered features"""
    STATISTICAL = "statistical"
    TEMPORAL = "temporal"
    INTERACTION = "interaction"
    DOMAIN = "domain"
    DERIVED = "derived"
    TRANSFORMED = "transformed"

class ModelMetricType(Enum):
    """Types of model evaluation metrics"""
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    ROC_AUC = "roc_auc"
    MSE = "mse"
    MAE = "mae"
    R2 = "r2"
    CUSTOM = "custom"

@dataclass
class AnalyticsContext:
    """Context for analytics processing"""
    pipeline_id: str
    staged_id: str
    current_phase: AnalyticsPhase
    data_config: Dict[str, Any]
    model_config: Dict[str, Any]
    phase_results: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class DataPreparationConfig:
    """Configuration for data preparation phase"""
    cleaning_operations: List[str]
    transformation_operations: List[str]
    validation_rules: Dict[str, Any]
    data_types: Dict[str, AnalyticsDataType]
    handling_missing: str = "drop"
    handling_outliers: str = "clip"
    validation_threshold: float = 0.8

@dataclass
class FeatureEngineeringConfig:
    """Configuration for feature engineering phase"""
    feature_types: List[FeatureType]
    selection_method: str
    extraction_config: Dict[str, Any]
    transformation_config: Dict[str, Any]
    max_features: Optional[int] = None
    correlation_threshold: float = 0.8
    significance_threshold: float = 0.05

@dataclass
class ModelTrainingConfig:
    """Configuration for model training phase"""
    model_type: str
    hyperparameters: Dict[str, Any]
    validation_split: float
    optimization_metric: ModelMetricType
    early_stopping: bool = True
    max_epochs: int = 100
    batch_size: Optional[int] = None

@dataclass
class ModelEvaluationConfig:
    """Configuration for model evaluation phase"""
    metrics: List[ModelMetricType]
    validation_data_split: float
    confidence_threshold: float
    calibration_method: Optional[str] = None
    bias_check_config: Optional[Dict[str, Any]] = None

@dataclass
class VisualizationConfig:
    """Configuration for visualization phase"""
    plot_types: List[str]
    chart_styles: Dict[str, Any]
    interactive: bool = True
    export_formats: List[str] = field(default_factory=lambda: ["png", "html"])

@dataclass
class AnalyticsResult:
    """Results from analytics process"""
    pipeline_id: str
    staged_id: str
    phase: AnalyticsPhase
    results: Dict[str, Any]
    metrics: Optional[Dict[str, float]] = None
    artifacts: Optional[Dict[str, str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

@dataclass
class ProcessingError:
    """Error information for analytics processing"""
    pipeline_id: str
    phase: AnalyticsPhase
    error_type: str
    error_message: str
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class PhaseTransition:
    """Information for phase transitions"""
    from_phase: AnalyticsPhase
    to_phase: AnalyticsPhase
    triggered_by: str
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)

# Type aliases for common types
FeatureMap = Dict[str, Union[float, str, int]]
ModelMetrics = Dict[ModelMetricType, float]
ValidationResult = Dict[str, Union[bool, str, Dict[str, Any]]]
PhaseConfig = Union[
    DataPreparationConfig,
    FeatureEngineeringConfig,
    ModelTrainingConfig,
    ModelEvaluationConfig,
    VisualizationConfig
]