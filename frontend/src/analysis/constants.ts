// src/analysis/constants.ts

export const ANALYSIS_CONSTANTS = {
    POLLING_INTERVAL: 2000, // 2 seconds
    MAX_RETRIES: 3,
    
    THRESHOLDS: {
      ERROR: {
        DEFAULT: 10,
        MIN: 0,
        MAX: 100
      },
      WARNING: {
        DEFAULT: 20,
        MIN: 0,
        MAX: 100
      }
    },
  
    CONFIDENCE_LEVELS: {
      HIGH: 90,
      MEDIUM: 70,
      LOW: 50
    },
  
    STATUS_MESSAGES: {
      STARTING: 'Starting analysis...',
      IN_PROGRESS: 'Analysis in progress...',
      COMPLETED: 'Analysis completed',
      FAILED: 'Analysis failed',
      CANCELLED: 'Analysis cancelled'
    },
  
    ERROR_MESSAGES: {
      START_FAILED: 'Failed to start analysis',
      LOAD_FAILED: 'Failed to load analysis data',
      UPDATE_FAILED: 'Failed to update analysis',
      INVALID_CONFIG: 'Invalid analysis configuration'
    },
  
    VISUALIZATION: {
      CHART_HEIGHT: 300,
      DEFAULT_COLOR: '#6366f1',
      COLOR_SCHEME: {
        POSITIVE: '#10b981',
        NEGATIVE: '#ef4444',
        NEUTRAL: '#6366f1',
        WARNING: '#f59e0b'
      }
    },
  
    DATE_RANGES: {
      DEFAULT_LOOKBACK: 7, // days
      MAX_LOOKBACK: 90 // days
    }
  };
  
  export const CHART_CONFIG = {
    LINE: {
      strokeWidth: 2,
      dot: false,
      activeDot: { r: 4 },
    },
    AXIS: {
      stroke: '#e5e7eb',
      strokeWidth: 1
    },
    GRID: {
      strokeDasharray: '3 3',
      stroke: '#e5e7eb'
    }
  };
  
  export const QUALITY_RULES = {
    DATA_TYPES: {
      id: 'dataTypes',
      label: 'Data Types Validation',
      description: 'Validate data type consistency across fields'
    },
    NULL_CHECKS: {
      id: 'nullChecks',
      label: 'Null Checks',
      description: 'Check for null or missing values'
    },
    RANGE_VALIDATION: {
      id: 'rangeValidation',
      label: 'Range Validation',
      description: 'Validate numeric values within expected ranges'
    }
  };
  
  export const INSIGHT_TYPES = {
    PATTERNS: {
      id: 'patterns',
      label: 'Pattern Detection',
      description: 'Identify recurring patterns in data'
    },
    CORRELATIONS: {
      id: 'correlations',
      label: 'Correlation Analysis',
      description: 'Analyze relationships between variables'
    },
    ANOMALIES: {
      id: 'anomalies',
      label: 'Anomaly Detection',
      description: 'Detect outliers and unusual patterns'
    },
    TRENDS: {
      id: 'trends',
      label: 'Trend Analysis',
      description: 'Analyze data trends over time'
    }
  };