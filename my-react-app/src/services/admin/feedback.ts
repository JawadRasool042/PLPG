import { adminApi } from './client';
import type { FeedbackRecord, FeedbackStatus } from '../feedbackService';

export interface FeedbackListParams {
  page?: number;
  limit?: number;
  status?: FeedbackStatus | '';
  category?: string;
  search?: string;
}

export interface FeedbackPagination {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
}

export interface FeedbackStats {
  total: number;
  recent: number;
  averageRating: number;
  ratingCount: number;
  byCategory: { category: string; count: number }[];
  byStatus: Record<string, number>;
  windowDays: number;
}

export const fetchAllFeedback = async (
  params: FeedbackListParams = {}
): Promise<{ data: FeedbackRecord[]; pagination: FeedbackPagination }> => {
  const { data } = await adminApi.get<{
    success: boolean;
    data: FeedbackRecord[];
    pagination: FeedbackPagination;
  }>('/feedback', { params });
  return {
    data: data.data || [],
    pagination: data.pagination || { page: 1, limit: 25, total: 0, totalPages: 0 },
  };
};

export const fetchFeedbackStats = async (days = 30): Promise<FeedbackStats> => {
  const { data } = await adminApi.get<{ success: boolean; data: FeedbackStats }>(
    '/feedback/stats',
    { params: { days } }
  );
  return data.data;
};

export const updateFeedbackStatus = async (
  id: string,
  payload: { status?: FeedbackStatus; adminNote?: string }
): Promise<FeedbackRecord> => {
  const { data } = await adminApi.patch<{ success: boolean; data: FeedbackRecord }>(
    `/feedback/${id}`,
    payload
  );
  return data.data;
};

export const deleteFeedback = async (id: string): Promise<void> => {
  await adminApi.delete(`/feedback/${id}`);
};
