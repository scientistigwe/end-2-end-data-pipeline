// src/dataSource/types/filters.ts
import type { DataSourceType, DataSourceStatus } from './base';

export interface DataSourceFilters {
  types?: DataSourceType[];
  status?: DataSourceStatus[];
  tags?: string[];
  search?: string;
  page?: number;
  limit?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}