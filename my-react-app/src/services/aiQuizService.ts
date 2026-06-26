/**
 * AI Quiz Service
 *
 * Real-time OpenAI-powered quiz API client. Questions are generated
 * dynamically — there is no pre-stored question bank. When the user
 * submits a wrong answer, the backend persists the weak concept and
 * future questions target it.
 */

import axios from "axios";
import { parseApiError } from "./apiError";
import { API_BASE_URL } from "../config/apiBase";
import type { QuizAttempt, QuizResult } from "./quizService";

const AI_QUIZ_BASE = `${API_BASE_URL}/ai-quiz`;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type AIQuizDifficulty = "basic" | "intermediate" | "advanced" | "expert";

export interface AIQuizQuestion {
  question: string;
  options: string[];
  topic?: string;
  difficulty?: AIQuizDifficulty | string;
}

export interface AIQuizWrongOption {
  option: string;
  reason: string;
}

export interface AIQuizReasoning {
  why_correct: string;
  wrong_options: AIQuizWrongOption[];
}

export interface AIQuizFeedback {
  is_correct: boolean;
  user_answer: string;
  correct_answer: string;
  why_correct?: string;
  why_wrong?: Record<string, string>;
  reasoning: AIQuizReasoning;
  concept_summary?: string;
  memory_tip?: string;
  topic?: string;
  difficulty?: string;
}

/** Hard limit imposed by the backend (`AI_QUIZ_QUESTION_LIMIT`). */
export const AI_QUIZ_QUESTION_LIMIT = 10;

export interface AIQuizStartResponse {
  session_id: string;
  attempt_id?: string;
  topic: string;
  difficulty: AIQuizDifficulty | string;
  requested_difficulty?: AIQuizDifficulty | string;
  easier_quiz_triggered?: boolean;
  target_question_count: number;
  question_limit?: number;
  question_index: number;
  question: AIQuizQuestion;
  weak_concepts: string[];
}

export interface AIQuizNextResponse {
  session_id: string;
  question_index: number;
  question: AIQuizQuestion;
  weak_concepts: string[];
}

export interface AIQuizAnswerResponse {
  session_id: string;
  question_index: number;
  feedback: AIQuizFeedback;
  total_answered?: number;
  target_question_count?: number;
  limit_reached?: boolean;
}

export type AIQuizLevelChange = "demote" | "repeat" | "promote" | "jump";
export type AIQuizScoreBand =
  | "struggling"
  | "developing"
  | "on-track"
  | "excellent"
  | "mastery";

export interface AIQuizLevelRecommendation {
  recommended: AIQuizDifficulty | string;
  from: AIQuizDifficulty | string;
  change: AIQuizLevelChange;
  reason: string;
  score_band: AIQuizScoreBand;
  score: number;
  easier_triggered?: boolean;
}

export interface AIQuizSessionSummary {
  id: string;
  topic: string;
  difficulty: string;
  status: "active" | "completed" | "abandoned";
  targetQuestionCount: number;
  totalAnswered: number;
  correctCount: number;
  score: number;
  weakConcepts: string[];
  createdAt: string | null;
  completedAt: string | null;
  questions: Array<
    AIQuizQuestion & {
      concept_summary?: string;
      memory_tip?: string;
      correct_answer?: string;
      reasoning?: AIQuizReasoning;
    }
  >;
  answers?: Array<{
    questionIndex: number;
    userAnswer: string;
    isCorrect: boolean;
    timeSpentMs?: number;
    answeredAt?: string | null;
  }>;
  /** Populated by the frontend after /finish from the response envelope. */
  recommendation?: AIQuizLevelRecommendation;
  attemptId?: string;
  remediation?: import('./remediationService').RemediationStatus;
}

const LEVEL_ORDER: AIQuizDifficulty[] = [
  "basic",
  "intermediate",
  "advanced",
  "expert",
];

/**
 * Mirrors backend `routes/ai_quiz._build_level_recommendation` so the UI always
 * has coaching text even if an older API build omits `level_recommendation`.
 */
