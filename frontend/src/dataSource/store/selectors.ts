import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../store/types';
import type { DataSourceMetadata, DataSourceType } from '../types/dataSources';

// Basic selectors
export const selectSources = (state: RootState) => state.dataSources.sources;
export const selectConfigs = (state: RootState) => state.dataSources.configs;
export const selectSelectedSourceId = (state: RootState) => state.dataSources.selectedSourceId;
export const selectFilters = (state: RootState) => state.dataSources.filters;
export const selectIsLoading = (state: RootState) => state.dataSources.isLoading;
export const selectError = (state: RootState) => state.dataSources.error;

// Memoized selectors
export const selectFilteredSources = createSelector(
  [selectSources, selectFilters],
  (sources, filters) => {
    return Object.values(sources).filter(source => {
      const matchesType = !filters.types?.length || filters.types.includes(source.type);
      const matchesStatus = !filters.status?.length || filters.status.includes(source.status);
      const matchesSearch = !filters.search || (
        source.name.toLowerCase().includes(filters.search.toLowerCase()) ||
        source.description?.toLowerCase().includes(filters.search.toLowerCase())
      );
      
      return matchesType && matchesStatus && matchesSearch;
    });
  }
);

export const selectSourcesByType = createSelector(
  [selectSources],
  (sources): Record<DataSourceType, DataSourceMetadata[]> => {
    return Object.values(sources).reduce((acc, source) => {
      if (!acc[source.type]) {
        acc[source.type] = [];
      }
      acc[source.type].push(source);
      return acc;
    }, {} as Record<DataSourceType, DataSourceMetadata[]>);
  }
);

export const selectSelectedSource = createSelector(
  [selectSources, selectConfigs, selectSelectedSourceId],
  (sources, configs, selectedId) => {
    if (!selectedId) return null;
    const metadata = sources[selectedId];
    const config = configs[selectedId];
    return metadata && config ? { metadata, config } : null;
  }
);