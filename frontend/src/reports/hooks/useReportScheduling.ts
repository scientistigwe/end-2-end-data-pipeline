// src/report/hooks/useReportScheduling.ts
import { useMutation } from 'react-query';
import { useDispatch } from 'react-redux';
import { reportsApi } from '../api/reportsApi';
import { setReportSchedule } from '../store/reportSlice';
import type { ScheduleConfig } from '../types/models';

export function useReportScheduling(reportId: string) {
  const dispatch = useDispatch();

  const scheduleReport = useMutation(
    async (config: ScheduleConfig) => {
      const response = await reportsApi.scheduleReport(config);
      dispatch(setReportSchedule({ id: reportId, schedule: config }));
      return response;
    }
  );

  const updateSchedule = useMutation(
    async (updates: Partial<ScheduleConfig>) => {
      const response = await reportsApi.updateSchedule(reportId, updates);
      dispatch(setReportSchedule({ 
        id: reportId, 
        schedule: response.config as ScheduleConfig 
      }));
      return response;
    }
  );

  return {
    scheduleReport,
    updateSchedule
  };
}

