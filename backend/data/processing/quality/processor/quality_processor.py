# backend/data_pipeline/quality/processor/quality_processor.py

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from core.messaging.broker import MessageBroker
from core.messaging.event_types import MessageType, ProcessingMessage
from core.staging.staging_manager import StagingManager

# Import quality modules
from ..detectors import (
    basic_data_validation,
    address_location,
    code_classification,
    date_time_processing,
    domain_specific_validation,
    duplication_management,
    identifier_processing,
    numeric_currency_processing,
    text_standardization
)

from ..analyzers import (
    basic_data_validation as basic_analyzer,
    address_location as address_analyzer,
    code_classification as code_analyzer,
    date_time_processing as datetime_analyzer,
    domain_specific_validation as domain_analyzer,
    identifier_processing as id_analyzer,
    numeric_currency_processing as numeric_analyzer,
    text_standardization as text_analyzer
)

from ..resolvers import (
    basic_data_validation as basic_resolver,
    address_location as address_resolver,
    code_classification as code_resolver,
    date_time_processing as datetime_resolver,
    domain_specific_validation as domain_resolver,
    identifier_processing as id_resolver,
    numeric_currency_processing as numeric_resolver,
    text_standardization as text_resolver
)

logger = logging.getLogger(__name__)


class QualityCheckType(Enum):
    """Types of quality checks"""
    BASIC_VALIDATION = "basic_validation"
    ADDRESS_LOCATION = "address_location"
    CODE_CLASSIFICATION = "code_classification"
    DATETIME_PROCESSING = "datetime_processing"
    DOMAIN_VALIDATION = "domain_validation"
    DUPLICATION_CHECK = "duplication_check"
    IDENTIFIER_CHECK = "identifier_check"
    NUMERIC_CURRENCY = "numeric_currency"
    TEXT_STANDARD = "text_standard"


