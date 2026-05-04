/**
 * Quiz Service
 * API client for quiz-related operations
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';

// Quiz interfaces
export interface Quiz {
  id: string;
  interest: string;
  level: string;
  totalQuestions: number;
  createdAt: string;
  questions: Question[];
}

export interface Question {
  index: number;
  q: string;
  options: string[];
  answer?: string;
  explanation?: string;
}

export interface QuizAttempt {
  id: string;
  quizId: string;
  interest: string;
  level: string;
  score: number;
  correctCount: number;
  totalQuestions: number;
  completedAt: string;
  results?: QuizResult[];
}

export interface QuizResult {
  questionIndex: number;
  question: string;
  options: string[];
  userAnswer: string;
  correctAnswer: string;
  isCorrect: boolean;
  explanation: string;
}

export interface QuizCategory {
  interest: string;
  levels: {
    Beginner: boolean;
    Intermediate: boolean;
    Advanced: boolean;
  };
  questionCounts: {
    Beginner: number;
    Intermediate: number;
    Advanced: number;
  };
}

export interface UserPerformance {
  overallStats: {
    totalQuizzes: number;
    averageScore: number;
    bestScore: number;
    totalCorrect: number;
    totalQuestions: number;
  };
  byInterest: {
    [interest: string]: {
      totalQuizzes: number;
      averageScore: number;
      bestScore: number;
      lastAttempted: string;
    };
  };
  recentScores: Array<{
    interest: string;
    score: number;
    date: string;
  }>;
  analysis: {
    strengths: Array<{
      interest: string;
      score: number;
      quizzes: number;
    }>;
    weaknesses: Array<{
      interest: string;
      score: number;
      quizzes: number;
    }>;
    recommendations: string[];
  };
  updatedAt: string;
}

// Mixed quiz types
export type QuestionType = 'mcq' | 'true_false' | 'short_answer' | 'scenario';

export interface MCQQuestion {
  type: 'mcq';
  id: number;
  q: string;
  options: string[];
  correct_answer: string;
  explanation: string;
}

export interface TrueFalseQuestion {
  type: 'true_false';
  id: number;
  q: string;
  options: ['True', 'False'];
  correct_answer: 'True' | 'False';
  explanation: string;
}

export interface ShortAnswerQuestion {
  type: 'short_answer';
  id: number;
  q: string;
  expected_keywords: string[];
  correct_answer: string;
  explanation: string;
}

export interface ScenarioQuestion {
  type: 'scenario';
  id: number;
  scenario_context: string;
  q: string;
  expected_keywords: string[];
  correct_answer: string;
  explanation: string;
}

export type MixedQuestion = MCQQuestion | TrueFalseQuestion | ShortAnswerQuestion | ScenarioQuestion;

export interface MixedQuiz {
  id?: string;
  domain: string;
  difficulty: string;
  question_count: number;
  questions: MixedQuestion[];
  created_at?: string;
}

export interface MixedQuizAttempt {
  attempt_id?: string;
  quiz_id?: string;
  domain: string;
  difficulty: string;
  answers: Record<number, string>;
  score: number;
  summary?: string;
  submitted_at?: string;
}

export interface UserProfile {
  user_id?: string;
  email?: string;
  user?: {
    id: string;
    email: string;
    name: string;
    preferences?: Record<string, any>;
  };
  latest_prediction?: {
    primary_interest: string;
    secondary_interests: string[];
    confidence_score: number;
    analysis_timestamp: string;
  };
  latest_roadmap?: {
    domain: string;
    current_level: string;
    career_paths: Array<{
      title: string;
      median_salary: string;
      market_demand: string;
      alignment_score: number;
    }>;
    skill_roadmap: Array<{
      phase: string;
      skills: string[];
      timeline: string;
    }>;
  };
  latest_progress?: {
    total_xp: number;
    level: number;
    current_streak: number;
    achievements: string[];
    last_activity: string;
  };
  latest_quiz?: MixedQuiz & { attempt_score?: number };
}

/**
 * Get authorization token from localStorage
 */
const getAuthToken = (): string | null => {
  return localStorage.getItem('plpg_access_token');
};

/**
 * Get auth headers
 */
const getAuthHeaders = () => {
  const token = getAuthToken();
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

/**
 * Generate a new quiz
 */
export const generateQuiz = async (
  interest: string,
  level: string = 'Beginner'
): Promise<Quiz> => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/quiz/generate`,
      { interest, level },
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data.quiz;
    }
    throw new Error(response.data.message || 'Failed to generate quiz');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to generate quiz');
  }
};

/**
 * Get a specific quiz by ID
 */
export const getQuiz = async (quizId: string): Promise<Quiz> => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/quiz/${quizId}`,
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data.quiz;
    }
    throw new Error(response.data.message || 'Failed to fetch quiz');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to fetch quiz');
  }
};

/**
 * Submit quiz answers
 */
export const submitQuiz = async (
  quizId: string,
  answers: Record<string, string>
): Promise<QuizAttempt> => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/quiz/${quizId}/submit`,
      { answers },
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data.attempt;
    }
    throw new Error(response.data.message || 'Failed to submit quiz');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to submit quiz');
  }
};

/**
 * Get available quiz categories
 */
export const getAvailableQuizzes = async (): Promise<QuizCategory[]> => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/quiz/available`,
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data.categories;
    }
    throw new Error(response.data.message || 'Failed to fetch categories');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to fetch categories');
  }
};

/**
 * Get user's quiz history
 */
