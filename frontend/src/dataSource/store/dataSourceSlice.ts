import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import type {
  DataSourceState,
  DataSourceMetadata,
  DataSourceConfig,
  DataSourceFilters,
  ValidationResult,
  PreviewData
} from '../types/dataSources';
import { dataSourceApi } from '../api';

// Define error interface
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

// Async Thunks
export const fetchDataSources = createAsyncThunk(
  'dataSources/fetchAll',
  async () => {
    const response = await dataSourceApi.listDataSources();
    return response.data;
  }
);

export const createDataSource = createAsyncThunk<
  DataSourceMetadata,
  DataSourceConfig,
  {
    rejectValue: string;
  }
>(
  'dataSources/createDataSource',
  async (config: DataSourceConfig, { rejectWithValue }) => {
    try {
      const response = await dataSourceApi.createDataSource(config);
      return response.data;
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

// Slice
const dataSourceSlice = createSlice({
  name: 'dataSource',
  initialState,
  reducers: {
    setDataSources(state, action: PayloadAction<DataSourceMetadata[]>) {
      state.sources = action.payload.reduce((acc, source) => {
        acc[source.id] = source;
        return acc;
      }, {} as Record<string, DataSourceMetadata>);
    },
    updateDataSource(state, action: PayloadAction<DataSourceMetadata>) {
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
    setConfig(state, action: PayloadAction<{ id: string; config: DataSourceConfig }>) {
      state.configs[action.payload.id] = action.payload.config;
    },
    setValidation(state, action: PayloadAction<{ id: string; validation: ValidationResult }>) {
      state.validation[action.payload.id] = action.payload.validation;
    },
    setPreview(state, action: PayloadAction<{ id: string; preview: PreviewData }>) {
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
    },
    clearState(state) {
      Object.assign(state, initialState);
    }
  },
  extraReducers: (builder) => {
    builder
      // Fetch cases
      .addCase(fetchDataSources.pending, (state) => {
        state.isLoading = true;
        state.error = null;
      })
      .addCase(fetchDataSources.fulfilled, (state, action) => {
        state.isLoading = false;
        state.sources = action.payload.reduce((acc, source) => {
          acc[source.id] = source;
          return acc;
        }, {} as Record<string, DataSourceMetadata>);
        state.error = null;
      })
      .addCase(fetchDataSources.rejected, (state, action) => {
        state.isLoading = false;
        state.error = action.error.message ?? 'Failed to fetch data sources';
      })
      // Create cases
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
      // Delete cases
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