@dataclass
class ColumnContext:
    """Context for a data column"""
    name: str
    data_type: str
    sample_values: List[Any]
    missing_count: int
    unique_count: int
    patterns: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DataContext:
    """Context for the entire dataset"""
    total_rows: int
    total_columns: int
    column_contexts: Dict[str, ColumnContext]
    relationships: Dict[str, List[str]]
    domain_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class QualityProcessor:
    """
    Quality processor that analyzes context and coordinates quality checks.
    Acts as an intelligent router for quality modules.
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
        """Initialize registries for quality modules"""
        # Detector modules
        self.detectors = {
            QualityCheckType.BASIC_VALIDATION: {
                "missing_values": basic_data_validation.detect_missing_value,
                "data_types": basic_data_validation.detect_data_type_mismatch,
                "empty_strings": basic_data_validation.detect_default_placeholder_value
            },
            QualityCheckType.DATETIME_PROCESSING: {
                "date_format": date_time_processing.detect_date_format,
                "timezone": date_time_processing.detect_timezone_error,
                "sequence": date_time_processing.detect_sequence_invalid
            },
            QualityCheckType.NUMERIC_CURRENCY: {
                "format": numeric_currency_processing.detect_format,
                "range": numeric_currency_processing.detect_range,
                "precision": numeric_currency_processing.detect_precision
            },
            # Add other detector mappings
        }

        # Analyzer modules
        self.analyzers = {
            QualityCheckType.BASIC_VALIDATION: {
                "missing_values": basic_analyzer.analyze_missing_value,
                "data_types": basic_analyzer.analyze_data_type_mismatch,
                "empty_strings": basic_analyzer.analyze_empty_string
            },
            QualityCheckType.DATETIME_PROCESSING: {
                "date_format": datetime_analyzer.analyze_date_format,
                "timezone": datetime_analyzer.analyze_timezone_error,
                "sequence": datetime_analyzer.analyze_sequence_invalid
            },
            # Add other analyzer mappings
        }

        # Resolver modules
        self.resolvers = {
            QualityCheckType.BASIC_VALIDATION: {
                "missing_values": basic_resolver.resolve_missing_value,
                "data_types": basic_resolver.resolve_data_type_mismatch,
                "empty_strings": basic_resolver.resolve_empty_string
            },
            QualityCheckType.DATETIME_PROCESSING: {
                "date_format": datetime_resolver.resolve_date_format,
                "timezone": datetime_resolver.resolve_timezone_error,
                "sequence": datetime_resolver.resolve_sequence_invalid
            },
            # Add other resolver mappings
        }

    async def analyze_context(
            self,
            data: Any,
            metadata: Dict[str, Any]
    ) -> DataContext:
        """Analyze data context to determine required quality checks"""
        try:
            # Initial data profiling
            context = self._profile_data(data)

            # Enhance context with metadata
            if metadata.get('domain_type'):
                context.domain_type = metadata['domain_type']

            # Identify relationships
            context.relationships = self._identify_relationships(data)

            # Determine required checks based on context
            required_checks = self._determine_required_checks(context)
            context.metadata['required_checks'] = required_checks

            return context

        except Exception as e:
            self.logger.error(f"Context insight failed: {str(e)}")
            raise

    def _profile_data(self, data: Any) -> DataContext:
        """Profile data to understand its structure and characteristics"""
        column_contexts = {}

        for column in data.columns:
            sample = data[column].head(100).tolist()
            column_contexts[column] = ColumnContext(
                name=column,
                data_type=str(data[column].dtype),
                sample_values=sample,
                missing_count=data[column].isna().sum(),
                unique_count=data[column].nunique(),
                patterns=self._detect_patterns(sample)
            )

        return DataContext(
            total_rows=len(data),
            total_columns=len(data.columns),
            column_contexts=column_contexts,
            relationships={}
        )

    def _detect_patterns(self, values: List[Any]) -> List[str]:
        """Detect patterns in data values"""
        patterns = set()
        for value in values:
            if value is not None:
                pattern = self._analyze_value_pattern(value)
                if pattern:
                    patterns.add(pattern)
        return list(patterns)

    def _analyze_value_pattern(self, value: Any) -> Optional[str]:
        """Analyze pattern of a single value"""
        try:
            str_value = str(value)
            if self._is_date_pattern(str_value):
                return "DATE"
            elif self._is_numeric_pattern(str_value):
                return "NUMERIC"
            elif self._is_code_pattern(str_value):
                return "CODE"
            elif self._is_address_pattern(str_value):
                return "ADDRESS"
            return "TEXT"
        except:
            return None

    def _identify_relationships(self, data: Any) -> Dict[str, List[str]]:
        """Identify relationships between columns"""
        relationships = {}
        # Implement relationship detection logic
        # - Correlation insight
        # - Pattern matching
        # - Domain-specific rules
        return relationships

    def _determine_required_checks(self, context: DataContext) -> Dict[str, List[str]]:
        """Determine which quality checks are needed based on context"""
        required_checks = {}

        # Check each column
        for col_name, col_context in context.column_contexts.items():
            column_checks = []

            # Basic validation for all columns
            column_checks.append(QualityCheckType.BASIC_VALIDATION.value)

            # Type-specific checks
            if "DATE" in col_context.patterns:
                column_checks.append(QualityCheckType.DATETIME_PROCESSING.value)
            elif "NUMERIC" in col_context.patterns:
                column_checks.append(QualityCheckType.NUMERIC_CURRENCY.value)
            elif "CODE" in col_context.patterns:
                column_checks.append(QualityCheckType.CODE_CLASSIFICATION.value)
            elif "ADDRESS" in col_context.patterns:
                column_checks.append(QualityCheckType.ADDRESS_LOCATION.value)

            # Add checks based on column characteristics
            if col_context.unique_count == context.total_rows:
                column_checks.append(QualityCheckType.IDENTIFIER_CHECK.value)
            if col_context.missing_count > 0:
                column_checks.append(QualityCheckType.BASIC_VALIDATION.value)

            required_checks[col_name] = column_checks

        # Add dataset-level checks
        required_checks['dataset'] = [
            QualityCheckType.DUPLICATION_CHECK.value,
            QualityCheckType.DOMAIN_VALIDATION.value
        ]

        return required_checks

    async def process_quality_checks(
            self,
            pipeline_id: str,
            staged_id: str,
            context: DataContext
    ) -> Dict[str, Any]:
        """Process quality checks based on context"""
        try:
            # Get data from staging
            staged_data = await self.staging_manager.get_staged_data(staged_id)
            if not staged_data:
                raise ValueError(f"No data found in staging for ID: {staged_id}")

            data = staged_data.get('data')
            results = {}

            # Process required checks for each column
            for column, required_checks in context.metadata['required_checks'].items():
                column_results = await self._process_column_checks(
                    data=data,
                    column=column,
                    required_checks=required_checks,
                    context=context
                )
                results[column] = column_results

            # Process dataset-level checks
            dataset_results = await self._process_dataset_checks(
                data=data,
                required_checks=context.metadata['required_checks']['dataset'],
                context=context
            )
            results['dataset'] = dataset_results

            # Store results in staging
            results_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=results,
                metadata={
                    'pipeline_id': pipeline_id,
                    'check_summary': self._get_check_summary(results)
                }
            )

            return results

        except Exception as e:
            self.logger.error(f"Quality check processing failed: {str(e)}")
            raise

    async def _process_column_checks(
            self,
            data: Any,
            column: str,
            required_checks: List[str],
            context: DataContext
    ) -> Dict[str, Any]:
        """Process quality checks for a specific column"""
        results = {}

        for check_type in required_checks:
            check_enum = QualityCheckType(check_type)

            # Run detectors
            if check_enum in self.detectors:
                for check_name, detector in self.detectors[check_enum].items():
                    detected_issues = detector(data[column])
                    if detected_issues:
                        # Run analyzer
                        analyzer = self.analyzers[check_enum].get(check_name)
                        if analyzer:
                            analysis = analyzer(detected_issues)
                            # Run resolver
                            resolver = self.resolvers[check_enum].get(check_name)
                            if resolver:
                                resolution = resolver(analysis)
                                results[check_name] = {
                                    'issues': detected_issues,
                                    'insight': analysis,
                                    'resolution': resolution
                                }

        return results

    async def _process_dataset_checks(
            self,
            data: Any,
            required_checks: List[str],
            context: DataContext
    ) -> Dict[str, Any]:
        """Process dataset-level quality checks"""
        results = {}

        for check_type in required_checks:
            check_enum = QualityCheckType(check_type)

            if check_enum in self.detectors:
                for check_name, detector in self.detectors[check_enum].items():
                    detected_issues = detector(data)
                    if detected_issues:
                        analyzer = self.analyzers[check_enum].get(check_name)
                        if analyzer:
                            analysis = analyzer(detected_issues)
                            resolver = self.resolvers[check_enum].get(check_name)
                            if resolver:
                                resolution = resolver(analysis)
                                results[check_name] = {
                                    'issues': detected_issues,
                                    'insight': analysis,
                                    'resolution': resolution
                                }

        return results

    def _get_check_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of quality check results"""
        return {
            'total_checks': len(results),
            'issues_found': sum(1 for r in results.values() if r.get('issues')),
            'auto_resolvable': sum(1 for r in results.values()
                                   if r.get('resolution', {}).get('auto_resolvable', False)),
            'manual_required': sum(1 for r in results.values()
                                   if not r.get('resolution', {}).get('auto_resolvable', False))
        }

    async def apply_resolutions(
            self,
            pipeline_id: str,
            staged_id: str,
            resolutions: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply resolutions to quality issues"""
        try:
            # Get data and results from staging
            staged_data = await self.staging_manager.get_staged_data(staged_id)
            if not staged_data:
                raise ValueError(f"No data found in staging for ID: {staged_id}")

            data = staged_data.get('data')
            resolution_results = {}

            # Apply resolutions by type
            for column, column_resolutions in resolutions.items():
                resolution_results[column] = {}

                for check_type, resolution in column_resolutions.items():
                    check_enum = QualityCheckType(check_type)
                    if check_enum in self.resolvers:
                        resolver = self.resolvers[check_enum].get(resolution['type'])
                        if resolver:
                            # Apply resolution
                            resolved_data = resolver(data[column], resolution['params'])
                            data[column] = resolved_data

                            resolution_results[column][check_type] = {
                                'status': 'resolved',
                                'method': resolution['type'],
                                'params': resolution['params']
                            }

            # Store resolved data in staging
            resolved_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=data,
                metadata={
                    'pipeline_id': pipeline_id,
                    'resolution_summary': self._get_resolution_summary(resolution_results),
                    'original_staged_id': staged_id
                }
            )

            return {
                'staged_id': resolved_staged_id,
                'resolutions': resolution_results
            }

        except Exception as e:
            self.logger.error(f"Resolution application failed: {str(e)}")
            raise

    def _get_resolution_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of resolution results"""
        total_resolutions = 0
        successful_resolutions = 0
        failed_resolutions = 0

        for column, resolutions in results.items():
            for check_type, resolution in resolutions.items():
                total_resolutions += 1
                if resolution['status'] == 'resolved':
                    successful_resolutions += 1
                else:
                    failed_resolutions += 1

        return {
            'total_resolutions': total_resolutions,
            'successful_resolutions': successful_resolutions,
            'failed_resolutions': failed_resolutions,
            'success_rate': successful_resolutions / total_resolutions if total_resolutions > 0 else 0
        }

    async def validate_resolutions(
            self,
            pipeline_id: str,
            staged_id: str
    ) -> Dict[str, Any]:
        """Validate applied resolutions"""
        try:
            # Get resolved data from staging
            staged_data = await self.staging_manager.get_staged_data(staged_id)
            if not staged_data:
                raise ValueError(f"No resolved data found in staging for ID: {staged_id}")

            data = staged_data.get('data')
            metadata = staged_data.get('metadata', {})
            original_staged_id = metadata.get('original_staged_id')

            # Re-run quality checks on resolved data
            context = await self.analyze_context(data, metadata)
            validation_results = await self.process_quality_checks(
                pipeline_id=pipeline_id,
                staged_id=staged_id,
                context=context
            )

            # Compare with original issues
            if original_staged_id:
                original_results = await self.staging_manager.get_staged_data(original_staged_id)
                if original_results:
                    validation_results['comparison'] = self._compare_quality_results(
                        original_results.get('data', {}),
                        validation_results
                    )

            # Store validation results
            validation_staged_id = await self.staging_manager.store_staged_data(
                staged_id=staged_id,
                data=validation_results,
                metadata={
                    'pipeline_id': pipeline_id,
                    'validation_summary': self._get_validation_summary(validation_results),
                    'resolved_staged_id': staged_id
                }
            )

            return {
                'staged_id': validation_staged_id,
                'validation_results': validation_results
            }

        except Exception as e:
            self.logger.error(f"Resolution validation failed: {str(e)}")
            raise

    def _compare_quality_results(
            self,
            original_results: Dict[str, Any],
            new_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compare original and new quality check results"""
        comparison = {
            'improved_checks': [],
            'unchanged_checks': [],
            'new_issues': []
        }

        for column in original_results:
            if column not in new_results:
                continue

            orig_checks = original_results[column]
            new_checks = new_results[column]

            for check_type, orig_result in orig_checks.items():
                if check_type not in new_checks:
                    continue

                new_result = new_checks[check_type]
                if not new_result.get('issues'):
                    comparison['improved_checks'].append({
                        'column': column,
                        'check_type': check_type
                    })
                else:
                    comparison['unchanged_checks'].append({
                        'column': column,
                        'check_type': check_type
                    })

            # Check for new issues
            for check_type, new_result in new_checks.items():
                if check_type not in orig_checks and new_result.get('issues'):
                    comparison['new_issues'].append({
                        'column': column,
                        'check_type': check_type
                    })

        return comparison

    def _get_validation_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of validation results"""
        summary = {
            'total_columns': len(results) - 1,  # Exclude 'comparison' key
            'resolved_issues': 0,
            'remaining_issues': 0,
            'new_issues': 0
        }

        if 'comparison' in results:
            comparison = results['comparison']
            summary.update({
                'improved_checks': len(comparison['improved_checks']),
                'unchanged_checks': len(comparison['unchanged_checks']),
                'new_issues': len(comparison['new_issues'])
            })

        return summary

    async def cleanup(self) -> None:
        """Cleanup processor resources"""
        # Cleanup any resources
        pass