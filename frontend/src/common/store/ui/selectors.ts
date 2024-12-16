// src/common/store/ui/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '@/store/types';
import type { 
  Theme, 
  Modal, 
  Notification, 
  TableConfig, 
  Breadcrumb,
  UserPreferences 
} from '../../types/ui';
import type { UIState } from './uiSlice';

// Base selectors
export const selectUI = (state: RootState): UIState => state.ui;

export const selectTheme = (state: RootState): Theme => 
  state.ui.theme || 'light';

export const selectSidebarState = createSelector(
  (state: RootState) => ({
    isOpen: state.ui.sidebarOpen,
    width: state.ui.sidebarWidth,
    isCollapsed: state.ui.sidebarCollapsed
  }),
  (sidebar) => sidebar
);

// Modal selectors
export const selectActiveModals = (state: RootState): Modal[] => 
  state.ui.activeModals || [];

export const selectModalById = (modalId: string) => createSelector(
  selectActiveModals,
  (modals): Modal | undefined => 
    modals.find(modal => modal.id === modalId)
);

export const selectHasActiveModals = createSelector(
  selectActiveModals,
  (modals): boolean => modals.length > 0
);

// Notification selectors
export const selectNotifications = (state: RootState): Notification[] => 
  state.ui.notifications || [];

export const selectNotificationsByType = (type: Notification['type']) => createSelector(
  selectNotifications,
  (notifications): Notification[] => 
    notifications.filter(notification => notification.type === type)
);

// Table configuration selectors
export const selectTableConfigs = (state: RootState): Record<string, TableConfig> => 
  state.ui.tableConfigs || {};

export const selectTableConfig = (tableId: string) => createSelector(
  selectTableConfigs,
  (configs): TableConfig | undefined => configs[tableId]
);

// Loading state selectors
export const selectLoadingStates = (state: RootState): Record<string, boolean> => 
  state.ui.loadingStates || {};

export const selectLoadingState = (key: string) => createSelector(
  selectLoadingStates,
  (loadingStates): boolean => loadingStates[key] ?? false
);

export const selectIsAnyLoading = createSelector(
  selectLoadingStates,
  (loadingStates): boolean => 
    Object.values(loadingStates).some(isLoading => isLoading)
);

// Breadcrumb selectors
export const selectBreadcrumbs = (state: RootState): Breadcrumb[] => 
  state.ui.breadcrumbs || [];

export const selectCurrentPath = createSelector(
  selectBreadcrumbs,
  (breadcrumbs): string => 
    breadcrumbs.length > 0 ? breadcrumbs[breadcrumbs.length - 1].path : '/'
);

// Preferences selectors
export const selectPreferences = (state: RootState): UserPreferences[] => 
  state.ui.preferences || [];

// Composite selectors
export const selectUIState = createSelector(
  [selectTheme, selectSidebarState, selectHasActiveModals],
  (theme, sidebar, hasModals) => ({
    theme,
    sidebar,
    hasModals
  })
);

export const selectTableState = (tableId: string) => createSelector(
  [selectTableConfig(tableId), selectLoadingState(`table_${tableId}`)],
  (config, isLoading) => ({
    config,
    isLoading
  })
);