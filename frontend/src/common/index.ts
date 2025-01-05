// frontend\src\common\index.ts

// Component exports with explicit naming
export * from './components';

// Utilities with explicit exports
export { dateUtils } from './utils/date/dateUtils';
export { storageUtils } from './utils/storage/storageUtils';
export { handleApiError } from './utils/api/apiUtils';
export { cn } from './utils/cn';

// Core exports
export * from './hooks';
export { BaseClient } from './api/client';
export * from './types';
export * from './styles';
export * from './store';