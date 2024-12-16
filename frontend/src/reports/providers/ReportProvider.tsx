// src/report/providers/ReportProvider.tsx
import React, { useState, useCallback } from "react";
import { useDispatch, useSelector } from "react-redux";
import { ReportContext } from "../context/ReportContext";
import { reportsApi } from "../api/reportsApi";
import { reportService } from "../services/reportService";
import {
  setSelectedReport,
  addReport,
  updateReport as updateReportState,
  removeReport,
  setError
} from "../store/reportSlice";
import { selectSelectedReportId } from "../store/selectors";
import type {
  Report,
  ReportConfig,
  ReportMetadata,
  ScheduleConfig,
  ExportOptions,
  ReportStatus,
} from "../types/report";

interface ReportProviderProps {
  children: React.ReactNode;
}

export const ReportProvider: React.FC<ReportProviderProps> = ({ children }) => {
  const dispatch = useDispatch();
  const selectedReportId = useSelector(selectSelectedReportId);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setErrorState] = useState<string | null>(null);

  // Error Handler
  const handleError = useCallback(
    (error: unknown, fallbackMessage: string) => {
      const message = error instanceof Error ? error.message : fallbackMessage;
      setErrorState(message);
      dispatch(setError(message));
      throw error;
    },
    [dispatch]
  );

  // Report Selection
  const setSelectedReportId = useCallback(
    (id: string | null) => {
      try {
        dispatch(setSelectedReport(id));
      } catch (err) {
        handleError(err, "Failed to set selected report");
      }
    },
    [dispatch, handleError]
  );

  // Report Operations
  const createReport = useCallback(
    async (config: ReportConfig): Promise<Report> => {
      setIsLoading(true);
      setErrorState(null);
      try {
        const validationResult = reportService.validateReportConfig(config);
        if (!validationResult.isValid) {
          throw new Error(validationResult.errors.join(", "));
        }

        const response = await reportsApi.createReport(config);
        const report = response.data;
        dispatch(addReport(report));
        return report;
      } catch (err) {
        return handleError(err, "Failed to create report");
      } finally {
        setIsLoading(false);
      }
    },
    [dispatch, handleError]
  );

  const updateReport = useCallback(
    async (id: string, updates: Partial<ReportConfig>): Promise<Report> => {
      setIsLoading(true);
      try {
        const currentReport = await reportsApi.getReport(id);
        const updatedConfig = { ...currentReport.data.config, ...updates };
        const response = await reportsApi.updateReport(id, updatedConfig);
        const updatedReport = response.data;
        dispatch(updateReportState(updatedReport));
        return updatedReport;
      } catch (err) {
        return handleError(err, "Failed to update report");
      } finally {
        setIsLoading(false);
      }
    },
    [dispatch, handleError]
  );

  const deleteReport = useCallback(
    async (id: string): Promise<void> => {
      setIsLoading(true);
      try {
        await reportsApi.deleteReport(id);
        dispatch(removeReport(id));
      } catch (err) {
        return handleError(err, "Failed to delete report");
      } finally {
        setIsLoading(false);
      }
    },
    [dispatch, handleError]
  );

  // Report Generation
  const generateReport = useCallback(
    async (id: string): Promise<void> => {
      setIsLoading(true);
      try {
        const response = await reportsApi.getReport(id);
        const report = response.data;
        await reportsApi.waitForReportGeneration(id, {
          onProgress: (progress) => {
            dispatch(
              updateReportState({
                id,
                progress,
                status: "generating" as ReportStatus,
              })
            );
          },
        });
      } catch (err) {
        return handleError(err, "Failed to generate report");
      } finally {
        setIsLoading(false);
      }
    },
    [dispatch, handleError]
  );

  const cancelGeneration = useCallback(
    async (id: string): Promise<void> => {
      try {
        await reportsApi.cancelGeneration(id);
        dispatch(
          updateReportState({
            id,
            status: "cancelled" as ReportStatus,
          })
        );
      } catch (err) {
        return handleError(err, "Failed to cancel report generation");
      }
    },
    [dispatch, handleError]
  );

  const getReportStatus = useCallback(
    async (id: string): Promise<ReportStatus> => {
      try {
        const response = await reportsApi.getReportStatus(id);
        return response.data.status;
      } catch (err) {
        return handleError(err, "Failed to get report status");
      }
    },
    [handleError]
  );

  // Report Export
  const exportReport = useCallback(
    async (id: string, options: ExportOptions): Promise<string> => {
      try {
        const response = await reportsApi.exportReport(id, options);
        return response.data.downloadUrl;
      } catch (err) {
        return handleError(err, "Failed to export report");
      }
    },
    [handleError]
  );

  // Report Scheduling
  const scheduleReport = useCallback(
    async (config: ScheduleConfig): Promise<void> => {
      setIsLoading(true);
      try {
        const validationResult = reportService.validateScheduleConfig(config);
        if (!validationResult.isValid) {
          throw new Error(validationResult.errors.join(", "));
        }

        await reportsApi.scheduleReport(config);
      } catch (err) {
        return handleError(err, "Failed to schedule report");
      } finally {
        setIsLoading(false);
      }
    },
    [handleError]
  );

  const updateSchedule = useCallback(
    async (id: string, updates: Partial<ScheduleConfig>): Promise<void> => {
      try {
        await reportsApi.updateSchedule(id, updates);
      } catch (err) {
        return handleError(err, "Failed to update schedule");
      }
    },
    [handleError]
  );

  // Report Metadata
  const getReportMetadata = useCallback(
    async (id: string): Promise<ReportMetadata> => {
      try {
        const response = await reportsApi.getReportMetadata(id);
        return response.data;
      } catch (err) {
        return handleError(err, "Failed to get report metadata");
      }
    },
    [handleError]
  );

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
    error,
  };

  return (
    <ReportContext.Provider value={value}>{children}</ReportContext.Provider>
  );
};
