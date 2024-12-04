```typescript
// src/hooks/useDataSource.ts
import { useState, useCallback, useEffect } from 'react';
import { useQuery, useMutation } from 'react-query';
import { dataSourceApi } from '../services/dataSourceApi';
import { handleApiError } from '../utils/apiUtils';
import {
  SourceType,
  SourceConfig,
  ConnectionStatus
} from '../types/dataSources';

interface UseDataSourceProps {
  sourceType: SourceType;
  onError?: (error: any) => void;
  onSuccess?: (data: any) => void;
}

export const useDataSource = ({ sourceType, onError, onSuccess }: UseDataSourceProps) => {
  const [connectionId, setConnectionId] = useState<string | null>(null);
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');

  // Connection mutation
  const { mutate: connect, isLoading: isConnecting } = useMutation(
    async (config: SourceConfig) => {
      switch (sourceType) {
        case 'file':
          return dataSourceApi.uploadFile(config.files);
        case 'api':
          return dataSourceApi.connectApi(config);
        case 'database':
          return dataSourceApi.connectDatabase(config);
        case 's3':
          return dataSourceApi.connectS3(config);
        case 'stream':
          return dataSourceApi.connectStream(config);
        default:
          throw new Error(`Unsupported source type: ${sourceType}`);
      }
    },
    {
      onSuccess: (response) => {
        setConnectionId(response.data.connectionId);
        setStatus('connected');
        onSuccess?.(response.data);
      },
      onError: (error) => {
        setStatus('error');
        onError?.(handleApiError(error));
      }
    }
  );

  // Status polling
  const { data: connectionStatus } = useQuery(
    ['sourceStatus', connectionId],
    () => dataSourceApi.getStatus(connectionId!),
    {
      enabled: !!connectionId && status === 'connected',
      refetchInterval: 5000,
      onError: (error) => {
        setStatus('error');
        onError?.(handleApiError(error));
      }
    }
  );

  // Disconnect mutation
  const { mutate: disconnect } = useMutation(
    async () => {
      if (connectionId) {
        return dataSourceApi.disconnect(connectionId);
      }
    },
    {
      onSuccess: () => {
        setConnectionId(null);
        setStatus('disconnected');
      },
      onError: (error) => onError?.(handleApiError(error))
    }
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (connectionId) {
        disconnect();
      }
    };
  }, [connectionId]);

  return {
    connect,
    disconnect,
    connectionId,
    status,
    connectionStatus,
    isConnecting
  };
};


// src/hooks/useAnalysis.ts
import { useState } from 'react';
import { useQuery, useMutation } from 'react-query';
import { analysisApi } from '../services/analysisApi';
import { handleApiError } from '../utils/apiUtils';
import { AnalysisConfig, AnalysisType } from '../types/analysis';

interface UseAnalysisProps {
  analysisId?: string;
  type: AnalysisType;
  onError?: (error: any) => void;
  onSuccess?: (data: any) => void;
}

export const useAnalysis = ({ analysisId, type, onError, onSuccess }: UseAnalysisProps) => {
  const [status, setStatus] = useState<string>('idle');

  // Start analysis mutation
  const { mutate: startAnalysis, isLoading: isStarting } = useMutation(
    (config: AnalysisConfig) => {
      return type === 'quality'
        ? analysisApi.startQualityAnalysis(config)
        : analysisApi.startInsightAnalysis(config);
    },
    {
      onSuccess: (response) => {
        setStatus('running');
        onSuccess?.(response.data);
      },
      onError: (error) => onError?.(handleApiError(error))
    }
  );

  // Status polling
  const { data: analysisStatus } = useQuery(
    ['analysisStatus', analysisId, type],
    () => {
      return type === 'quality'
        ? analysisApi.getQualityStatus(analysisId!)
        : analysisApi.getInsightStatus(analysisId!);
    },
    {
      enabled: !!analysisId && status === 'running',
      refetchInterval: 3000
    }
  );

  // Get report query
  const { data: report, refetch: refreshReport } = useQuery(
    ['analysisReport', analysisId, type],
    () => {
      return type === 'quality'
        ? analysisApi.getQualityReport(analysisId!)
        : analysisApi.getInsightReport(analysisId!);
    },
    {
      enabled: !!analysisId && status === 'completed'
    }
  );

  // Cancel analysis mutation
  const { mutate: cancelAnalysis } = useMutation(
    () => analysisApi.cancelAnalysis(analysisId!, type),
    {
      onSuccess: () => {
        setStatus('cancelled');
        onSuccess?.({ status: 'cancelled' });
      },
      onError: (error) => onError?.(handleApiError(error))
    }
  );

  return {
    startAnalysis,
    cancelAnalysis,
    refreshReport,
    status,
    analysisStatus,
    report,
    isStarting
  };
};