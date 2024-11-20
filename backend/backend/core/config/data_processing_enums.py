from enum import Enum
from typing import Dict

class ProcessingModule(Enum):
    # Existing Modules
    BASIC_DATA_VALIDATION = "basic_data_validation"
    TEXT_STANDARDIZATION = "text_standardization"
    IDENTIFIER_PROCESSING = "identifier_processing"
    NUMERIC_CURRENCY_PROCESSING = "numeric_currency_processing"
    DATE_TIME_PROCESSING = "date_time_processing"
    CODE_CLASSIFICATION = "code_classification"
    ADDRESS_LOCATION = "address_location"
    DUPLICATION_MANAGEMENT = "duplication_management"
    DOMAIN_SPECIFIC_VALIDATION = "domain_specific_validation"
    REFERENCE_DATA_MANAGEMENT = "reference_data_management"
    DATA_ISSUE_ANALYSIS = "data_issue_analysis_framework"
    DATA_ISSUE_RESOLUTION = "data_issue_resolution_framework"
    QUALITY_REPORT_GENERATION = "quality_report_generation"
    CLEANSED_DATA_REPORT = "cleansed_data_report"

    # NEW: Machine Learning and Advanced Processing Modules
    ML_FEATURE_ENGINEERING = "ml_feature_engineering"
    ML_ANOMALY_DETECTION = "ml_anomaly_detection"
    ML_CLASSIFICATION = "ml_classification"
    ML_CLUSTERING = "ml_clustering"

    # NEW: Advanced Data Processing
    PREDICTIVE_MODELING = "predictive_modeling"
    SEMANTIC_ANALYSIS = "semantic_analysis"
    NATURAL_LANGUAGE_PROCESSING = "natural_language_processing"

    # NEW: Data Integration and Transformation
    DATA_INTEGRATION = "data_integration"
    DATA_TRANSFORMATION = "data_transformation"
    SCHEMA_MAPPING = "schema_mapping"

    # NEW: Security and Compliance
    DATA_MASKING = "data_masking"
    ENCRYPTION_PROCESSING = "encryption_processing"
    COMPLIANCE_VALIDATION = "compliance_validation"


class DataIssueType(Enum):
    # Basic Data Validation Issues
    MISSING_VALUE = "missing_value"
    DATA_TYPE_MISMATCH = "data_type_mismatch"
    REQUIRED_FIELD = "required_field"
    NULL_CHECK = "null_check"
    EMPTY_STRING = "empty_string"

    # Text Standardization Issues
    CASE_INCONSISTENCY = "case_inconsistency"
    WHITESPACE_IRREGULARITY = "whitespace_irregularity"
    SPECIAL_CHARACTER = "special_character"
    TYPO = "typo"
    PATTERN_NORMALIZATION = "pattern_normalization"

    # Identifier Processing Issues
    ACCOUNT_NUMBER_INVALID = "account_number_invalid"
    PATIENT_ID_MISMATCH = "patient_id_mismatch"

    # Numeric and Currency Processing Issues
    CURRENCY_FORMAT = "currency_format"
    INTEREST_CALCULATION = "interest_calculation"
    INVENTORY_COUNT = "inventory_count"
    PRICE_FORMAT = "price_format"
    UNIT_CONVERSION = "unit_conversion"

    # Date and Time Processing Issues
    DATE_FORMAT = "date_format"
    TIMESTAMP_INVALID = "timestamp_invalid"
    AGE_CALCULATION = "age_calculation"
    SEQUENCE_INVALID = "sequence_invalid"
    TIMEZONE_ERROR = "timezone_error"

    # Code Classification Issues
    BATCH_CODE = "batch_code"
    FUNDING_CODE = "funding_code"
    JURISDICTION_CODE = "jurisdiction_code"
    MEDICAL_CODE_INVALID = "medical_code_invalid"
    TRANSACTION_CODE = "transaction_code"

    # Address Location Issues
    ADDRESS_FORMAT = "address_format"
    COORDINATE_INVALID = "coordinate_invalid"
    JURISDICTION_MAPPING = "jurisdiction_mapping"
    LOCATION_CODE = "location_code"
    POSTAL_CODE = "postal_code"

    # Duplication Management Issues
    EXACT_DUPLICATE = "exact_duplicate"
    FUZZY_MATCH = "fuzzy_match"
    MERGE_CONFLICT = "merge_conflict"
    RESOLUTION_NEEDED = "resolution_needed"
    VERSION_CONFLICT = "version_conflict"

    # Domain Specific Validation Issues
    COMPLIANCE_VIOLATION = "compliance_violation"
    INSTRUMENT_INVALID = "instrument_invalid"
    INVENTORY_RULE = "inventory_rule"
    SPEC_MISMATCH = "spec_mismatch"
    TERMINOLOGY_INVALID = "terminology_invalid"

    # Reference Data Management Issues
    CODELIST_OUTDATED = "codelist_outdated"
    LOOKUP_MISSING = "lookup_missing"
    RANGE_VIOLATION = "range_violation"
    REFERENCE_INVALID = "reference_invalid"
    TERMINOLOGY_MISMATCH = "terminology_mismatch"

    # NEW: Machine Learning Related Issues
    ML_FEATURE_INCONSISTENCY = "ml_feature_inconsistency"
    ML_MODEL_DRIFT = "ml_model_drift"
    ML_BIAS_DETECTION = "ml_bias_detection"

    # NEW: Data Integration Issues
    SCHEMA_MISMATCH = "schema_mismatch"
    DATA_SOURCE_CONFLICT = "data_source_conflict"
    INTEGRATION_MAPPING_ERROR = "integration_mapping_error"

    # NEW: Advanced Processing Issues
    SEMANTIC_PARSING_ERROR = "semantic_parsing_error"
    NLP_CONTEXT_MISUNDERSTANDING = "nlp_context_misunderstanding"

    # NEW: Security and Compliance Issues
    DATA_ANONYMIZATION_FAILURE = "data_anonymization_failure"
    ENCRYPTION_VIOLATION = "encryption_violation"
    COMPLIANCE_RULE_BREACH = "compliance_rule_breach"


