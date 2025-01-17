# backend/data_pipeline/insights/processor/insight_processor.py

import logging
from typing import Dict, Any, Optional
import uuid

from core.messaging.broker import MessageBroker
from core.staging.staging_manager import StagingManager

from ..types.insight_types import (
    InsightType,
    InsightCategory,
    InsightPriority,
    InsightPhase,
    InsightContext,
    InsightConfig,
    InsightResult
)

# Import insight modules
from ..generators import (
    pattern_insights,
    trend_insights,
    relationship_insights,
    anomaly_insights,
    business_goal_insights
)

from ..validators import (
    pattern_validator,
    trend_validator,
    relationship_validator,
    anomaly_validator,
business_goal_validator
)

logger = logging.getLogger(__name__)

class InsightProcessor:
    """
    Processor for insight generation and analysis.
    Coordinates between different insight modules and manages results.
    """

    def __init__(
            self,
            message_broker: MessageBroker,
            staging_manager: StagingManager
    ):
        self.message_broker = message_broker
        self.staging_manager = staging_manager
        self.logger = logging.getLogger(__name__)

        # Initialize module registries
        self._initialize_module_registries()

    def _initialize_module_registries(self) -> None:
        """Initialize registries for insight modules"""
        # Insight generators
        self.generators = {
            InsightType.PATTERN: {
                "detect": pattern_insights.detect_patterns,
                "analyze": pattern_insights.analyze_patterns,
                "validate": pattern_insights.validate_patterns
            },
            InsightType.TREND: {
                "detect": trend_insights.detect_trends,
                "analyze": trend_insights.analyze_trends,
                "validate": trend_insights.validate_trends
            },
            InsightType.CORRELATION: {
                "detect": relationship_insights.detect_relationships,
                "analyze": relationship_insights.analyze_relationships,
                "validate": relationship_insights.validate_relationships
            },
            InsightType.ANOMALY: {
                "detect": anomaly_insights.detect_anomalies,
                "analyze": anomaly_insights.analyze_anomalies,
                "validate": anomaly_insights.validate_anomalies
            },
            InsightType.BUSINESS_GOAL: {  # Add this block
                "detect": business_goal_insights.detect_business_insights,
                "analyze": business_goal_insights.analyze_business_insights,
                "validate": business_goal_insights.validate_business_insights
            }
        }

        # Insight validation
        self.validators = {
            InsightType.PATTERN: pattern_validator.validate_pattern_insight,
            InsightType.TREND: trend_validator.validate_trend_insight,
            InsightType.CORRELATION: relationship_validator.validate_relationship_insight,
            InsightType.ANOMALY: anomaly_validator.validate_anomaly_insight,
            InsightType.BUSINESS_GOAL: business_goal_validator.validate_business_goal_insight  # Add this
        }

    def _determine_appropriate_insights(
            self,
            characteristics: Dict[str, Any],
            domain_type: Optional[str]
    ) -> Dict[InsightType, float]:
        """Determine which insight types are appropriate"""
        appropriate = {}

        # Check for patterns
        if characteristics['size'] > 100:
            appropriate[InsightType.PATTERN] = 0.8

        # Check for trends
        if characteristics['temporal']:
            appropriate[InsightType.TREND] = 0.9

        # Check for correlations
        if characteristics['numeric'] and characteristics['dimensions'] > 1:
            appropriate[InsightType.CORRELATION] = 0.85

        # Check for anomalies
        if characteristics['numeric'] or characteristics['temporal']:
            appropriate[InsightType.ANOMALY] = 0.7

        # Always include business goal insights if business goals are present
        if 'business_goals' in characteristics:  # Add this block
            appropriate[InsightType.BUSINESS_GOAL] = 0.95

        # Add domain-specific weights
        if domain_type:
            self._adjust_for_domain(appropriate, domain_type)

        return appropriate

    def _analyze_data_characteristics(self, data: Any) -> Dict[str, Any]:
        """Analyze characteristics of the data"""
        characteristics = {
            'temporal': self._has_temporal_data(data),
            'numeric': self._has_numeric_data(data),
            'categorical': self._has_categorical_data(data),
            'size': len(data),
            'dimensions': len(data.columns) if hasattr(data, 'columns') else 1,
            'has_missing': self._has_missing_data(data),
            'business_goals': self._has_business_goals(data)  # Add this
        }
        return characteristics

    def _has_business_goals(self, data: Any) -> bool:
        """Check if business goals are present in metadata"""
        # This should check if business goals exist in the metadata
        return hasattr(data, 'metadata') and 'business_goals' in data.metadata

    def _adjust_for_domain(
            self,
            insights: Dict[InsightType, float],
            domain_type: str
    ) -> None:
        """Adjust insight weights based on domain"""
        domain_adjustments = {
            'financial': {
                InsightType.ANOMALY: 0.2,
                InsightType.TREND: 0.1,
                InsightType.BUSINESS_GOAL: 0.2  # Add this
            },
            'operational': {
                InsightType.PATTERN: 0.15,
                InsightType.CORRELATION: 0.1,
                InsightType.BUSINESS_GOAL: 0.15  # Add this
            }
        }

        if domain_type in domain_adjustments:
            for insight_type, adjustment in domain_adjustments[domain_type].items():
                if insight_type in insights:
                    insights[insight_type] += adjustment

    async def analyze_context(
            self,
            data: Any,
            metadata: Dict[str, Any]
    ) -> InsightContext:
        """Analyze data context to determine appropriate insights"""
        try:
            # Create initial context
            context = InsightContext(
                pipeline_id=metadata['pipeline_id'],
                staged_id=metadata['staged_id'],
                current_phase=InsightPhase.INITIALIZATION,
                metadata=metadata,
                quality_check_passed=metadata.get('quality_check_passed', False),
                domain_type=metadata.get('domain_type')
            )

            # Analyze data characteristics
            characteristics = self._analyze_data_characteristics(data)
            context.metadata['data_characteristics'] = characteristics

            # Determine appropriate insight types
            appropriate_insights = self._determine_appropriate_insights(
                characteristics,
                context.domain_type
            )
            context.metadata['appropriate_insights'] = appropriate_insights

            return context

        except Exception as e:
            self.logger.error(f"Context analysis failed: {str(e)}")
            raise

    async def generate_insights(
            self,
            pipeline_id: str,
            staged_id: str,
            context: InsightContext,
            config: InsightConfig
    ) -> Dict[str, Any]:
        """Generate insights based on context and configuration"""
        try:
            results = {}

            # Get data from staging
            staged_data = await self.staging_manager.get_staged_data(staged_id)
            if not staged_data:
                raise ValueError(f"No data found in staging for ID: {staged_id}")

            data = staged_data.get('data')

            # Generate insights by type
            for insight_type, confidence in context.metadata['appropriate_insights'].items():
                if insight_type in config.enabled_types:
                    # Skip if confidence below threshold
                    if confidence < config.confidence_threshold:
                        continue

                    # Generate insights of this type
                    type_results = await self._generate_type_insights(
                        insight_type=insight_type,
                        data=data,
                        context=context,
                        config=config
                    )

                    if type_results:
                        results[insight_type.value] = type_results

            # Store results in staging
            results_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'pipeline_id': pipeline_id,
                    'insight_summary': self._get_insight_summary(results)
                }
            )

            return {
                'staged_id': results_staged_id,
                'insights': results
            }

        except Exception as e:
            self.logger.error(f"Insight generation failed: {str(e)}")
            raise

    # backend/data_pipeline/insights/processor/insight_processor.py (continued)

    async def _generate_type_insights(
            self,
            insight_type: InsightType,
            data: Any,
            context: InsightContext,
            config: InsightConfig
    ) -> Optional[Dict[str, Any]]:
        """Generate insights for a specific type"""
        if insight_type not in self.generators:
            return None

        generator = self.generators[insight_type]
        results = {}

        try:
            # Detect patterns/insights
            detected = await generator['detect'](data)
            if not detected:
                return None

            # Analyze detected patterns
            analyzed = await generator['analyze'](detected, context.metadata)

            # Validate findings
            validated = await generator['validate'](analyzed, config.confidence_threshold)

            # Filter and format results
            insights = []
            for finding in validated:
                if finding['confidence'] >= config.confidence_threshold:
                    insight = InsightResult(
                        insight_id=str(uuid.uuid4()),
                        insight_type=insight_type,
                        category=self._determine_category(finding),
                        priority=self._calculate_priority(finding),
                        title=finding['title'],
                        description=finding['description'],
                        confidence=finding['confidence'],
                        supporting_data=finding['supporting_data'],
                        recommendations=finding.get('recommendations', []),
                        metadata=finding.get('metadata', {})
                    )
                    insights.append(insight)

            # Sort by priority and confidence
            insights.sort(
                key=lambda x: (x.priority.value, x.confidence),
                reverse=True
            )

            # Apply max insights limit if configured
            if config.max_insights:
                insights = insights[:config.max_insights]

            results = {
                'insights': [insight.__dict__ for insight in insights],
                'metadata': {
                    'total_detected': len(detected),
                    'total_validated': len(validated),
                    'total_accepted': len(insights)
                }
            }

            return results

        except Exception as e:
            self.logger.error(f"Failed to generate {insight_type.value} insights: {str(e)}")
            return None

    def _determine_category(self, finding: Dict[str, Any]) -> InsightCategory:
        """Determine category of an insight"""
        # Implement category determination logic based on finding characteristics
        if 'temporal' in finding.get('tags', []):
            return InsightCategory.TEMPORAL
        elif 'business' in finding.get('tags', []):
            return InsightCategory.BUSINESS
        elif 'technical' in finding.get('tags', []):
            return InsightCategory.TECHNICAL
        elif 'operational' in finding.get('tags', []):
            return InsightCategory.OPERATIONAL
        return InsightCategory.STATISTICAL

    def _calculate_priority(self, finding: Dict[str, Any]) -> InsightPriority:
        """Calculate priority of an insight"""
        confidence = finding['confidence']
        impact = finding.get('impact', 0.5)
        urgency = finding.get('urgency', 0.5)

        score = (confidence * 0.4) + (impact * 0.4) + (urgency * 0.2)

        if score >= 0.8:
            return InsightPriority.CRITICAL
        elif score >= 0.6:
            return InsightPriority.HIGH
        elif score >= 0.4:
            return InsightPriority.MEDIUM
        elif score >= 0.2:
            return InsightPriority.LOW
        return InsightPriority.INFORMATIONAL

    async def validate_insights(
            self,
            pipeline_id: str,
            staged_id: str,
            insights: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate generated insights"""
        try:
            validation_results = {}

            for insight_type_str, type_insights in insights.items():
                insight_type = InsightType(insight_type_str)
                if insight_type not in self.validators:
                    continue

                validator = self.validators[insight_type]
                type_validations = []

                for insight in type_insights['insights']:
                    validation = await validator(insight)
                    type_validations.append({
                        'insight_id': insight['insight_id'],
                        'validation_status': validation['status'],
                        'validation_score': validation['score'],
                        'validation_details': validation['details']
                    })

                validation_results[insight_type_str] = {
                    'validations': type_validations,
                    'summary': {
                        'total': len(type_validations),
                        'passed': sum(1 for v in type_validations if v['validation_status']),
                        'failed': sum(1 for v in type_validations if not v['validation_status'])
                    }
                }

            # Store validation results in staging
            validation_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=validation_results,
                metadata={
                    'pipeline_id': pipeline_id,
                    'validation_summary': self._get_validation_summary(validation_results)
                }
            )

            return {
                'staged_id': validation_staged_id,
                'validations': validation_results
            }

        except Exception as e:
            self.logger.error(f"Insight validation failed: {str(e)}")
            raise

    def _get_insight_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of insight generation results"""
        summary = {
            'total_insights': 0,
            'insights_by_type': {},
            'insights_by_priority': {
                priority.value: 0 for priority in InsightPriority
            },
            'average_confidence': 0.0
        }

        total_confidence = 0.0

        for insight_type, type_results in results.items():
            insights = type_results.get('insights', [])
            summary['insights_by_type'][insight_type] = len(insights)
            summary['total_insights'] += len(insights)

            for insight in insights:
                summary['insights_by_priority'][insight['priority']] += 1
                total_confidence += insight['confidence']

        if summary['total_insights'] > 0:
            summary['average_confidence'] = total_confidence / summary['total_insights']

        return summary

    def _get_validation_summary(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of validation results"""
        summary = {
            'total_validations': 0,
            'passed_validations': 0,
            'failed_validations': 0,
            'validation_rate': 0.0,
            'validations_by_type': {}
        }

        for insight_type, type_results in validation_results.items():
            type_summary = type_results['summary']
            summary['total_validations'] += type_summary['total']
            summary['passed_validations'] += type_summary['passed']
            summary['failed_validations'] += type_summary['failed']
            summary['validations_by_type'][insight_type] = type_summary

        if summary['total_validations'] > 0:
            summary['validation_rate'] = (
                    summary['passed_validations'] / summary['total_validations']
            )

        return summary

    def _has_temporal_data(self, data: Any) -> bool:
        """Check if data contains temporal elements"""
        if hasattr(data, 'dtypes'):
            return any(str(dtype).startswith('datetime') for dtype in data.dtypes)
        return False

    def _has_numeric_data(self, data: Any) -> bool:
        """Check if data contains numeric elements"""
        if hasattr(data, 'dtypes'):
            return any(str(dtype).startswith(('int', 'float')) for dtype in data.dtypes)
        return False

    def _has_categorical_data(self, data: Any) -> bool:
        """Check if data contains categorical elements"""
        if hasattr(data, 'dtypes'):
            return any(str(dtype) == 'object' or str(dtype) == 'category'
                       for dtype in data.dtypes)
        return False

    def _has_missing_data(self, data: Any) -> bool:
        """Check if data contains missing values"""
        if hasattr(data, 'isna'):
            return data.isna().any().any()
        return False

    async def cleanup(self) -> None:
        """Cleanup processor resources"""
        # Cleanup any resources if needed
        pass