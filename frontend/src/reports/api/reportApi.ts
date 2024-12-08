// src/services/api/reportsApi.ts
import { BaseApiClient } from '../../common/api/client';
import { API_CONFIG } from '../../common/api/config';
import type { ApiResponse } from '../../common/types/api';
import type {
  Report,
  ReportConfig,
  ScheduleConfig,
  ExportOptions,
  ReportGenerationOptions
} from '../types/report';

class ReportsApi extends BaseApiClient {
  async listReports(): Promise<ApiResponse<Report[]>> {
    return this.request('get', API_CONFIG.ENDPOINTS.REPORTS.LIST);
  }

  async createReport(
    config: ReportConfig,
    options?: ReportGenerationOptions
  ): Promise<ApiResponse<Report>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.REPORTS.CREATE,
      {},
      { config, options }
    );
  }

  async getReport(id: string): Promise<ApiResponse<Report>> {
    return this.request('get', API_CONFIG.ENDPOINTS.REPORTS.GET, {
      routeParams: { id }
    });
  }

  async getReportStatus(id: string): Promise<ApiResponse<Report>> {
    return this.request('get', API_CONFIG.ENDPOINTS.REPORTS.STATUS, {
      routeParams: { id }
    });
  }

  async deleteReport(id: string): Promise<ApiResponse<void>> {
    return this.request('delete', API_CONFIG.ENDPOINTS.REPORTS.DELETE, {
      routeParams: { id }
    });
  }

  async exportReport(
    id: string,
    options: ExportOptions
  ): Promise<ApiResponse<{ downloadUrl: string }>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.REPORTS.EXPORT,
      {
        routeParams: { id }
      },
      options
    );
  }

  async scheduleReport(config: ScheduleConfig): Promise<ApiResponse<Report>> {
    return this.request(
      'post',
      API_CONFIG.ENDPOINTS.REPORTS.SCHEDULE,
      {},
      config
    );
  }
}

export const reportsApi = new ReportsApi();