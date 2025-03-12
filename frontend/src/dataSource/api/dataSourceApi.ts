// src/dataSource/api/dataSourceApi.ts

import axios, { AxiosResponse } from 'axios';
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
    private isInitialized = false;
    private isAuthenticating = false;
    private authPromise: Promise<void> | null = null;

    constructor() {
        this.client.setServiceConfig({
            service: ServiceType.DATA_SOURCES,
            headers: {
                'Accept': 'application/json',
            }
        });

        // Initialize authentication immediately
        this.initializeAuth();
    }

    private async initializeAuth(): Promise<void> {
        if (this.isAuthenticating) {
            return this.authPromise;
        }

        this.isAuthenticating = true;
        this.authPromise = (async () => {
            try {
                // Try to refresh the token directly
                await this.refreshAuthentication();
                console.log('Authentication refreshed during initialization');
                this.isInitialized = true;
            } catch (error) {
                console.error('Authentication initialization failed:', error);
                // Trigger logout event
                window.dispatchEvent(new Event('auth:logout'));
            } finally {
                this.isAuthenticating = false;
            }
        })();

        return this.authPromise;
    }

    private async refreshAuthentication(): Promise<void> {
        try {
            // Call the auth refresh endpoint
            // Since we're using HTTP-only cookies, we don't need to handle the token manually
            await this.client.executePost('/auth/refresh', undefined, undefined, {
                withCredentials: true
            });

            console.log('Authentication refreshed successfully');
        } catch (error) {
            console.error('Authentication refresh failed:', error);
            throw error;
        }
    }

    // Ensure any method that requires authentication waits for initialization
    private async ensureAuthenticated(): Promise<void> {
        if (!this.isInitialized) {
            await this.initializeAuth();
        }
    }

    // File Operations with proper typing
    async uploadFile(
        file: File,
        metadata: Record<string, any>,
        onProgress?: (progress: number) => void
    ): Promise<ApiResponse<FileUploadResponse>> {
        try {
            // First ensure we have a fresh authentication token
            await this.refreshAuthentication();
            
            // Log detailed information for debugging
            console.log('Uploading file:', {
                name: file.name,
                type: file.type,
                size: file.size,
            });
            console.log('Metadata:', metadata);
    
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
                    // The browser will automatically set 'Content-Type': 'multipart/form-data; boundary=...'
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
            
            console.log('Upload response:', response.status);
            
            return {
                success: true,
                data: response.data?.data || response.data
            };
        } catch (error) {
            console.error('File upload error:', error);
            
            // Detailed error logging
            if (axios.isAxiosError(error)) {
                console.error('Error details:', {
                    status: error.response?.status,
                    statusText: error.response?.statusText,
                    data: error.response?.data,
                    headers: error.response?.headers
                });
                
                // Try one more time with token refresh if we got 401/403
                if (error.response?.status === 401 || error.response?.status === 403) {
                    try {
                        console.log('Attempting to refresh token and retry upload...');
                        await this.refreshAuthentication();
                        
                        const formData = new FormData();
                        formData.append('file', file);
                        formData.append('metadata', JSON.stringify(metadata));
                        
                        const axiosInstance = this.client.getAxiosInstance();
                        const baseUrl = axiosInstance.defaults.baseURL || '';
                        const uploadUrl = `${baseUrl.replace(/\/$/, '')}/data-sources/file/upload`;
                        
                        // Second attempt after refresh
                        const response = await axiosInstance({
                            method: 'POST',
                            url: uploadUrl,
                            data: formData,
                            withCredentials: true,
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
                    } catch (retryError) {
                        console.error('Retry failed:', retryError);
                        throw new Error('File upload failed after authentication refresh');
                    }
                }
            }
            
            throw this.handleError(error);
        }
    }
    
    async getFileMetadata(fileId: string): Promise<ApiResponse<FileMetadataResponse>> {
        await this.ensureAuthenticated();

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
            throw this.handleError(error);
        }
    }

    async parseFile(
        fileId: string,
        parseOptions: FileParseOptions
    ): Promise<ApiResponse<FileParseResponse>> {
        await this.ensureAuthenticated();

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
            throw this.handleError(error);
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
        await this.ensureAuthenticated();

        try {
            return await this.client.executeGet(
                RouteHelper.getRoute('DATA_SOURCES', 'LIST'),
                { params: filters }
            );
        } catch (error) {
            // If we get a 401/403, try to refresh auth once and retry
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();

                    // Retry the request after refreshing
                    return await this.client.executeGet(
                        RouteHelper.getRoute('DATA_SOURCES', 'LIST'),
                        { params: filters }
                    );
                } catch (refreshError) {
                    console.error('Authentication refresh failed during list retry:', refreshError);
                    throw this.handleError(error);
                }
            }

            throw this.handleError(error);
        }
    }

    // Basic CRUD operations
    async createDataSource(
        config: BaseDataSourceConfig
    ): Promise<ApiResponse<BaseMetadata>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executePost(
                RouteHelper.getRoute('DATA_SOURCES', 'CREATE'),
                config
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executePost(
                        RouteHelper.getRoute('DATA_SOURCES', 'CREATE'),
                        config
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    async deleteDataSource(sourceId: string): Promise<ApiResponse<void>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executeDelete(
                RouteHelper.getRoute('DATA_SOURCES', 'DELETE', { source_id: sourceId })
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executeDelete(
                        RouteHelper.getRoute('DATA_SOURCES', 'DELETE', { source_id: sourceId })
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    // Validation and Preview
    async validateDataSource(sourceId: string): Promise<ApiResponse<ValidationResult>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executePost(
                RouteHelper.getRoute('DATA_SOURCES', 'VALIDATE', { source_id: sourceId })
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executePost(
                        RouteHelper.getRoute('DATA_SOURCES', 'VALIDATE', { source_id: sourceId })
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    async previewData(
        sourceId: string,
        options?: { limit?: number; offset?: number }
    ): Promise<ApiResponse<PreviewData>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executeGet(
                RouteHelper.getRoute('DATA_SOURCES', 'PREVIEW', { source_id: sourceId }),
                { params: options }
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executeGet(
                        RouteHelper.getRoute('DATA_SOURCES', 'PREVIEW', { source_id: sourceId }),
                        { params: options }
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    // Error handling
    private handleError(error: any): Error {
        if (axios.isAxiosError(error)) {
            const message = error.response?.data?.message || error.message;
            return new Error(`API Error: ${message}`);
        }
        return error instanceof Error ? error : new Error('Unknown error occurred');
    }

    // Database Operations
    async connectDatabase(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'CONNECT'),
                config
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executePost(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'CONNECT'),
                        config
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
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
        await this.ensureAuthenticated();

        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'QUERY', { connection_id: connectionId }),
                { query, params }
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executePost(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'QUERY', { connection_id: connectionId }),
                        { query, params }
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
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
        await this.ensureAuthenticated();

        try {
            return await this.client.executeGet(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'SCHEMA', { connection_id: connectionId })
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executeGet(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'DATABASE', 'SCHEMA', { connection_id: connectionId })
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    // API Operations
    async connectApi(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'CONNECT'),
                config
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executePost(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'CONNECT'),
                        config
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    async testApiEndpoint(url: string): Promise<ApiResponse<{
        status: number;
        responseTime: number;
        isValid: boolean;
    }>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'TEST'),
                { url }
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executePost(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'API', 'TEST'),
                        { url }
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    // S3 Operations
    async connectS3(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'CONNECT'),
                config
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executePost(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'CONNECT'),
                        config
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
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
        await this.ensureAuthenticated();

        try {
            return await this.client.executeGet(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'LIST', { connection_id: connectionId }),
                { params: { prefix } }
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executeGet(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'S3', 'LIST', { connection_id: connectionId }),
                        { params: { prefix } }
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    // Stream Operations
    async connectStream(
        config: BaseDataSourceConfig['config']
    ): Promise<ApiResponse<SourceConnectionResponse>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'CONNECT'),
                config
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executePost(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'CONNECT'),
                        config
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    async getStreamMetrics(connectionId: string): Promise<ApiResponse<{
        messagesPerSecond: number;
        bytesPerSecond: number;
        totalMessages: number;
    }>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executeGet(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'METRICS', { connection_id: connectionId })
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executeGet(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'STREAM', 'METRICS', { connection_id: connectionId })
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }

    async disconnectSource(
        connectionId: string
    ): Promise<ApiResponse<void>> {
        await this.ensureAuthenticated();

        try {
            return await this.client.executePost(
                RouteHelper.getNestedRoute('DATA_SOURCES', 'CONNECTION', 'DISCONNECT', { connection_id: connectionId })
            );
        } catch (error) {
            if (axios.isAxiosError(error) &&
                (error.response?.status === 401 || error.response?.status === 403)) {
                try {
                    await this.refreshAuthentication();
                    return await this.client.executePost(
                        RouteHelper.getNestedRoute('DATA_SOURCES', 'CONNECTION', 'DISCONNECT', { connection_id: connectionId })
                    );
                } catch (refreshError) {
                    throw this.handleError(error);
                }
            }
            throw this.handleError(error);
        }
    }
}

export const dataSourceApi = new DataSourceApi();

// Type definitions (should be in a separate types file)
export interface FileUploadProgressEvent extends ProgressEvent {
    total: number;
    loaded: number;
}