import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import { getUserPerformance, getQuizHistory, type UserPerformance, type QuizAttempt } from '../../services/quizService';
import { generateRoadmap, type RoadmapResponse } from '../../services/learningIntelligenceService';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import EmptyState from '../../components/EmptyState';
import {
  buildRoadmapScoresPayload,
  getEffectivePrimaryInterest,
  getInterestAssessmentDisplay,
  getInterestDomainIcon,
  getPercentage,
  ratedDomainsFromScores,
} from '../../utils/interestDisplay';
import { hasCompletedDomainQuiz } from '../../utils/learningPathGate';
import { computePathProgression, getDomainPerfSnapshot, resolveCurrentPhase } from '../../utils/learningPathProgress';
import { normalizeRoadmapDomain } from '../../utils/roadmapTopics';

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

const Dashboard: React.FC = () => {
  const { isAuthenticated, user, hasCompletedOnboarding, userInterests } = useStore();
  const navigate = useNavigate();
  const [performance, setPerformance] = useState<UserPerformance | null>(null);
  const [history, setHistory] = useState<QuizAttempt[]>([]);
  const [pathIntel, setPathIntel] = useState<RoadmapResponse | null>(null);
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

  const learningPathSteps = useMemo(() => {
    if (!learningPathUnlocked) return [];
    const r = pathIntel?.roadmap as
      | {
          basic?: { topics?: string[]; all_topics?: string[] };
          beginner?: { topics?: string[]; all_topics?: string[] };
          intermediate?: { topics?: string[]; all_topics?: string[] };
          advanced?: { topics?: string[]; all_topics?: string[] };
          expert?: { topics?: string[]; all_topics?: string[] };
          next_step?: { title?: string };
        }
      | undefined;
    if (r) {
      const steps: string[] = [];
      const bTopics = r.basic?.all_topics?.length ? r.basic.all_topics : r.basic?.topics ?? r.beginner?.all_topics ?? r.beginner?.topics;
      (bTopics || []).slice(0, 2).forEach((t) => steps.push(t));
      const ns = r.next_step?.title;
      if (ns) steps.push(ns);
      const iTopics = r.intermediate?.all_topics?.length ? r.intermediate.all_topics : r.intermediate?.topics;
      (iTopics || []).slice(0, 2).forEach((t) => steps.push(t));
      const out = steps.slice(0, 6);
      if (out.length) return out;
    }
    return [
      ...(userInterests?.allInterests?.slice(0, 2).map((i) => i.domain) || []),
      ...(performance?.analysis?.recommendations?.slice(0, 2) || []),
      ...(Object.keys(performance?.byInterest || {}).slice(0, 2) || []),
    ].slice(0, 6);
  }, [pathIntel, performance, userInterests, learningPathUnlocked]);

  const completedSteps = useMemo(() => {
    if (!learningPathSteps.length) return 0;
    const primary = normalizeRoadmapDomain(primaryInterest || '');
    const perf = getDomainPerfSnapshot(performance, primary);
    const adaptiveState = (
      pathIntel?.roadmap as { adaptive_state?: Record<string, number | string> } | undefined
    )?.adaptive_state;
    const totalPhases = Math.max(learningPathSteps.length, 1);
    const currentPhase = resolveCurrentPhase(totalPhases, perf, adaptiveState);
    const liveProgress = computePathProgression(totalPhases, currentPhase, perf);
    const fromLive = Math.round(liveProgress * learningPathSteps.length);
    const fromQuizzes = performance
      ? Math.min(Math.floor(performance.overallStats.totalQuizzes / 2), learningPathSteps.length)
      : 0;
    if (pathIntel?.roadmap || performance) {
      return Math.min(learningPathSteps.length, Math.max(fromLive, fromQuizzes));
    }
    return fromQuizzes;
  }, [learningPathSteps.length, pathIntel, performance, primaryInterest]);

  const weeklyProgress = useMemo(
    () => buildWeeklyProgress(history, LEARNING_PROGRESS_WEEKS),
    [history],
  );
  const learningChartUid = React.useId().replace(/:/g, '');

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
        </div>

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

        {hasCompletedOnboarding && userInterests && learningPathUnlocked && learningPathSteps.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8 mb-8">
            <div className="flex items-center justify-between mb-6 gap-3">
              <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                <span aria-hidden>🗺️</span>
                Learning path
              </h2>
              <button
                onClick={() => navigate('/learning-path')}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors shrink-0"
              >
                Open path
              </button>
            </div>
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              {learningPathSteps.map((step: string, i: number) => (
                <React.Fragment key={i}>
                  <div className={`flex-shrink-0 flex flex-col items-center gap-2`}>
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all ${
                      i < completedSteps
                        ? 'bg-emerald-500 border-emerald-500 text-white'
                        : i === completedSteps
                        ? 'bg-indigo-600 border-indigo-600 text-white ring-4 ring-indigo-100'
                        : 'bg-white border-slate-200 text-slate-400'
                    }`}>
                      {i < completedSteps ? '✓' : i + 1}
                    </div>
                    <span className={`text-xs font-medium text-center w-20 sm:w-24 ${i <= completedSteps ? 'text-slate-700' : 'text-slate-400'}`}>
                      {step}
                    </span>
                  </div>
                  {i < learningPathSteps.length - 1 && (
                    <div className={`flex-shrink-0 h-0.5 w-8 mt-[-16px] ${i < completedSteps ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                  )}
                </React.Fragment>
              ))}
            </div>
            <div className="mt-4 flex items-center gap-3">
              <div className="flex-1 bg-slate-100 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-indigo-500 to-emerald-500 h-2 rounded-full transition-all"
                  style={{ width: `${(completedSteps / Math.max(1, learningPathSteps.length)) * 100}%` }}
                />
              </div>
              <span className="text-sm font-semibold text-slate-700 flex items-center gap-1">
                <span aria-hidden>✅</span>
                {completedSteps}/{learningPathSteps.length} done
              </span>
            </div>
          </div>
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
        {hasCompletedOnboarding && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8">
            <LearningProgressCard weeklyProgress={weeklyProgress} chartUid={learningChartUid} />
          </div>
        )}

        {/* No Performance Yet */}
        {performance && performance.overallStats.totalQuizzes === 0 && hasCompletedOnboarding && (
          <EmptyState
            icon={
              <svg className="w-16 h-16 sm:w-20 sm:h-20 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            }
            title="No quizzes yet"
            description="Take a quiz to see your scores and progress."
            actionLabel="Browse quizzes 🎯"
            onAction={() => navigate('/quizzes')}
          />
        )}
      </div>
    </div>
  );
};

export default Dashboard;
