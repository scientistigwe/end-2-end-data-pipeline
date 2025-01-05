// src/dataSource/components/validation/types.ts
import type { ValidationResult } from '../../types/base';

export interface ValidationDisplayProps {
  validation: ValidationResult;
  className?: string;
  compact?: boolean;
  showTitle?: boolean;
}

export interface ValidationIssueProps {
  field?: string;
  type: string;
  severity: string;
  message: string;
}