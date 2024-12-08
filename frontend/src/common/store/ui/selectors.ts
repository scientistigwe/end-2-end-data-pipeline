// src/common/store/ui/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../types';
import type { Modal } from '@/common/types/ui'; 

export const selectTheme = (state: RootState) => state.ui.theme;
export const selectSidebarOpen = (state: RootState) => state.ui.sidebarOpen;
export const selectSidebarWidth = (state: RootState) => state.ui.sidebarWidth;
export const selectActiveModals = (state: RootState) => state.ui.activeModals;
export const selectNotifications = (state: RootState) => state.ui.notifications;
export const selectBreadcrumbs = (state: RootState) => state.ui.breadcrumbs;


export const selectModalById = (modalId: string) =>
  createSelector(selectActiveModals, (modals) =>
    modals.find((modal: Modal) => modal.id === modalId)
  );

export const selectTableConfig = (tableId: string) =>
  createSelector(
    (state: RootState) => state.ui.tableConfigs,
    (configs) => configs[tableId]
  );

export const selectLoadingState = (key: string) =>
  createSelector(
    (state: RootState) => state.ui.loadingStates,
    (loadingStates) => loadingStates[key] ?? false
  );

