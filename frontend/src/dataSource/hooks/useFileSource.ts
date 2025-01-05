// src/dataSource/hooks/useFileSource.ts - REFACTORED
import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '@/common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { FileUploadMetadata, PreviewData } from '../types/base';

export const useFileSource = () => {
    const queryClient = useQueryClient();
    const [uploadProgress, setUploadProgress] = useState(0);
    const [fileId, setFileId] = useState<string | null>(null);
    const [previewData, setPreviewData] = useState<PreviewData | null>(null);

    const { mutateAsync: upload, isLoading: isUploading } = useMutation(
        async ({ 
            file, 
            metadata 
        }: { 
            file: File; 
            metadata: FileUploadMetadata 
        }) => {
            try {
                const response = await DataSourceService.uploadFile(
                    file,
                    metadata,
                    (progress) => setUploadProgress(progress)
                );
                setFileId(response.fileId);
                return response;
            } catch (err) {
                handleApiError(err);
                throw new Error(DATASOURCE_MESSAGES.ERRORS.UPLOAD_FAILED);
            }
        },
        {
            onSuccess: () => {
                queryClient.invalidateQueries('dataSources');
            }
        }
    );

    const { mutateAsync: parseFile, isLoading: isParsing } = useMutation(
        async (options: Record<string, any>) => {
            if (!fileId) throw new Error('No file uploaded');
            try {
                const data = await DataSourceService.parseFile(fileId, options);
                setPreviewData(data);
                return data;
            } catch (err) {
                handleApiError(err);
                throw new Error(DATASOURCE_MESSAGES.ERRORS.PARSE_FAILED);
            }
        }
    );

    const { mutateAsync: validate, isLoading: isValidating } = useMutation(
        async () => {
            if (!fileId) throw new Error('No file uploaded');
            return DataSourceService.validateDataSource(fileId);
        }
    );

    const resetProgress = useCallback(() => {
        setUploadProgress(0);
        setFileId(null);
        setPreviewData(null);
    }, []);

    return {
        upload,
        parseFile,
        validate,
        fileId,
        previewData,
        isUploading,
        isParsing,
        isValidating,
        uploadProgress,
        resetProgress
    };
};