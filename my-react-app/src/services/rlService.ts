/**
 * Reinforcement Learning Service
 * -------------------------------
 * API client for the adaptive RL engine exposed at /api/rl/*.
 *
 * The RL engine is layered ON TOP of the existing interest/quiz pipeline.
 * Use these helpers to:
 *   - request the next adaptive action
 *   - record per-question and end-of-quiz outcomes
 *   - inspect the user's current policy and history
 */

import axios from 'axios';

import { API_BASE_URL } from '../config/apiBase';

export type RLAction =
  | 'increase_difficulty'
  | 'decrease_difficulty'
  | 'keep_difficulty'
  | 'change_topic'
  | 'give_hint'
  | 'shorten_quiz'
  | 'extend_quiz'
  | 'recommend_revision'
  | 'recommend_project'
  | 'recommend_resource';

export interface RLStateInput {
  domain?: string;
  profile?: string;
  difficulty?: string;
  accuracy?: number;
  response_time?: number;
  streak?: number;
  wrong_answers?: number;
  hints_used?: number;
  engagement_score?: number;
  dropout_risk?: number;
  topic_performance?: number;
}

export interface RLStateBuckets {
  difficulty: number;
  accuracy: number;
  response_time: number;
  streak: number;
  wrong: number;
  hint: number;
  engagement: number;
  dropout_risk: number;
  topic_performance: number;
}

export interface RLState {
  domain: string;
  profile: string;
  difficulty: string;
  accuracy: number;
  response_time: number;
  streak: number;
  wrong_answers: number;
  hints_used: number;
  engagement_score: number;
  dropout_risk: number;
  topic_performance: number;
  buckets: RLStateBuckets;
}

export interface RLDecision {
  state: RLState;
  action: RLAction;
  reason: string;
  reward: number;
  next_difficulty: string;
  exploration: boolean;
  policy_version: number;
  episode_id: number | null;
  metadata: {
    valid_actions: RLAction[];
    epsilon: number;
    reward_components?: Record<string, number>;
    reward_notes?: string[];
  };
}

export interface RLFeedback {
  is_correct?: boolean;
  response_time_sec?: number;
  expected_time_sec?: number;
  used_hint?: boolean;
  repeated_mistake?: boolean;
  streak_length?: number;
  quiz_completed?: boolean;
  quiz_dropped?: boolean;
  score_delta?: number;
  returned_next_session?: boolean;
  notes?: string;
}

export interface RLUpdateResult {
  episode_id: number;
  step: number;
  reward: number;
  td_error: number;
  components: Record<string, number>;
  notes: string[];
  policy_version: number;
  epsilon: number;
}

export interface RLPolicySummary {
  user_id: string;
  scope: string;
  policy: {
    epsilon: number;
    version: number;
    episodes_trained: number;
    steps_trained: number;
    states_covered: number;
    top_actions: Array<{ state: unknown[]; action: RLAction; q: number }>;
  };
  session: Record<string, unknown> | null;
  recent_episodes: Array<Record<string, unknown>>;
  recent_actions: Array<Record<string, unknown>>;
}

export interface RLTrainingReport {
  mode: 'replay' | 'simulator';
  episodes: number;
  steps: number;
  avg_reward: number;
  td_error_mean: number;
  td_error_max: number;
  epsilon_after: number;
  extras: Record<string, unknown>;
}

const getAuthHeaders = () => {
  const token = localStorage.getItem('plpg_access_token');
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

const unwrap = <T>(payload: any, key?: string): T => {
  if (!payload || payload.success === false) {
    throw new Error(payload?.error || payload?.message || 'RL request failed');
  }
  if (key && payload[key] !== undefined) {
    return payload[key] as T;
  }
  return payload as T;
};

/**
 * Ask the RL agent for the next adaptive action given the current state.
 * The state can come from the quiz UI (after each answer) or from a
 * dashboard summary.
 */
export const fetchNextAction = async (
  userId: string,
  state: RLStateInput,
  options: { forceExplore?: boolean } = {}
): Promise<RLDecision> => {
  const response = await axios.post(
    `${API_BASE_URL}/rl/next-action`,
    {
      user_id: userId,
      state,
      force_explore: options.forceExplore ?? false,
    },
    { headers: getAuthHeaders() }
  );
  return unwrap<RLDecision>(response.data);
};

/**
 * Record a (state, action, reward) transition.
 * Set `terminal: true` for the final step of a quiz/session.
 */
export const recordReward = async (params: {
  userId: string;
  action: RLAction;
  feedback: RLFeedback;
  previousState: RLStateInput;
  nextState?: RLStateInput;
  episodeId?: number | null;
  terminal?: boolean;
}): Promise<RLUpdateResult> => {
  const response = await axios.post(
    `${API_BASE_URL}/rl/update-reward`,
    {
      user_id: params.userId,
      action: params.action,
      feedback: params.feedback,
      previous_state: params.previousState,
      next_state: params.nextState ?? params.previousState,
      episode_id: params.episodeId ?? undefined,
      terminal: params.terminal ?? false,
    },
    { headers: getAuthHeaders() }
  );
  return unwrap<RLUpdateResult>(response.data);
};

export const getPolicySummary = async (userId: string): Promise<RLPolicySummary> => {
  const response = await axios.get(`${API_BASE_URL}/rl/policy/${encodeURIComponent(userId)}`, {
    headers: getAuthHeaders(),
  });
  return unwrap<RLPolicySummary>(response.data);
};

export const getHistory = async (userId: string, limit = 25) => {
  const response = await axios.get(
    `${API_BASE_URL}/rl/history/${encodeURIComponent(userId)}?limit=${limit}`,
    { headers: getAuthHeaders() }
  );
  return unwrap<{
    transitions: Array<Record<string, unknown>>;
    actions: Array<Record<string, unknown>>;
    episodes: Array<Record<string, unknown>>;
  }>(response.data);
};

export const trainPolicy = async (
  payload: {
    mode?: 'replay' | 'simulator';
    episodes?: number;
    epochs?: number;
    batchSize?: number;
    userId?: string;
    seed?: number;
  } = {}
): Promise<RLTrainingReport> => {
  const response = await axios.post(
    `${API_BASE_URL}/rl/train`,
    {
      mode: payload.mode ?? 'replay',
      episodes: payload.episodes,
      epochs: payload.epochs,
      batch_size: payload.batchSize,
      user_id: payload.userId,
      seed: payload.seed,
    },
    { headers: getAuthHeaders() }
  );
  return unwrap<RLTrainingReport>(response.data, 'report');
};

export const explainAction = async (state: RLStateInput, action: RLAction) => {
  const response = await axios.post(
    `${API_BASE_URL}/rl/explain`,
    { state, action },
    { headers: getAuthHeaders() }
  );
  return unwrap<{
    next_difficulty: string;
    quiz_length_delta: number;
    change_topic: boolean;
    deliver_hint: boolean;
    recommend_revision: boolean;
    recommend_project: boolean;
    recommend_resource: boolean;
    metadata: Record<string, unknown>;
  }>(response.data, 'effect');
};

export const getRLHealth = async () => {
  const response = await axios.get(`${API_BASE_URL}/rl/health`, { headers: getAuthHeaders() });
  return unwrap<Record<string, unknown>>(response.data);
};

/**
 * Convenience: turn an RLAction into the friendly label shown to users.
 */
export const formatActionLabel = (action: RLAction): string =>
  action.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default {
  fetchNextAction,
  recordReward,
  getPolicySummary,
  getHistory,
  trainPolicy,
  explainAction,
  getRLHealth,
  formatActionLabel,
};
