import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import type {
  DataSourceType,
  DataSourceStatus,
  BaseMetadata,
  BaseDataSourceConfig,
  ValidationRule,
  PreviewData
} from '../types/base';
import { dataSourceApi } from '../api';

interface DataSourceState {
  sources: Record<string, BaseMetadata>;
  configs: Record<string, BaseDataSourceConfig>;
  validation: Record<string, ValidationRule[]>;
  preview: Record<string, PreviewData>;
  selectedSourceId: string | null;
  filters: Record<string, unknown>;
  isLoading: boolean;
  error: string | null;
}

interface ApiError {
  response?: {
    data?: string;
  };
  message: string;
}

const initialState: DataSourceState = {
  sources: {},
  configs: {},
  validation: {},
  preview: {},
  selectedSourceId: null,
  filters: {},
  isLoading: false,
  error: null
};

export const fetchDataSources = createAsyncThunk(
  'dataSources/fetchAll',
  async () => {
    const response = await dataSourceApi.listDataSources();
    const allSources = Object.entries(response.data.sources).reduce<BaseMetadata[]>((acc, [sourceType, sources]) => {
      const typedSources = (sources as any[]).map(source => ({
        ...source,
        type: sourceType as DataSourceType,
        status: source.status || 'disconnected' as DataSourceStatus,
      }));
      return [...acc, ...typedSources];
    }, []);
    return allSources;
  }
);

export const createDataSource = createAsyncThunk(
  'dataSources/createDataSource',
  async (config: BaseDataSourceConfig, { rejectWithValue }) => {
    try {
      const response = await dataSourceApi.createDataSource(config);
      return response.data as BaseMetadata;
    } catch (error) {
      const apiError = error as ApiError;
      return rejectWithValue(
        apiError.response?.data || apiError.message || 'An error occurred'
      );
    }
  }
);

export const deleteDataSource = createAsyncThunk(
  'dataSources/delete',
  async (sourceId: string, { rejectWithValue }) => {
    try {
      await dataSourceApi.deleteDataSource(sourceId);
      return sourceId;
    } catch (error) {
      const apiError = error as ApiError;
      return rejectWithValue(
        apiError.response?.data || apiError.message || 'Failed to delete data source'
      );
    }
  }
);

const dataSourceSlice = createSlice({
  name: 'dataSource',
  initialState,
  reducers: {
    setDataSources(state, action: PayloadAction<BaseMetadata[]>) {
      state.sources = action.payload.reduce((acc, source) => {
        acc[source.id] = source;
        return acc;
      }, {} as Record<string, BaseMetadata>);
    },
    updateDataSource(state, action: PayloadAction<BaseMetadata>) {
      state.sources[action.payload.id] = action.payload;
    },
    removeDataSource(state, action: PayloadAction<string>) {
      delete state.sources[action.payload];
      delete state.configs[action.payload];
      delete state.validation[action.payload];
      delete state.preview[action.payload];
      if (state.selectedSourceId === action.payload) {
        state.selectedSourceId = null;
      }
    },
    setConfig(state, action: PayloadAction<{ id: string; config: BaseDataSourceConfig }>) {
      state.configs[action.payload.id] = action.payload.config;
    },
    setValidation(state, action: PayloadAction<{ id: string; validation: ValidationRule[] }>) {
      state.validation[action.payload.id] = action.payload.validation;
    },
    setPreview(state, action: PayloadAction<{ id: string; preview: PreviewData }>) {
      state.preview[action.payload.id] = action.payload.preview;
    },
    setFilters(state, action: PayloadAction<Record<string, unknown>>) {
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
    },
    clearState(state) {
      Object.assign(state, initialState);
    }
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchDataSources.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchDataSources.fulfilled, (state, action) => {
        state.isLoading = false;
        if (Array.isArray(action.payload)) {
          state.sources = action.payload.reduce((acc, source) => {
            if (source && source.id) {
              acc[source.id] = {
                ...source,
                type: source.type as DataSourceType,
                status: source.status as DataSourceStatus
              };
            }
            return acc;
          }, {} as Record<string, BaseMetadata>);
        } else {
          state.sources = {};
        }
        state.error = null;
      })
      .addCase(fetchDataSources.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message ?? 'Failed to fetch data sources';
      })
      .addCase(createDataSource.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(createDataSource.fulfilled, (state, action) => {
        state.isLoading = false;
        state.sources[action.payload.id] = action.payload;
        state.error = null;
      })
      .addCase(createDataSource.rejected, (state, action) => {
        state.isLoading = false;
        state.error = typeof action.payload === 'string' ? action.payload : 'Failed to create data source';
      })
      .addCase(deleteDataSource.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(deleteDataSource.fulfilled, (state, action) => {
        state.isLoading = false;
        delete state.sources[action.payload];
        delete state.configs[action.payload];
        delete state.validation[action.payload];
        delete state.preview[action.payload];
        if (state.selectedSourceId === action.payload) {
          state.selectedSourceId = null;
        }
        state.error = null;
      })
      .addCase(deleteDataSource.rejected, (state, action) => {
        state.isLoading = false;
        state.error = typeof action.payload === 'string' ? action.payload : 'Failed to delete data source';
      });
  }
});

export const {
  setDataSources,
  updateDataSource,
  removeDataSource,
  setConfig,
  setValidation,
  setPreview,
  setFilters,
  setSelectedSource,
  setLoading,
  setError,
  clearState
} = dataSourceSlice.actions;

export type dataSourceState = typeof initialState;
export default dataSourceSlice.reducer;