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
      // Transform the config to match the backend schema
      const transformedConfig = {
        name: config.name,
        type: config.type,
        description: config.description || '',
        // Conditionally add source-specific config based on type
        ...(config.type === 'file' && {
          file_config: {
            original_filename: config.name,
            file_type: config.config.type,
            delimiter: config.config.delimiter,
            encoding: config.config.encoding,
            mime_type: 'text/csv', // Infer or set appropriately
            size: 0, // You might want to calculate this
            hash: '', // Generate a hash if possible
            compression: null,
            parse_options: config.config.parseOptions
          }
        }),
        ...(config.type === 'database' && {
          database_config: config.config
        }),
        ...(config.type === 'api' && {
          api_config: config.config
        }),
        ...(config.type === 's3' && {
          s3_config: config.config
        }),
        ...(config.type === 'stream' && {
          stream_config: config.config
        }),

        // Additional common fields
        is_active: config.status === 'active',
        refresh_interval: config.refreshInterval || 0
      };

      console.log('Transformed config for backend:', transformedConfig);

      const response = await dataSourceApi.createDataSource(transformedConfig);
      return response.data as BaseMetadata || {
        id: null,
        name: config.name,
        type: config.type
      };
    } catch (error) {
      const apiError = error as ApiError;
      console.error('Create data source error:', error);
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