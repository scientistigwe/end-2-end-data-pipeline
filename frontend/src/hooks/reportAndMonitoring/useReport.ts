// src/hooks/reports/useReport.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { reportApi } from '../../services/reportApi';
import { handleApiError } from '../../utils/apiUtils';

interface ReportConfig {
  type: 'quality' | 'insight' | 'performance' | 'summary';
  timeRange?: {
    start: string;
    end: string;
  };
  filters?: Record<string, any>;
  format?: 'pdf' | 'csv' | 'json';
}

interface ReportMetadata {
  id: string;
  type: string;
  generatedAt: string;
  status: string;
  filters: Record<string, any>;
}

export const useReport = (pipelineId: string) => {
  const [activeReportId, setActiveReportId] = useState<string | null>(null);

  // Generate Report
  const { mutate: generateReport, isLoading: isGenerating } = useMutation(
    async (config: ReportConfig) => {
      const response = await reportApi.generateReport(pipelineId, config);
      setActiveReportId(response.data.reportId);
      return response;
    },
    {
      onError: (error) => handleApiError(error)
    }
  );

  // Get Report Status
  const { data: reportStatus, refetch: refreshStatus } = useQuery(
    ['reportStatus', activeReportId],
    () => reportApi.getReportStatus(activeReportId!),
    {
      enabled: !!activeReportId,
      refetchInterval: 3000
    }
  );

  // Get Report Data
  const { data: reportData, refetch: refreshReport } = useQuery(
    ['reportData', activeReportId],
    () => reportApi.getReportData(activeReportId!),
    {
      enabled: !!activeReportId && reportStatus?.status === 'completed'
    }
  );

  // Get Report History
  const { data: reportHistory } = useQuery(
    ['reportHistory', pipelineId],
    () => reportApi.getReportHistory(pipelineId),
    {
      enabled: !!pipelineId
    }
  );

  // Export Report
  const { mutate: exportReport } = useMutation(
    async ({ reportId, format }: { reportId: string; format: string }) =>
      reportApi.exportReport(reportId, format)
  );

  // Schedule Report
  const { mutate: scheduleReport } = useMutation(
    async (schedule: {
      config: ReportConfig;
      frequency: 'daily' | 'weekly' | 'monthly';
      recipients: string[];
    }) => reportApi.scheduleReport(pipelineId, schedule)
  );

  return {
    generateReport,
    exportReport,
    scheduleReport,
    refreshStatus,
    refreshReport,
    reportStatus,
    reportData,
    reportHistory,
    isGenerating,
    activeReportId
  };
};
