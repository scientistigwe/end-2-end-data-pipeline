// store/slices/uiSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

// Define types
type ThemeType = 'light' | 'dark' | 'system';
type NotificationType = 'success' | 'error' | 'warning' | 'info';
type ToastPosition = 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
type ModalSize = 'sm' | 'md' | 'lg' | 'xl' | 'full';

// Define interfaces
interface LoadingState {
  [key: string]: boolean;
}

interface ModalConfig {
  isOpen: boolean;
  size?: ModalSize;
  data?: any;
  closeable?: boolean;
  animated?: boolean;
}

interface ModalState {
  [key: string]: ModalConfig;
}

interface Notification {
  id: string;
  type: NotificationType;
  message: string;
  title?: string;
  duration?: number;
  dismissible?: boolean;
  position?: ToastPosition;
  action?: {
    label: string;
    onClick: () => void;
  };
}

interface UIPreferences {
  sidebarWidth: number;
  contentPadding: number;
  animationsEnabled: boolean;
  denseMode: boolean;
  notificationPosition: ToastPosition;
  defaultNotificationDuration: number;
}

interface UIState {
  theme: ThemeType;
  sidebarCollapsed: boolean;
  loadingStates: LoadingState;
  modals: ModalState;
  notifications: Notification[];
  globalLoading: boolean;
  preferences: UIPreferences;
  activeView: string;
  breadcrumbs: Array<{ label: string; path: string }>;
}

const defaultPreferences: UIPreferences = {
  sidebarWidth: 256,
  contentPadding: 24,
  animationsEnabled: true,
  denseMode: false,
  notificationPosition: 'top-right',
  defaultNotificationDuration: 5000
};

const initialState: UIState = {
  theme: 'light',
  sidebarCollapsed: false,
  loadingStates: {},
  modals: {},
  notifications: [],
  globalLoading: false,
  preferences: defaultPreferences,
  activeView: 'dashboard',
  breadcrumbs: []
};

export const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    // Theme management
    setTheme(state, action: PayloadAction<ThemeType>) {
      state.theme = action.payload;
    },

    // Sidebar management
    toggleSidebar(state) {
      state.sidebarCollapsed = !state.sidebarCollapsed;
    },
    setSidebarState(state, action: PayloadAction<boolean>) {
      state.sidebarCollapsed = action.payload;
    },

    // Loading states
    setLoading(state, action: PayloadAction<{ key: string; isLoading: boolean }>) {
      state.loadingStates[action.payload.key] = action.payload.isLoading;
    },
    setGlobalLoading(state, action: PayloadAction<boolean>) {
      state.globalLoading = action.payload;
    },
    clearLoadingStates(state) {
      state.loadingStates = {};
      state.globalLoading = false;
    },

    // Modal management
    openModal(state, action: PayloadAction<{ 
      modalId: string; 
      data?: any;
      size?: ModalSize;
      closeable?: boolean;
      animated?: boolean;
    }>) {
      state.modals[action.payload.modalId] = {
        isOpen: true,
        size: action.payload.size || 'md',
        data: action.payload.data,
        closeable: action.payload.closeable ?? true,
        animated: action.payload.animated ?? true
      };
    },
    closeModal(state, action: PayloadAction<string>) {
      if (state.modals[action.payload]?.closeable !== false) {
        state.modals[action.payload] = {
          isOpen: false,
          data: undefined
        };
      }
    },
    closeAllModals(state) {
      Object.keys(state.modals).forEach(modalId => {
        if (state.modals[modalId].closeable !== false) {
          state.modals[modalId].isOpen = false;
        }
      });
    },

    // Notification management
    addNotification(state, action: PayloadAction<Omit<Notification, 'id'>>) {
      const notification = {
        ...action.payload,
        id: Date.now().toString(),
        position: action.payload.position || state.preferences.notificationPosition,
        duration: action.payload.duration || state.preferences.defaultNotificationDuration,
        dismissible: action.payload.dismissible ?? true
      };
      state.notifications.push(notification);
    },
    removeNotification(state, action: PayloadAction<string>) {
      state.notifications = state.notifications.filter(
        notification => notification.id !== action.payload
      );
    },
    clearNotifications(state) {
      state.notifications = [];
    },

    // Preferences management
    updatePreferences(state, action: PayloadAction<Partial<UIPreferences>>) {
      state.preferences = {
        ...state.preferences,
        ...action.payload
      };
    },
    resetPreferences(state) {
      state.preferences = defaultPreferences;
    },

    // View management
    setActiveView(state, action: PayloadAction<string>) {
      state.activeView = action.payload;
    },
    setBreadcrumbs(state, action: PayloadAction<Array<{ label: string; path: string }>>) {
      state.breadcrumbs = action.payload;
    }
  }
});

// Export actions
export const {
  setTheme,
  toggleSidebar,
  setSidebarState,
  setLoading,
  setGlobalLoading,
  clearLoadingStates,
  openModal,
  closeModal,
  closeAllModals,
  addNotification,
  removeNotification,
  clearNotifications,
  updatePreferences,
  resetPreferences,
  setActiveView,
  setBreadcrumbs
} = uiSlice.actions;

// Selectors
export const selectTheme = (state: RootState) => state.ui.theme;
export const selectSidebarState = (state: RootState) => state.ui.sidebarCollapsed;
export const selectLoadingState = (key: string) => 
  (state: RootState) => state.ui.loadingStates[key] ?? false;
export const selectGlobalLoading = (state: RootState) => state.ui.globalLoading;
export const selectModalState = (modalId: string) => 
  (state: RootState) => state.ui.modals[modalId];
export const selectNotifications = (state: RootState) => state.ui.notifications;
export const selectPreferences = (state: RootState) => state.ui.preferences;
export const selectActiveView = (state: RootState) => state.ui.activeView;
export const selectBreadcrumbs = (state: RootState) => state.ui.breadcrumbs;

export default uiSlice.reducer;