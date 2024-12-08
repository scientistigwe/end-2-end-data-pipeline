// src/store/datasource/selectors.ts
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../common/types/store';
import type { 
  DataSourceConfig,
  DataSourceMetadata,
  DataSourceType,
  DataSourceStatus,
  DataSourceFilters,
  ValidationResult,
  PreviewData
} from '../types/dataSources';

// Basic Selectors
export const selectSources = (state: RootState): Record<string, DataSourceMetadata> => 
  state.dataSources.sources;

export const selectConfigs = (state: RootState): Record<string, DataSourceConfig> => 
  state.dataSources.configs;

export const selectValidation = (state: RootState): Record<string, ValidationResult> => 
  state.dataSources.validation;

export const selectPreview = (state: RootState): Record<string, PreviewData> => 
  state.dataSources.preview;

export const selectFilters = (state: RootState): DataSourceFilters => 
  state.dataSources.filters;

export const selectSelectedSourceId = (state: RootState): string | null => 
  state.dataSources.selectedSourceId;

export const selectIsLoading = (state: RootState): boolean =>
  state.dataSources.isLoading;

export const selectError = (state: RootState): string | null =>
  state.dataSources.error;

// Memoized Selectors
export const selectFilteredSources = createSelector(
  [selectSources, selectFilters],
  (sources, filters): DataSourceMetadata[] => {
    return Object.values(sources).filter((source) => {
      // Type filter
      if (filters.types?.length && !filters.types.includes(source.type)) {
        return false;
      }

      // Status filter
      if (filters.status?.length && !filters.status.includes(source.status)) {
        return false;
      }

      // Tags filter
      if (filters.tags?.length) {
        if (!source.tags?.some((tag: string) => filters.tags?.includes(tag))) {
          return false;
        }
      }

      // Search filter
      if (filters.search) {
        const search = filters.search.toLowerCase();
        const name = source.name.toLowerCase();
        const description = source.description?.toLowerCase() || '';
        
        return name.includes(search) || description.includes(search);
      }

      return true;
    });
  }
);


export interface SelectedSource {
  metadata: DataSourceMetadata;
  config: DataSourceConfig;
}

export const selectSelectedSource = createSelector(
  [selectSources, selectConfigs, selectSelectedSourceId],
  (sources, configs, selectedId): SelectedSource | null => {
    if (!selectedId) return null;
    
    const metadata = sources[selectedId];
    const config = configs[selectedId];
    
    if (!metadata || !config) return null;

    return { metadata, config };
  }
);

// Additional useful selectors
export const selectSourcesByType = createSelector(
  [selectSources],
  (sources): Record<DataSourceType, DataSourceMetadata[]> => {
    const result = {} as Record<DataSourceType, DataSourceMetadata[]>;
    
    Object.values(sources).forEach(source => {
      if (!result[source.type]) {
        result[source.type] = [];
      }
      result[source.type].push(source);
    });

    return result;
  }
);

export const selectSourcesByStatus = createSelector(
  [selectSources],
  (sources): Record<DataSourceStatus, DataSourceMetadata[]> => {
    const result = {} as Record<DataSourceStatus, DataSourceMetadata[]>;
    
    Object.values(sources).forEach(source => {
      if (!result[source.status]) {
        result[source.status] = [];
      }
      result[source.status].push(source);
    });

    return result;
  }
);