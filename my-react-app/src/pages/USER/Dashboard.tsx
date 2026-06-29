import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import { getUserPerformance, getQuizHistory, type UserPerformance, type QuizAttempt } from '../../services/quizService';
import { generateRoadmap, type RoadmapResponse } from '../../services/learningIntelligenceService';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import {
  buildRoadmapScoresPayload,
  getEffectivePrimaryInterest,
  getInterestAssessmentDisplay,
  getInterestDomainIcon,
  getPercentage,
  ratedDomainsFromScores,
} from '../../utils/interestDisplay';
import { hasCompletedDomainQuiz } from '../../utils/learningPathGate';
import { normalizeRoadmapDomain, buildRoadmapPhaseList } from '../../utils/roadmapTopics';
import LearningPathRoadmapPreview from '../../components/learning/LearningPathRoadmapPreview';

const LEARNING_PROGRESS_WEEKS = 8;

/** Plot layout in SVG user units (uniform scale via preserveAspectRatio meet — keeps circles round). */
const LP_CHART = {
  viewW: 100,
  viewH: 88,
  plotL: 14,
  plotR: 94,
  plotT: 10,
  plotB: 62,
  xLabelY: 72,
  yLabelX: 11,
} as const;

function lpPlotX(weekIndex: number, numWeeks: number): number {
  const { plotL, plotR } = LP_CHART;
  if (numWeeks <= 1) return (plotL + plotR) / 2;
  return plotL + (weekIndex / (numWeeks - 1)) * (plotR - plotL);
}

function lpPlotY(scorePercent: number): number {
  const { plotT, plotB } = LP_CHART;
  return plotT + ((100 - scorePercent) / 100) * (plotB - plotT);
}

function startOfWeekMonday(d: Date): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  const day = x.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  x.setDate(x.getDate() + diff);
  return x;
}

function attemptScorePercent(a: QuizAttempt): number {
  if (a.totalQuestions > 0) {
    return Math.round((a.correctCount / a.totalQuestions) * 100);
  }
  const s = Number(a.score);
  return Number.isFinite(s) ? Math.max(0, Math.min(100, Math.round(s))) : 0;
}

type WeeklyBucket = {
  weekStart: Date;
  label: string;
  average: number | null;
  attempts: number;
};

type WeeklyProgressModel = {
  buckets: WeeklyBucket[];
  lineSegments: { x: number; y: number; score: number }[][];
  trendDelta: number | null;
  trendLabel: 'improving' | 'declining' | 'steady' | 'insufficient';
  weekStreak: number;
  thisWeekAverage: number | null;
  improvementDisplay: string;
  hasLine: boolean;
  totalAttemptsInWindow: number;
};

function buildWeeklyProgress(attempts: QuizAttempt[], numWeeks: number): WeeklyProgressModel {
  const now = new Date();
  const currentWeekStart = startOfWeekMonday(now);
  const buckets: WeeklyBucket[] = [];
  for (let i = numWeeks - 1; i >= 0; i--) {
    const ws = new Date(currentWeekStart);
    ws.setDate(ws.getDate() - i * 7);
    const label = ws.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    buckets.push({ weekStart: ws, label, average: null, attempts: 0 });
  }

  const sums = buckets.map(() => ({ sum: 0, n: 0 }));
  for (const a of attempts) {
    const t = new Date(a.completedAt);
    if (Number.isNaN(t.getTime())) continue;
    const ws = startOfWeekMonday(t);
    const idx = buckets.findIndex((b) => b.weekStart.getTime() === ws.getTime());
    if (idx === -1) continue;
    sums[idx].sum += attemptScorePercent(a);
    sums[idx].n += 1;
    buckets[idx].attempts += 1;
  }
  buckets.forEach((b, i) => {
    if (sums[i].n > 0) b.average = Math.round(sums[i].sum / sums[i].n);
  });

  const lineSegments: { x: number; y: number; score: number }[][] = [];
  let cur: { x: number; y: number; score: number }[] = [];
  for (let i = 0; i < numWeeks; i++) {
    const avg = buckets[i].average;
    if (avg == null) {
      if (cur.length) {
        lineSegments.push(cur);
        cur = [];
      }
      continue;
    }
    cur.push({ x: lpPlotX(i, numWeeks), y: lpPlotY(avg), score: avg });
  }
  if (cur.length) lineSegments.push(cur);

  const nonNullIdx = buckets.map((b, i) => (b.average != null ? i : -1)).filter((i) => i >= 0);
  let trendDelta: number | null = null;
  if (nonNullIdx.length >= 2) {
    const first = nonNullIdx[0];
    const last = nonNullIdx[nonNullIdx.length - 1];
    trendDelta = (buckets[last].average ?? 0) - (buckets[first].average ?? 0);
  }

  let trendLabel: WeeklyProgressModel['trendLabel'] = 'insufficient';
  if (nonNullIdx.length >= 2 && trendDelta != null) {
    if (trendDelta > 2) trendLabel = 'improving';
    else if (trendDelta < -2) trendLabel = 'declining';
    else trendLabel = 'steady';
  }

  let weekStreak = 0;
  for (let i = numWeeks - 1; i >= 0; i--) {
    if (buckets[i].attempts > 0) weekStreak += 1;
    else break;
  }

  const thisWeekAverage = buckets[numWeeks - 1]?.average ?? null;
  const improvementDisplay =
    trendDelta == null ? '—' : `${trendDelta > 0 ? '+' : ''}${Math.round(trendDelta)}%`;

  const totalAttemptsInWindow = buckets.reduce((s, b) => s + b.attempts, 0);
  const hasLine = lineSegments.some((s) => s.length >= 2);

  return {
    buckets,
    lineSegments,
    trendDelta,
    trendLabel,
    weekStreak,
    thisWeekAverage,
    improvementDisplay,
    hasLine,
    totalAttemptsInWindow,
  };
}

