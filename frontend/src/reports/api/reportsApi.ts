// src/report/api/reportsApi.ts
import { BaseClient } from '@/common/api/client/baseClient';
import { API_CONFIG } from '@/common/api/client/config';
import type { ApiResponse } from '@/common/types/api';
import type {
  Report,
  ReportConfig,
  ScheduleConfig,
  ExportOptions,
  ReportGenerationOptions,
  ReportMetadata
} from '../types/report';

class ReportsApi extends BaseClient {
  private readonly REPORT_EVENTS = {
    GENERATION_COMPLETE: 'report:generationComplete',
    EXPORT_READY: 'report:exportReady',
    STATUS_CHANGE: 'report:statusChange',
    ERROR: 'report:error'
  };

  constructor() {
    super({
      baseURL: import.meta.env.VITE_REPORTS_API_URL || API_CONFIG.BASE_URL,
      timeout: API_CONFIG.TIMEOUT,
      headers: {
        ...API_CONFIG.DEFAULT_HEADERS,
        'X-Service': 'reports'
      }
    });

    this.setupReportInterceptors();
  }

  // Interceptors and Error Handling
  private setupReportInterceptors() {
    this.client.interceptors.request.use(
      (config) => {
        config.headers.set('X-Report-Timestamp', new Date().toISOString());
        return config;
      }
    );

    this.client.interceptors.response.use(
      response => {
        this.handleReportEvents(response);
        return response;
      },
      error => {
        const enhancedError = this.handleReportError(error);
        this.notifyError(enhancedError);
        throw enhancedError;
      }
    );
  }

  private handleReportError(error: any): Error {
    if (error.response?.status === 404) {
      return new Error('Report not found');
    }
    if (error.response?.status === 400) {
      return new Error(`Invalid report configuration: ${error.response.data?.message}`);
    }
    return error;
  }

  private handleReportEvents(response: any) {
    const url = response.config.url;
    if (url?.includes('/status') && response.data?.status === 'completed') {
      this.dispatchEvent(this.REPORT_EVENTS.GENERATION_COMPLETE, response.data);
    }
  }

  private notifyError(error: Error): void {
    this.dispatchEvent(this.REPORT_EVENTS.ERROR, { error: error.message });
  }

  private dispatchEvent(eventName: string, detail: unknown): void {
    window.dispatchEvent(new CustomEvent(eventName, { detail }));
  }

