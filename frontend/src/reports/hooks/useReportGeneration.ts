// src/report/hooks/useReportGeneration.ts
import { useMutation, useQueryClient } from 'react-query';
import { useDispatch } from 'react-redux';
import { reportsApi } from '../api/reportsApi';
import { updateReportStatus } from '../store/reportSlice';
import type { ReportStatus } from '../types/models';

export function useReportGeneration(reportId: string) {
  const dispatch = useDispatch();
  const queryClient = useQueryClient();

  const generateReport = useMutation(
    async (options?: ReportGenerationOptions) => {
      dispatch(updateReportStatus({ 
        id: reportId, 
        status: 'generating' 
      }));
      
      try {
        const response = await reportsApi.createReport(
          { id: reportId },
          options
        );
        dispatch(updateReportStatus({ 
          id: reportId, 
          status: 'completed' 
        }));
        return response;
      } catch (error) {
        dispatch(updateReportStatus({ 
          id: reportId, 
          status: 'failed',
          error: error instanceof Error ? error.message : 'Generation failed'
        }));
        throw error;
      }
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['report', reportId]);
      }
    }
  );

  const exportReport = useMutation(
    async (format: string) => {
      const response = await reportsApi.exportReport(reportId, { format });
      return response.downloadUrl;
    }
  );

  return {
    generateReport,
    exportReport
  };
}
