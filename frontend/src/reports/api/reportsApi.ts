// src/report/api/reportsApi.ts
import { ApiClient } from './client';
import { API_CONFIG } from './config';
import type {
  Report,
  ReportConfig,
  ScheduleConfig,
  ExportOptions,
  ReportGenerationOptions,
  ReportMetadata
} from '../types/report';

class ReportsApi extends ApiClient {
  // Report CRUD Operations
  listReports(params?: {
    page?: number;
    limit?: number;
    type?: string[];
    status?: string[];
  }): Promise<Report[]> {
    return this.request('GET', API_CONFIG.ENDPOINTS.LIST, { params });
  }

  createReport(
    config: ReportConfig,
    options?: ReportGenerationOptions
  ): Promise<Report> {
    return this.request('POST', API_CONFIG.ENDPOINTS.CREATE, {
      data: { config, options }
    });
  }

  getReport(id: string): Promise<Report> {
    const url = API_CONFIG.ENDPOINTS.GET.replace(':id', id);
    return this.request('GET', url);
  }

  deleteReport(id: string): Promise<void> {
    const url = API_CONFIG.ENDPOINTS.DELETE.replace(':id', id);
    return this.request('DELETE', url);
  }

  // Report Generation and Status
  getReportStatus(id: string): Promise<{
    status: Report['status'];
    progress?: number;
    error?: string;
  }> {
    const url = API_CONFIG.ENDPOINTS.STATUS.replace(':id', id);
    return this.request('GET', url);
  }

  exportReport(
    id: string,
    options: ExportOptions
  ): Promise<{ downloadUrl: string }> {
    const url = API_CONFIG.ENDPOINTS.EXPORT.replace(':id', id);
    return this.request('POST', url, { data: options });
  }

  // Report Scheduling
  scheduleReport(config: ScheduleConfig): Promise<Report> {
    return this.request('POST', API_CONFIG.ENDPOINTS.SCHEDULE, {
      data: config
    });
  }

  updateSchedule(
    id: string,
    updates: Partial<ScheduleConfig>
  ): Promise<Report> {
    const url = `${API_CONFIG.ENDPOINTS.SCHEDULE}/${id}`;
    return this.request('PUT', url, { data: updates });
  }

  // Report Metadata and Preview
  getReportMetadata(id: string): Promise<ReportMetadata> {
    const url = API_CONFIG.ENDPOINTS.METADATA.replace(':id', id);
    return this.request('GET', url);
  }

  previewReport(
    id: string,
    section?: string
  ): Promise<{ content: string }> {
    const url = API_CONFIG.ENDPOINTS.PREVIEW.replace(':id', id);
    return this.request('GET', url, {
      params: { section }
    });
  }

  // Report Templates
  getTemplates(): Promise<{
    id: string;
    name: string;
    type: string;
  }[]> {
    return this.request('GET', API_CONFIG.ENDPOINTS.TEMPLATES);
  }

  // Report Download Helpers
  downloadReport(url: string): Promise<Blob> {
    return this.client.get(url, {
      responseType: 'blob'
    }).then(response => response.data);
  }
}

export const reportsApi = new ReportsApi();