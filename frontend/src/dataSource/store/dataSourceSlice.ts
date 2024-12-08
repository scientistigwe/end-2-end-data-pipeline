// src/store/datasource/dataSourceSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type {
  DataSourceConfig,
  DataSourceMetadata,
  ValidationResult,
  PreviewData,
  DataSourceFilters
} from '../types/dataSources';

interface DataSourceState {
  sources: Record<string, DataSourceMetadata>;
  configs: Record<string, DataSourceConfig>;
  validation: Record<string, ValidationResult>;
  preview: Record<string, PreviewData>;
  selectedSourceId: string | null;
  filters: DataSourceFilters;
  isLoading: boolean;
  error: string | null;
  activeSources: Record<string, {
    id: string;
    type: 'file' | 'api' | 'database' | 's3' | 'stream';
    status: 'connecting' | 'connected' | 'error' | 'disconnected';
    config: unknown;
    metadata: unknown;
    error?: string;
  }>;
  sourceConfigurations: Record<string, unknown>;
  uploadProgress: Record<string, number>;
  connectionHistory: Array<{
    id: string;
    type: string;
    timestamp: string;
    status: string;
  }>;
}

const initialState: DataSourceState = {
  sources: {},
  configs: {},
  validation: {},
  preview: {},
  selectedSourceId: null,
  filters: {
    types: [],
    status: [],
    tags: [],
    search: ''
  },
  isLoading: false,
  error: null
};

const dataSourceSlice = createSlice({
  name: 'dataSource',
  initialState,
  reducers: {
    setSources(state, action: PayloadAction<DataSourceMetadata[]>) {
      state.sources = action.payload.reduce((acc, source) => {
        acc[source.id] = source;
        return acc;
      }, {} as Record<string, DataSourceMetadata>);
    },
    updateSource(state, action: PayloadAction<DataSourceMetadata>) {
      state.sources[action.payload.id] = action.payload;
    },
    removeSource(state, action: PayloadAction<string>) {
      delete state.sources[action.payload];
      delete state.configs[action.payload];
      delete state.validation[action.payload];
      delete state.preview[action.payload];
    },
    setConfig(
      state,
      action: PayloadAction<{ id: string; config: DataSourceConfig }>
    ) {
      state.configs[action.payload.id] = action.payload.config;
    },
    setValidation(
      state,
      action: PayloadAction<{ id: string; validation: ValidationResult }>
    ) {
      state.validation[action.payload.id] = action.payload.validation;
    },
    setPreview(
      state,
      action: PayloadAction<{ id: string; preview: PreviewData }>
    ) {
      state.preview[action.payload.id] = action.payload.preview;
    },
    setFilters(state, action: PayloadAction<DataSourceFilters>) {
      state.filters = action.payload;
    },
    setSelectedSource(state, action: PayloadAction<string | null>) {
      state.selectedSourceId = action.payload;
    },
    setLoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },
    setError(state, action: PayloadAction<string | null>) {
      state.error = action.payload;
    }
  }
});

export const {
  setSources,
  updateSource,
  removeSource,
  setConfig,
  setValidation,
  setPreview,
  setFilters,
  setSelectedSource,
  setLoading,
  setError
} = dataSourceSlice.actions;

export default dataSourceSlice.reducer;