def build_routing_graph() -> Dict[ProcessingModule, Dict[DataIssueType, ProcessingModule]]:
    """
    Construct a comprehensive dynamic routing graph with issue-specific routing
    """
    return {
        # Basic Data Validation Flow
        ProcessingModule.BASIC_DATA_VALIDATION: {
            DataIssueType.MISSING_VALUE: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.DATA_TYPE_MISMATCH: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.REQUIRED_FIELD: ProcessingModule.DATA_ISSUE_RESOLUTION,
            None: ProcessingModule.TEXT_STANDARDIZATION
        },

        # Text Standardization Flow
        ProcessingModule.TEXT_STANDARDIZATION: {
            DataIssueType.CASE_INCONSISTENCY: ProcessingModule.TEXT_STANDARDIZATION,
            DataIssueType.SPECIAL_CHARACTER: ProcessingModule.TEXT_STANDARDIZATION,
            DataIssueType.WHITESPACE_IRREGULARITY: ProcessingModule.TEXT_STANDARDIZATION,
            None: ProcessingModule.IDENTIFIER_PROCESSING
        },

        # Identifier Processing Flow
        ProcessingModule.IDENTIFIER_PROCESSING: {
            DataIssueType.ACCOUNT_NUMBER_INVALID: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.PATIENT_ID_MISMATCH: ProcessingModule.DATA_ISSUE_RESOLUTION,
            None: ProcessingModule.NUMERIC_CURRENCY_PROCESSING
        },

        # Numeric and Currency Processing Flow
        ProcessingModule.NUMERIC_CURRENCY_PROCESSING: {
            DataIssueType.CURRENCY_FORMAT: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.PRICE_FORMAT: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.UNIT_CONVERSION: ProcessingModule.DATA_ISSUE_RESOLUTION,
            None: ProcessingModule.DATE_TIME_PROCESSING
        },

        # Date and Time Processing Flow
        ProcessingModule.DATE_TIME_PROCESSING: {
            DataIssueType.DATE_FORMAT: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.TIMESTAMP_INVALID: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.TIMEZONE_ERROR: ProcessingModule.DATA_ISSUE_RESOLUTION,
            None: ProcessingModule.CODE_CLASSIFICATION
        },

        # Code Classification Flow
        ProcessingModule.CODE_CLASSIFICATION: {
            DataIssueType.BATCH_CODE: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.TRANSACTION_CODE: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.MEDICAL_CODE_INVALID: ProcessingModule.DATA_ISSUE_RESOLUTION,
            None: ProcessingModule.ADDRESS_LOCATION
        },

        # Address Location Processing Flow
        ProcessingModule.ADDRESS_LOCATION: {
            DataIssueType.ADDRESS_FORMAT: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.COORDINATE_INVALID: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.POSTAL_CODE: ProcessingModule.DATA_ISSUE_RESOLUTION,
            None: ProcessingModule.DUPLICATION_MANAGEMENT
        },

        # Duplication Management Flow
        ProcessingModule.DUPLICATION_MANAGEMENT: {
            DataIssueType.EXACT_DUPLICATE: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.FUZZY_MATCH: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.VERSION_CONFLICT: ProcessingModule.DATA_ISSUE_RESOLUTION,
            None: ProcessingModule.DOMAIN_SPECIFIC_VALIDATION
        },

        # NEW: Machine Learning Flow
        ProcessingModule.ML_FEATURE_ENGINEERING: {
            DataIssueType.ML_FEATURE_INCONSISTENCY: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.ML_MODEL_DRIFT: ProcessingModule.ML_ANOMALY_DETECTION,
            None: ProcessingModule.ML_CLASSIFICATION
        },

        # NEW: Data Integration Flow
        ProcessingModule.DATA_INTEGRATION: {
            DataIssueType.SCHEMA_MISMATCH: ProcessingModule.SCHEMA_MAPPING,
            DataIssueType.DATA_SOURCE_CONFLICT: ProcessingModule.DATA_ISSUE_RESOLUTION,
            None: ProcessingModule.DATA_TRANSFORMATION
        },

        # NEW: Security and Compliance Flow
        ProcessingModule.COMPLIANCE_VALIDATION: {
            DataIssueType.COMPLIANCE_RULE_BREACH: ProcessingModule.DATA_ISSUE_RESOLUTION,
            DataIssueType.ENCRYPTION_VIOLATION: ProcessingModule.ENCRYPTION_PROCESSING,
            None: ProcessingModule.QUALITY_REPORT_GENERATION
        }
    }