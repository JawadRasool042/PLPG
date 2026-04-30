import { adminApi } from './client';
import type { DashboardMetrics } from './types';

export const fetchDashboardAnalytics = async () => {
  const { data } = await adminApi.get<{ data: DashboardMetrics }>('/analytics/dashboard');
  return data.data;
};

export const fetchEngagementAnalytics = async (days = 30) => {
  const { data } = await adminApi.get('/analytics/engagement', { params: { days } });
  return data.data;
};

export const fetchSystemHealth = async () => {
  const { data } = await adminApi.get('/analytics/health');
  return data.data;
};

export const fetchReport = async (params: { reportType: string; startDate?: string; endDate?: string }) => {
  const { data } = await adminApi.get('/analytics/report', { params });
  return data.data;
};
