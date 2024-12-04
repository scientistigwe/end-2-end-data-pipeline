// src/hooks/sources/useFileSource.ts
import { useState, useCallback } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../../services/dataSourceApi';
import { handleApiError } from '../../utils/apiUtils';

interface FileUploadConfig {
  files: File[];
  chunk_size?: number;
  validate_only?: boolean;
}

interface FileMetadata {
  filename: string;
  size: number;
  mime_type: string;
  columns?: string[];
  row_count?: number;
}

export const useFileSource = () => {
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [fileId, setFileId] = useState<string | null>(null);

  // Upload file mutation
  const { mutate: uploadFile, isLoading: isUploading } = useMutation(
    async (config: FileUploadConfig) => {
      const formData = new FormData();
      config.files.forEach(file => formData.append('files', file));
      
      if (config.validate_only) {
        formData.append('validate_only', 'true');
      }

      const response = await dataSourceApi.uploadFile(formData, {
        onUploadProgress: (progressEvent) => {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          setUploadProgress(progress);
        }
      });

      if (response.data?.fileId) {
        setFileId(response.data.fileId);
      }

      return response;
    },
    {
      onError: (error) => handleApiError(error)
    }
  );

  // Get file metadata
  const { data: metadata, refetch: refreshMetadata } = useQuery(
    ['fileMetadata', fileId],
    () => dataSourceApi.getMetadata(fileId!),
    {
      enabled: !!fileId
    }
  );

  // Validate file
  const { mutate: validateFile } = useMutation(
    (files: File[]) => uploadFile({ files, validate_only: true })
  );

  // Cancel upload
  const cancelUpload = useCallback(async () => {
    if (fileId) {
      await dataSourceApi.cancelUpload(fileId);
      setFileId(null);
      setUploadProgress(0);
    }
  }, [fileId]);

  return {
    uploadFile,
    validateFile,
    cancelUpload,
    refreshMetadata,
    uploadProgress,
    fileId,
    metadata,
    isUploading
  };
};
