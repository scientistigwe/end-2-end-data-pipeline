// src/dataSource/utils/validators.ts
import type { 
  DataSourceConfig, 
  ValidationResult,
  DataSourceValidationSeverity,
  FileSourceConfig,
  ApiSourceConfig,
  DBSourceConfig,
  S3SourceConfig,
  StreamSourceConfig 
} from '../types/base';

interface ValidationIssue {
  field?: string;
  type: string;
  severity: DataSourceValidationSeverity;
  message: string;
}

export const validateDataSourceConfig = (config: Partial<DataSourceConfig>): ValidationResult => {
  const issues: ValidationIssue[] = [];
  const warnings: { field?: string; message: string }[] = [];

  // Base validation
  if (!config.name?.trim()) {
    issues.push({
      field: 'name',
      type: 'required',
      severity: 'error',
      message: 'Name is required'
    });
  }

  if (!config.type) {
    issues.push({
      field: 'type',
      type: 'required',
      severity: 'error',
      message: 'Type is required'
    });
  }

  // Type-specific validation
  const typeValidation = validateSourceTypeConfig(config);
  issues.push(...typeValidation.errors.map(error => ({
    type: 'validation',
    severity: 'error' as DataSourceValidationSeverity,
    message: error
  })));
  warnings.push(...typeValidation.warnings.map(warning => ({
    message: warning
  })));

  return {
    isValid: issues.length === 0,
    issues,
    warnings
  };
};

interface ValidationResponse {
  errors: string[];
  warnings: string[];
}

export const validateFileConfig = (config: FileSourceConfig['config']): ValidationResponse => {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!config.type) {
    errors.push('File type is required');
  }

  if (config.type === 'csv') {
    if (!config.delimiter) {
      errors.push('Delimiter is required for CSV files');
    }
    if (!config.hasHeader) {
      warnings.push('Consider specifying whether the file contains headers');
    }
  }

  return { errors, warnings };
};

export const validateApiConfig = (config: ApiSourceConfig['config']): ValidationResponse => {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!config.url) {
    errors.push('URL is required');
  } else {
    try {
      new URL(config.url);
    } catch {
      errors.push('Invalid URL format');
    }
  }

  if (!config.method) {
    errors.push('HTTP method is required');
  }

  if (!config.rateLimit) {
    warnings.push('Consider adding rate limiting to prevent API throttling');
  } else {
    if (config.rateLimit.requests <= 0) {
      errors.push('Rate limit requests must be greater than 0');
    }
    if (config.rateLimit.period <= 0) {
      errors.push('Rate limit period must be greater than 0');
    }
  }

  return { errors, warnings };
};

export const validateDBConfig = (config: DBSourceConfig['config']): ValidationResponse => {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!config.type) {
    errors.push('Database type is required');
  }

  if (!config.host) {
    errors.push('Host is required');
  }

  if (!config.port) {
    errors.push('Port is required');
  }

  if (!config.database) {
    errors.push('Database name is required');
  }

  if (!config.username) {
    errors.push('Username is required');
  }

  if (!config.pool) {
    warnings.push('Consider configuring connection pooling for better performance');
  }

  return { errors, warnings };
};

export const validateS3Config = (config: S3SourceConfig['config']): ValidationResponse => {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!config.bucket) {
    errors.push('Bucket name is required');
  }

  if (!config.region) {
    errors.push('Region is required');
  }

  if (!config.accessKeyId) {
    errors.push('Access Key ID is required');
  }

  if (!config.secretAccessKey) {
    errors.push('Secret Access Key is required');
  }

  if (!config.sslEnabled) {
    warnings.push('SSL should be enabled for secure data transfer');
  }

  return { errors, warnings };
};

export const validateStreamConfig = (config: StreamSourceConfig['config']): ValidationResponse => {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!config.protocol) {
    errors.push('Protocol is required');
  }

  if (!config.connection.hosts?.length) {
    errors.push('At least one host is required');
  }

  if (!config.consumer?.groupId) {
    warnings.push('Consider specifying a consumer group ID for better message handling');
  }

  return { errors, warnings };
};

const validateSourceTypeConfig = (config: Partial<DataSourceConfig>): ValidationResponse => {
  switch (config.type) {
    case 'file':
      return validateFileConfig(config.config as FileSourceConfig['config']);
    case 'api':
      return validateApiConfig(config.config as ApiSourceConfig['config']);
    case 'database':
      return validateDBConfig(config.config as DBSourceConfig['config']);
    case 's3':
      return validateS3Config(config.config as S3SourceConfig['config']);
    case 'stream':
      return validateStreamConfig(config.config as StreamSourceConfig['config']);
    default:
      return { errors: [], warnings: [] };
  }
};