export const getQuizHistory = async (limit: number = 20): Promise<QuizAttempt[]> => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/quiz/history?limit=${limit}`,
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data.attempts;
    }
    throw new Error(response.data.message || 'Failed to fetch quiz history');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to fetch quiz history');
  }
};

/**
 * Get user performance analytics
 */
export const getUserPerformance = async (interest?: string): Promise<UserPerformance> => {
  try {
    const url = interest
      ? `${API_BASE_URL}/quiz/performance?interest=${encodeURIComponent(interest)}`
      : `${API_BASE_URL}/quiz/performance`;

    const response = await axios.get(url, { headers: getAuthHeaders() });

    if (response.data.success) {
      return response.data.performance;
    }
    throw new Error(response.data.message || 'Failed to fetch performance data');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to fetch performance data');
  }
};

/**
 * Get a specific quiz attempt
 */
export const getQuizAttempt = async (attemptId: string): Promise<QuizAttempt> => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/quiz/attempt/${attemptId}`,
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data.attempt;
    }
    throw new Error(response.data.message || 'Failed to fetch attempt');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to fetch attempt');
  }
};

/**
 * Generate a mixed-type quiz (supports MCQ, True/False, Short Answer, Scenario)
 */
export const generateMixedQuiz = async (
  domain: string,
  difficulty: string = 'intermediate',
  questionCount: number = 10,
  userProfile?: any
): Promise<MixedQuiz> => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/advanced/generate-quiz`,
      {
        domain,
        difficulty,
        question_count: questionCount,
        user_profile: userProfile,
      },
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      const rawQuestions = (response.data.quiz || response.data.questions || []) as any[];
      const questions: MixedQuestion[] = rawQuestions.map((q: any) => {
        const base = {
          id: Number(q.id),
          type: q.type as QuestionType,
          q: q.question,
          explanation: q.explanation,
        } as any;

        if (q.type === 'mcq') {
          const opts = q.options || {};
          const options = Array.isArray(opts)
            ? opts
            : ['A', 'B', 'C', 'D'].map((k) => `${k}) ${opts[k] ?? ''}`.trim());
          return { ...base, options, correct_answer: q.correct_answer } as MCQQuestion;
        }

        if (q.type === 'true_false') {
          return {
            ...base,
            options: ['True', 'False'],
            correct_answer: q.correct_answer,
          } as TrueFalseQuestion;
        }

        if (q.type === 'scenario') {
          return {
            ...base,
            scenario_context: q.scenario,
            expected_keywords: q.expected_keywords || [],
            correct_answer: q.correct_answer,
          } as ScenarioQuestion;
        }

        return {
          ...base,
          expected_keywords: q.expected_keywords || [],
          correct_answer: q.correct_answer,
        } as ShortAnswerQuestion;
      });

      return {
        domain: response.data.domain,
        difficulty: response.data.difficulty,
        question_count: response.data.question_count,
        questions,
        id: response.data.quiz_id,
        created_at: new Date().toISOString(),
      };
    }
    throw new Error(response.data.message || 'Failed to generate mixed quiz');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to generate mixed quiz');
  }
};

/**
 * Submit a mixed quiz attempt
 */
export const submitMixedQuizAttempt = async (
  quizId: string,
  answers: Record<number, string>,
  domain: string,
  difficulty: string,
  userId: string
): Promise<MixedQuizAttempt> => {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/advanced/submit-quiz`,
      {
        user_id: userId,
        quiz_id: quizId,
        answers,
        domain,
        difficulty,
      },
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data.attempt || {
        quiz_id: quizId,
        domain,
        difficulty,
        answers,
        score: response.data.score || response.data.attempt?.score || 0,
        summary: response.data.summary,
      };
    }
    throw new Error(response.data.message || 'Failed to submit quiz attempt');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to submit quiz attempt');
  }
};

/**
 * Get comprehensive user profile with latest data
 */
export const getUserProfile = async (userId: string): Promise<UserProfile> => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/advanced/user-profile/${userId}`,
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data;
    }
    throw new Error(response.data.message || 'Failed to fetch user profile');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to fetch user profile');
  }
};

/**
 * Get latest progress data
 */
export const getLatestProgress = async (userId: string) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/advanced/latest-progress/${userId}`,
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data;
    }
    throw new Error(response.data.message || 'Failed to fetch progress data');
  } catch (error: any) {
    throw new Error(error.response?.data?.message || error.message || 'Failed to fetch progress data');
  }
};

/**
 * Get latest quiz
 */
export const getLatestQuiz = async (userId: string): Promise<MixedQuiz | null> => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/advanced/latest-quiz/${userId}`,
      { headers: getAuthHeaders() }
    );

    if (response.data.success && response.data.quiz) {
      return response.data.quiz;
    }
    return null;
  } catch (error: any) {
    console.warn('Failed to fetch latest quiz:', error.message);
    return null;
  }
};

/**
 * Get latest roadmap
 */
export const getLatestRoadmap = async (userId: string) => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/advanced/latest-roadmap/${userId}`,
      { headers: getAuthHeaders() }
    );

    if (response.data.success) {
      return response.data.roadmap;
    }
    return null;
  } catch (error: any) {
    console.warn('Failed to fetch latest roadmap:', error.message);
    return null;
  }
};

export default {
  generateQuiz,
  getQuiz,
  submitQuiz,
  getAvailableQuizzes,
  getQuizHistory,
  getUserPerformance,
  getQuizAttempt,
  generateMixedQuiz,
  submitMixedQuizAttempt,
  getUserProfile,
  getLatestProgress,
  getLatestQuiz,
  getLatestRoadmap,
};
