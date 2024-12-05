// src/hooks/sources/useFileSource.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../../services/api/dataSourceAPI';
import { handleApiError } from '../../utils/helpers/apiUtils';
import type { FileSourceConfig } from '../../hooks/dataSource/types';  // Use the same import as dataSourceApi
import type { SourceMetadata } from '../../types/source';
import type { ApiResponse } from '../../types/api';

export function useFileSource() {
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [fileId, setFileId] = useState<string | null>(null);

  // Upload file mutation
  const { mutate: uploadFile, isLoading: isUploading } = useMutation<
    ApiResponse<FileSourceConfig>,
    Error,
    File[]
  >(
    (files) => dataSourceApi.uploadFile(files, {
      onProgress: (progress) => setUploadProgress(progress)
    }),
    {
      onError: handleApiError,
      onSuccess: (response) => {
        if (response.data?.id) {
          setFileId(response.data.id);
        }
      }
    }
  );

  // Get file metadata
  const { data: metadata, refetch: refreshMetadata } = useQuery<
    ApiResponse<SourceMetadata>,
    Error
  >(
    ['fileMetadata', fileId],
    () => dataSourceApi.getFileMetadata(fileId!),
    {
      enabled: !!fileId
    }
  );

  return {
    uploadFile,
    refreshMetadata,
    uploadProgress,
    fileId,
    metadata: metadata?.data,
    isUploading
  } as const;
}