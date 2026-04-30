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

export default {
  generateQuiz,
  getQuiz,
  submitQuiz,
  getAvailableQuizzes,
  getQuizHistory,
  getUserPerformance,
  getQuizAttempt,
};
