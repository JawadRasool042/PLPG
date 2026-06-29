import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { registerUser, loginUser, logoutUser, getCurrentUserData, type RegisterResult, type InterestAssessmentMe } from '../services/authService';

export interface User {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  role: string;
}

export interface LearningGoal {
  id: string;
  title: string;
  description: string;
  category: string;
  selected: boolean;
}

export interface Quiz {
  id: string;
  title: string;
  description: string;
  questions: Question[];
  completed: boolean;
  score?: number;
}

export interface Question {
  id: string;
  text: string;
  options: string[];
  correctAnswer: number;
  selectedAnswer?: number;
}

export interface Feedback {
  id: string;
  quizId: string;
  quizTitle: string;
  score: number;
  totalQuestions: number;
  feedback: string;
  timestamp: Date;
}

export interface Progress {
  userId: string;
  completedQuizzes: number;
  totalQuizzes: number;
  averageScore: number;
  learningGoalsCompleted: number;
  totalLearningGoals: number;
  recentActivity: Activity[];
}

export interface Activity {
  id: string;
  type: 'quiz' | 'goal' | 'feedback';
  title: string;
  description: string;
  timestamp: Date;
}

export interface UserInterests {
  primaryInterest: string;
  confidence: number;
  allInterests: { domain: string; confidence: number }[];
  /** Raw 0–10 domain ratings from the assessment sliders (when persisted). */
  domainScores?: Record<string, number>;
  completedAt: string;
  assessmentContext?: {
    known?: string;
    want?: string;
    goals?: string;
  };
  /** Normalized tags from assessment text (known / want / goals) for personalization + careers. */
  assessmentTags?: string[];
  realtimeSignals?: {
    totalTimeSpentSec?: number;
    domainsInteracted?: number;
  };
}

interface AppState {
  // User state
  user: User | null;
  isAuthenticated: boolean;
  hasCompletedOnboarding: boolean;
  userInterests: UserInterests | null;
  login: (email: string, password: string) => Promise<boolean>;
  register: (userData: Omit<User, 'id' | 'role'> & { password: string }) => Promise<RegisterResult>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
  initializeAuth: () => void;
  setOnboardingComplete: (interests: UserInterests) => void;
  resetOnboarding: () => void;

  // Theme state
  theme: 'light' | 'dark' | 'auto';
  setTheme: (theme: 'light' | 'dark' | 'auto') => void;

  // Learning Goals
  learningGoals: LearningGoal[];
  selectedGoals: string[];
  toggleGoal: (goalId: string) => void;
  setLearningGoals: (goals: LearningGoal[]) => void;

  // Learning Path
  learningPath: string[];
  generateLearningPath: () => void;

  // Quizzes
  quizzes: Quiz[];
  currentQuiz: Quiz | null;
  setCurrentQuiz: (quizId: string) => void;
  submitQuizAnswer: (questionId: string, answerIndex: number) => void;
  submitQuiz: () => Feedback | null;

  // Feedback
  feedbacks: Feedback[];
  addFeedback: (feedback: Feedback) => void;

  // Progress
  progress: Progress | null;
  updateProgress: () => void;
}

const mapAssessmentToStore = (
  assessment: InterestAssessmentMe | null | undefined,
): Pick<AppState, 'hasCompletedOnboarding' | 'userInterests'> => {
  if (!assessment?.completed) {
    return { hasCompletedOnboarding: false, userInterests: null };
  }

  const rawScores = assessment.domainScores ?? {};
  const domainScores =
    rawScores && typeof rawScores === 'object'
      ? Object.fromEntries(
          Object.entries(rawScores).map(([k, v]) => [k, typeof v === 'number' ? v : Number(v)]),
        )
      : undefined;

  const atags = assessment.assessmentTags;
  const assessmentTags = Array.isArray(atags)
    ? atags.map((t) => String(t).trim()).filter(Boolean)
    : undefined;

  const actx = assessment.assessmentContext;
  const assessmentContext =
    actx && typeof actx === 'object'
      ? {
          known: actx.known != null ? String(actx.known) : undefined,
          want: actx.want != null ? String(actx.want) : undefined,
          goals: actx.goals != null ? String(actx.goals) : undefined,
        }
      : undefined;

  return {
    hasCompletedOnboarding: true,
    userInterests: {
      primaryInterest: assessment.primaryInterest ?? '',
      confidence: Number(assessment.confidence ?? 0),
      allInterests: assessment.allInterests ?? [],
      ...(domainScores && Object.keys(domainScores).length > 0 ? { domainScores } : {}),
      completedAt: assessment.completedAt ?? new Date().toISOString(),
      ...(assessmentContext ? { assessmentContext } : {}),
      ...(assessmentTags?.length ? { assessmentTags } : {}),
    },
  };
};

