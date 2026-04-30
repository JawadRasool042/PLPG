import { adminApi } from './client';
import type { AuditLogRow, PaginatedResult } from './types';

export const fetchLogs = async (params: {
  page?: number;
  limit?: number;
  action?: string;
  resource?: string;
  startDate?: string;
  endDate?: string;
}): Promise<PaginatedResult<AuditLogRow>> => {
  const { data } = await adminApi.get<{ data: AuditLogRow[]; pagination: PaginatedResult<AuditLogRow>['pagination'] }>('/logs', {
    params,
  });

  return {
    data: data.data,
    pagination: data.pagination,
  };
};

export const exportLogsCsv = async (params?: { startDate?: string; endDate?: string }) => {
  const response = await adminApi.get('/logs/export/csv', {
    params,
    responseType: 'blob',
  });
  return response.data;
};
