const INTEREST_API_BASE = import.meta.env.VITE_INTEREST_API_URL || 'http://localhost:5000/api';

const getAuthToken = (): string | null => {
  return localStorage.getItem('plpg_access_token');
};

const getAuthHeaders = () => {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

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
  resources: string[];
  suggested_projects: string[];
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
  save_results?: boolean;
  dataset_path?: string;
}

export const checkInterestApiHealth = async (): Promise<{ status: string }> => {
  const res = await fetch(`${INTEREST_API_BASE}/interest/health`);
  if (!res.ok) throw new Error('Failed to reach Interest API');
  return res.json();
};

export const submitInterestAssessment = async (
  payload: InterestRequest
): Promise<AnalysisResponse> => {
  const res = await fetch(`${INTEREST_API_BASE}/interest/analyze`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({
      interests: payload.scores,
      user_context: {
        name: payload.user.name,
        email: payload.user.email,
      }
    }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || data.detail || data.message || 'Failed to submit assessment');
  }
  return data as AnalysisResponse;
};

export const resolveTie = async (selectedInterest: string): Promise<any> => {
  const res = await fetch(`${INTEREST_API_BASE}/interest/resolve-tie`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ selected_interest: selectedInterest }),
  });

  const data = await res.json();
  if (!res.ok) {
    throw new Error(data.error || data.detail || data.message || 'Failed to resolve tie');
  }
  return data;
};
