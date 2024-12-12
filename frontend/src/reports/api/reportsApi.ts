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
  
  export class ReportsApi extends ApiClient {
    // Report CRUD Operations
    async listReports(params?: {
      page?: number;
      limit?: number;
      type?: string[];
      status?: string[];
    }): Promise<Report[]> {
      return this.request('GET', API_CONFIG.ENDPOINTS.LIST, { params });
    }
  
    async createReport(
      config: ReportConfig,
      options?: ReportGenerationOptions
    ): Promise<Report> {
      return this.request('POST', API_CONFIG.ENDPOINTS.CREATE, {
        data: { config, options }
      });
    }
  
    async getReport(id: string): Promise<Report> {
      const url = API_CONFIG.ENDPOINTS.GET.replace(':id', id);
      return this.request('GET', url);
    }
  
    async deleteReport(id: string): Promise<void> {
      const url = API_CONFIG.ENDPOINTS.DELETE.replace(':id', id);
      return this.request('DELETE', url);
    }
  
    // Report Generation and Status
    async getReportStatus(id: string): Promise<{
      status: Report['status'];
      progress?: number;
      error?: string;
    }> {
      const url = API_CONFIG.ENDPOINTS.STATUS.replace(':id', id);
      return this.request('GET', url);
    }
  
    async exportReport(
      id: string,
      options: ExportOptions
    ): Promise<{ downloadUrl: string }> {
      const url = API_CONFIG.ENDPOINTS.EXPORT.replace(':id', id);
      return this.request('POST', url, { data: options });
    }
  
    // Report Scheduling
    async scheduleReport(config: ScheduleConfig): Promise<Report> {
      return this.request('POST', API_CONFIG.ENDPOINTS.SCHEDULE, {
        data: config
      });
    }
  
    async updateSchedule(
      id: string,
      updates: Partial<ScheduleConfig>
    ): Promise<Report> {
      const url = `${API_CONFIG.ENDPOINTS.SCHEDULE}/${id}`;
      return this.request('PUT', url, { data: updates });
    }
  
    // Report Metadata and Preview
    async getReportMetadata(id: string): Promise<ReportMetadata> {
      const url = API_CONFIG.ENDPOINTS.METADATA.replace(':id', id);
      return this.request('GET', url);
    }
  
    async previewReport(
      id: string,
      section?: string
    ): Promise<{ content: string }> {
      const url = API_CONFIG.ENDPOINTS.PREVIEW.replace(':id', id);
      return this.request('GET', url, {
        params: { section }
      });
    }
  
    // Report Templates
    async getTemplates(): Promise<{
      id: string;
      name: string;
      type: string;
    }[]> {
      return this.request('GET', API_CONFIG.ENDPOINTS.TEMPLATES);
    }
  
    // Report Download Helpers
    async downloadReport(url: string): Promise<Blob> {
      const response = await this.client.get(url, {
        responseType: 'blob'
      });
      return response.data;
    }
  }
  
