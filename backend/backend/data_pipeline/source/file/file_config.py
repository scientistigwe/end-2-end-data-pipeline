from __future__ import annotations
import os
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import timedelta


@dataclass
class ProcessingConfig:
    """Processing pipeline configuration"""
    max_retries: int = 3
    retry_delay: int = 5
    timeout: int = 300
    chunk_size: int = 8192
    max_workers: int = 4
    queue_size: int = 1000


@dataclass
class QualityConfig:
    """Data quality configuration"""
    completeness_threshold: float = 80.0
    consistency_threshold: float = 90.0
    duplicate_threshold: float = 5.0
    date_formats: List[str] = field(default_factory=lambda: [
        '%Y-%m-%d', '%d/%m/%Y', '%m-%d-%Y'
    ])
    numeric_columns: List[str] = field(default_factory=list)
    categorical_columns: List[str] = field(default_factory=list)
    date_columns: List[str] = field(default_factory=list)
    outlier_threshold: float = 3.0
    validation_rules: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityConfig:
    """Security and validation configuration"""
    allowed_mime_types: Dict[str, List[str]] = field(default_factory=lambda: {
        'csv': ['text/csv', 'text/plain'],
        'xlsx': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        'xls': ['application/vnd.ms-excel'],
        'parquet': ['application/octet-stream'],
        'json': ['application/json', 'text/plain']
    })
    max_file_size_mb: int = 50
    scan_viruses: bool = True
    check_sensitive_data: bool = True
    sensitive_patterns: List[str] = field(default_factory=lambda: [
        r'(?i)(password|secret|key|token)',
        r'(?i)(ssn|social security)',
        r'(?i)(credit.?card)'
    ])


@dataclass
class ControlPointConfig:
    """Control point configuration"""
    default_timeout: int = 3600
    auto_approve_stages: List[str] = field(default_factory=list)
    required_approvers: Dict[str, int] = field(default_factory=dict)
    notification_delay: int = 300


@dataclass
class Config:
    """Comprehensive configuration for file processing system"""

    # Base settings
    ENVIRONMENT: str = field(default="development")
    DEBUG: bool = field(default=False)
    UPLOAD_DIRECTORY: str = field(default="uploads")
    TEMP_DIRECTORY: str = field(default="temp")
    LOG_DIRECTORY: str = field(default="logs")

    # File handling settings
    ALLOWED_FORMATS: List[str] = field(default_factory=lambda: [
        'csv', 'xlsx', 'parquet', 'json'
    ])

    # Component configurations
    PROCESSING: ProcessingConfig = field(default_factory=ProcessingConfig)
    QUALITY: QualityConfig = field(default_factory=QualityConfig)
    SECURITY: SecurityConfig = field(default_factory=SecurityConfig)
    CONTROL_POINTS: ControlPointConfig = field(default_factory=ControlPointConfig)

    # Performance settings
    RATE_LIMIT_MAX_CALLS: int = field(default=100)
    RATE_LIMIT_PERIOD: float = field(default=1.0)
    CACHE_MAX_SIZE: int = field(default=1000)
    CACHE_TTL: int = field(default=3600)

    def __post_init__(self):
        """Post initialization setup"""
        self._create_directories()
        self._validate_configuration()

    def _create_directories(self):
        """Create necessary directories"""
        directories = [
            self.UPLOAD_DIRECTORY,
            self.TEMP_DIRECTORY,
            self.LOG_DIRECTORY
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def _validate_configuration(self):
        """Validate configuration settings"""
        self._validate_directories()
        self._validate_formats()
        self._validate_thresholds()

    def _validate_directories(self):
        """Validate directory permissions"""
        for directory in [self.UPLOAD_DIRECTORY, self.TEMP_DIRECTORY, self.LOG_DIRECTORY]:
            if not os.access(directory, os.W_OK):
                raise ValueError(f"Directory {directory} is not writable")

    def _validate_formats(self):
        """Validate file format configurations"""
        if not self.ALLOWED_FORMATS:
            raise ValueError("No allowed file formats specified")

        if not all(fmt in self.SECURITY.allowed_mime_types for fmt in self.ALLOWED_FORMATS):
            raise ValueError("MIME type mappings missing for some allowed formats")

    def _validate_thresholds(self):
        """Validate threshold values"""
        if self.QUALITY.completeness_threshold < 0 or self.QUALITY.completeness_threshold > 100:
            raise ValueError("Completeness threshold must be between 0 and 100")

        if self.QUALITY.consistency_threshold < 0 or self.QUALITY.consistency_threshold > 100:
            raise ValueError("Consistency threshold must be between 0 and 100")

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> Config:
        """Create configuration from dictionary"""
        # Handle nested configurations
        processing_config = ProcessingConfig(
            **config_dict.get('PROCESSING', {})
        )
        quality_config = QualityConfig(
            **config_dict.get('QUALITY', {})
        )
        security_config = SecurityConfig(
            **config_dict.get('SECURITY', {})
        )
        control_point_config = ControlPointConfig(
            **config_dict.get('CONTROL_POINTS', {})
        )

        # Create main config
        return cls(
            **{
                k: v for k, v in config_dict.items()
                if k not in ['PROCESSING', 'QUALITY', 'SECURITY', 'CONTROL_POINTS']
            },
            PROCESSING=processing_config,
            QUALITY=quality_config,
            SECURITY=security_config,
            CONTROL_POINTS=control_point_config
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'ENVIRONMENT': self.ENVIRONMENT,
            'DEBUG': self.DEBUG,
            'UPLOAD_DIRECTORY': self.UPLOAD_DIRECTORY,
            'TEMP_DIRECTORY': self.TEMP_DIRECTORY,
            'LOG_DIRECTORY': self.LOG_DIRECTORY,
            'ALLOWED_FORMATS': self.ALLOWED_FORMATS,
            'PROCESSING': self.PROCESSING.__dict__,
            'QUALITY': self.QUALITY.__dict__,
            'SECURITY': self.SECURITY.__dict__,
            'CONTROL_POINTS': self.CONTROL_POINTS.__dict__,
            'RATE_LIMIT_MAX_CALLS': self.RATE_LIMIT_MAX_CALLS,
            'RATE_LIMIT_PERIOD': self.RATE_LIMIT_PERIOD,
            'CACHE_MAX_SIZE': self.CACHE_MAX_SIZE,
            'CACHE_TTL': self.CACHE_TTL
        }

    def update(self, **kwargs):
        """Update configuration settings"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                if isinstance(value, dict) and isinstance(getattr(self, key), (
                        ProcessingConfig, QualityConfig, SecurityConfig, ControlPointConfig
                )):
                    # Update nested config
                    current_config = getattr(self, key)
                    for k, v in value.items():
                        if hasattr(current_config, k):
                            setattr(current_config, k, v)
                else:
                    setattr(self, key, value)

        # Revalidate after updates
        self._validate_configuration()