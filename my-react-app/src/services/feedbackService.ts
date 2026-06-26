/**
 * Feedback Service (Requirement #11)
 * --------------------------------------
 * User-side wrapper for the feedback API. Sends real submissions to
 * the Flask backend and lists the authenticated user's history.
 */

import { API_BASE_URL } from '../config/apiBase';

const getAuthToken = (): string | null => localStorage.getItem('plpg_access_token');

const authHeaders = (): HeadersInit => {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

export type FeedbackCategory =
  | 'General'
  | 'Quiz Quality'
  | 'Learning Path'
  | 'UI/UX'
  | 'Bug Report'
  | 'Feature Request';

export type FeedbackStatus = 'new' | 'in_review' | 'resolved' | 'dismissed';

export interface FeedbackPayload {
  category: FeedbackCategory | string;
  rating: number;
  subject?: string;
  message: string;
  page?: string;
  /** Optional context (e.g. quiz attempt) — merged into stored metadata on the server. */
  metadata?: Record<string, string | number | boolean | null | undefined>;
}

export interface FeedbackRecord {
  id: string;
  userId?: string | null;
  userEmail?: string | null;
  userName?: string | null;
  category: string;
  rating: number;
  subject: string;
  message: string;
  status: FeedbackStatus;
  adminNote?: string | null;
  metadata?: Record<string, unknown>;
  createdAt: string | null;
  updatedAt: string | null;
}

const handleJson = async (res: Response) => {
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data?.success === false) {
    const message = data?.message || data?.detail || data?.error || `Request failed (${res.status})`;
    throw new Error(message);
  }
  return data;
};

export const submitFeedback = async (payload: FeedbackPayload): Promise<FeedbackRecord> => {
  const res = await fetch(`${API_BASE_URL}/feedback`, {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify(payload),
  });
  const data = await handleJson(res);
  return data.data as FeedbackRecord;
};

export const getMyFeedback = async (limit = 20): Promise<FeedbackRecord[]> => {
  const res = await fetch(`${API_BASE_URL}/feedback/me?limit=${limit}`, {
    method: 'GET',
    headers: authHeaders(),
  });
  const data = await handleJson(res);
  return (data.data || []) as FeedbackRecord[];
};
