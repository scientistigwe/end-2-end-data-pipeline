
// src/report/providers/ReportProvider.tsx
import React, { useState, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { ReportContext } from '../context/ReportContext';
import { reportsApi } from '../api/reportsApi';
import { reportService } from '../services/reportService';
import {
  setSelectedReport,
  addReport,
  updateReport as updateReportState,
  removeReport,
  setError,
  setLoading
} from '../store/reportSlice';
import { selectSelectedReportId } from '../store/selectors';
import type {
  Report,
  ReportConfig,
  ReportMetadata,
  ScheduleConfig,
  ExportOptions
} from '../types/report';

interface ReportProviderProps {
  children: React.ReactNode;
}

export const ReportProvider: React.FC<ReportProviderProps> = ({ children }) => {
  const dispatch = useDispatch();
  const selectedReportId = useSelector(selectSelectedReportId);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setErrorState] = useState<string | null>(null);

  // Report Selection
  const setSelectedReportId = useCallback((id: string | null) => {
    dispatch(setSelectedReport(id));
  }, [dispatch]);

  // Report Operations
  const createReport = useCallback(async (config: ReportConfig) => {
    setIsLoading(true);
    setErrorState(null);
    try {
      const validationResult = reportService.validateReportConfig(config);
      if (!validationResult.isValid) {
        throw new Error(validationResult.errors.join(', '));
      }

      const report = await reportsApi.createReport(config);
      dispatch(addReport(report));
      return report;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create report';
      setErrorState(message);
      dispatch(setError(message));
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [dispatch]);

  const updateReport = useCallback(async (id: string, updates: Partial<ReportConfig>) => {
    setIsLoading(true);
    try {
      const report = await reportsApi.updateReport(id, updates);
      dispatch(updateReportState(report));
      return report;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update report';
      setErrorState(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [dispatch]);

  const deleteReport = useCallback(async (id: string) => {
    setIsLoading(true);
    try {
      await reportsApi.deleteReport(id);
      dispatch(removeReport(id));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete report';
      setErrorState(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [dispatch]);

  // Report Generation
  const generateReport = useCallback(async (id: string) => {
    setIsLoading(true);
    try {
      await reportsApi.generateReport(id);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to generate report';
      setErrorState(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const cancelGeneration = useCallback(async (id: string) => {
    try {
      await reportsApi.cancelGeneration(id);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to cancel generation';
      setErrorState(message);
      throw err;
    }
  }, []);

  const getReportStatus = useCallback(async (id: string) => {
    try {
      const status = await reportsApi.getReportStatus(id);
      return status;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to get report status';
      setErrorState(message);
      throw err;
    }
  }, []);

  // Report Export
  const exportReport = useCallback(async (id: string, options: ExportOptions) => {
    try {
      const { downloadUrl } = await reportsApi.exportReport(id, options);
      return downloadUrl;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to export report';
      setErrorState(message);
      throw err;
    }
  }, []);

  // Report Scheduling
  const scheduleReport = useCallback(async (config: ScheduleConfig) => {
    setIsLoading(true);
    try {
      const validationResult = reportService.validateScheduleConfig(config);
      if (!validationResult.isValid) {
        throw new Error(validationResult.errors.join(', '));
      }

      await reportsApi.scheduleReport(config);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to schedule report';
      setErrorState(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const updateSchedule = useCallback(async (id: string, updates: Partial<ScheduleConfig>) => {
    try {
      await reportsApi.updateSchedule(id, updates);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update schedule';
      setErrorState(message);
      throw err;
    }
  }, []);

  // Report Metadata
  const getReportMetadata = useCallback(async (id: string): Promise<ReportMetadata> => {
    try {
      const metadata = await reportsApi.getReportMetadata(id);
      return metadata;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to get report metadata';
      setErrorState(message);
      throw err;
    }
  }, []);

  const value = {
    selectedReportId,
    setSelectedReportId,
    createReport,
    updateReport,
    deleteReport,
    generateReport,
    cancelGeneration,
    getReportStatus,
    exportReport,
    scheduleReport,
    updateSchedule,
    getReportMetadata,
    isLoading,
    error
  };

  return (
    <ReportContext.Provider value={value}>
      {children}
    </ReportContext.Provider>
  );
};

