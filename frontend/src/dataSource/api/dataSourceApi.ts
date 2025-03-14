import axios, { AxiosInstance } from 'axios';
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import { RouteHelper } from '@/common/api/routes';
import { API_CONFIG } from '@/common/api/client/config';
import type { ApiRequestConfig, ApiResponse } from '@/common/types/api';
import type { 
    BaseDataSourceConfig,
    BaseMetadata,
    ValidationResult,
    PreviewData,
    DataSourceFilters,
    SourceConnectionResponse,
    FileUploadResponse,
    FileMetadataResponse,
    FileParseOptions,
    FileParseResponse
} from '../types/base';

class DataSourceApi {
    private client = baseAxiosClient;
    // Create a dedicated axios instance that won't be affected by other services' interceptors
    private dsAxios: AxiosInstance;

    constructor() {
        // Configure shared client for standard operations
        this.client.setServiceConfig({
            service: ServiceType.DATA_SOURCES,
            headers: {
                'Accept': 'application/json',
            }
        });
        
        // Create a dedicated instance for data source operations
        const baseInstance = this.client.getAxiosInstance();
        this.dsAxios = axios.create({
            baseURL: baseInstance.defaults.baseURL,
            timeout: baseInstance.defaults.timeout,
            withCredentials: true,
            headers: {
                'Accept': 'application/json',
            }
        });
    }

