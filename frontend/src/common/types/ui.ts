// src/common/types/ui.ts
export type Theme = 'light' | 'dark' | 'system';
export type Size = 'sm' | 'md' | 'lg' | 'xl';
export type Variant = 'primary' | 'secondary' | 'outline' | 'ghost';
export type Status = 'idle' | 'loading' | 'success' | 'error';

export interface Modal {
  id: string;
  type: string;
  props?: Record<string, any>;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  title?: string;
  duration?: number;
  dismissible?: boolean;
}

export interface TableConfig {
  pageSize: number;
  visibleColumns: string[];
  sortColumn?: string;
  sortDirection?: 'asc' | 'desc';
  filters?: Record<string, unknown>;
}
