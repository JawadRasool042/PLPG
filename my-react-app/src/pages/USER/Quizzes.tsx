import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { Check, ChevronDown, History, Map } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { getUserPerformance, type UserPerformance } from '../../services/quizService';
import { parseApiError } from '../../services/apiError';
import {
  getEffectivePrimaryInterest,
  getInterestAssessmentDisplay,
  getInterestDomainIcon,
} from '../../utils/interestDisplay';
import { LEARNING_DOMAIN_LABELS, normalizeRoadmapDomain } from '../../utils/roadmapTopics';

const Quizzes: React.FC = () => {
  const { isAuthenticated, user, hasCompletedOnboarding, userInterests } = useStore();
  const navigate = useNavigate();

  const [error, setError] = useState<string | null>(null);
  const [performance, setPerformance] = useState<UserPerformance | null>(null);
  const interestUi = useMemo(() => getInterestAssessmentDisplay(userInterests), [userInterests]);
  const effectivePrimary = useMemo(
    () => getEffectivePrimaryInterest(userInterests),
    [userInterests],
  );

  const [coursePathTopics, setCoursePathTopics] = useState<string[]>([]);
  const [coursePathError, setCoursePathError] = useState<string | null>(null);
  const [selectedCourseTopic, setSelectedCourseTopic] = useState<string | null>(null);
  const [showTopicPicker, setShowTopicPicker] = useState(false);
  const [courseQuizDifficulty, setCourseQuizDifficulty] = useState<
    'basic' | 'intermediate' | 'advanced' | 'expert'
  >('basic');
  const [startingCourseQuiz, setStartingCourseQuiz] = useState(false);
  const topicPickerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showTopicPicker) return;
    const onPointerDown = (event: MouseEvent) => {
      if (topicPickerRef.current && !topicPickerRef.current.contains(event.target as Node)) {
        setShowTopicPicker(false);
      }
    };
    document.addEventListener('mousedown', onPointerDown);
    return () => document.removeEventListener('mousedown', onPointerDown);
  }, [showTopicPicker]);

  const quizTopicOptions = useMemo(() => {
    const all = coursePathTopics;
    if (!all.length) return { rated: [] as string[], other: [] as string[] };

    const ratedKeys = new Set<string>();
    if (userInterests?.domainScores) {
      Object.entries(userInterests.domainScores).forEach(([domain, score]) => {
        if (Number(score) > 0) ratedKeys.add(domain.trim().toLowerCase());
      });
    }
    if (effectivePrimary) {
      ratedKeys.add(normalizeRoadmapDomain(effectivePrimary).toLowerCase());
    }

    const rated: string[] = [];
    const other: string[] = [];
    const seen = new Set<string>();

    const push = (list: string[], topic: string) => {
      const key = topic.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      list.push(topic);
    };

    all.forEach((topic) => {
      if (ratedKeys.has(topic.toLowerCase())) {
        push(rated, topic);
      } else {
        push(other, topic);
      }
    });

    return { rated, other };
  }, [coursePathTopics, userInterests?.domainScores, effectivePrimary]);

  const loadCoursePathTopics = useCallback(() => {
    if (!user?.id || !hasCompletedOnboarding) return;
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
    }
  }, [user?.id, hasCompletedOnboarding, effectivePrimary]);

  useEffect(() => {
    if (!isAuthenticated || !user?.id) return;
    void loadCoursePathTopics();
  }, [isAuthenticated, user?.id, loadCoursePathTopics]);

  useEffect(() => {
    if (!isAuthenticated) return;
    void getUserPerformance()
      .then(setPerformance)
      .catch(() => setPerformance(null));
  }, [isAuthenticated]);

  const handleStartCourseTopicQuiz = () => {
    if (!hasCompletedOnboarding) {
      setError('Complete the interest assessment first before starting a quiz.');
      navigate('interest-check');
      return;
    }
    if (!selectedCourseTopic) {
      setError('Choose a topic before starting.');
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

  return (
    <div className="min-h-screen bg-slate-50 pt-24 pb-12">
      <div className="max-w-4xl mx-auto px-4">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Quiz Hub</h1>
            <p className="text-slate-600 text-sm mt-1">
              {hasCompletedOnboarding
                ? 'Pick a topic and difficulty — questions are built for you on the spot.'
                : 'Rate your interests to unlock personalized quizzes.'}
            </p>
          </div>
          {hasCompletedOnboarding && (
            <button
              type="button"
              onClick={() => navigate('interest-check')}
              className="text-sm text-indigo-600 hover:text-indigo-700 font-medium shrink-0"
            >
              Update interests
            </button>
          )}
        </div>

        {!hasCompletedOnboarding && (
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-amber-200 bg-amber-50 px-5 py-4">
            <div>
              <p className="font-semibold text-amber-900">Complete your interest profile</p>
              <p className="text-sm text-amber-800/90 mt-0.5">We use this to suggest topics and tune quiz difficulty.</p>
            </div>
            <button
              type="button"
              onClick={() => navigate('interest-check')}
              className="px-5 py-2.5 bg-amber-600 text-white rounded-xl font-semibold text-sm hover:bg-amber-700 shrink-0"
            >
              Rate interests
            </button>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700">
            {error}
          </div>
        )}

        {performance && performance.overallStats.totalQuizzes > 0 && (
          <div className="grid grid-cols-3 gap-3 mb-6">
            <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 text-center">
              <p className="text-2xl font-bold text-slate-900 tabular-nums">
                {performance.overallStats.totalQuizzes}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">Quizzes</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 text-center">
              <p className="text-2xl font-bold text-slate-900 tabular-nums">
                {performance.overallStats.averageScore}%
              </p>
              <p className="text-xs text-slate-500 mt-0.5">Average</p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 px-4 py-3 text-center">
              <p className="text-2xl font-bold text-slate-900 tabular-nums">
                {performance.overallStats.bestScore}%
              </p>
              <p className="text-xs text-slate-500 mt-0.5">Best</p>
            </div>
          </div>
        )}

        {hasCompletedOnboarding && effectivePrimary ? (
          <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl shadow-lg p-6 sm:p-8 mb-6 text-white">
            <div className="mb-6">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <span aria-hidden>📝</span>
                New quiz
              </h2>
              {userInterests && (
                <p className="text-sm text-indigo-100 mt-1">
                  Top interest: {getInterestDomainIcon(interestUi.primary)} {interestUi.primary}
                </p>
              )}
            </div>

            {coursePathError ? (
              <div className="rounded-xl border border-amber-300/50 bg-amber-500/20 px-4 py-3 text-sm text-amber-50">
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
              <p className="text-sm text-indigo-100">No topics available.</p>
            ) : (
              <div className="grid md:grid-cols-2 gap-6 items-start">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-indigo-200 mb-2">Topic</p>
                  <div ref={topicPickerRef} className="relative">
                    <button
                      type="button"
                      onClick={() => setShowTopicPicker((open) => !open)}
                      className="w-full flex items-center justify-between gap-3 rounded-xl bg-white/10 border border-white/25 px-4 py-3.5 hover:bg-white/15 transition-colors text-left"
                      aria-expanded={showTopicPicker}
                      aria-haspopup="listbox"
                    >
                      <span className="flex items-center gap-3 min-w-0">
                        <span className="text-2xl shrink-0" aria-hidden>
                          {getInterestDomainIcon(selectedCourseTopic ?? '')}
                        </span>
                        <span className="font-semibold truncate">{selectedCourseTopic}</span>
                      </span>
                      <ChevronDown
                        className={`w-5 h-5 shrink-0 text-indigo-100 transition-transform ${showTopicPicker ? 'rotate-180' : ''}`}
                        aria-hidden
                      />
                    </button>

                    {showTopicPicker && (
                      <div
                        className="absolute z-20 left-0 top-full mt-2 w-full rounded-xl bg-white shadow-2xl border border-slate-200 overflow-hidden"
                        role="listbox"
                        aria-label="Quiz topics"
                      >
                        <div className="max-h-56 overflow-y-auto py-1">
                          {quizTopicOptions.rated.length > 0 && (
                            <>
                              <p className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
                                Your interests
                              </p>
                              {quizTopicOptions.rated.map((topic) => {
                                const selected =
                                  selectedCourseTopic?.toLowerCase() === topic.toLowerCase();
                                return (
                                  <button
                                    key={topic}
                                    type="button"
                                    role="option"
                                    aria-selected={selected}
                                    onClick={() => {
                                      setSelectedCourseTopic(topic);
                                      setShowTopicPicker(false);
                                    }}
                                    className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left transition-colors ${
                                      selected
                                        ? 'bg-indigo-50 text-indigo-700 font-semibold'
                                        : 'text-slate-700 hover:bg-slate-50'
                                    }`}
                                  >
                                    <span className="text-base shrink-0" aria-hidden>
                                      {getInterestDomainIcon(topic)}
                                    </span>
                                    <span className="truncate flex-1">{topic}</span>
                                    {selected && <Check className="w-4 h-4 shrink-0 text-indigo-600" aria-hidden />}
                                  </button>
                                );
                              })}
                            </>
                          )}
                          {quizTopicOptions.other.length > 0 && (
                            <>
                              <p className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-400 border-t border-slate-100">
                                More topics
                              </p>
                              {quizTopicOptions.other.map((topic) => {
                                const selected =
                                  selectedCourseTopic?.toLowerCase() === topic.toLowerCase();
                                return (
                                  <button
                                    key={topic}
                                    type="button"
                                    role="option"
                                    aria-selected={selected}
                                    onClick={() => {
                                      setSelectedCourseTopic(topic);
                                      setShowTopicPicker(false);
                                    }}
                                    className={`w-full flex items-center gap-2.5 px-3 py-2 text-sm text-left transition-colors ${
                                      selected
                                        ? 'bg-indigo-50 text-indigo-700 font-semibold'
                                        : 'text-slate-700 hover:bg-slate-50'
                                    }`}
                                  >
                                    <span className="text-base shrink-0" aria-hidden>
                                      {getInterestDomainIcon(topic)}
                                    </span>
                                    <span className="truncate flex-1">{topic}</span>
                                    {selected && <Check className="w-4 h-4 shrink-0 text-indigo-600" aria-hidden />}
                                  </button>
                                );
                              })}
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-indigo-200 mb-2">Difficulty</p>
                  <div className="grid grid-cols-2 gap-2 mb-4">
                    {(['basic', 'intermediate', 'advanced', 'expert'] as const).map((level) => (
                      <button
                        key={level}
                        type="button"
                        onClick={() => setCourseQuizDifficulty(level)}
                        className={`px-3 py-2.5 rounded-xl border-2 text-sm font-semibold capitalize transition-colors ${
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
                    className="w-full px-8 py-3.5 bg-white text-indigo-700 rounded-xl font-semibold hover:bg-indigo-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {startingCourseQuiz ? 'Starting…' : 'Start Quiz'}
                  </button>
                </div>
              </div>
            )}
          </div>
        ) : null}

        {hasCompletedOnboarding && (
          <div className="grid sm:grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => navigate('/quizzes/recent')}
              className="flex items-center gap-3 bg-white rounded-xl border border-slate-200 p-4 hover:border-indigo-200 hover:shadow-sm transition-all text-left"
            >
              <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0">
                <History className="w-5 h-5 text-indigo-600" aria-hidden />
              </div>
              <div>
                <p className="font-semibold text-slate-900">Recent quizzes</p>
                <p className="text-xs text-slate-500">Scores and past attempts</p>
              </div>
            </button>
            <button
              type="button"
              onClick={() => navigate('/learning-path')}
              className="flex items-center gap-3 bg-white rounded-xl border border-slate-200 p-4 hover:border-indigo-200 hover:shadow-sm transition-all text-left"
            >
              <div className="w-10 h-10 rounded-lg bg-purple-100 flex items-center justify-center shrink-0">
                <Map className="w-5 h-5 text-purple-600" aria-hidden />
              </div>
              <div>
                <p className="font-semibold text-slate-900">Learning path</p>
                <p className="text-xs text-slate-500">Roadmap and milestones</p>
              </div>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default Quizzes;
