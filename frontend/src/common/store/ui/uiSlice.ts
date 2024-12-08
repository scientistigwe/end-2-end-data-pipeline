// src/common/store/ui/uiSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { Theme, Modal, Notification, TableConfig } from '../../types/ui';

interface UIState {
  theme: Theme;
  sidebarOpen: boolean;
  sidebarWidth: number;
  activeModals: Modal[];
  notifications: Notification[];
  tableConfigs: Record<string, TableConfig>;
  loadingStates: Record<string, boolean>;
  breadcrumbs: Array<{ path: string; label: string }>;
}

const initialState: UIState = {
  theme: 'system',
  sidebarOpen: true,
  sidebarWidth: 256,
  activeModals: [],
  notifications: [],
  tableConfigs: {},
  loadingStates: {},
  breadcrumbs: []
};

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    setTheme: (state, action: PayloadAction<Theme>) => {
      state.theme = action.payload;
    },
    toggleSidebar: (state) => {
      state.sidebarOpen = !state.sidebarOpen;
    },
    setSidebarWidth: (state, action: PayloadAction<number>) => {
      state.sidebarWidth = action.payload;
    },
    openModal: (state, action: PayloadAction<Omit<Modal, 'id'>>) => {
      state.activeModals.push({
        id: Date.now().toString(),
        ...action.payload
      });
    },
    closeModal: (state, action: PayloadAction<string>) => {
      state.activeModals = state.activeModals.filter(
        modal => modal.id !== action.payload
      );
    },
    addNotification: (state, action: PayloadAction<Omit<Notification, 'id'>>) => {
      state.notifications.push({
        id: Date.now().toString(),
        ...action.payload
      });
    },
    removeNotification: (state, action: PayloadAction<string>) => {
      state.notifications = state.notifications.filter(
        notification => notification.id !== action.payload
      );
    },
    setTableConfig: (
      state,
      action: PayloadAction<{ tableId: string; config: Partial<TableConfig> }>
    ) => {
      const { tableId, config } = action.payload;
      state.tableConfigs[tableId] = {
        ...state.tableConfigs[tableId],
        ...config
      };
    },
    setLoadingState: (
      state,
      action: PayloadAction<{ key: string; isLoading: boolean }>
    ) => {
      state.loadingStates[action.payload.key] = action.payload.isLoading;
    },
    setBreadcrumbs: (
      state,
      action: PayloadAction<Array<{ path: string; label: string }>>
    ) => {
      state.breadcrumbs = action.payload;
    }
  }
});

export const {
  setTheme,
  toggleSidebar,
  setSidebarWidth,
  openModal,
  closeModal,
  addNotification,
  removeNotification,
  setTableConfig,
  setLoadingState,
  setBreadcrumbs
} = uiSlice.actions;

export default uiSlice.reducer;