const defaultLearningGoals: LearningGoal[] = [
  { id: '1', title: 'Web Development', description: 'Learn HTML, CSS, JavaScript, and modern frameworks', category: 'Programming', selected: false },
  { id: '2', title: 'Data Science', description: 'Master Python, statistics, and machine learning', category: 'Data', selected: false },
  { id: '3', title: 'Mobile Development', description: 'Build iOS and Android applications', category: 'Programming', selected: false },
  { id: '4', title: 'Cloud Computing', description: 'AWS, Azure, and cloud architecture', category: 'Infrastructure', selected: false },
  { id: '5', title: 'Cybersecurity', description: 'Network security, ethical hacking, and cryptography', category: 'Security', selected: false },
  { id: '6', title: 'UI/UX Design', description: 'Design principles, Figma, and user experience', category: 'Design', selected: false },
  { id: '7', title: 'DevOps', description: 'CI/CD, Docker, Kubernetes, and automation', category: 'Infrastructure', selected: false },
  { id: '8', title: 'Blockchain', description: 'Smart contracts, Ethereum, and decentralized apps', category: 'Technology', selected: false },
];

const defaultQuizzes: Quiz[] = [];

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
      // User state
      user: null,
      isAuthenticated: false,
      hasCompletedOnboarding: false,
      userInterests: null,

      // Theme state
      theme: 'light',

      setTheme: (theme: 'light' | 'dark' | 'auto') => {
        set({ theme });
        
        // Apply theme to document
        const root = document.documentElement;
        
        if (theme === 'auto') {
          // Check system preference
          const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
          if (prefersDark) {
            root.classList.add('dark');
          } else {
            root.classList.remove('dark');
          }
        } else if (theme === 'dark') {
          root.classList.add('dark');
        } else {
          root.classList.remove('dark');
        }
      },

      login: async (email: string, password: string) => {
        const userData = await loginUser(email, password);
        set({
          user: {
            id: userData.id,
            firstName: userData.firstName,
            lastName: userData.lastName,
            email: userData.email,
            role: userData.role,
          },
          isAuthenticated: true,
          ...mapAssessmentToStore(userData.interestAssessment),
        });
        return true;
      },

      register: async (userData) => {
        const newUser = await registerUser(
          userData.email,
          userData.password,
          userData.firstName,
          userData.lastName,
          'Student'
        );
        return newUser;
      },

      logout: async () => {
        try {
          await logoutUser();
          set({ user: null, isAuthenticated: false, hasCompletedOnboarding: false, userInterests: null });
        } catch (error: any) {
          console.error('Logout error:', error);
          set({ user: null, isAuthenticated: false, hasCompletedOnboarding: false, userInterests: null });
        }
      },

      setUser: (user: User) => {
        set({
          user,
          isAuthenticated: true,
        });
      },

      initializeAuth: async () => {
        try {
          const userData = await getCurrentUserData();
          if (userData) {
            set({
              user: {
                id: userData.id,
                firstName: userData.firstName,
                lastName: userData.lastName,
                email: userData.email,
                role: userData.role,
              },
              isAuthenticated: true,
              ...mapAssessmentToStore(userData.interestAssessment),
            });
          } else {
            set({ user: null, isAuthenticated: false, hasCompletedOnboarding: false, userInterests: null });
          }
        } catch (error) {
          console.error('Error initializing auth:', error);
          set({ user: null, isAuthenticated: false, hasCompletedOnboarding: false, userInterests: null });
        }
      },

      setOnboardingComplete: (interests: UserInterests) => {
        set({ hasCompletedOnboarding: true, userInterests: interests });
      },

      resetOnboarding: () => {
        set({ hasCompletedOnboarding: false, userInterests: null });
      },

      // Learning Goals
      learningGoals: defaultLearningGoals,
      selectedGoals: [],

      toggleGoal: (goalId: string) => {
        const goals = get().learningGoals.map(goal =>
          goal.id === goalId ? { ...goal, selected: !goal.selected } : goal
        );
        const selected = goals.filter(g => g.selected).map(g => g.id);
        set({ learningGoals: goals, selectedGoals: selected });
      },

      setLearningGoals: (goals) => {
        set({ learningGoals: goals });
      },

      // Learning Path
      learningPath: [],
      generateLearningPath: () => {
        const selected = get().selectedGoals;
        const path = selected.map(id => {
          const goal = get().learningGoals.find(g => g.id === id);
          return goal?.title || '';
        });
        set({ learningPath: path });
      },

      // Quizzes
      quizzes: defaultQuizzes,
      currentQuiz: null,

      setCurrentQuiz: (quizId: string) => {
        const quiz = get().quizzes.find(q => q.id === quizId);
        if (quiz) {
          set({ currentQuiz: { ...quiz, questions: quiz.questions.map(q => ({ ...q, selectedAnswer: undefined })) } });
        }
      },

      submitQuizAnswer: (questionId: string, answerIndex: number) => {
        const currentQuiz = get().currentQuiz;
        if (currentQuiz) {
          const updatedQuestions = currentQuiz.questions.map(q =>
            q.id === questionId ? { ...q, selectedAnswer: answerIndex } : q
          );
          set({ currentQuiz: { ...currentQuiz, questions: updatedQuestions } });
        }
      },

      submitQuiz: () => {
        const currentQuiz = get().currentQuiz;
        if (!currentQuiz) return null;

        let correct = 0;
        currentQuiz.questions.forEach(q => {
          if (q.selectedAnswer === q.correctAnswer) {
            correct++;
          }
        });

        const score = Math.round((correct / currentQuiz.questions.length) * 100);
        const feedback: Feedback = {
          id: Date.now().toString(),
          quizId: currentQuiz.id,
          quizTitle: currentQuiz.title,
          score,
          totalQuestions: currentQuiz.questions.length,
          feedback: score >= 80 ? 'Excellent work! You have a strong understanding of this topic.' : score >= 60 ? 'Good job! Review the areas you missed to improve further.' : 'Keep practicing! Review the material and try again.',
          timestamp: new Date(),
        };

        // Update quiz as completed
        const quizzes = get().quizzes.map(q =>
          q.id === currentQuiz.id ? { ...q, completed: true, score } : q
        );

        // Add feedback
        const feedbacks = [...get().feedbacks, feedback];

        set({
          quizzes,
          currentQuiz: null,
          feedbacks,
        });

        get().updateProgress();
        return feedback;
      },

      // Feedback
      feedbacks: [],

      addFeedback: (feedback) => {
        set({ feedbacks: [...get().feedbacks, feedback] });
      },

      // Progress
      progress: null,

      updateProgress: () => {
        const user = get().user;
        if (!user) return;

        const quizzes = get().quizzes;
        const completedQuizzes = quizzes.filter(q => q.completed).length;
        const totalQuizzes = quizzes.length;
        const scores = quizzes.filter(q => q.completed && q.score !== undefined).map(q => q.score!);
        const averageScore = scores.length > 0 ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0;

        const selectedGoals = get().selectedGoals.length;
        const totalGoals = get().learningGoals.length;

        const recentActivity: Activity[] = [
          ...get().feedbacks.slice(-5).map(f => ({
            id: f.id,
            type: 'feedback' as const,
            title: `Quiz: ${f.quizTitle}`,
            description: `Scored ${f.score}%`,
            timestamp: f.timestamp,
          })),
        ].sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

        set({
          progress: {
            userId: user.id,
            completedQuizzes,
            totalQuizzes,
            averageScore,
            learningGoalsCompleted: selectedGoals,
            totalLearningGoals: totalGoals,
            recentActivity,
          },
        });
      },
    }),
    {
      name: 'plpg-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        theme: state.theme,
        learningGoals: state.learningGoals,
        selectedGoals: state.selectedGoals,
        learningPath: state.learningPath,
        quizzes: state.quizzes,
        feedbacks: state.feedbacks,
        progress: state.progress,
      }),
    }
  )
);

