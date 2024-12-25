import { baseAxiosClient } from '@/common/api/client/baseClient';
import type { ApiResponse } from '@/common/types/api';
import type {
  Report,
  ReportConfig,
  ScheduleConfig,
  ExportOptions,
  ReportGenerationOptions,
  ReportMetadata,
  ReportError,
  ReportEventMap,
  ReportEventName,
  ReportGenerationCompleteDetail,
  ReportExportReadyDetail,
  ReportStatusChangeDetail,
  ReportErrorDetail
} from '../types/report';
import { REPORT_EVENTS } from '../types/report';

class ReportsApi {
  private client = baseAxiosClient;
  private readonly REPORT_EVENTS = REPORT_EVENTS;

  constructor() {
    this.setupReportHeaders();
    this.setupReportInterceptors();
  }

  private setupReportHeaders() {
    this.client.setDefaultHeaders({
      'X-Service': 'reports'
    });
  }

  // Interceptors and Error Handling
  private setupReportInterceptors() {
    // Add custom interceptor on the axios instance
    const instance = (this.client as any).client;
    if (!instance) return;

    instance.interceptors.request.use(
      (config) => {
        return config;
      }
    );

    instance.interceptors.response.use(
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

  private handleReportError(error: unknown): ReportError {
    const baseError: ReportError = {
      name: 'ReportError',
      message: 'Unknown report error',
      timestamp: new Date().toISOString(),
      component: 'report',
      details: {}
    };

    if (error instanceof Error) {
      return {
        ...error,
        ...baseError,
        message: error.message
      };
    }

    if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, any>;
      if (errorObj.config?.routeParams?.id) {
        baseError.details.reportId = errorObj.config.routeParams.id;
      }

      if (errorObj.response?.status === 404) {
        return {
          ...baseError,
          message: 'Report not found',
          code: 'REPORT_NOT_FOUND'
        };
      }

      if (errorObj.response?.status === 400) {
        return {
          ...baseError,
          message: `Invalid report configuration: ${errorObj.response.data?.message}`,
          code: 'INVALID_CONFIG'
        };
      }
    }

    return baseError;
  }

  // Event Management
  private handleReportEvents(response: any) {
    const url = response.config.url;
    if (url?.includes('/status') && response.data?.status === 'completed') {
      this.notifyGenerationComplete(
        response.data.id,
        response.data.status,
        response.data.metadata
      );
    }
  }

  private notifyError(error: ReportError): void {
    window.dispatchEvent(
      new CustomEvent<ReportErrorDetail>(this.REPORT_EVENTS.ERROR, {
        detail: {
          error: error.message,
          code: error.code,
          reportId: error.details.reportId || 'unknown'
        }
      })
    );
  }

  private notifyGenerationComplete(
    reportId: string,
    status: string,
    metadata: ReportMetadata
  ): void {
    window.dispatchEvent(
      new CustomEvent<ReportGenerationCompleteDetail>(
        this.REPORT_EVENTS.GENERATION_COMPLETE,
        {
          detail: { reportId, status, metadata }
        }
      )
    );
  }

  private notifyExportReady(exports: Array<{ id: string; downloadUrl: string }>): void {
    window.dispatchEvent(
      new CustomEvent<ReportExportReadyDetail>(this.REPORT_EVENTS.EXPORT_READY, {
        detail: { exports }
      })
    );
  }

  private notifyStatusChange(
    reportId: string,
    status: string,
    previousStatus?: string,
    progress?: number
  ): void {
    window.dispatchEvent(
      new CustomEvent<ReportStatusChangeDetail>(this.REPORT_EVENTS.STATUS_CHANGE, {
        detail: { reportId, status, previousStatus, progress }
      })
    );
  }

  // Report Status
  async getReportStatus(id: string): Promise<ApiResponse<{
    status: string;
    progress?: number;
    error?: string;
  }>> {
    return this.client.executeGet(
      this.client.createRoute('REPORTS', 'STATUS', { id })
    );
  }

  // CRUD Operations
  async listReports(params?: {
    page?: number;
    limit?: number;
    type?: string[];
    status?: string[];
  }): Promise<ApiResponse<Report[]>> {
    return this.client.executeGet(
      this.client.createRoute('REPORTS', 'LIST'),
      { params }
    );
  }

  async createReport(
    config: ReportConfig,
    options?: ReportGenerationOptions
  ): Promise<ApiResponse<Report>> {
    return this.client.executePost(
      this.client.createRoute('REPORTS', 'CREATE'),
      { config, options }
    );
  }

  async getReport(id: string): Promise<ApiResponse<Report>> {
    return this.client.executeGet(
      this.client.createRoute('REPORTS', 'DETAIL', { id })
    );
  }

  async updateReport(
    id: string,
    updates: Partial<ReportConfig>
  ): Promise<ApiResponse<Report>> {
    return this.client.executePut(
      this.client.createRoute('REPORTS', 'UPDATE', { id }),
      updates
    );
  }

  async deleteReport(id: string): Promise<ApiResponse<void>> {
    return this.client.executeDelete(
      this.client.createRoute('REPORTS', 'DELETE', { id })
    );
  }

  // Export Operations
  async exportReport(
    id: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.client.executePost(
      this.client.createRoute('REPORTS', 'EXPORT', { id }),
      options
    );
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

    this.notifyExportReady(exports);
    return exports;
  }

  // Schedule Operations
  async scheduleReport(config: ScheduleConfig): Promise<ApiResponse<Report>> {
    return this.client.executePost(
      this.client.createRoute('REPORTS', 'SCHEDULE'),
      config
    );
  }

  async updateSchedule(
    id: string,
    updates: Partial<ScheduleConfig>
  ): Promise<ApiResponse<Report>> {
    return this.client.executePut(
      this.client.createRoute('REPORTS', 'SCHEDULE', { id }),
      updates
    );
  }

  // Metadata and Preview
  async getReportMetadata(id: string): Promise<ApiResponse<ReportMetadata>> {
    return this.client.executeGet(
      this.client.createRoute('REPORTS', 'METADATA', { id })
    );
  }

  async previewReport(
    id: string,
    section?: string
  ): Promise<ApiResponse<{ content: string }>> {
    return this.client.executeGet(
      this.client.createRoute('REPORTS', 'PREVIEW', { id }),
      { params: { section } }
    );
  }

  // Templates
  async getTemplates(): Promise<ApiResponse<Array<{
    id: string;
    name: string;
    type: string;
  }>>> {
    return this.client.executeGet(
      this.client.createRoute('REPORTS', 'TEMPLATES')
    );
  }

  // Generation Monitoring
  private async checkGenerationStatus(
    id: string,
    startTime: number,
    interval: number,
    timeout: number,
    onProgress?: (progress: number) => void
  ): Promise<ApiResponse<Report>> {
    if (Date.now() - startTime >= timeout) {
      throw this.handleReportError({
        message: 'Report generation timeout',
        code: 'GENERATION_TIMEOUT',
        details: { reportId: id }
      });
    }

    const response = await this.getReportStatus(id);
    const { status, progress } = response.data;

    if (onProgress && progress !== undefined) {
      onProgress(progress);
    }

    this.notifyStatusChange(id, status, undefined, progress);

    if (status === 'completed' || status === 'failed' || status === 'cancelled') {
      const report = await this.getReport(id);
      if (status === 'completed') {
        const metadata = await this.getReportMetadata(id);
        this.notifyGenerationComplete(id, status, metadata.data);
      }
      return report;
    }

    await new Promise(resolve => setTimeout(resolve, interval));
    return this.checkGenerationStatus(id, startTime, interval, timeout, onProgress);
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
    const timeout = options?.timeout || 300000;
    return this.checkGenerationStatus(
      id,
      Date.now(),
      interval,
      timeout,
      options?.onProgress
    );
  }

  // Event Subscription
  subscribeToEvents<E extends ReportEventName>(
    event: E,
    callback: (event: ReportEventMap[E]) => void
  ): () => void {
    const handler = (e: Event) => callback(e as ReportEventMap[E]);
    window.addEventListener(event, handler);
    return () => window.removeEventListener(event, handler);
  }
}

// Export singleton instance
export const reportsApi = new ReportsApi();