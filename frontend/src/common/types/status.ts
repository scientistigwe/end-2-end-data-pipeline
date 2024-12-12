// src/common/types/status.ts
export const DATA_STATUS_TYPES = ['active', 'inactive', 'pending', 'error'] as const;
export const UI_STATUS_TYPES = ['idle', 'loading', 'success', 'error'] as const;

export type DataStatus = typeof DATA_STATUS_TYPES[number];
export type UiStatus = typeof UI_STATUS_TYPES[number];