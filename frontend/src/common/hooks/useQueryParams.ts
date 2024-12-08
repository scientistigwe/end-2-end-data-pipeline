// src/common/hooks/useQueryParams.ts
import { useSearchParams } from 'react-router-dom';
import { useMemo } from 'react';

export function useQueryParams<T extends Record<string, string>>() {
  const [searchParams, setSearchParams] = useSearchParams();

  const params = useMemo(() => {
    const result: Partial<T> = {};
    searchParams.forEach((value, key) => {
      result[key as keyof T] = value as T[keyof T];
    });
    return result;
  }, [searchParams]);

  const setParams = (newParams: Partial<T>) => {
    const current = { ...params, ...newParams };
    setSearchParams(new URLSearchParams(current));
  };

  return [params, setParams] as const;
}

