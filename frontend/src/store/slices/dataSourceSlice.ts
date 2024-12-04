// store/slices/dataSourcesSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { RootState } from '../index';

type DataSourceStatus = 'connecting' | 'connected' | 'error' | 'disconnected';
type DataSourceType = 'file' | 'api' | 'database' | 's3' | 'stream';

interface DataSource {
  id: string;
  type: DataSourceType;
  status: DataSourceStatus;
  config: any;
  metadata: any;
  error?: string;
}

interface DataSourceState {
  activeSources: Record<string, DataSource>;
  sourceConfigurations: Record<string, any>;
  uploadProgress: Record<string, number>;
  connectionHistory: Array<{
    id: string;
    type: string;
    timestamp: string;
    status: string;
  }>;
}

// Create a custom type for the RootState that includes our slice
declare module '../types' {
  interface RootState {
    dataSources: DataSourceState;
  }
}

const initialState: DataSourceState = {
  activeSources: {},
  sourceConfigurations: {},
  uploadProgress: {},
  connectionHistory: []
};

export const dataSourcesSlice = createSlice({
  name: 'dataSources',
  initialState,
  reducers: {
    sourceConnected(state, action: PayloadAction<{ sourceId: string; sourceData: DataSource }>) {
      state.activeSources[action.payload.sourceId] = {
        ...action.payload.sourceData,
        status: 'connected'
      };
    },
    sourceDisconnected(state, action: PayloadAction<string>) {
      delete state.activeSources[action.payload];
    },
    updateSourceStatus(state, action: PayloadAction<{
      sourceId: string;
      status: DataSourceStatus;
    }>) {
      const { sourceId, status } = action.payload;
      if (state.activeSources[sourceId]) {
        state.activeSources[sourceId].status = status;
      }
    },
    updateUploadProgress(state, action: PayloadAction<{ sourceId: string; progress: number }>) {
      state.uploadProgress[action.payload.sourceId] = action.payload.progress;
    }
  }
});

// Export actions
export const {
  sourceConnected,
  sourceDisconnected,
  updateSourceStatus,
  updateUploadProgress
} = dataSourcesSlice.actions;

// Typed selectors
export const selectActiveSources = (state: RootState) => state.dataSources.activeSources;
export const selectUploadProgress = (state: RootState) => state.dataSources.uploadProgress;
export const selectConnectionHistory = (state: RootState) => state.dataSources.connectionHistory;
export const selectSourceById = (id: string) => (state: RootState) => 
  state.dataSources.activeSources[id];

export default dataSourcesSlice.reducer;