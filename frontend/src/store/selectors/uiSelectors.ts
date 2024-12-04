// src/store/selectors/uiSelectors.ts
import { createSelector } from '@reduxjs/toolkit';
import { RootState } from '../types';

// Basic selectors
export const selectUI = (state: RootState) => state.ui;
export const selectTheme = (state: RootState) => state.ui.theme;
export const selectSidebarState = (state: RootState) => state.ui.sidebarCollapsed;
export const selectNotifications = (state: RootState) => state.ui.notifications;
export const selectGlobalLoading = (state: RootState) => state.ui.globalLoading;

// Memoized selectors
export const selectLoadingState = (key: string) =>
  createSelector(
    selectUI,
    (ui) => ui.loadingStates[key] || false
  );

export const selectModalState = (modalId: string) =>
  createSelector(
    selectUI,
    (ui) => ui.modals[modalId] || { isOpen: false, data: undefined }
  );

export const selectActiveNotifications = createSelector(
  selectNotifications,
  (notifications) => notifications.filter(n => !n.dismissed)
);

// Composite selectors
export const selectUIState = createSelector(
  [selectTheme, selectSidebarState, selectGlobalLoading],
  (theme, sidebarCollapsed, globalLoading) => ({
    theme,
    sidebarCollapsed,
    globalLoading
  })
);