  // Report CRUD Operations
  async listReports(params?: {
    page?: number;
    limit?: number;
    type?: string[];
    status?: string[];
  }): Promise<ApiResponse<Report[]>> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.LIST, { params });
  }

  async createReport(
    config: ReportConfig,
    options?: ReportGenerationOptions
  ): Promise<ApiResponse<Report>> {
    return this.post(
      API_CONFIG.ENDPOINTS.REPORTS.CREATE,
      { config, options }
    );
  }

  async getReport(id: string): Promise<ApiResponse<Report>> {
    return this.get(
      API_CONFIG.ENDPOINTS.REPORTS.GET,
      { routeParams: { id } }
    );
  }

  async deleteReport(id: string): Promise<ApiResponse<void>> {
    return this.delete(
      API_CONFIG.ENDPOINTS.REPORTS.DELETE,
      { routeParams: { id } }
    );
  }

  async exportReport(
    id: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.post(
      API_CONFIG.ENDPOINTS.REPORTS.EXPORT,
      options,
      { routeParams: { id } }
    );
  }

  // Report Scheduling
  async scheduleReport(config: ScheduleConfig): Promise<ApiResponse<Report>> {
    return this.post(API_CONFIG.ENDPOINTS.REPORTS.SCHEDULE, config);
  }

  async updateSchedule(
    id: string,
    updates: Partial<ScheduleConfig>
  ): Promise<ApiResponse<Report>> {
    return this.put(
      `${API_CONFIG.ENDPOINTS.REPORTS.SCHEDULE}/${id}`,
      updates
    );
  }

  // Report Metadata and Preview
  async getReportMetadata(id: string): Promise<ApiResponse<ReportMetadata>> {
    return this.get(
      API_CONFIG.ENDPOINTS.REPORTS.METADATA,
      { routeParams: { id } }
    );
  }

  async previewReport(
    id: string,
    section?: string
  ): Promise<ApiResponse<{ content: string }>> {
    return this.get(
      API_CONFIG.ENDPOINTS.REPORTS.PREVIEW,
      {
        routeParams: { id },
        params: { section }
      }
    );
  }

  // Report Templates
  async getTemplates(): Promise<ApiResponse<Array<{
    id: string;
    name: string;
    type: string;
  }>>> {
    return this.get(API_CONFIG.ENDPOINTS.REPORTS.TEMPLATES);
  }

  // Helper Methods
  async downloadReport(url: string): Promise<Blob> {
    const response = await this.client.get(url, {
      responseType: 'blob'
    });
    return response.data;
  }

  async batchExportReports(
    reports: Array<{ id: string; options: ExportOptions }>
  ): Promise<Array<{ id: string; downloadUrl: string }>> {
    const exports = await Promise.all(
      reports.map(report => 
        this.exportReport(report.id, report.options)
          .then(response => ({
            id: report.id,
            downloadUrl: response.data.downloadUrl
          }))
      )
    );

    this.dispatchEvent(this.REPORT_EVENTS.EXPORT_READY, { exports });
    return exports;
  }

  async cancelGeneration(id: string): Promise<ApiResponse<void>> {
    return this.post(
      `${API_CONFIG.ENDPOINTS.REPORTS.STATUS}/${id}/cancel`, 
      // or use the proper endpoint from your API_CONFIG
      { routeParams: { id } }
    );
  }

  async generateReport(id: string): Promise<ApiResponse<void>> {
    return this.post(
      `${API_CONFIG.ENDPOINTS.REPORTS.STATUS}/${id}/generate`,
      // or use the proper endpoint from your API_CONFIG
      { routeParams: { id } }
    );
  }

  async updateReport(
    id: string, 
    updates: Partial<ReportConfig>
  ): Promise<ApiResponse<Report>> {
    return this.put(
      API_CONFIG.ENDPOINTS.REPORTS.UPDATE,
      updates,
      { routeParams: { id } }
    );
  }

  // Enhanced status methods
  async getReportStatus(id: string): Promise<ApiResponse<{
    status: Report['status'];
    progress?: number;
    error?: string;
  }>> {
    return this.get(
      API_CONFIG.ENDPOINTS.REPORTS.STATUS,
      { routeParams: { id } }
    );
  }

  async waitForReportGeneration(
    id: string,
    options?: {
      pollingInterval?: number;
      timeout?: number;
      onProgress?: (progress: number) => void;
    }
  ): Promise<ApiResponse<Report>> {
    const interval = options?.pollingInterval || 2000;
    const timeout = options?.timeout || 300000; // 5 minutes default
    const startTime = Date.now();

    while (Date.now() - startTime < timeout) {
      const response = await this.getReportStatus(id);
      const { status, progress } = response.data;

      if (options?.onProgress && progress !== undefined) {
        options.onProgress(progress);
      }

      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        return this.getReport(id);
      }

      await new Promise(resolve => setTimeout(resolve, interval));
    }

    throw new Error('Report generation timeout');
  }

  // Event Subscription
  subscribeToEvents(
    event: keyof typeof this.REPORT_EVENTS,
    callback: (event: CustomEvent) => void
  ): () => void {
    const handler = (e: Event) => callback(e as CustomEvent);
    window.addEventListener(this.REPORT_EVENTS[event], handler);
    return () => window.removeEventListener(this.REPORT_EVENTS[event], handler);
  }
}

// Export singleton instance
export const reportsApi = new ReportsApi();