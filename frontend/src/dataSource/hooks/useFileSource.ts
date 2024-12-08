// src/hooks/sources/useFileSource.ts
import { useState } from 'react';
import { useMutation } from 'react-query';
import { dataSourceApi } from '../api/dataSourceApi';
import type { FileSourceConfig } from '../types/dataSources';
import type { ApiResponse } from '../../common/types/api';

export function useFileSource() {
  const [uploadProgress, setUploadProgress] = useState(0);

  const { mutate: upload, isLoading: isUploading } = useMutation<
    ApiResponse<{ fileId: string }>,
    Error,
    { file: File; config: FileSourceConfig['config'] }
  >(({ file, config }) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('config', JSON.stringify(config));
    
    return dataSourceApi.uploadFile([file], {
      onProgress: (progress) => setUploadProgress(progress)
    });
  });

  return {
    upload,
    uploadProgress,
    isUploading
  } as const;
}