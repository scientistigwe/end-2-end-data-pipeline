// src/report/hooks/useReportMetadata.ts
import { useQuery } from 'react-query';
import { useDispatch } from 'react-redux';
import { reportsApi } from '../api/reportsApi';
import { setReportMetadata } from '../store/reportSlice';
import { REPORT_CONSTANTS } from '../constants';

export function useReportMetadata(reportId: string) {
  const dispatch = useDispatch();

  return useQuery(
    ['reportMetadata', reportId],
    async () => {
      const metadata = await reportsApi.getReportMetadata(reportId);
      dispatch(setReportMetadata({ id: reportId, metadata }));
      return metadata;
    },
    {
      enabled: !!reportId,
      refetchInterval: REPORT_CONSTANTS.UI.REFRESH_INTERVAL
    }
  );
}


