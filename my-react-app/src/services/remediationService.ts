import axios from 'axios';
import { API_BASE_URL } from '../config/apiBase';
import { throwParsedApiError } from './apiError';
import { getAuthenticatedHeaders } from './authService';
import type { QuizAttempt } from './quizService';

const REMEDIATION_BASE = `${API_BASE_URL}/remediation`;

export interface RemediationQuestionSection {
  question_index: number;
  topic: string;
  question: string;
  your_answer: string;
  correct_answer: string;
  is_correct: boolean;
  explanation: string;
}

/** @deprecated Legacy grouped-concept format */
export interface RemediationConcept {
  concept: string;
  why_it_mattered: string;
  clear_explanation: string;
  related_question_indexes?: number[];
}

/** @deprecated Legacy mistake list format */
export interface RemediationMistake {
  question_index: number;
  question: string;
  your_answer: string;
  correct_answer: string;
  why_yours_was_wrong: string;
  why_correct_is_right: string;
}

export interface RemediationLessonContent {
  title: string;
  summary: string;
  question_sections?: RemediationQuestionSection[];
  quick_revision?: string[];
  /** @deprecated */
  struggling_concepts?: RemediationConcept[];
  /** @deprecated */
  mistake_review?: RemediationMistake[];
  /** @deprecated */
  key_facts?: string[];
  /** @deprecated */
  revision_checklist?: string[];
  generation_error?: string;
}

export interface RemediationLock {
  id: string;
  attemptId: string;
  quizId?: string;
  retakeQuizId?: string;
  interest?: string;
  level?: string;
  score?: number;
  passed: boolean;
  status: 'pending' | 'studied' | 'completed' | 'skipped';
  lesson: RemediationLessonContent;
}

export interface RemediationStatus {
  passed: boolean;
  passingScore: number;
  needsRemediation: boolean;
  canContinue: boolean;
  score?: number;
  attemptId?: string;
  lessonId?: string;
  retakeQuizId?: string;
  lessonStatus?: string;
  lesson?: RemediationLock | null;
  activeLock?: RemediationLock | null;
}

export const DEFAULT_PASSING_SCORE = 70;

function normalizeRemediationStatus(raw: Record<string, unknown>): RemediationStatus {
  return {
    passed: Boolean(raw.passed),
    passingScore: Number(raw.passingScore ?? raw.passing_score ?? DEFAULT_PASSING_SCORE),
    needsRemediation: Boolean(raw.needsRemediation ?? raw.needs_remediation),
    canContinue: !((raw.canContinue === false) || (raw.can_continue === false)),
    score: raw.score != null ? Number(raw.score) : undefined,
    attemptId: (raw.attemptId ?? raw.attempt_id) as string | undefined,
    lessonId: (raw.lessonId ?? raw.lesson_id) as string | undefined,
    retakeQuizId: (raw.retakeQuizId ?? raw.retake_quiz_id) as string | undefined,
    lessonStatus: (raw.lessonStatus ?? raw.lesson_status) as string | undefined,
    lesson: (raw.lesson as RemediationLock | null | undefined) ?? null,
    activeLock: (raw.activeLock ?? raw.active_lock) as RemediationLock | null | undefined,
  };
}

/** Ensure lesson + retake quiz exist when score is below the passing threshold. */
export async function resolveRemediationForAttempt(
  attemptId: string,
  score: number,
  snapshot?: QuizAttempt,
  initial?: RemediationStatus | null,
): Promise<RemediationStatus | null> {
  const passing = initial?.passingScore ?? DEFAULT_PASSING_SCORE;
  if (score >= passing) {
    if (initial) return initial;
    try {
      return await getRemediationStatus(attemptId);
    } catch {
      return null;
    }
  }

  if (initial?.needsRemediation && getRetakeQuizId(initial)) {
    return initial;
  }

  try {
    if (snapshot) {
      return await processRemediationAttempt(attemptId, snapshot);
    }
    return await getOrCreateRemediationLesson(attemptId);
  } catch {
    try {
      return await getRemediationStatus(attemptId);
    } catch {
      return {
        passed: false,
        passingScore: passing,
        needsRemediation: true,
        canContinue: false,
        score,
        attemptId,
      };
    }
  }
}

export const getRemediationStatus = async (attemptId: string): Promise<RemediationStatus> => {
  try {
    const response = await axios.get(`${REMEDIATION_BASE}/status/${attemptId}`, {
      headers: await getAuthenticatedHeaders(),
    });
    if (!response.data?.success) {
      throw new Error(response.data?.message || 'Failed to load remediation status');
    }
    const { success: _s, ...payload } = response.data;
    return normalizeRemediationStatus(payload as Record<string, unknown>);
  } catch (error: unknown) {
    throwParsedApiError(error, 'Failed to load remediation status');
  }
};

