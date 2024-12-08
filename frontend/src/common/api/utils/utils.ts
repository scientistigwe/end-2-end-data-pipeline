// src/services/api/utils.ts
export const formatEndpoint = (url: string, params?: Record<string, string>): string => {
    if (!params) return url;
    return Object.entries(params).reduce(
      (acc, [key, value]) => acc.replace(`:${key}`, value),
      url
    );
  };