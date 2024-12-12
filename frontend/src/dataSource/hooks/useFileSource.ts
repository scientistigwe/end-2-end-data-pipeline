// src/dataSource/hooks/useFileSource.ts
import { useState, useCallback } from 'react';
import { useMutation } from 'react-query';
import { DataSourceService } from '../services/dataSourceService';
import { handleApiError } from '../../common/utils/api/apiUtils';
import { DATASOURCE_MESSAGES } from '../constants';
import type { FileSourceConfig } from '../types/dataSources';

export const useFileSource = () => {
  const [uploadProgress, setUploadProgress] = useState(0);

  const { mutateAsync: upload, isLoading: isUploading } = useMutation(
    async ({ file, config }: { file: File; config: FileSourceConfig['config'] }) => {
      try {
        const response = await DataSourceService.uploadFile([file], (progress) => {
          setUploadProgress(progress);
        });
        return response;
      } catch (err) {
        handleApiError(err);
        throw new Error(DATASOURCE_MESSAGES.ERRORS.UPLOAD_FAILED);
      }
    }
  );

  const resetProgress = useCallback(() => {
    setUploadProgress(0);
  }, []);

  return {
    upload,
    isUploading,
    uploadProgress,
    resetProgress
  };
};