    // File Operations with isolated axios instance
    async uploadFile(
        file: File,
        metadata: Record<string, any>,
        onProgress?: (progress: number) => void
    ): Promise<ApiResponse<FileUploadResponse>> {
        try {
            // Log detailed information for debugging
            console.log('Uploading file:', {
                name: file.name,
                type: file.type,
                size: file.size,
            });
            
            // Simplify metadata to match backend expectations exactly
            const simplifiedMetadata = {
                file_type: metadata.file_type || metadata.type,
                encoding: metadata.encoding || 'utf-8',
                skip_rows: metadata.skip_rows || metadata.skipRows || 0,
                tags: metadata.tags || ['data'],
                parse_options: {
                    date_format: metadata.parse_options?.date_format || 
                               metadata.parseOptions?.dateFormat || 
                               'YYYY-MM-DD',
                    null_values: metadata.parse_options?.null_values || 
                               metadata.parseOptions?.nullValues || 
                               ['', 'null', 'NA', 'N/A']
                }
            };
            
            // Add file-type specific fields
            if (simplifiedMetadata.file_type === 'csv') {
                simplifiedMetadata['delimiter'] = metadata.delimiter || ',';
                simplifiedMetadata['has_header'] = metadata.has_header ?? metadata.hasHeader ?? true;
            }
            
            if (simplifiedMetadata.file_type === 'excel') {
                simplifiedMetadata['sheet_name'] = metadata.sheet_name || metadata.sheet || 'Sheet1';
                simplifiedMetadata['has_header'] = metadata.has_header ?? metadata.hasHeader ?? true;
            }
            
            console.log('Simplified metadata:', simplifiedMetadata);
            
            // Create form data properly
            const formData = new FormData();
            formData.append('file', file);
            formData.append('metadata', JSON.stringify(simplifiedMetadata));
    
            // Construct URL without trailing slash
            const baseUrl = this.dsAxios.defaults.baseURL || '';
            const uploadUrl = `${baseUrl.replace(/\/$/, '')}/data-sources/file/upload`;
            
            console.log('Uploading to URL:', uploadUrl);
    
            // Use our isolated axios instance for the request
            const response = await this.dsAxios.post(
                uploadUrl,
                formData,
                {
                    withCredentials: true,
                    // Don't set Content-Type - let the browser set it
                    maxContentLength: Infinity,
                    maxBodyLength: Infinity,
                    onUploadProgress: (progressEvent) => {
                        if (onProgress && progressEvent.total) {
                            const progress = Math.round(
                                (progressEvent.loaded * 100) / progressEvent.total
                            );
                            onProgress(progress);
                        }
                    }
                }
            );
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('File upload error:', error);
            
            if (axios.isAxiosError(error)) {
                console.error('Error details:', {
                    status: error.response?.status,
                    statusText: error.response?.statusText,
                    data: error.response?.data
                });
                
                // Return a standardized error response
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message || 'File upload failed',
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            // Re-throw non-axios errors
            throw error;
        }
    }
    
    async getFileMetadata(fileId: string): Promise<ApiResponse<FileMetadataResponse>> {
        try {
            const url = RouteHelper.getNestedRoute(
                'DATA_SOURCES',
                'FILE',
                'METADATA',
                { file_id: fileId }
            );
            
            // Use isolated instance
            const response = await this.dsAxios.get(url, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Get file metadata error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    async parseFile(
        fileId: string,
        parseOptions: FileParseOptions
    ): Promise<ApiResponse<FileParseResponse>> {
        try {
            const url = RouteHelper.getNestedRoute(
                'DATA_SOURCES',
                'FILE',
                'PARSE',
                { file_id: fileId }
            );
            
            // Use isolated instance
            const response = await this.dsAxios.post(url, parseOptions, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('File parsing error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    // List all data sources with filters
    async listDataSources(filters?: DataSourceFilters): Promise<ApiResponse<{
        sources: {
            files: BaseMetadata[];
            databases: BaseMetadata[];
            api: BaseMetadata[];
            s3: BaseMetadata[];
            stream: BaseMetadata[];
        }
    }>> {
        try {
            const url = RouteHelper.getRoute('DATA_SOURCES', 'LIST');
            
            // Use isolated instance
            const response = await this.dsAxios.get(url, {
                params: filters,
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('List data sources error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    // Basic CRUD operations
    async createDataSource(
        config: BaseDataSourceConfig
    ): Promise<ApiResponse<BaseMetadata>> {
        try {
            const url = RouteHelper.getRoute('DATA_SOURCES', 'CREATE');
            
            // Use isolated instance
            const response = await this.dsAxios.post(url, config, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Create data source error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    async deleteDataSource(sourceId: string): Promise<ApiResponse<void>> {
        try {
            const url = RouteHelper.getRoute('DATA_SOURCES', 'DELETE', { source_id: sourceId });
            
            // Use isolated instance
            const response = await this.dsAxios.delete(url, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Delete data source error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    // Validation and Preview
    async validateDataSource(sourceId: string): Promise<ApiResponse<ValidationResult>> {
        try {
            const url = RouteHelper.getRoute('DATA_SOURCES', 'VALIDATE', { source_id: sourceId });
            
            // Use isolated instance
            const response = await this.dsAxios.post(url, {}, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Validate data source error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    async previewData(
        sourceId: string,
        options?: { limit?: number; offset?: number }
    ): Promise<ApiResponse<PreviewData>> {
        try {
            const url = RouteHelper.getRoute('DATA_SOURCES', 'PREVIEW', { source_id: sourceId });
            
            // Use isolated instance
            const response = await this.dsAxios.get(url, {
                params: options,
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Preview data error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    // Database Operations
    async connectDatabase(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        try {
            const url = RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'CONNECT');
            
            // Use isolated instance
            const response = await this.dsAxios.post(url, config, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Connect database error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    async executeDatabaseQuery(
        connectionId: string,
        query: string,
        params?: unknown[]
    ): Promise<ApiResponse<{
        rows: unknown[];
        rowCount: number;
        fields: Array<{ name: string; type: string }>;
    }>> {
        try {
            const url = RouteHelper.getNestedRoute(
                'DATA_SOURCES', 
                'DATABASE', 
                'QUERY', 
                { connection_id: connectionId }
            );
            
            // Use isolated instance
            const response = await this.dsAxios.post(url, { query, params }, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Execute database query error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    async getDatabaseSchema(connectionId: string): Promise<ApiResponse<{
        tables: Array<{
            name: string;
            columns: Array<{
                name: string;
                type: string;
                nullable: boolean;
            }>;
        }>;
    }>> {
        try {
            const url = RouteHelper.getNestedRoute(
                'DATA_SOURCES', 
                'DATABASE', 
                'SCHEMA', 
                { connection_id: connectionId }
            );
            
            // Use isolated instance
            const response = await this.dsAxios.get(url, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Get database schema error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    // API Operations
    async connectApi(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        try {
            const url = RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'CONNECT');
            
            // Use isolated instance
            const response = await this.dsAxios.post(url, config, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Connect API error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    async testApiEndpoint(url: string): Promise<ApiResponse<{
        status: number;
        responseTime: number;
        isValid: boolean;
    }>> {
        try {
            const apiUrl = RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'TEST');
            
            // Use isolated instance
            const response = await this.dsAxios.post(apiUrl, { url }, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Test API endpoint error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    // S3 Operations
    async connectS3(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        try {
            const url = RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'CONNECT');
            
            // Use isolated instance
            const response = await this.dsAxios.post(url, config, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Connect S3 error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    async listS3Objects(
        connectionId: string,
        prefix?: string
    ): Promise<ApiResponse<{
        objects: Array<{
            key: string;
            size: number;
            lastModified: string;
        }>;
    }>> {
        try {
            const url = RouteHelper.getNestedRoute(
                'DATA_SOURCES', 
                'S3', 
                'LIST', 
                { connection_id: connectionId }
            );
            
            // Use isolated instance
            const response = await this.dsAxios.get(url, {
                params: { prefix },
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('List S3 objects error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    // Stream Operations
    async connectStream(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        try {
            const url = RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'CONNECT');
            
            // Use isolated instance
            const response = await this.dsAxios.post(url, config, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Connect stream error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    async getStreamMetrics(connectionId: string): Promise<ApiResponse<{
        messagesPerSecond: number;
        bytesPerSecond: number;
        totalMessages: number;
    }>> {
        try {
            const url = RouteHelper.getNestedRoute(
                'DATA_SOURCES', 
                'STREAM', 
                'METRICS', 
                { connection_id: connectionId }
            );
            
            // Use isolated instance
            const response = await this.dsAxios.get(url, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Get stream metrics error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }

    async disconnectSource(
        connectionId: string
    ): Promise<ApiResponse<void>> {
        try {
            const url = RouteHelper.getNestedRoute(
                'DATA_SOURCES', 
                'CONNECTION', 
                'DISCONNECT', 
                { connection_id: connectionId }
            );
            
            // Use isolated instance
            const response = await this.dsAxios.post(url, {}, {
                withCredentials: true
            });
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('Disconnect source error:', error);
            
            if (axios.isAxiosError(error)) {
                return {
                    success: false,
                    data: null,
                    error: {
                        message: error.response?.data?.message || error.message,
                        code: `HTTP_${error.response?.status || 'ERROR'}`,
                        details: error.response?.data
                    }
                };
            }
            
            throw error;
        }
    }
}

export const dataSourceApi = new DataSourceApi();