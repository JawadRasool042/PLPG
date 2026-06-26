import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import { getUserPerformance, type UserPerformance } from '../../services/quizService';
import { parseApiError } from '../../services/apiError';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import EmptyState from '../../components/EmptyState';
import { getEffectivePrimaryInterest, getInterestAssessmentDisplay } from '../../utils/interestDisplay';
import { LEARNING_DOMAIN_LABELS, normalizeRoadmapDomain } from '../../utils/roadmapTopics';

const Quizzes: React.FC = () => {
  const { isAuthenticated, user, hasCompletedOnboarding, userInterests, logout } = useStore();
  const navigate = useNavigate();

  const [performance, setPerformance] = useState<UserPerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingAIQuiz, setStartingAIQuiz] = useState(false);
  const [selectedDifficulty, setSelectedDifficulty] = useState<'basic' | 'intermediate' | 'advanced' | 'expert'>('basic');
  const interestUi = useMemo(() => getInterestAssessmentDisplay(userInterests), [userInterests]);
  const primaryInterest = interestUi.primary;
  const effectivePrimary = useMemo(
    () => getEffectivePrimaryInterest(userInterests),
    [userInterests],
  );

  const [coursePathTopics, setCoursePathTopics] = useState<string[]>([]);
  const [coursePathTopicsLoading, setCoursePathTopicsLoading] = useState(false);
  const [coursePathError, setCoursePathError] = useState<string | null>(null);
  const [courseTopicQuery, setCourseTopicQuery] = useState('');
  const [selectedCourseTopic, setSelectedCourseTopic] = useState<string | null>(null);
  const [courseQuizDifficulty, setCourseQuizDifficulty] = useState<
    'basic' | 'intermediate' | 'advanced' | 'expert'
  >('basic');
  const [startingCourseQuiz, setStartingCourseQuiz] = useState(false);

  const filteredCourseTopics = useMemo(() => {
    const q = courseTopicQuery.trim().toLowerCase();
    if (!q) return coursePathTopics;
    return coursePathTopics.filter((t) => t.toLowerCase().includes(q));
  }, [coursePathTopics, courseTopicQuery]);

  const loadData = useCallback(async (showSkeleton = false) => {
    try {
      if (showSkeleton) {
        setLoading(true);
      }
      setError(null);
      const [perfSettled] = await Promise.allSettled([getUserPerformance()]);
      const perf = perfSettled.status === 'fulfilled' ? perfSettled.value : null;

      setPerformance(perf);

      if (perfSettled.status === 'rejected') {
        const rootError = perfSettled.reason;
        const parsed = parseApiError(rootError, 'Failed to load quiz data.');
        if (parsed.status === 401 || parsed.code === 'INVALID_TOKEN' || parsed.code === 'TOKEN_EXPIRED' || parsed.code === 'INVALID_TOKEN_CONTEXT') {
          try {
            await logout();
          } catch {
            // Ignore logout API failures; we still redirect to login.
          }
          navigate('/login', {
            replace: true,
            state: {
              from: '/quizzes',
              message: 'Your session is invalid or expired. Please log in again.',
            },
          });
          return;
        }
        setError(parsed.message);
      }
    } catch (error: unknown) {
      const parsed = parseApiError(error, 'Failed to load quiz data.');
      if (parsed.status === 401 || parsed.code === 'INVALID_TOKEN' || parsed.code === 'TOKEN_EXPIRED' || parsed.code === 'INVALID_TOKEN_CONTEXT') {
        try {
          await logout();
        } catch {
          // Ignore logout API failures; we still redirect to login.
        }
        navigate('/login', {
          replace: true,
          state: {
            from: '/quizzes',
            message: 'Your session is invalid or expired. Please log in again.',
          },
        });
        return;
      }
      setError(parsed.message);
    } finally {
      if (showSkeleton) {
        setLoading(false);
      }
    }
  }, [logout, navigate]);

  const loadCoursePathTopics = useCallback(() => {
    if (!user?.id || !hasCompletedOnboarding) return;
    setCoursePathTopicsLoading(true);
    setCoursePathError(null);
    try {
      const merged = [...LEARNING_DOMAIN_LABELS];
      const domain = effectivePrimary ? normalizeRoadmapDomain(effectivePrimary) : '';
      setCoursePathTopics(merged);
      setSelectedCourseTopic((prev) => {
        if (prev && merged.some((t) => t.toLowerCase() === prev.toLowerCase())) return prev;
        if (domain) {
          const match = merged.find((t) => t.toLowerCase() === domain.toLowerCase());
          if (match) return match;
        }
        return merged[0] ?? null;
      });
    } catch (err: unknown) {
      setCoursePathError(parseApiError(err, 'Could not load course topics.').message);
      setCoursePathTopics([]);
    } finally {
      setCoursePathTopicsLoading(false);
    }
  }, [user?.id, hasCompletedOnboarding, effectivePrimary]);

  useEffect(() => {
    if (!isAuthenticated || !user?.id) return;
    void loadCoursePathTopics();
  }, [isAuthenticated, user?.id, loadCoursePathTopics]);

  useEffect(() => {
    if (!isAuthenticated || !user) return;

    // Initial database fetch with skeleton, then keep stats in sync.
    loadData(true);

    const pollInterval = window.setInterval(() => {
      loadData(false);
    }, 5000);

    const handleFocusRefresh = () => {
      loadData(false);
    };

    const handleVisibilityRefresh = () => {
      if (document.visibilityState === 'visible') {
        loadData(false);
      }
    };

    window.addEventListener('focus', handleFocusRefresh);
    document.addEventListener('visibilitychange', handleVisibilityRefresh);

    return () => {
      window.clearInterval(pollInterval);
      window.removeEventListener('focus', handleFocusRefresh);
      document.removeEventListener('visibilitychange', handleVisibilityRefresh);
    };
  }, [isAuthenticated, user, loadData]);

  const handleStartQuiz = async () => {
    try {
      setStartingAIQuiz(true);
      setError(null);
      if (!primaryInterest) {
        setError('Complete the interest assessment first (Quizzes → Interest Assessment) to start an AI quiz.');
        return;
      }
      navigate('/ai-quiz', {
        state: {
          topic: primaryInterest,
          difficulty: selectedDifficulty,
        },
      });
    } catch (error: unknown) {
      setError(parseApiError(error, 'Failed to start AI quiz.').message);
    } finally {
      setStartingAIQuiz(false);
    }
  };

  const handleStartCourseTopicQuiz = () => {
    if (!hasCompletedOnboarding) {
      setError('Complete the interest assessment first before starting a quiz.');
      navigate('interest-check');
      return;
    }
    if (!selectedCourseTopic) {
      setError('Choose a domain (search and select a chip below).');
      return;
    }
    setError(null);
    setStartingCourseQuiz(true);
    navigate('/ai-quiz', {
      state: {
        topic: selectedCourseTopic,
        difficulty: courseQuizDifficulty,
      },
    });
    setStartingCourseQuiz(false);
  };

  // If not authenticated, redirect to login
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: '/quizzes', message: 'Please log in to access quizzes.' }} replace />;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 pt-24 pb-12">
        <div className="max-w-6xl mx-auto px-4">
          {/* Welcome Section Skeleton */}
          <LoadingSkeleton variant="card" className="mb-6" />
          
          {/* Interest Check Status Skeleton */}
          <LoadingSkeleton variant="card" className="mb-6" />
          
          {/* Performance + generated quiz skeleton */}
          <LoadingSkeleton variant="card" className="mb-6" />
          <LoadingSkeleton variant="card" className="mb-6" />
          <LoadingSkeleton variant="card" className="mb-6" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 pt-24 pb-12">
      <div className="max-w-6xl mx-auto px-4">
        {/* Welcome Section */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-6">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">
            Welcome back, {user.firstName}! 👋
          </h1>
          <p className="text-slate-600">
            Your personalized quiz dashboard
          </p>
        </div>

        {/* Interest Check Status */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${hasCompletedOnboarding
                  ? 'bg-green-100 text-green-600'
                  : 'bg-amber-100 text-amber-600'
                  }`}>
                  {hasCompletedOnboarding ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  )}
                </div>
                <h2 className="text-xl font-semibold text-slate-900">
                  {hasCompletedOnboarding ? 'Interest Assessment Complete' : 'Complete Your Interest Assessment'}
                </h2>
              </div>

              {hasCompletedOnboarding && userInterests ? (
                <div className="ml-13">
                  <p className="text-slate-600 mb-4">
                    Your primary interest: <span className="font-semibold text-indigo-600">{interestUi.primary}</span>
                    <span className="text-slate-500 ml-2">({interestUi.confidencePct}% confidence)</span>
                  </p>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {interestUi.tagDomains.map((domain) => (
                      <span
                        key={domain}
                        className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-sm font-medium"
                      >
                        {domain}
                      </span>
                    ))}
                  </div>
                  <button
                    onClick={() => navigate('interest-check')}
                    className="text-indigo-600 hover:text-indigo-700 font-medium text-sm flex items-center gap-1"
                  >
                    Retake Assessment
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              ) : (
                <div className="ml-13">
                  <p className="text-slate-600 mb-4">
                    Take a quick assessment to discover your learning interests and get personalized recommendations.
                  </p>
                  <button
                    onClick={() => navigate('interest-check')}
                    className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors flex items-center gap-2"
                  >
                    Start Interest Assessment
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700">
            {error}
          </div>
        )}

        {/* Performance Overview */}
        {performance && performance.overallStats.totalQuizzes > 0 && (
          <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl shadow-lg p-8 mb-6 text-white">
            <h2 className="text-xl font-bold mb-6">Your Performance</h2>
            <div className="grid md:grid-cols-3 gap-6">
              <div>
                <p className="text-indigo-200 text-sm mb-1">Total Quizzes</p>
                <p className="text-3xl font-bold">{performance.overallStats.totalQuizzes}</p>
              </div>
              <div>
                <p className="text-indigo-200 text-sm mb-1">Average Score</p>
                <p className="text-3xl font-bold">{performance.overallStats.averageScore}%</p>
              </div>
              <div>
                <p className="text-indigo-200 text-sm mb-1">Best Score</p>
                <p className="text-3xl font-bold">{performance.overallStats.bestScore}%</p>
              </div>
            </div>
          </div>
        )}

        {/* PLPG Generated quiz */}
        <div className="mb-6">
          {hasCompletedOnboarding && primaryInterest ? (
            <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl shadow-lg p-6 text-white">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <p className="text-xs uppercase tracking-wide text-indigo-200">
                    PLPG
                  </p>
                  <h2 className="text-2xl font-bold mt-1">
                    PLPG Generated quiz
                  </h2>
                  <p className="text-sm text-indigo-100 mt-2 max-w-2xl">
                    Questions are built on demand by your PLPG backend from your interest assessment (sliders and primary
                    domain), roadmap context, and the difficulty you choose—not from a fixed question bank.
                  </p>
                  <div className="flex flex-wrap gap-2 mt-3">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-white/20 text-white border border-white/30">
                      Topic: {primaryInterest}
                    </span>
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-white/15 text-white/95 border border-white/25 capitalize">
                      {selectedDifficulty}
                    </span>
                  </div>
                </div>
              </div>

              <div className="mt-5">
                <p className="text-sm font-semibold mb-3 text-indigo-100">Difficulty</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                  {(['basic', 'intermediate', 'advanced', 'expert'] as const).map((level) => (
                    <button
                      key={level}
                      onClick={() => setSelectedDifficulty(level)}
                      className={`px-4 py-3 rounded-xl border-2 font-semibold capitalize transition-colors ${
                        selectedDifficulty === level
                          ? 'bg-white text-indigo-700 border-white'
                          : 'bg-transparent text-white border-white/40 hover:bg-white/10'
                      }`}
                    >
                      {level}
                    </button>
                  ))}
                </div>
              </div>

              <div className="mt-5">
                <button
                  onClick={handleStartQuiz}
                  disabled={startingAIQuiz}
                  className="w-full sm:w-auto px-6 py-3 bg-white text-indigo-700 rounded-xl font-semibold hover:bg-indigo-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {startingAIQuiz ? 'Starting...' : 'Start Quiz'}
                </button>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={
                <svg className="w-16 h-16 sm:w-20 sm:h-20 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              }
              title="Complete Interest Assessment"
              description="We need your interest profile so PLPG can generate quizzes matched to your domains and roadmap."
              actionLabel="Start Assessment"
              onAction={() => navigate('interest-check')}
            />
          )}
        </div>

        {/* Domain quiz — same purple PLPG card + OpenAI flow as primary generated quiz */}
        {hasCompletedOnboarding && effectivePrimary ? (
          <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl shadow-lg p-6 mb-6 text-white">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div>
                <p className="text-xs uppercase tracking-wide text-indigo-200">PLPG</p>
                <h2 className="text-2xl font-bold mt-1">PLPG Generated quiz</h2>
                <p className="text-sm text-indigo-100 mt-2 max-w-2xl">
                  Choose one of the nine PLPG learning domains (same labels as your interest assessment). Questions are
                  built on demand by your PLPG backend from that domain, roadmap context, and the difficulty you
                  choose—not from a fixed question bank.
                </p>
                {selectedCourseTopic ? (
                  <div className="flex flex-wrap gap-2 mt-3">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-white/20 text-white border border-white/30">
                      Topic: {selectedCourseTopic}
                    </span>
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-white/15 text-white/95 border border-white/25 capitalize">
                      {courseQuizDifficulty}
                    </span>
                  </div>
                ) : null}
              </div>
            </div>

            {coursePathTopicsLoading ? (
              <p className="text-sm text-indigo-100 mt-5">Loading domains…</p>
            ) : coursePathError ? (
              <div className="mt-5 rounded-xl border border-amber-300/50 bg-amber-500/20 px-4 py-3 text-sm text-amber-50">
                {coursePathError}{' '}
                <button
                  type="button"
                  onClick={() => void loadCoursePathTopics()}
                  className="font-semibold text-white underline underline-offset-2"
                >
                  Retry
                </button>
              </div>
            ) : coursePathTopics.length === 0 ? (
              <div className="mt-5 rounded-xl border border-white/25 bg-white/10 px-4 py-4 text-sm text-indigo-100">
                No learning domains available. Try refreshing the page or signing in again.
              </div>
            ) : (
              <>
                <label className="block text-sm font-semibold text-indigo-100 mb-2 mt-5" htmlFor="course-topic-search">
                  Search domains
                </label>
                <div className="relative mb-4">
                  <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-indigo-200">
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z"
                      />
                    </svg>
                  </span>
                  <input
                    id="course-topic-search"
                    type="search"
                    value={courseTopicQuery}
                    onChange={(e) => setCourseTopicQuery(e.target.value)}
                    placeholder="Filter by name…"
                    className="w-full rounded-xl border-2 border-white/40 bg-white/10 py-3 pl-10 pr-4 text-sm text-white placeholder:text-indigo-200/80 focus:outline-none focus:ring-2 focus:ring-white/40"
                    autoComplete="off"
                  />
                </div>

                <p className="text-xs font-semibold uppercase tracking-wide text-indigo-200 mb-2">
                  Select a domain ({filteredCourseTopics.length} shown)
                </p>
                <div className="max-h-52 overflow-y-auto rounded-xl border border-white/25 bg-white/5 p-3 mb-5">
                  <div className="flex flex-wrap gap-2">
                    {filteredCourseTopics.map((t) => {
                      const active =
                        selectedCourseTopic &&
                        selectedCourseTopic.toLowerCase() === t.toLowerCase();
                      return (
                        <button
                          key={t}
                          type="button"
                          onClick={() => setSelectedCourseTopic(t)}
                          className={`rounded-full px-3 py-1.5 text-sm font-semibold border-2 capitalize transition-colors ${
                            active
                              ? 'border-white bg-white text-indigo-700'
                              : 'border-white/40 bg-transparent text-white hover:bg-white/10'
                          }`}
                        >
                          {t}
                        </button>
                      );
                    })}
                  </div>
                  {filteredCourseTopics.length === 0 && courseTopicQuery.trim() ? (
                    <p className="text-sm text-indigo-100 py-2">No domains match that search.</p>
                  ) : null}
                </div>

                <p className="text-sm font-semibold mb-3 text-indigo-100">Difficulty</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
                  {(['basic', 'intermediate', 'advanced', 'expert'] as const).map((level) => (
                    <button
                      key={level}
                      type="button"
                      onClick={() => setCourseQuizDifficulty(level)}
                      className={`px-4 py-3 rounded-xl border-2 font-semibold capitalize transition-colors ${
                        courseQuizDifficulty === level
                          ? 'bg-white text-indigo-700 border-white'
                          : 'bg-transparent text-white border-white/40 hover:bg-white/10'
                      }`}
                    >
                      {level}
                    </button>
                  ))}
                </div>

                <button
                  type="button"
                  onClick={handleStartCourseTopicQuiz}
                  disabled={!selectedCourseTopic || startingCourseQuiz}
                  className="w-full sm:w-auto px-6 py-3 bg-white text-indigo-700 rounded-xl font-semibold hover:bg-indigo-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {startingCourseQuiz ? 'Starting…' : 'Start Quiz'}
                </button>
              </>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default Quizzes;