export function deriveLevelRecommendation(
  score: number,
  currentLevel: string
): AIQuizLevelRecommendation {
  const scoreN = Math.max(0, Math.min(100, Number(score) || 0));
  const raw = String(currentLevel || "")
    .trim()
    .toLowerCase();
  const current = LEVEL_ORDER.includes(raw as AIQuizDifficulty)
    ? (raw as AIQuizDifficulty)
    : "basic";
  const currentIdx = LEVEL_ORDER.indexOf(current);

  let target: AIQuizDifficulty;
  let change: AIQuizLevelChange;
  let reason: string;
  let band: AIQuizScoreBand;

  if (scoreN < 40) {
    target = LEVEL_ORDER[Math.max(0, currentIdx - 1)];
    change = target !== current ? "demote" : "repeat";
    reason =
      change === "demote"
        ? `Score ${Math.round(scoreN)}% is below 40%. ` +
          `We'll drop back to **${titleCase(target)}** so you can reinforce the basics.`
        : `Score ${Math.round(scoreN)}% is low — let's stay on **${titleCase(
            target
          )}** and rebuild confidence.`;
    band = "struggling";
  } else if (scoreN < 60) {
    target = current;
    change = "repeat";
    reason =
      `Score ${Math.round(scoreN)}% shows real progress on **${titleCase(
        current
      )}**. ` + `Run another session at the same level to lock it in.`;
    band = "developing";
  } else if (scoreN < 80) {
    target = LEVEL_ORDER[Math.min(LEVEL_ORDER.length - 1, currentIdx + 1)];
    change = target !== current ? "promote" : "repeat";
    reason =
      change === "promote"
        ? `Score ${Math.round(scoreN)}% — you're ready for harder questions. ` +
          `Stepping up to **${titleCase(target)}**.`
        : `Score ${Math.round(scoreN)}% — you're already at the top level. Keep practising on **${titleCase(
            current
          )}**.`;
    band = "on-track";
  } else if (scoreN < 90) {
    target = LEVEL_ORDER[Math.min(LEVEL_ORDER.length - 1, currentIdx + 2)];
    change = target !== current ? "jump" : "repeat";
    reason =
      change === "jump"
        ? `Score ${Math.round(scoreN)}% is excellent. ` +
          `Jumping ahead to **${titleCase(target)}** — you've earned it.`
        : `Score ${Math.round(scoreN)}% — already at the top level. Try a new topic at **${titleCase(
            current
          )}**.`;
    band = "excellent";
  } else {
    target = "expert";
    change = target !== current ? "promote" : "repeat";
    reason =
      change !== "repeat"
        ? `Score ${Math.round(scoreN)}% — true mastery. ` +
          `Taking on **${titleCase(target)}**-tier questions next.`
        : `Score ${Math.round(scoreN)}% — you're already running at **${titleCase(
            target
          )}** level. Keep the streak going.`;
    band = "mastery";
  }

  return {
    recommended: target,
    from: current,
    change,
    reason,
    score_band: band,
    score: Math.round(scoreN * 100) / 100,
  };
}

function titleCase(level: string): string {
  return level ? level.charAt(0).toUpperCase() + level.slice(1) : level;
}

function inferChangeByLevels(from: string, to: string): AIQuizLevelChange {
  const fi = LEVEL_ORDER.indexOf(from as AIQuizDifficulty);
  const ti = LEVEL_ORDER.indexOf(to as AIQuizDifficulty);
  if (fi < 0 || ti < 0) return "repeat";
  if (ti < fi) return "demote";
  if (ti === fi) return "repeat";
  if (ti === fi + 1) return "promote";
  return "jump";
}

function mergeRecommendationFromFinish(
  session: AIQuizSessionSummary,
  envelope: {
    level_recommendation?: AIQuizLevelRecommendation | null;
    recommended_next_level?: string;
    score?: number;
  }
): AIQuizLevelRecommendation {
  const score =
    typeof envelope.score === "number" ? envelope.score : session.score;
  const from = String(session.difficulty || "basic")
    .trim()
    .toLowerCase();

  const raw = envelope.level_recommendation;
  if (
    raw &&
    raw.recommended != null &&
    String(raw.recommended).length > 0 &&
    raw.reason
  ) {
    const fromNorm = String(raw.from || from).toLowerCase();
    const recNorm = String(raw.recommended).toLowerCase();
    const change =
      raw.change ||
      inferChangeByLevels(fromNorm, recNorm);
    return {
      ...raw,
      from: fromNorm,
      recommended: recNorm as AIQuizDifficulty,
      change,
      score: typeof raw.score === "number" ? raw.score : score,
    };
  }

  const hinted = envelope.recommended_next_level
    ?.toString()
    .trim()
    .toLowerCase();
  const base = deriveLevelRecommendation(score, from);
  if (hinted && LEVEL_ORDER.includes(hinted as AIQuizDifficulty)) {
    const h = hinted as AIQuizDifficulty;
    if (h !== base.recommended) {
      const fi = LEVEL_ORDER.indexOf(base.from as AIQuizDifficulty);
      const ti = LEVEL_ORDER.indexOf(h);
      let change: AIQuizLevelChange = "repeat";
      if (ti < fi) change = "demote";
      else if (ti === fi) change = "repeat";
      else if (ti === fi + 1) change = "promote";
      else if (ti > fi + 1) change = "jump";
      return {
        ...base,
        recommended: h,
        change,
        reason:
          `Based on your **${Math.round(score)}%** result, try your next session at **${titleCase(
            h
          )}** to match your current pace.`,
      };
    }
  }
  return base;
}

