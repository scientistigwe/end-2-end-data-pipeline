// src/common/api/utils/formatters.ts
export const formatEndpoint = (url: string, params: Record<string, string>): string => {
    let formattedEndpoint = url;
    Object.entries(params).forEach(([key, value]) => {
      formattedEndpoint = formattedEndpoint.replace(`:${key}`, encodeURIComponent(value));
    });
    return formattedEndpoint;
  };
  