// common/utils/retry/retryUtils.ts
import type { AxiosError } from 'axios';

interface RetryConfig {
  maxRetries: number;
  initialDelay: number;
  maxDelay: number;
  backoffFactor: number;
  shouldRetry: (error: unknown) => boolean;
  onRetry?: (error: unknown, attempt: number) => void;
  timeout: number;
}

interface RetryState {
  attempt: number;
  error: unknown;
  startTime: number;
}

const defaultConfig: RetryConfig = {
  maxRetries: 3,
  initialDelay: 1000,
  maxDelay: 30000,
  backoffFactor: 2,
  timeout: 60000,
  shouldRetry: (error: unknown) => {
    if (isAxiosError(error)) {
      return error.response?.status ? error.response.status >= 500 || error.response.status === 429 : true;
    }
    return true;
  }
};

// Helper functions
const isAxiosError = (error: unknown): error is AxiosError => {
  return !!(error && typeof error === 'object' && 'isAxiosError' in error && error.isAxiosError);
};

const delay = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

const calculateDelay = (
  attempt: number,
  config: RetryConfig
): number => {
  const delay = config.initialDelay * Math.pow(config.backoffFactor, attempt - 1);
  return Math.min(delay, config.maxDelay);
};

const shouldContinueRetrying = (
  state: RetryState,
  config: RetryConfig
): boolean => {
  if (state.attempt >= config.maxRetries) return false;
  if (Date.now() - state.startTime > config.timeout) return false;
  return config.shouldRetry(state.error);
};

export const retryUtils = {
  /**
   * Main retry operation function
   */
  async retry<T>(
    operation: () => Promise<T>,
    config?: Partial<RetryConfig>
  ): Promise<T> {
    const finalConfig: RetryConfig = { ...defaultConfig, ...config };
    const state: RetryState = {
      attempt: 0,
      error: null,
      startTime: Date.now()
    };

    while (state.attempt < finalConfig.maxRetries) {
      try {
        return await operation();
      } catch (error) {
        state.error = error;
        state.attempt++;

        if (!shouldContinueRetrying(state, finalConfig)) {
          throw error;
        }

        const delayMs = calculateDelay(state.attempt, finalConfig);
        finalConfig.onRetry?.(error, state.attempt);
        await delay(delayMs);
      }
    }

    throw state.error;
  },

  /**
   * Creates a retryable version of any async function 
   */
  createRetryable<T extends (...args: any[]) => Promise<any>>(
    fn: T,
    config?: Partial<RetryConfig>
  ): T {
    return (async (...args: Parameters<T>): Promise<ReturnType<T>> => {
      return this.retry(() => fn(...args), config);
    }) as T;
  },

  /**
   * Gets the default configuration
   */
  getDefaultConfig(): RetryConfig {
    return { ...defaultConfig };
  }
};

// Export types and utilities
export type { RetryConfig, RetryState };
export { isAxiosError };

