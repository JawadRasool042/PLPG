import { parseApiError } from './apiError';
import { API_BASE_URL } from '../config/apiBase';
import { authenticatedFetch } from './authService';

const interestEnv = import.meta.env.VITE_INTEREST_API_URL?.trim();
const INTEREST_API_BASE = interestEnv ? interestEnv.replace(/\/$/, '') : API_BASE_URL;

export type InterestDomain =
  | 'Coding'
  | 'Web Development'
  | 'Game Development'
  | 'Cybersecurity'
  | 'Data Science'
  | 'Mobile Development'
  | 'Cloud Computing'
  | 'AI & Machine Learning'
  | 'Physical Games / Sports';

export type InterestScores = Record<InterestDomain, number>;

export interface InterestUserInfo {
  name?: string;
  email?: string;
  known?: string;
  want?: string;
  goals?: string;
}

export interface InterestPrediction {
  primary_interest: string;
  confidence: number;
  all_probabilities: Record<string, number>;
  top_3_interests: { domain: string; confidence: number }[];
}

export interface LearningApproach {
  type: 'physical' | 'digital';
  message: string;
  suggestions: string[];
}

export interface InterestRecommendations {
  primary_interest: string;
  confidence: number;
  description: string;
  recommended_courses: string[];
  advanced_courses?: string[];
  resources: string[];
  advanced_resources?: string[];
  suggested_projects: string[];
  advanced_projects?: string[];
  /** Official Basic → Advanced topic steps (keys: Beginner, Intermediate, Advanced). */
  topic_roadmap?: Record<string, string[]>;
  /** Three project ideas per stage (same tier keys). */
  stage_project_roadmap?: Record<string, string[]>;
  secondary_interests: string[];
  learning_approach?: LearningApproach;
  is_physical_domain?: boolean;
  user_info?: InterestUserInfo;
}

export interface InterestResponse {
  prediction: InterestPrediction;
  recommendations: InterestRecommendations;
  chart_path?: string | null;
  saved_to?: string | null;
  metadata: {
    domains: string[];
    model_path: string;
    dataset: string;
  };
}

export interface TieDetection {
  is_tie: boolean;
  tie_candidates: string[];
  resolution_question?: string;
}

export interface AnalysisResponse {
  success: boolean;
  primary_interest: string;
  ranked_interests: Array<{
    name: string;
    score: number;
    percentage: string;
    confidence: string;
    reason: string;
    rank: number;
    base_score?: number;
    behavioral_score?: number | null;
  }>;
  tie_detected: TieDetection;
  recommendation: {
    career_paths: Array<{
      title: string;
      industry: string;
      salary_range: string;
      growth_potential: string;
      required_skills?: string[];
      entry_requirements?: string;
    }>;
    skill_roadmap: Array<{
      level: string;
      duration: string;
      topics: string[];
      projects: string[];
      resources?: Array<Record<string, string>>;
    }>;
    learning_next_step: string;
    justification: string;
    learning_approach?: LearningApproach;
  };
  data_validation: {
    total_percentage: string;
    accuracy_status: string;
    expected_percentage?: string;
    domain_count?: number;
    all_scores_positive?: boolean;
    no_random_values?: boolean;
  };
  timestamp: string;
  metadata?: {
    system: string;
    version: string;
    accuracy: string;
  };
}

export interface InterestRequest {
  user: InterestUserInfo;
  scores: InterestScores;
  /** Tags derived from known/want/goals for profile + career matching */
  tags?: string[];
  save_results?: boolean;
  dataset_path?: string;
  behavioral_data?: Record<string, Record<string, any>>;
  historical_data?: Array<Record<string, any>>;
}

export interface OfficialCurriculumResponse {
  requested_domain: string;
  canonical_domain: string;
  topic_roadmap: Record<string, string[]>;
  stage_project_roadmap: Record<string, string[]>;
}

/**
 * Load dynamic topic + stage-project roadmaps for one domain (`/api/interest/curriculum` → OpenAI API).
 */
export const fetchOfficialCurriculum = async (domain: string): Promise<OfficialCurriculumResponse> => {
  const params = new URLSearchParams({ domain: domain.trim() });
  const res = await fetch(`${API_BASE_URL}/interest/curriculum?${params.toString()}`);
  const data = (await res.json()) as OfficialCurriculumResponse & { error?: string; domains?: string[] };
  if (!res.ok) {
    const msg = data.error || 'Failed to load curriculum';
    throw new Error(msg);
  }
  if (data.error) {
    throw new Error(data.error);
  }
  return data as OfficialCurriculumResponse;
};

export const checkInterestApiHealth = async (): Promise<{ status: string }> => {
  const res = await fetch(`${INTEREST_API_BASE}/interest/health`);
  if (!res.ok) throw new Error('Failed to reach Interest API');
  return res.json();
};

export const submitInterestAssessment = async (
  payload: InterestRequest
): Promise<AnalysisResponse> => {
  try {
    const res = await authenticatedFetch(`${INTEREST_API_BASE}/interest/analyze`, {
      method: 'POST',
      body: JSON.stringify({
        interests: payload.scores,
        behavioral_data: payload.behavioral_data || {},
        historical_data: payload.historical_data || [],
        user_context: {
          name: payload.user.name,
          email: payload.user.email,
          known: payload.user.known,
          want: payload.user.want,
          goals: payload.user.goals,
          learning_goals: payload.user.goals,
          assessment_tags: payload.tags?.length ? payload.tags : [],
        }
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw { response: { status: res.status, data } };
    }
    return data as AnalysisResponse;
  } catch (error) {
    const parsed = parseApiError(error, 'Failed to submit assessment');
    throw Object.assign(new Error(parsed.message), { code: parsed.code, status: parsed.status });
  }
};

export const resolveTie = async (
  selectedInterest: string,
  analysisSnapshot?: Pick<AnalysisResponse, 'ranked_interests' | 'tie_detected'>
): Promise<any> => {
  try {
    const res = await authenticatedFetch(`${INTEREST_API_BASE}/interest/resolve-tie`, {
      method: 'POST',
      body: JSON.stringify({
        selected_interest: selectedInterest,
        ...(analysisSnapshot ? { analysis_snapshot: analysisSnapshot } : {}),
      }),
    });

    const data = await res.json();
    if (!res.ok) {
      throw { response: { status: res.status, data } };
    }
    return data;
  } catch (error) {
    const parsed = parseApiError(error, 'Failed to resolve tie');
    throw Object.assign(new Error(parsed.message), { code: parsed.code, status: parsed.status });
  }
};