export interface AIQuizDashboardData {
  scoreHistory: Array<{
    attemptId: string;
    topic: string;
    score: number;
    level: string;
    completedAt: string | null;
  }>;
  levelProgress: Array<{
    attemptId: string;
    fromLevel: string;
    recommendedLevel: string;
    easierQuizTriggered: boolean;
  }>;
  weakTopics: WeakConceptRecord[];
  recommendations: string[];
}

export interface WeakConceptRecord {
  id: string | null;
  concept: string;
  topic?: string | null;
  difficulty?: string | null;
  failureCount: number;
  successCount: number;
  mastered: boolean;
  lastSeenAt?: string | null;
  firstSeenAt?: string | null;
  lastWrongQuestion?: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
const getAuthToken = (): string | null =>
  localStorage.getItem("plpg_access_token");

const authHeaders = () => {
  const token = getAuthToken();
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

const unwrapError = (err: any, fallback: string): Error => {
  return new Error(parseApiError(err, fallback).message);
};

const normalizeQuestion = (question: any): AIQuizQuestion => {
  const rawOptions = question?.options;
  let options: string[] = [];

  if (Array.isArray(rawOptions)) {
    options = rawOptions.map((opt: any) => String(opt ?? ""));
  } else if (rawOptions && typeof rawOptions === "object") {
    options = (["A", "B", "C", "D"] as const).map(
      (letter) => `${letter}) ${String(rawOptions[letter] ?? "")}`
    );
  }

  return {
    question: String(question?.question ?? ""),
    options,
    topic: question?.topic,
    difficulty: question?.difficulty,
  };
};

// ---------------------------------------------------------------------------
// API
// ---------------------------------------------------------------------------
export const startAIQuiz = async (params: {
  topic: string;
  difficulty?: AIQuizDifficulty;
  questionCount?: number;
}): Promise<AIQuizStartResponse> => {
  try {
    const requested = params.questionCount ?? AI_QUIZ_QUESTION_LIMIT;
    const clamped = Math.max(1, Math.min(requested, AI_QUIZ_QUESTION_LIMIT));
    const response = await axios.post(
      `${AI_QUIZ_BASE}/start`,
      {
        topic: params.topic,
        difficulty: params.difficulty || "basic",
        question_count: clamped,
      },
      { headers: authHeaders() }
    );
    if (!response.data?.success) {
      throw new Error(response.data?.message || "Failed to start AI quiz");
    }
    const data = response.data as AIQuizStartResponse;
    return {
      ...data,
      question: normalizeQuestion((data as any).question),
    };
  } catch (err: any) {
    throw unwrapError(err, "Failed to start AI quiz");
  }
};

export const requestNextAIQuestion = async (params: {
  sessionId: string;
  difficulty?: AIQuizDifficulty;
}): Promise<AIQuizNextResponse> => {
  try {
    const response = await axios.post(
      `${AI_QUIZ_BASE}/next`,
      {
        session_id: params.sessionId,
        difficulty: params.difficulty,
      },
      { headers: authHeaders() }
    );
    if (!response.data?.success) {
      throw new Error(
        response.data?.message || "Failed to fetch next question"
      );
    }
    const data = response.data as AIQuizNextResponse;
    return {
      ...data,
      question: normalizeQuestion((data as any).question),
    };
  } catch (err: any) {
    throw unwrapError(err, "Failed to fetch next question");
  }
};

export const submitAIAnswer = async (params: {
  sessionId: string;
  questionIndex: number;
  answer: string;
  timeSpentMs?: number;
}): Promise<AIQuizAnswerResponse> => {
  try {
    const response = await axios.post(
      `${AI_QUIZ_BASE}/answer`,
      {
        session_id: params.sessionId,
        question_index: params.questionIndex,
        answer: params.answer,
        time_spent_ms: params.timeSpentMs ?? 0,
      },
      { headers: authHeaders() }
    );
    if (!response.data?.success) {
      throw new Error(response.data?.message || "Failed to submit answer");
    }
    const data = response.data as AIQuizAnswerResponse;
    return {
      ...data,
      feedback: {
        ...data.feedback,
        why_correct: (data.feedback as any)?.why_correct || data.feedback?.reasoning?.why_correct,
        why_wrong: (data.feedback as any)?.why_wrong,
      },
    };
  } catch (err: any) {
    throw unwrapError(err, "Failed to submit answer");
  }
};

export const finishAIQuiz = async (
  sessionId: string
): Promise<AIQuizSessionSummary> => {
  try {
    const response = await axios.post(
      `${AI_QUIZ_BASE}/finish`,
      { session_id: sessionId },
      { headers: authHeaders() }
    );
    if (!response.data?.success) {
      throw new Error(response.data?.message || "Failed to finish AI quiz");
    }
    const session = response.data.session as AIQuizSessionSummary;
    // Envelope fields (`level_recommendation`, `recommended_next_level`) are merged
    // so the summary always carries coaching text (fallback matches the backend).
    return {
      ...session,
      questions: (session.questions || []).map((q: any) => ({
        ...q,
        ...normalizeQuestion(q),
      })),
      recommendation: mergeRecommendationFromFinish(session, response.data),
      attemptId: response.data.attempt_id as string | undefined,
      remediation: response.data.remediation,
    };
  } catch (err: any) {
    throw unwrapError(err, "Failed to finish AI quiz");
  }
};

export const getAIQuizSession = async (
  sessionId: string
): Promise<AIQuizSessionSummary> => {
  try {
    const response = await axios.get(`${AI_QUIZ_BASE}/session/${sessionId}`, {
      headers: authHeaders(),
    });
    if (!response.data?.success) {
      throw new Error(response.data?.message || "Failed to load session");
    }
    const session = response.data.session as AIQuizSessionSummary;
    return {
      ...session,
      questions: (session.questions || []).map((q: any) => ({
        ...q,
        ...normalizeQuestion(q),
      })),
    };
  } catch (err: any) {
    throw unwrapError(err, "Failed to load session");
  }
};

export const getWeakConcepts = async (
  includeMastered = false,
  limit = 50
): Promise<WeakConceptRecord[]> => {
  try {
    const response = await axios.get(`${AI_QUIZ_BASE}/weak-concepts`, {
      headers: authHeaders(),
      params: {
        include_mastered: includeMastered ? "true" : "false",
        limit,
      },
    });
    if (!response.data?.success) {
      throw new Error(
        response.data?.message || "Failed to load weak concepts"
      );
    }
    return (response.data.weak_concepts || []) as WeakConceptRecord[];
  } catch (err: any) {
    throw unwrapError(err, "Failed to load weak concepts");
  }
};

export const getAIQuizDashboard = async (
  limit = 20
): Promise<AIQuizDashboardData> => {
  try {
    const response = await axios.get(`${AI_QUIZ_BASE}/dashboard`, {
      headers: authHeaders(),
      params: { limit },
    });
    if (!response.data?.success) {
      throw new Error(response.data?.message || "Failed to load AI quiz dashboard");
    }
    return response.data.dashboard as AIQuizDashboardData;
  } catch (err: any) {
    throw unwrapError(err, "Failed to load AI quiz dashboard");
  }
};

/** Build a QuizResults snapshot from a finished AI session (no extra API round-trip). */
export function buildAIQuizAttemptSnapshot(
  summary: AIQuizSessionSummary,
  attemptId: string,
): QuizAttempt {
  const questions = summary.questions || [];
  const answers = summary.answers || [];
  const answerByIndex = new Map(
    answers.map((a) => [Number(a.questionIndex), a]),
  );

  const results: QuizResult[] = questions.map((q, idx) => {
    const ans = answerByIndex.get(idx);
    const options = (q.options || []).map(String);
    return {
      questionIndex: idx,
      question: q.question || "",
      options,
      userAnswer: String(ans?.userAnswer ?? ""),
      correctAnswer: String(q.correct_answer ?? ""),
      isCorrect: Boolean(ans?.isCorrect),
      explanation: String(
        q.reasoning?.why_correct || q.concept_summary || q.memory_tip || "",
      ),
    };
  });

  const correctCount =
    summary.correctCount ?? results.filter((r) => r.isCorrect).length;

  return {
    id: attemptId,
    quizId: attemptId,
    interest: summary.topic,
    level: summary.difficulty,
    score: Math.round(summary.score),
    correctCount,
    totalQuestions: summary.totalAnswered || questions.length,
    completedAt: summary.completedAt || new Date().toISOString(),
    quizType: "ai",
    results,
  };
}

export default {
  startAIQuiz,
  requestNextAIQuestion,
  submitAIAnswer,
  finishAIQuiz,
  getAIQuizSession,
  getWeakConcepts,
  getAIQuizDashboard,
  buildAIQuizAttemptSnapshot,
};
