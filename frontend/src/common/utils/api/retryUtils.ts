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
