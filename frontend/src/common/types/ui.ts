// src/common/types/ui.ts
import { UiStatus } from './status';

export type Theme = 'light' | 'dark' | 'system';
export type Size = 'sm' | 'md' | 'lg' | 'xl';
export type Variant = 'primary' | 'secondary' | 'outline' | 'ghost';

// Re-export UiStatus for convenience
export type { UiStatus } from './status';

// Use UiStatus instead of Status
export interface Modal {
  id: string;
  type: string;
  props?: Record<string, any>;
  title: string;
  content?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  onClose?: () => void;

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
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  customizations?: {
    density?: 'compact' | 'normal' | 'spacious';
    showBorders?: boolean;
    highlightOnHover?: boolean;
  };

}

export interface Breadcrumb {
  path: string;
  label: string;
}

export interface UserPreferences {
  dateFormat: string;
  timezone: string;
  language: string;
}