function LearningProgressCard({
  weeklyProgress,
  chartUid,
}: {
  weeklyProgress: WeeklyProgressModel;
  chartUid: string;
}) {
  const {
    buckets,
    lineSegments,
    trendLabel,
    weekStreak,
    thisWeekAverage,
    improvementDisplay,
    totalAttemptsInWindow,
  } = weeklyProgress;

  const trendPill =
    trendLabel === 'improving'
      ? {
          text: 'Improving',
          className: 'bg-green-50 text-green-700',
          icon: (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
          ),
        }
        : trendLabel === 'declining'
        ? {
            text: 'Needs focus',
            className: 'bg-rose-50 text-rose-700',
            icon: (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
            ),
          }
        : null;

  const lineGradId = `lp-line-${chartUid}`;
  const areaGradId = `lp-area-${chartUid}`;
  const hasChartData = totalAttemptsInWindow > 0;
  const scoreChangeDisplay = hasChartData ? improvementDisplay : '—';
  const activeWeeksDisplay = hasChartData ? String(weekStreak) : '—';
  const thisWeekDisplay = hasChartData && thisWeekAverage != null ? `${thisWeekAverage}%` : '—';

  return (
    <>
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <span aria-hidden>📈</span>
          Quiz scores
        </h2>
        {trendPill && hasChartData && (
          <span className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium ${trendPill.className}`}>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {trendPill.icon}
            </svg>
            {trendPill.text}
          </span>
        )}
      </div>

      <div className="relative h-80 bg-slate-50 rounded-xl p-4 sm:p-6 border border-slate-200 flex items-center justify-center">
        {hasChartData ? (
        <svg
          className="w-full max-w-3xl h-72 sm:h-80"
          viewBox={`0 0 ${LP_CHART.viewW} ${LP_CHART.viewH}`}
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Weekly average quiz score chart"
        >
          <defs>
            <linearGradient id={lineGradId} x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#a855f7" />
            </linearGradient>
            <linearGradient id={areaGradId} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#6366f1" stopOpacity="0.28" />
              <stop offset="100%" stopColor="#a855f7" stopOpacity="0.06" />
            </linearGradient>
          </defs>

          {[100, 75, 50, 25, 0].map((g) => (
            <g key={g}>
              <line
                x1={LP_CHART.plotL}
                x2={LP_CHART.plotR}
                y1={lpPlotY(g)}
                y2={lpPlotY(g)}
                stroke="#e2e8f0"
                strokeWidth={0.35}
              />
              <text
                x={LP_CHART.yLabelX}
                y={lpPlotY(g)}
                textAnchor="end"
                dominantBaseline="middle"
                fill="#64748b"
                fontSize={3.4}
              >
                {g}%
              </text>
            </g>
          ))}

          {buckets.map((b, i) => (
            <text
              key={`xl-${b.weekStart.getTime()}`}
              x={lpPlotX(i, LEARNING_PROGRESS_WEEKS)}
              y={LP_CHART.xLabelY}
              textAnchor="middle"
              fill="#64748b"
              fontSize={3}
            >
              {b.label}
            </text>
          ))}

          {lineSegments.map((seg, si) => {
            if (!seg.length) return null;
            const bottom = LP_CHART.plotB;
            if (seg.length === 1) {
              const p = seg[0];
              return (
                <g key={si}>
                  <line
                    x1={p.x}
                    x2={p.x}
                    y1={p.y}
                    y2={bottom}
                    stroke="#c7d2fe"
                    strokeWidth={0.45}
                    strokeDasharray="1.2 1.2"
                  />
                  <circle cx={p.x} cy={p.y} r={3.2} fill="white" stroke="#6366f1" strokeWidth={1.1}>
                    <title>{`${p.score}% avg this week`}</title>
                  </circle>
                  <circle cx={p.x} cy={p.y} r={1.35} fill="#a855f7" opacity={0.9} />
                </g>
              );
            }
            const lineD = seg.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ');
            const areaD =
              seg.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ') +
              ` L ${seg[seg.length - 1].x} ${bottom} L ${seg[0].x} ${bottom} Z`;
            return (
              <g key={si}>
                <path d={areaD} fill={`url(#${areaGradId})`} />
                <path
                  d={lineD}
                  fill="none"
                  stroke={`url(#${lineGradId})`}
                  strokeWidth={1.35}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                {seg.map((p, pi) => (
                  <circle key={pi} cx={p.x} cy={p.y} r={2.8} fill="white" stroke="#6366f1" strokeWidth={1}>
                    <title>{`${p.score}%`}</title>
                  </circle>
                ))}
              </g>
            );
          })}
        </svg>
        ) : (
          <p className="text-sm text-slate-500 text-center px-4 flex items-center justify-center gap-2">
            <span aria-hidden>📝</span>
            Take a quiz to see your weekly scores here.
          </p>
        )}
      </div>

      <div className="mt-8 grid md:grid-cols-3 gap-4">
        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-4 border border-indigo-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                {weeklyProgress.trendLabel === 'declining' ? (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                ) : (
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                )}
              </svg>
            </div>
            <div className="min-w-0">
              <p
                className={`text-2xl font-bold tabular-nums ${
                  hasChartData && weeklyProgress.trendDelta != null && weeklyProgress.trendDelta < 0
                    ? 'text-rose-700'
                    : 'text-slate-900'
                }`}
              >
                {scoreChangeDisplay}
              </p>
              <p className="text-xs text-slate-600">Score change</p>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border border-green-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900 tabular-nums">{activeWeeksDisplay}</p>
              <p className="text-xs text-slate-600">Active weeks</p>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-4 border border-yellow-100">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-yellow-600 rounded-lg flex items-center justify-center shrink-0">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                />
              </svg>
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900 tabular-nums">{thisWeekDisplay}</p>
              <p className="text-xs text-slate-600">This week</p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

