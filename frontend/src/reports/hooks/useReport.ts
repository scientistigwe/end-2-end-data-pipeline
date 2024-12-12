// src/report/hooks/useReport.ts
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { reportsApi } from '../api/reportsApi';
import {
  addReport,
  updateReport,
  removeReport,
  setLoading,
  setError,
  setReportMetadata
} from '../store/reportSlice';
import type { Report, ReportConfig, ReportGenerationOptions } from '../types/report';

export function useReport(reportId?: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  // Get single report
  const { data: report, isLoading } = useQuery(
    ['report', reportId],
    async () => {
      if (!reportId) return null;
      const response = await reportsApi.getReport(reportId);
      return response;
    },
    {
      enabled: !!reportId
    }
  );

  // Create report
  const createReport = useMutation(
    async ({ config, options }: { 
      config: ReportConfig; 
      options?: ReportGenerationOptions 
    }) => {
      dispatch(setLoading(true));
      try {
        const response = await reportsApi.createReport(config, options);
        dispatch(addReport(response));
        return response;
      } finally {
        dispatch(setLoading(false));
      }
    },
    {
      onError: (error: Error) => {
        dispatch(setError(error.message));
      },
      onSuccess: () => {
        queryClient.invalidateQueries('reports');
      }
    }
  );

  // Delete report
  const deleteReport = useMutation(
    async (id: string) => {
      await reportsApi.deleteReport(id);
      dispatch(removeReport(id));
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries('reports');
      }
    }
  );

  return {
    report,
    isLoading,
    createReport,
    deleteReport
  };
}

