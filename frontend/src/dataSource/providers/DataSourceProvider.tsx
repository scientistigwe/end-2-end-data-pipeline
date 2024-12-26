// src/dataSource/providers/DataSourceProvider.tsx
import React, { useState, useCallback } from "react";
import { useDispatch } from "react-redux";
import { DataSourceContext } from "../context/DataSourceContext";
import { DataSourceService } from "../services/dataSourceService";
import { handleApiError } from "../../common/utils/api/apiUtils";
import { DATASOURCE_MESSAGES } from "../constants";
import {
  setDataSources,
  updateDataSource,
  removeDataSource,
  setFilters as setStoreFilters,
  setSelectedSource,
  setLoading,
  setError,
} from "../store/dataSourceSlice";
import type {
  DataSourceMetadata,
  DataSourceConfig,
  DataSourceFilters,
  ValidationResult,
  PreviewData,
} from "../types/base";

interface DataSourceProviderProps {
  children: React.ReactNode;
}

export const DataSourceProvider: React.FC<DataSourceProviderProps> = ({
  children,
}) => {
  const dispatch = useDispatch();

  // State
  const [dataSources, setDataSourcesState] = useState<DataSourceMetadata[]>([]);
  const [selectedSource, setSelectedSourceState] =
    useState<DataSourceConfig | null>(null);
  const [filters, setFiltersState] = useState<DataSourceFilters>({});
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);
  const [validationResult, setValidationResult] =
    useState<ValidationResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setErrorState] = useState<Error | null>(null);

  // Actions
  const loadDataSources = useCallback(
    async (filters?: DataSourceFilters) => {
      setIsLoading(true);
      dispatch(setLoading(true));

      try {
        const data = await DataSourceService.listDataSources(filters);
        setDataSourcesState(data);
        dispatch(setDataSources(data));
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        const errorMessage = DATASOURCE_MESSAGES.ERRORS.LOAD_FAILED;
        setErrorState(new Error(errorMessage));
        dispatch(setError(errorMessage));
      } finally {
        setIsLoading(false);
        dispatch(setLoading(false));
      }
    },
    [dispatch]
  );

  const createDataSource = useCallback(
    async (config: DataSourceConfig) => {
      setIsLoading(true);
      try {
        const response = await DataSourceService.createDataSource(config);
        setDataSourcesState((prev) => [...prev, response]);
        dispatch(updateDataSource(response));
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.CREATE_FAILED);
      } finally {
        setIsLoading(false);
      }
    },
    [dispatch]
  );

  const updateDataSourceConfig = useCallback(
    async (id: string, updates: Partial<DataSourceConfig>) => {
      setIsLoading(true);
      try {
        const response = await DataSourceService.updateDataSource(id, updates);
        setDataSourcesState((prev) =>
          prev.map((source) => (source.id === id ? response : source))
        );
        dispatch(updateDataSource(response));
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.UPDATE_FAILED);
      } finally {
        setIsLoading(false);
      }
    },
    [dispatch]
  );

  const deleteDataSource = useCallback(
    async (id: string) => {
      setIsLoading(true);
      try {
        await DataSourceService.deleteDataSource(id);
        setDataSourcesState((prev) =>
          prev.filter((source) => source.id !== id)
        );
        dispatch(removeDataSource(id));
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.DELETE_FAILED);
      } finally {
        setIsLoading(false);
      }
    },
    [dispatch]
  );

  const validateDataSource = useCallback(async (id: string) => {
    setIsLoading(true);
    try {
      const result = await DataSourceService.validateDataSource(id);
      setValidationResult(result);
      setErrorState(null);
      return result;
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.VALIDATION_FAILED);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const previewDataSource = useCallback(
    async (id: string, options?: { limit?: number; offset?: number }) => {
      setIsLoading(true);
      try {
        const data = await DataSourceService.previewData(id, options);
        setPreviewData(data);
        setErrorState(null);
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.PREVIEW_FAILED);
      } finally {
        setIsLoading(false);
      }
    },
    []
  );

  const setFilters = useCallback(
    (newFilters: DataSourceFilters) => {
      setFiltersState(newFilters);
      dispatch(setStoreFilters(newFilters));
    },
    [dispatch]
  );

  const selectDataSource = useCallback(
    (source: DataSourceConfig | null) => {
      setSelectedSourceState(source);
      dispatch(setSelectedSource(source?.id || null));
    },
    [dispatch]
  );

  const clearError = useCallback(() => {
    setErrorState(null);
    dispatch(setError(null));
  }, [dispatch]);

  const value = {
    // State
    dataSources,
    selectedSource,
    filters,
    previewData,
    validationResult,
    isLoading,
    error,

    // Actions
    loadDataSources,
    createDataSource,
    updateDataSource: updateDataSourceConfig,
    deleteDataSource,
    validateDataSource,
    previewDataSource,
    setFilters,
    selectDataSource,
    clearError,
  };

  return (
    <DataSourceContext.Provider value={value}>
      {children}
    </DataSourceContext.Provider>
  );
};
