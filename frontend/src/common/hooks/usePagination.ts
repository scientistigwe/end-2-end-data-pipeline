// src/common/hooks/usePagination.ts
import { useState, useMemo } from 'react';
import type { PaginationParams } from '../types/api';

interface UsePaginationProps {
  totalItems: number;
  initialPage?: number;
  initialLimit?: number;
}

export function usePagination({
  totalItems,
  initialPage = 1,
  initialLimit = 10
}: UsePaginationProps) {
  const [page, setPage] = useState(initialPage);
  const [limit, setLimit] = useState(initialLimit);

  const totalPages = useMemo(() => 
    Math.ceil(totalItems / limit), 
    [totalItems, limit]
  );

  const paginationParams: PaginationParams = useMemo(() => ({
    page,
    limit
  }), [page, limit]);

  const canNextPage = page < totalPages;
  const canPreviousPage = page > 1;

  const nextPage = () => {
    if (canNextPage) {
      setPage(prev => prev + 1);
    }
  };

  const previousPage = () => {
    if (canPreviousPage) {
      setPage(prev => prev - 1);
    }
  };

  const setPageSize = (pageSize: number) => {
    setLimit(pageSize);
    setPage(1);
  };

  return {
    page,
    setPage,
    limit,
    setPageSize,
    canNextPage,
    canPreviousPage,
    nextPage,
    previousPage,
    totalPages,
    paginationParams
  };
}
