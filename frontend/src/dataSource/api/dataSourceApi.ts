import axios from 'axios';
import { baseAxiosClient, ServiceType } from '@/common/api/client/baseClient';
import { RouteHelper } from '@/common/api/routes';
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

    constructor() {
        this.client.setServiceConfig({
            service: ServiceType.DATA_SOURCES,
            headers: {
                'Accept': 'application/json',
            }
        });
        
        // No automatic auth initialization - rely on the app's auth state
    }

    // File Operations with proper typing
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
            
            // Create form data properly
            const formData = new FormData();
            formData.append('file', file);
            formData.append('metadata', JSON.stringify(metadata));
    
            // Get direct axios instance
            const axiosInstance = this.client.getAxiosInstance();
            
            // Construct URL without trailing slash - your API route doesn't have one
            const baseUrl = axiosInstance.defaults.baseURL || '';
            const uploadUrl = `${baseUrl.replace(/\/$/, '')}/data-sources/file/upload`;
            
            console.log('Uploading to URL:', uploadUrl);
    
            // Use direct axios request for maximum control
            const response = await axiosInstance({
                method: 'POST',
                url: uploadUrl,
                data: formData,
                withCredentials: true,
                headers: {
                    // Don't set Content-Type - let the browser set it with the boundary parameter
                },
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
            });
            
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
            }
            
            throw error;
        }
    }
    
    async getFileMetadata(fileId: string): Promise<ApiResponse<FileMetadataResponse>> {
        try {
            return await this.client.executeGet(
                RouteHelper.getNestedRoute(
                    'DATA_SOURCES',
                    'FILE',
                    'METADATA',
                    { file_id: fileId }
                )
            );
        } catch (error) {
            console.error('Get file metadata error:', error);
            throw error;
        }
    }

    async parseFile(
        fileId: string,
        parseOptions: FileParseOptions
    ): Promise<ApiResponse<FileParseResponse>> {
        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute(
                    'DATA_SOURCES',
                    'FILE',
                    'PARSE',
                    { file_id: fileId }
                ),
                parseOptions
            );
        } catch (error) {
            console.error('File parsing error:', error);
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
            return await this.client.executeGet(
                RouteHelper.getRoute('DATA_SOURCES', 'LIST'),
                { params: filters }
            );
        } catch (error) {
            console.error('List data sources error:', error);
            throw error;
        }
    }

    // Basic CRUD operations
    async createDataSource(
        config: BaseDataSourceConfig
    ): Promise<ApiResponse<BaseMetadata>> {
        try {
            return await this.client.executePost(
                RouteHelper.getRoute('DATA_SOURCES', 'CREATE'),
                config
            );
        } catch (error) {
            console.error('Create data source error:', error);
            throw error;
        }
    }

    async deleteDataSource(sourceId: string): Promise<ApiResponse<void>> {
        try {
            return await this.client.executeDelete(
                RouteHelper.getRoute('DATA_SOURCES', 'DELETE', { source_id: sourceId })
            );
        } catch (error) {
            console.error('Delete data source error:', error);
            throw error;
        }
    }

    // Validation and Preview
    async validateDataSource(sourceId: string): Promise<ApiResponse<ValidationResult>> {
        try {
            return await this.client.executePost(
                RouteHelper.getRoute('DATA_SOURCES', 'VALIDATE', { source_id: sourceId })
            );
        } catch (error) {
            console.error('Validate data source error:', error);
            throw error;
        }
    }

    async previewData(
        sourceId: string,
        options?: { limit?: number; offset?: number }
    ): Promise<ApiResponse<PreviewData>> {
        try {
            return await this.client.executeGet(
                RouteHelper.getRoute('DATA_SOURCES', 'PREVIEW', { source_id: sourceId }),
                { params: options }
            );
        } catch (error) {
            console.error('Preview data error:', error);
            throw error;
        }
    }

    // Database Operations
    async connectDatabase(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'CONNECT'),
                config
            );
        } catch (error) {
            console.error('Connect database error:', error);
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
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'QUERY', { connection_id: connectionId }),
                { query, params }
            );
        } catch (error) {
            console.error('Execute database query error:', error);
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
            return await this.client.executeGet(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'SCHEMA', { connection_id: connectionId })
            );
        } catch (error) {
            console.error('Get database schema error:', error);
            throw error;
        }
    }

    // API Operations
    async connectApi(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'CONNECT'),
                config
            );
        } catch (error) {
            console.error('Connect API error:', error);
            throw error;
        }
    }

    async testApiEndpoint(url: string): Promise<ApiResponse<{
        status: number;
        responseTime: number;
        isValid: boolean;
    }>> {
        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'TEST'),
                { url }
            );
        } catch (error) {
            console.error('Test API endpoint error:', error);
            throw error;
        }
    }

    // S3 Operations
    async connectS3(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'CONNECT'),
                config
            );
        } catch (error) {
            console.error('Connect S3 error:', error);
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
            return await this.client.executeGet(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'LIST', { connection_id: connectionId }),
                { params: { prefix } }
            );
        } catch (error) {
            console.error('List S3 objects error:', error);
            throw error;
        }
    }

    // Stream Operations
    async connectStream(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'CONNECT'),
                config
            );
        } catch (error) {
            console.error('Connect stream error:', error);
            throw error;
        }
    }

    async getStreamMetrics(connectionId: string): Promise<ApiResponse<{
        messagesPerSecond: number;
        bytesPerSecond: number;
        totalMessages: number;
    }>> {
        try {
            return await this.client.executeGet(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'METRICS', { connection_id: connectionId })
            );
        } catch (error) {
            console.error('Get stream metrics error:', error);
            throw error;
        }
    }

    async disconnectSource(
        connectionId: string
    ): Promise<ApiResponse<void>> {
        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'CONNECTION', 'DISCONNECT', { connection_id: connectionId })
            );
        } catch (error) {
            console.error('Disconnect source error:', error);
            throw error;
        }
    }
}

export const dataSourceApi = new DataSourceApi();