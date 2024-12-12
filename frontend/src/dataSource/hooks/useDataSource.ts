// src/dataSource/hooks/useDataSource.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import {
  setDataSources,
  updateDataSource,
  setDataSourceDetails,
  setLoading,
  setError
} from '../store/dataSourceSlice';
import type {
  DataSourceConfig,
  DataSourceMetadata,
  DataSourceFilters,
  PreviewData
} from '../types/dataSources';

export const useDataSource = (filters?: DataSourceFilters) => {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();
  const [previewData, setPreviewData] = useState<PreviewData | null>(null);

  const {
    data: dataSources,
    isLoading,
    error: fetchError,
    refetch: refreshDataSources
  } = useQuery(
    ['dataSources', filters],
    async () => {
      dispatch(setLoading(true));
      try {
        const data = await DataSourceService.listDataSources(filters);
        dispatch(setDataSources(data));
        return data;
      } catch (err) {
        handleApiError(err);
        dispatch(setError('Failed to fetch data sources'));
        throw new Error(DATASOURCE_MESSAGES.ERRORS.LOAD_FAILED);
      } finally {
        dispatch(setLoading(false));
      }
    },
    {
      staleTime: 30000
    }
  );

  const { mutateAsync: createDataSource } = useMutation(
    async (config: DataSourceConfig) => {
      try {
        const response = await DataSourceService.createDataSource(config);
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.CREATE_FAILED);
      }
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['dataSources']);
      }
    }
  );

  const { mutateAsync: validateDataSource } = useMutation(
    async (id: string) => {
      return DataSourceService.validateDataSource(id);
    }
  );

  const getPreview = useCallback(async (id: string, options?: { limit?: number; offset?: number }) => {
    try {
      const data = await DataSourceService.previewData(id, options);
      setPreviewData(data);
      return data;
    } catch (err) {
      handleApiError(err);
      throw new Error(DATASOURCE_MESSAGES.ERRORS.PREVIEW_FAILED);
    }
  }, []);

  return {
    dataSources,
    isLoading,
    error: fetchError,
    previewData,
    createDataSource,
    validateDataSource,
    getPreview,
    refreshDataSources
  };
};


