// src/hooks/reports/useReports.ts
import { useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { reportsApi } from '../api/reportApi';
import { handleApiError } from '../../../../utils/apiUtils';
import {
  setReports,
  addReport,
  updateReport,
  removeReport,
  setLoading,
  setError
} from '../store/reportSlice';
import type {
  Report,
  ReportConfig,
  ScheduleConfig,
  ExportOptions,
  ReportGenerationOptions
} from '../../types/report';

export function useReports() {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  // Fetch reports list
  const { data: reports } = useQuery(
    'reports',
    async () => {
      dispatch(setLoading(true));
      try {
        const response = await reportsApi.listReports();
        dispatch(setReports(response.data));
        return response.data;
      } catch (error) {
        handleApiError(error);
        throw error;
      } finally {
        dispatch(setLoading(false));
      }
    }
  );

  // Create report mutation
  const { mutate: createReport } = useMutation<
    Report,
    Error,
    { config: ReportConfig; options?: ReportGenerationOptions }
  >(
    ({ config, options }) => reportsApi.createReport(config, options),
    {
      onSuccess: (response) => {
        dispatch(addReport(response.data));
        queryClient.invalidateQueries('reports');
      },
      onError: (error) => {
        handleApiError(error);
        dispatch(setError(error.message));
      }
    }
  );

  // Delete report mutation
  const { mutate: deleteReport } = useMutation<void, Error, string>(
    (id) => reportsApi.deleteReport(id),
    {
      onSuccess: (_, id) => {
        dispatch(removeReport(id));
        queryClient.invalidateQueries('reports');
      },
      onError: handleApiError
    }
  );

  // Export report mutation
  const { mutate: exportReport } = useMutation<
    { downloadUrl: string },
    Error,
    { id: string; options: ExportOptions }
  >(
    ({ id, options }) => reportsApi.exportReport(id, options),
    {
      onError: handleApiError
    }
  );

  // Schedule report mutation
  const { mutate: scheduleReport } = useMutation<Report, Error, ScheduleConfig>(
    (config) => reportsApi.scheduleReport(config),
    {
      onSuccess: (response) => {
        dispatch(addReport(response.data));
        queryClient.invalidateQueries('reports');
      },
      onError: handleApiError
    }
  );

  // Poll report status
  const pollReportStatus = useCallback(async (id: string) => {
    const response = await reportsApi.getReportStatus(id);
    dispatch(updateReport(response.data));
    return response.data;
  }, [dispatch]);

  return {
    reports,
    createReport,
    deleteReport,
    exportReport,
    scheduleReport,
    pollReportStatus
  } as const;
}