type QuickAction = {
  label: string;
  description: string;
  icon: string;
  to: string;
};

const Dashboard: React.FC = () => {
  const { isAuthenticated, user, hasCompletedOnboarding, userInterests } = useStore();
  const navigate = useNavigate();
  const [performance, setPerformance] = useState<UserPerformance | null>(null);
  const [history, setHistory] = useState<QuizAttempt[]>([]);
  const [pathIntel, setPathIntel] = useState<RoadmapResponse | null>(null);
  const [pathIntelLoading, setPathIntelLoading] = useState(false);
  const [loading, setLoading] = useState(true);

  const interestUi = useMemo(() => getInterestAssessmentDisplay(userInterests), [userInterests]);
  const primaryInterest = useMemo(() => getEffectivePrimaryInterest(userInterests), [userInterests]);
  const learningPathUnlocked = useMemo(
    () => hasCompletedDomainQuiz(performance, normalizeRoadmapDomain(primaryInterest)),
    [performance, primaryInterest],
  );

  const topInterestRows = useMemo(() => {
    if (!userInterests) return [];
    const primaryKey = (primaryInterest || '').trim().toLowerCase();
    const rated = ratedDomainsFromScores(userInterests.domainScores);
    const rows = rated.length
      ? rated.map((r) => ({
          domain: r.domain,
          pct: getPercentage(r.score),
        }))
      : userInterests.allInterests.map((i) => ({
          domain: i.domain,
          pct: getPercentage(i.confidence * 10),
        }));
    return rows.filter(
      (row) => row.pct > 0 && row.domain.trim().toLowerCase() !== primaryKey,
    );
  }, [userInterests, primaryInterest]);

  const domainScoresSignature = useMemo(
    () => JSON.stringify(userInterests?.domainScores ?? {}),
    [userInterests?.domainScores],
  );

  const loadData = useCallback(async () => {
    try {
      const [perf, hist] = await Promise.allSettled([
        getUserPerformance(),
        getQuizHistory(250),
      ]);
      if (perf.status === 'fulfilled') setPerformance(perf.value);
      if (hist.status === 'fulfilled') setHistory(hist.value);

      const perfData = perf.status === 'fulfilled' ? perf.value : null;

      if (hasCompletedOnboarding && userInterests) {
        const primary = getEffectivePrimaryInterest(userInterests);
        if (!primary) {
          setPathIntel(null);
        } else if (!hasCompletedDomainQuiz(perfData, normalizeRoadmapDomain(primary))) {
          setPathIntel(null);
        } else {
        setPathIntelLoading(true);
        try {
          const secondary = (userInterests.allInterests || [])
            .map((i) => i.domain)
            .filter(
              (d, idx, arr) =>
                Boolean(d) && d !== primary && arr.indexOf(d) === idx,
            )
            .slice(0, 5);
          const engagement = getInterestAssessmentDisplay(userInterests).confidenceRatio;
          const scoresPayload = buildRoadmapScoresPayload(userInterests.domainScores);
          const live = await generateRoadmap({
            domain: primary,
            primary_interest: primary,
            secondary_domains: secondary,
            user_id: user?.id,
            user: {
              weekly_availability_hours: 6,
              learning_style: 'mixed',
              known: userInterests.assessmentContext?.known || '',
              want: userInterests.assessmentContext?.want || '',
              goals: userInterests.assessmentContext?.goals || '',
              learning_goals: userInterests.assessmentContext?.goals || '',
              assessment_tags: userInterests.assessmentTags || [],
            },
            engagement_score: engagement,
            interest_strength: engagement,
            ...(scoresPayload ? { scores: scoresPayload } : {}),
          });
          setPathIntel(live);
        } catch (e: unknown) {
          setPathIntel(null);
          console.error('Could not load learning path preview:', e);
        } finally {
          setPathIntelLoading(false);
        }
        }
      }
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  }, [hasCompletedOnboarding, userInterests, domainScoresSignature, user?.id]);

  useEffect(() => {
    if (isAuthenticated && user) {
      void loadData();
    }
  }, [isAuthenticated, user, loadData]);

  const roadmapPhases = useMemo(
    () => buildRoadmapPhaseList((pathIntel?.roadmap as Record<string, unknown>) ?? null),
    [pathIntel?.roadmap],
  );

  const adaptiveState = useMemo(
    () =>
      (pathIntel?.roadmap as { adaptive_state?: Record<string, number | string> } | undefined)
        ?.adaptive_state,
    [pathIntel?.roadmap],
  );

  const weeklyProgress = useMemo(
    () => buildWeeklyProgress(history, LEARNING_PROGRESS_WEEKS),
    [history],
  );
  const learningChartUid = React.useId().replace(/:/g, '');

  const quickActions = useMemo<QuickAction[]>(
    () => [
      {
        label: 'Practice',
        description: 'Topic quizzes',
        icon: '📝',
        to: '/quizzes',
      },
      {
        label: 'Learning path',
        description: learningPathUnlocked ? 'Your roadmap' : 'Unlock with a quiz',
        icon: '🗺️',
        to: learningPathUnlocked ? '/learning-path' : '/quizzes',
      },
      {
        label: 'Notes',
        description: 'Study notes',
        icon: '📓',
        to: '/notes',
      },
      {
        label: 'AI assistant',
        description: 'Ask questions',
        icon: '💬',
        to: '/chat',
      },
    ],
    [learningPathUnlocked],
  );

  const statsSummary = useMemo(() => {
    const total = performance?.overallStats.totalQuizzes ?? 0;
    const avg = performance?.overallStats.averageScore ?? 0;
    const best = performance?.overallStats.bestScore ?? 0;
    const accuracy =
      performance && performance.overallStats.totalQuestions > 0
        ? Math.round(
            (performance.overallStats.totalCorrect / performance.overallStats.totalQuestions) * 100,
          )
        : null;
    return { total, avg, best, accuracy };
  }, [performance]);

  const hasQuizActivity = statsSummary.total > 0 || history.length > 0;

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: '/home' }} replace />;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12">
        <div className="max-w-7xl mx-auto px-4">
          {/* Header Skeleton */}
          <div className="mb-8 space-y-3">
            <div className="h-10 bg-slate-200 rounded-lg w-64 animate-pulse"></div>
            <div className="h-6 bg-slate-200 rounded-lg w-48 animate-pulse"></div>
          </div>

          {/* Onboarding Card Skeleton */}
          <LoadingSkeleton variant="card" className="mb-8" />

          {/* Quick Actions Skeleton */}
          <div className="grid md:grid-cols-3 gap-6 mb-8">
            <LoadingSkeleton variant="card" count={3} />
          </div>

          {/* Performance Skeleton */}
          <LoadingSkeleton variant="card" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12">
      <div className="max-w-7xl mx-auto px-4">
        {/* Welcome Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-slate-900">
            Welcome back, {user.firstName} <span className="inline-block" aria-hidden>👋</span>
          </h1>
          <p className="mt-2 text-slate-600 text-sm sm:text-base max-w-2xl">
            {hasCompletedOnboarding
              ? hasQuizActivity
                ? 'Here’s your progress and what to do next.'
                : 'Pick a topic below and take your first quiz to unlock scores and your learning path.'
              : 'Rate your interests first — we’ll tailor quizzes and your path to what you care about.'}
          </p>
        </div>

        {/* Quick actions */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {quickActions.map((action) => (
            <button
              key={action.label}
              type="button"
              onClick={() => navigate(action.to)}
              className="group text-left bg-white rounded-xl border border-slate-200 p-4 shadow-sm hover:border-indigo-200 hover:shadow-md hover:bg-indigo-50/40 transition-all"
            >
              <span className="text-2xl mb-3 block" aria-hidden>{action.icon}</span>
              <p className="font-semibold text-slate-900 group-hover:text-indigo-700">{action.label}</p>
              <p className="text-xs text-slate-500 mt-0.5">{action.description}</p>
            </button>
          ))}
        </div>

        {/* At-a-glance stats */}
        {hasCompletedOnboarding && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Quizzes</p>
              <p className="text-2xl font-bold text-slate-900 tabular-nums mt-1">
                {hasQuizActivity ? statsSummary.total : '—'}
              </p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Avg score</p>
              <p className="text-2xl font-bold text-slate-900 tabular-nums mt-1">
                {hasQuizActivity ? `${Math.round(statsSummary.avg)}%` : '—'}
              </p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Best score</p>
              <p className="text-2xl font-bold text-slate-900 tabular-nums mt-1">
                {hasQuizActivity ? `${Math.round(statsSummary.best)}%` : '—'}
              </p>
            </div>
            <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">Accuracy</p>
              <p className="text-2xl font-bold text-slate-900 tabular-nums mt-1">
                {statsSummary.accuracy != null ? `${statsSummary.accuracy}%` : '—'}
              </p>
            </div>
          </div>
        )}

        {/* Onboarding Flow - Interest Assessment */}
        {!hasCompletedOnboarding && (
          <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl shadow-xl p-8 mb-8 text-white">
            <div className="flex items-start gap-6">
              <div className="flex-shrink-0">
                <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-sm">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-bold mb-2 flex items-center gap-2">
                  <span aria-hidden>✨</span>
                  Get started
                </h2>
                <p className="text-indigo-100 mb-6">
                  Rate your interests so we can personalize your quizzes and learning path.
                </p>
                <button
                  onClick={() => navigate('/quizzes/interest-check')}
                  className="px-6 py-3 bg-white text-indigo-600 rounded-xl font-semibold hover:bg-indigo-50 transition-all shadow-lg flex items-center gap-2"
                >
                  <span aria-hidden>🎯</span>
                  Rate your interests
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Completed Onboarding - Show Interests */}
        {hasCompletedOnboarding && userInterests && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8 mb-8">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-6">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <span aria-hidden>🎯</span>
                Your interests
              </h2>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => navigate('/quizzes/interest-check')}
                  className="px-4 py-2 text-indigo-600 hover:bg-indigo-50 rounded-lg font-medium transition-colors text-sm flex items-center gap-1.5"
                >
                  <span aria-hidden>✏️</span>
                  Update
                </button>
                {learningPathUnlocked ? (
                  <button
                    onClick={() => navigate('/learning-path')}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium text-sm hover:bg-indigo-700 flex items-center gap-1.5"
                  >
                    <span aria-hidden>🗺️</span>
                    Learning path
                  </button>
                ) : (
                  <button
                    onClick={() => navigate('/quizzes')}
                    className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium text-sm hover:bg-indigo-700 flex items-center gap-1.5"
                  >
                    <span aria-hidden>📝</span>
                    Take a quiz
                  </button>
                )}
              </div>
            </div>

            <div className={topInterestRows.length > 0 ? 'grid md:grid-cols-2 gap-6' : ''}>
              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-100">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center text-2xl">
                    <span aria-hidden>{getInterestDomainIcon(interestUi.primary)}</span>
                  </div>
                  <div>
                    <p className="text-sm text-indigo-600 font-medium flex items-center gap-1">
                      <span aria-hidden>⭐</span>
                      Top pick
                    </p>
                    <h3 className="text-xl font-bold text-slate-900">{interestUi.primary}</h3>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-white rounded-full h-3 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-indigo-600 to-purple-600 h-full rounded-full transition-all"
                      style={{ width: `${interestUi.confidencePct}%` }}
                    />
                  </div>
                  <span className="text-sm font-semibold text-indigo-600">
                    {interestUi.confidencePct}%
                  </span>
                </div>
              </div>

              {topInterestRows.length > 0 && (
                <div className="bg-slate-50 rounded-xl p-6 border border-slate-200">
                  <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-1.5">
                    <span aria-hidden>📋</span>
                    Other ratings
                  </h3>
                  <div className="space-y-4">
                    {topInterestRows.map((row) => (
                      <div key={row.domain}>
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-slate-900 font-medium flex items-center gap-2">
                            <span className="text-lg" aria-hidden>{getInterestDomainIcon(row.domain)}</span>
                            {row.domain}
                          </span>
                          <span className="text-sm font-semibold text-slate-600 tabular-nums">{row.pct}%</span>
                        </div>
                        <div className="bg-white rounded-full h-2 overflow-hidden border border-slate-100">
                          <div
                            className="bg-indigo-400 h-full rounded-full transition-all"
                            style={{ width: `${row.pct}%` }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {hasCompletedOnboarding && userInterests && learningPathUnlocked && (
          <LearningPathRoadmapPreview
            primary={normalizeRoadmapDomain(primaryInterest || interestUi.primary)}
            phases={roadmapPhases}
            performance={performance}
            adaptiveState={adaptiveState}
            loading={pathIntelLoading}
            onOpenPath={() => navigate('/learning-path')}
          />
        )}

        {history.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8 mb-8">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <span aria-hidden>📝</span>
                Recent quizzes
              </h2>
              <button onClick={() => navigate('/quizzes/recent')} className="text-sm text-indigo-600 hover:underline font-medium">
                View all
              </button>
            </div>
            <div className="space-y-3">
              {history.slice(0, 3).map((attempt) => (
                <div key={attempt.id} className="flex items-center justify-between p-4 rounded-xl border border-slate-100 hover:border-indigo-200 hover:bg-indigo-50/30 transition-all">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold text-sm ${
                      attempt.score >= 80 ? 'bg-emerald-500' : attempt.score >= 60 ? 'bg-amber-500' : 'bg-rose-500'
                    }`}>
                      {attempt.score}%
                    </div>
                    <div>
                      <p className="font-semibold text-slate-900 flex items-center gap-2">
                        <span aria-hidden>{getInterestDomainIcon(attempt.interest)}</span>
                        {attempt.interest}
                      </p>
                      <p className="text-xs text-slate-500">{attempt.level} • {new Date(attempt.completedAt).toLocaleDateString()}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => navigate('/quizzes')}
                    className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
                  >
                    Continue
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Learning curve — real quiz history, last 8 calendar weeks (Mon-start) */}
        {hasCompletedOnboarding && hasQuizActivity && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8">
            <LearningProgressCard weeklyProgress={weeklyProgress} chartUid={learningChartUid} />
          </div>
        )}

        {/* First quiz prompt — compact when no activity yet */}
        {hasCompletedOnboarding && !hasQuizActivity && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8 mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center gap-6">
              <div className="flex-1">
                <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                  <span aria-hidden>🎯</span>
                  Ready for your first quiz?
                </h2>
                <p className="text-slate-600 mt-2 text-sm sm:text-base">
                  Start with{' '}
                  <span className="font-medium text-slate-800">{interestUi.primary}</span>
                  {primaryInterest ? '' : ' your top interest'} — scores, streaks, and your learning path unlock after you practice.
                </p>
              </div>
              <button
                type="button"
                onClick={() => navigate('/quizzes')}
                className="shrink-0 px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors shadow-sm"
              >
                Start quiz
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
