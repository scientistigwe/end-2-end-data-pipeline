```typescript
// src/services/analysisApi.ts
import { api } from './api/client';
import { API_CONFIG } from './api/config';
import { AnalysisConfig, AnalysisType } from '../types/analysis';

export const analysisApi = {
  // Quality Analysis
  startQualityAnalysis: async (config: AnalysisConfig) => {
    return api.post(API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.START, config);
  },

  getQualityStatus: async (analysisId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.STATUS, { id: analysisId });
  },

  getQualityReport: async (analysisId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.ANALYSIS.QUALITY.REPORT, { id: analysisId });
  },

  // Insight Analysis
  startInsightAnalysis: async (config: AnalysisConfig) => {
    return api.post(API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.START, config);
  },

  getInsightStatus: async (analysisId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.STATUS, { id: analysisId });
  },

  getInsightReport: async (analysisId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.ANALYSIS.INSIGHT.REPORT, { id: analysisId });
  },

  // Generic Analysis Operations
  cancelAnalysis: async (analysisId: string, type: AnalysisType) => {
    return api.post(`/analysis/${type}/${analysisId}/cancel`);
  },

  retryAnalysis: async (analysisId: string, type: AnalysisType) => {
    return api.post(`/analysis/${type}/${analysisId}/retry`);
  }
};

// src/services/recommendationApi.ts
import { api } from './api/client';
import { API_CONFIG } from './api/config';
import { RecommendationAction } from '../types/recommendations';

export const recommendationApi = {
  getRecommendations: async (pipelineId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.RECOMMENDATIONS.LIST, { pipelineId });
  },

  applyRecommendation: async (recommendationId: string, action: RecommendationAction) => {
    return api.post(API_CONFIG.ENDPOINTS.RECOMMENDATIONS.APPLY, {
      recommendationId,
      action
    });
  },

  getRecommendationStatus: async (recommendationId: string) => {
    return api.get(API_CONFIG.ENDPOINTS.RECOMMENDATIONS.STATUS, { id: recommendationId });
  }
};

// src/services/monitoringApi.ts
import { api } from './api/client';
import { MonitoringMetrics } from '../types/monitoring';

export const monitoringApi = {
  getPipelineMetrics: async (pipelineId: string): Promise<MonitoringMetrics> => {
    return api.get(`/monitoring/${pipelineId}/metrics`);
  },

  getSystemHealth: async () => {
    return api.get('/monitoring/health');
  },

  getResourceUsage: async (pipelineId: string) => {
    return api.get(`/monitoring/${pipelineId}/resources`);
  }
};
```

Now let's create some utility functions for common operations:

```typescript
// src/utils/apiUtils.ts
import { AxiosError } from 'axios';
import { ApiError } from '../services/api/types';

export const isApiError = (error: any): error is ApiError => {
  return error && 'code' in error && 'message' in error;
};

export const handleApiError = (error: AxiosError | ApiError): ApiError => {
  if (isApiError(error)) {
    return error;
  }

  if (error.response) {
    return {
      code: String(error.response.status),
      message: error.response.data?.message || 'An error occurred',
      details: error.response.data
    };
  }

  return {
    code: 'UNKNOWN_ERROR',
    message: error.message || 'An unknown error occurred'
  };
};

// src/utils/retryUtils.ts
interface RetryConfig {
  maxRetries?: number;
  delayMs?: number;
  backoffFactor?: number;
}

export const retryOperation = async <T>(
  operation: () => Promise<T>,
  config: RetryConfig = {}
): Promise<T> => {
  const {
    maxRetries = 3,
    delayMs = 1000,
    backoffFactor = 2
  } = config;

  let lastError: Error;
  let currentDelay = delayMs;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = error as Error;

      if (attempt < maxRetries - 1) {
        await new Promise(resolve => setTimeout(resolve, currentDelay));
        currentDelay *= backoffFactor;
      }
    }
  }

  throw lastError!;
};

// src/utils/websocketUtils.ts
type MessageHandler = (data: any) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private messageHandlers: Set<MessageHandler> = new Set();

  constructor(private url: string) {}

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      console.log('WebSocket connected');
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.messageHandlers.forEach(handler => handler(data));
    };

    this.ws.onclose = () => {
      this.handleDisconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  private handleDisconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      setTimeout(() => {
        this.reconnectAttempts++;
        this.connect();
      }, this.reconnectDelay * Math.pow(2, this.reconnectAttempts));
    }
  }

  subscribe(handler: MessageHandler) {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  send(data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}
