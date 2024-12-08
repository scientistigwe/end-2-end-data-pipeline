// src/auth/types/api.ts
import type { AxiosRequestConfig } from 'axios';

export interface ApiRequestConfig extends Omit<AxiosRequestConfig, 'onUploadProgress'> {
    routeParams?: Record<string, string>;
    onUploadProgress?: (progress: number) => void;
}

export interface ApiResponse<T = unknown> {
    data: T;
    message?: string;
    status: number;
}

