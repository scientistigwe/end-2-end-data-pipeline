// src/report/api/reportsApi.ts
import { RouteHelper } from '@/common/api/routes';
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import { 
  ApiResponse, 
  HTTP_STATUS,
  ERROR_CODES 
} from '@/common/types/api';
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
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
} from '../types';
import { REPORT_EVENTS } from '../types';

interface ReportErrorMetadata {
  retryable: boolean;
  critical: boolean;
  code: string;
}

class ReportsApi {
  private client = baseAxiosClient;
  private static readonly ERROR_METADATA: Record<number, ReportErrorMetadata> = {
    [HTTP_STATUS.NOT_FOUND]: {
      retryable: false,
      critical: true,
      code: 'REPORT_NOT_FOUND'
    },
    [HTTP_STATUS.BAD_REQUEST]: {
      retryable: false,
      critical: true,
      code: 'INVALID_CONFIG'
    }
  };

  constructor() {
  this.client.setServiceConfig({
    service: ServiceType.REPORTS,
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    }
  });
  this.setupReportInterceptors();  // Keep your existing interceptors
}
  private setupReportInterceptors(): void {
    const instance = this.client.getAxiosInstance();
    if (!instance) return;

    instance.interceptors.request.use(
      this.handleRequestInterceptor,
      this.handleRequestError
    );

    instance.interceptors.response.use(
      this.handleResponseInterceptor,
      this.handleResponseError
    );
  }

  private handleRequestInterceptor = (
    config: InternalAxiosRequestConfig
  ): InternalAxiosRequestConfig | Promise<InternalAxiosRequestConfig> => {
    return config;
  };

  private handleRequestError = (error: unknown): Promise<never> => {
    return Promise.reject(this.handleReportError(error));
  };

  private handleResponseInterceptor = (
    response: AxiosResponse
  ): AxiosResponse | Promise<AxiosResponse> => {
    this.handleReportEvents(response);
    return response;
  };

  private handleResponseError = (error: unknown): Promise<never> => {
    const enhancedError = this.handleReportError(error);
    this.notifyError(enhancedError);
    throw enhancedError;
  };

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
        ...baseError,
        message: error.message,
        stack: error.stack
      };
    }

    if (typeof error === 'object' && error !== null) {
      const errorObj = error as Record<string, any>;
      if (errorObj.config?.routeParams?.id) {
        baseError.details.reportId = errorObj.config.routeParams.id;
      }

      const status = errorObj.response?.status;
      const errorMetadata = ReportsApi.ERROR_METADATA[status];

      if (errorMetadata) {
        return {
          ...baseError,
          code: errorMetadata.code,
          message: this.getErrorMessage(errorMetadata.code, errorObj.response?.data)
        };
      }
    }

    return baseError;
  }

  private getErrorMessage(code: string, data?: any): string {
    switch (code) {
      case 'REPORT_NOT_FOUND':
        return 'Report not found';
      case 'INVALID_CONFIG':
        return `Invalid report configuration: ${data?.message || ''}`;
      default:
        return 'An error occurred during report operation';
    }
  }

  private handleReportEvents(response: AxiosResponse): void {
    const url = response.config.url;
    if (!url) return;

    if (url.includes('/status') && response.data?.status === 'completed') {
      this.notifyGenerationComplete(
        response.data.id,
        response.data.status,
        response.data.metadata
      );
    }
  }

  // Event Notification Methods
  private notifyError(error: ReportError): void {
    window.dispatchEvent(
      new CustomEvent<ReportErrorDetail>(REPORT_EVENTS.ERROR, {
        detail: {
          error: error.message,
          code: error.code,
          reportId: error.details.reportId
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
        REPORT_EVENTS.GENERATION_COMPLETE,
        {
          detail: { reportId, status, metadata }
        }
      )
    );
  }

  private notifyExportReady(exports: Array<{ id: string; downloadUrl: string }>): void {
    window.dispatchEvent(
      new CustomEvent<ReportExportReadyDetail>(REPORT_EVENTS.EXPORT_READY, {
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
      new CustomEvent<ReportStatusChangeDetail>(REPORT_EVENTS.STATUS_CHANGE, {
        detail: { reportId, status, previousStatus, progress }
      })
    );
  }

  // Core API Methods
  async listReports(params?: {
    page?: number;
    limit?: number;
    type?: string[];
    status?: string[];
  }): Promise<ApiResponse<Report[]>> {
    return this.client.executeGet(
      RouteHelper.getRoute('REPORTS', 'LIST'),
      { params }
    );
  }

  async createReport(
    config: ReportConfig,
    options?: ReportGenerationOptions
  ): Promise<ApiResponse<Report>> {
    return this.client.executePost(
      RouteHelper.getRoute('REPORTS', 'CREATE'),
      { config, options }
    );
  }

  async getReport(id: string): Promise<ApiResponse<Report>> {
    return this.client.executeGet(
      RouteHelper.getRoute('REPORTS', 'GET', { report_id: id })
    );
  }

  async updateReport(
    id: string,
    updates: Partial<ReportConfig>
  ): Promise<ApiResponse<Report>> {
    return this.client.executePut(
      RouteHelper.getRoute('REPORTS', 'UPDATE', { report_id: id }),
      updates
    );
  }

  async deleteReport(id: string): Promise<ApiResponse<void>> {
    return this.client.executeDelete(
      RouteHelper.getRoute('REPORTS', 'DELETE', { report_id: id })
    );
  }

  // Status & Monitoring
  async getReportStatus(id: string): Promise<ApiResponse<{
    status: string;
    progress?: number;
    error?: string;
  }>> {
    return this.client.executeGet(
      RouteHelper.getRoute('REPORTS', 'STATUS', { report_id: id })
    );
  }

  // Export Operations
  async exportReport(
    id: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.client.executePost(
      RouteHelper.getRoute('REPORTS', 'EXPORT', { report_id: id }),
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
      RouteHelper.getRoute('REPORTS', 'SCHEDULE'),
      config
    );
  }

  async updateSchedule(
    id: string,
    updates: Partial<ScheduleConfig>
  ): Promise<ApiResponse<Report>> {
    return this.client.executePut(
      RouteHelper.getRoute('REPORTS', 'SCHEDULE', { report_id: id }),
      updates
    );
  }

  // Metadata & Preview
  async getReportMetadata(id: string): Promise<ApiResponse<ReportMetadata>> {
    return this.client.executeGet(
      RouteHelper.getRoute('REPORTS', 'METADATA', { report_id: id })
    );
  }

  async previewReport(
    id: string,
    section?: string
  ): Promise<ApiResponse<{ content: string }>> {
    return this.client.executeGet(
      RouteHelper.getRoute('REPORTS', 'PREVIEW', { report_id: id }),
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
      RouteHelper.getRoute('REPORTS', 'TEMPLATES')
    );
  }

  // Generation Monitoring
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

export const reportsApi = new ReportsApi();