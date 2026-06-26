import { parseApiError } from './apiError';
import { API_BASE_URL } from '../config/apiBase';

const getAuthToken = (): string | null => localStorage.getItem('plpg_access_token');

const getAuthHeaders = () => {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

export interface TopDomainInsight {
  domain: string;
  score: number;
  percent?: number;
  confidence: number;
  model_confidence?: number;
  why_matched?: string[];
  skills_gap?: string[];
  fastest_path?: string;
  best_courses?: string[];
  best_projects?: string[];
  best_certifications?: string[];
  community_resources?: string[];
  career_paths?: Record<string, any>;
}

export interface PredictionResponse {
  success: boolean;
  user_profile?: string;
  primary_interest: string;
  predicted_interest?: string;
  confidence: number;
  model_confidence?: number;
  all_probabilities: Record<string, number>;
  top_domains?: TopDomainInsight[];
  top_3_interests?: TopDomainInsight[];
  roadmap?: Record<string, any>;
  career_paths?: Record<string, any>;
  skills_gap?: Record<string, any>;
  projects?: Array<Record<string, any>>;
  certifications?: string[];
  gamification?: Record<string, any>;
  visual_analytics?: Record<string, string>;
  metadata?: Record<string, any>;
}

export interface MixedQuizQuestion {
  id: number;
  type: 'mcq' | 'true_false' | 'short_answer' | 'scenario';
  question: string;
  scenario?: string;
  sub_topic: string;
  options?: Record<string, string> | string[];
  correct_answer: string;
  expected_keywords?: string[];
  explanation: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  targets_weak_area?: boolean;
}

export interface MixedQuizResponse {
  success: boolean;
  quiz_id?: number | string | null;
  domain: string;
  quiz: MixedQuizQuestion[];
  metadata: Record<string, any>;
}

export interface PakistaniJobRecommendation {
  title: string;
  matched_course?: string;
  employer_type?: string;
  city?: string;
  salary_pkr?: string;
  employment_type?: string;
  skills_match?: string[];
  why_recommended?: string;
}

export interface CareerRecommendation {
  title: string;
  level?: 'beginner' | 'intermediate' | 'advanced';
  progress_status?: 'achieved' | 'current' | 'upcoming';
  recommended?: boolean;
  industry?: string;
  salary_range?: string;
  growth_potential?: string;
  required_skills?: string[];
  resume_angle?: string;
  progress_note?: string;
}

export interface RoadmapResponse {
  success: boolean;
  domain: string;
  roadmap: Record<string, any>;
  career_paths?: Record<string, any>;
  careers_detailed?: CareerRecommendation[];
  careers_by_level?: Record<string, CareerRecommendation[]>;
  user_career_level?: 'beginner' | 'intermediate' | 'advanced';
  pakistani_jobs?: PakistaniJobRecommendation[];
  resume_outline?: { headline?: string; keywords?: string[]; bullets?: string[] };
  secondary_insights?: Record<string, Record<string, unknown>>;
  skills_gap?: Record<string, any>;
  quiz_caliber?: {
    attempt_count?: number;
    average_score?: number;
    best_score?: number;
    recent_scores?: number[];
    recommended_quiz_difficulty?: string;
    mastery_level?: number;
  };
  recommended_quiz_difficulty?: string;
  caliber_summary?: string;
  market_region?: string;
  salary_currency?: string;
  cached?: boolean;
  stale?: boolean;
  generated_at?: string;
  metadata?: Record<string, any>;
}

export interface UserProfileSnapshot {
  success: boolean;
  user: Record<string, any>;
  latest_prediction?: Record<string, any> | null;
  latest_roadmap?: Record<string, any> | null;
  latest_progress?: Record<string, any> | null;
  latest_quiz?: Record<string, any> | null;
}

export const predictInterest = async (payload: Record<string, any>): Promise<PredictionResponse> => {
  try {
    const res = await fetch(`${API_BASE_URL}/predict-interest`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      throw { response: { status: res.status, data } };
    }
    return data as PredictionResponse;
  } catch (error) {
    throw new Error(parseApiError(error, 'Failed to predict interest').message);
  }
};

export const generateQuiz = async (payload: Record<string, any>): Promise<MixedQuizResponse> => {
  const res = await fetch(`${API_BASE_URL}/generate-quiz`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || data.message || 'Failed to generate quiz');
  }
  return data as MixedQuizResponse;
};

export const generateRoadmap = async (payload: Record<string, any>): Promise<RoadmapResponse> => {
  const controller = new AbortController();
  const timeoutMs = 150_000;
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE_URL}/generate-roadmap`, {
      method: 'POST',
      headers: getAuthHeaders(),
      body: JSON.stringify(payload),
      signal: controller.signal,
    });

    const data = await res.json();
    if (!res.ok) {
      throw { response: { status: res.status, data } };
    }
    return data as RoadmapResponse;
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Learning path request timed out. Your last saved path may load on retry.');
    }
    throw new Error(parseApiError(error, 'Failed to generate roadmap').message);
  } finally {
    window.clearTimeout(timer);
  }
};

export const saveProgress = async (payload: Record<string, any>): Promise<Record<string, any>> => {
  const res = await fetch(`${API_BASE_URL}/save-progress`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || data.message || 'Failed to save progress');
  }
  return data as Record<string, any>;
};

export const getUserProfileSnapshot = async (userId: string): Promise<UserProfileSnapshot> => {
  const res = await fetch(`${API_BASE_URL}/user-profile/${encodeURIComponent(userId)}`, {
    headers: getAuthHeaders(),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || data.message || 'Failed to fetch user profile');
  }
  return data as UserProfileSnapshot;
};