export const getOrCreateRemediationLesson = async (attemptId: string): Promise<RemediationStatus> => {
  try {
    const response = await axios.get(`${REMEDIATION_BASE}/lesson/${attemptId}`, {
      headers: await getAuthenticatedHeaders(),
    });
    if (!response.data?.success) {
      throw new Error(response.data?.message || 'Failed to generate remediation lesson');
    }
    const { success: _s, ...payload } = response.data;
    return normalizeRemediationStatus(payload as Record<string, unknown>);
  } catch (error: unknown) {
    throwParsedApiError(error, 'Failed to generate remediation lesson');
  }
};

export const processRemediationAttempt = async (
  attemptId: string,
  snapshot?: QuizAttempt,
): Promise<RemediationStatus> => {
  try {
    const response = await axios.post(
      `${REMEDIATION_BASE}/process`,
      {
        attempt_id: attemptId,
        attempt_snapshot: snapshot,
      },
      { headers: await getAuthenticatedHeaders() },
    );
    if (!response.data?.success) {
      throw new Error(response.data?.message || 'Failed to process remediation');
    }
    const { success: _s, ...payload } = response.data;
    return normalizeRemediationStatus(payload as Record<string, unknown>);
  } catch (error: unknown) {
    throwParsedApiError(error, 'Failed to process remediation');
  }
};

export const markRemediationLessonStudied = async (lessonId: string): Promise<void> => {
  try {
    const response = await axios.post(
      `${REMEDIATION_BASE}/lesson/${lessonId}/complete`,
      {},
      { headers: await getAuthenticatedHeaders() },
    );
    if (!response.data?.success) {
      throw new Error(response.data?.message || 'Failed to mark lesson complete');
    }
  } catch (error: unknown) {
    throwParsedApiError(error, 'Failed to mark lesson complete');
  }
};

export const canContinueLearning = async (): Promise<{
  canContinue: boolean;
  activeLock: RemediationLock | null;
  passingScore: number;
}> => {
  try {
    const response = await axios.get(`${REMEDIATION_BASE}/can-continue`, {
      headers: await getAuthenticatedHeaders(),
    });
    if (!response.data?.success) {
      throw new Error(response.data?.message || 'Failed to check remediation lock');
    }
    return {
      canContinue: Boolean(response.data.canContinue),
      activeLock: response.data.activeLock ?? null,
      passingScore: Number(response.data.passingScore ?? DEFAULT_PASSING_SCORE),
    };
  } catch (error: unknown) {
    throwParsedApiError(error, 'Failed to check remediation lock');
  }
};

export const canRetakeQuiz = async (
  retakeQuizId: string,
): Promise<{
  canRetake: boolean;
  message: string;
  activeLock: RemediationLock | null;
  passingScore: number;
}> => {
  try {
    const response = await axios.get(`${REMEDIATION_BASE}/can-retake/${retakeQuizId}`, {
      headers: await getAuthenticatedHeaders(),
    });
    if (!response.data?.success) {
      throw new Error(response.data?.message || 'Failed to check retake eligibility');
    }
    return {
      canRetake: Boolean(response.data.canRetake),
      message: String(response.data.message || ''),
      activeLock: response.data.activeLock ?? null,
      passingScore: Number(response.data.passingScore ?? DEFAULT_PASSING_SCORE),
    };
  } catch (error: unknown) {
    throwParsedApiError(error, 'Failed to check retake eligibility');
  }
};

export async function canContinueLearningPath(): Promise<RemediationStatus> {
  const { canContinue, activeLock, passingScore } = await canContinueLearning();
  return {
    passed: canContinue,
    needsRemediation: !canContinue,
    canContinue,
    passingScore,
    activeLock,
  };
}

/** @deprecated Use processRemediationAttempt */
export const processRemediationSnapshot = processRemediationAttempt;

export function extractLessonContent(status: RemediationStatus): RemediationLessonContent | null {
  const lock = status.lesson;
  if (!lock) return null;

  const nested = lock.lesson;
  if (nested && typeof nested === 'object' && 'title' in nested) {
    return nested as RemediationLessonContent;
  }

  if (
    Array.isArray((lock as unknown as RemediationLessonContent).question_sections) ||
    'title' in lock
  ) {
    return lock as unknown as RemediationLessonContent;
  }

  return null;
}

export function getQuestionSections(lesson: RemediationLessonContent | null): RemediationQuestionSection[] {
  if (!lesson?.question_sections?.length) return [];
  return [...lesson.question_sections]
    .map((s) => ({
      question_index: s.question_index ?? 0,
      topic: s.topic || 'Core Concept',
      question: s.question || '',
      your_answer: s.your_answer || '—',
      correct_answer: s.correct_answer || '—',
      is_correct: Boolean(s.is_correct),
      explanation: (s.explanation || '').trim(),
    }))
    .sort((a, b) => a.question_index - b.question_index);
}

export function getQuickRevision(lesson: RemediationLessonContent | null): string[] {
  if (!lesson) return [];
  if (lesson.quick_revision?.length) return lesson.quick_revision;
  return lesson.revision_checklist ?? [];
}

export function getRetakeQuizId(status: RemediationStatus | null | undefined): string | null {
  if (!status) return null;
  return status.retakeQuizId || status.lesson?.retakeQuizId || null;
}
