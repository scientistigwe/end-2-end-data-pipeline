# schemas/staging/quality.py

from marshmallow import fields, validates_schema, ValidationError
from marshmallow.validate import Range, OneOf
from typing import Dict, Any
from .base import StagingRequestSchema, StagingResponseSchema


class QualityCheckRequestSchema(StagingRequestSchema):
    """Schema for quality check requests with comprehensive validation rules."""

    # Core validation configuration
    validation_rules = fields.Dict(
        keys=fields.String(),
        values=fields.Dict(
            rules=fields.List(fields.Dict()),
            severity=fields.String(validate=OneOf(['critical', 'major', 'minor'])),
            threshold=fields.Float(validate=Range(min=0, max=1))
        ),
        required=True
    )

    # Quality thresholds for different metrics
    quality_thresholds = fields.Dict(
        keys=fields.String(),
        values=fields.Float(validate=Range(min=0, max=1)),
        required=True
    )

    # Column-specific validation rules
    column_rules = fields.Dict(
        keys=fields.String(),
        values=fields.Dict(
            type=fields.String(required=True),
            format=fields.String(allow_none=True),
            constraints=fields.List(fields.Dict()),
            nullability=fields.Boolean(default=True)
        ),
        required=True
    )

    # Sampling configuration for large datasets
    sampling_config = fields.Dict(
        sample_size=fields.Integer(validate=Range(min=1)),
        sampling_method=fields.String(validate=OneOf(['random', 'stratified', 'systematic'])),
        seed=fields.Integer(allow_none=True),
        default=dict
    )

    # Advanced validation options
    advanced_options = fields.Dict(
        anomaly_detection=fields.Boolean(default=False),
        pattern_matching=fields.Boolean(default=False),
        correlation_analysis=fields.Boolean(default=False),
        default=dict
    )

    @validates_schema
    def validate_configuration(self, data: Dict[str, Any], **kwargs) -> None:
        """Validate the overall configuration consistency."""
        # Validate threshold consistency
        for column, rules in data['column_rules'].items():
            if column not in data['validation_rules']:
                raise ValidationError(f"Validation rules missing for column {column}")

            threshold = data['quality_thresholds'].get(column)
            if threshold is None:
                raise ValidationError(f"Quality threshold missing for column {column}")


class QualityCheckResponseSchema(StagingResponseSchema):
    """Schema for quality check responses with detailed results."""

    # Overall quality metrics
    quality_score = fields.Float(
        validate=Range(min=0, max=1),
        required=True
    )

    # Detailed issue counts by severity
    issues_found = fields.Dict(
        critical=fields.Integer(),
        major=fields.Integer(),
        minor=fields.Integer(),
        required=True
    )

    # Validation results per column
    validation_results = fields.Dict(
        keys=fields.String(),
        values=fields.Dict(
            passed_rules=fields.List(fields.String()),
            failed_rules=fields.List(fields.Dict(
                rule=fields.String(),
                severity=fields.String(),
                details=fields.Dict()
            )),
            quality_score=fields.Float(validate=Range(min=0, max=1))
        ),
        required=True
    )

    # Remediation suggestions for identified issues
    remediation_suggestions = fields.List(
        fields.Dict(
            issue_type=fields.String(required=True),
            severity=fields.String(required=True),
            suggestion=fields.String(required=True),
            impact=fields.Float(validate=Range(min=0, max=1)),
            effort_estimate=fields.String()
        ),
        required=True
    )

    # Performance metrics
    performance_metrics = fields.Dict(
        processing_time=fields.Float(),
        samples_processed=fields.Integer(),
        rules_evaluated=fields.Integer()
    )

    # Data profiling results
    data_profile = fields.Dict(
        column_statistics=fields.Dict(),
        correlations=fields.Dict(),
        patterns_detected=fields.List(fields.Dict()),
        allow_none=True
    )

    @validates_schema
    def validate_response_consistency(self, data: Dict[str, Any], **kwargs) -> None:
        """Validate consistency of response data."""
        total_issues = sum(data['issues_found'].values())
        if total_issues == 0 and data['quality_score'] < 1.0:
            raise ValidationError("Quality score should be 1.0 when no issues are found")


class QualityStagingRequestSchema(StagingRequestSchema):
    validation_rules = fields.Dict(required=True)
    quality_thresholds = fields.Dict(required=True)
    column_rules = fields.Dict(required=True)
    sampling_config = fields.Dict(default=dict)


class QualityStagingResponseSchema(StagingResponseSchema):
    quality_score = fields.Float(validate=lambda n: 0 <= n <= 1)
    issues_found = fields.Dict(
        critical=fields.Integer(),
        major=fields.Integer(),
        minor=fields.Integer()
    )
    validation_results = fields.Dict()
    remediation_suggestions = fields.List(fields.Dict())

