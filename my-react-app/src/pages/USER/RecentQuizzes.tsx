import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import {
  getQuizHistory,
  getQuizHistoryGraph,
  getUserPerformance,
  type QuizAttempt,
  type UserPerformance,
} from '../../services/quizService';
import { parseApiError } from '../../services/apiError';
import LoadingSkeleton from '../../components/LoadingSkeleton';

/** Percentage for charts/list when API omits `score` but sends correct/total counts. */
function attemptPercentScore(a: QuizAttempt): number {
  if (a.totalQuestions > 0) {
    return Math.max(0, Math.min(100, Math.round((a.correctCount / a.totalQuestions) * 100)));
  }
  const n = Number(a.score);
  if (Number.isFinite(n)) {
    return Math.max(0, Math.min(100, Math.round(n)));
  }
  return 0;
}

function mergeAttemptsById(lists: QuizAttempt[][]): QuizAttempt[] {
  const byId = new Map<string, QuizAttempt>();
  for (const list of lists) {
    for (const row of list) {
      const id = String(row.id);
      const prev = byId.get(id);
      if (!prev) {
        byId.set(id, row);
        continue;
      }
      byId.set(id, {
        ...prev,
        ...row,
        correctCount: row.correctCount ?? prev.correctCount,
        totalQuestions: row.totalQuestions ?? prev.totalQuestions,
        score: row.score ?? prev.score,
        interest: row.interest || prev.interest,
        completedAt: (() => {
          const a = prev.completedAt;
          const b = row.completedAt;
          const ta = a ? new Date(a).getTime() : NaN;
          const tb = b ? new Date(b).getTime() : NaN;
          const valid = (x: number) => Number.isFinite(x) && x > 0;
          if (valid(tb) && (!valid(ta) || tb >= ta)) return b;
          if (valid(ta)) return a;
          return b || a;
        })(),
      });
    }
  }
  return Array.from(byId.values());
}

/** Avoid showing Unix epoch when API sent null/invalid (was `new Date(null)` → 1969 in US zones). */
function formatAttemptDateTime(iso: string | null | undefined): string {
  if (iso == null || String(iso).trim() === '') return '—';
  const t = new Date(iso).getTime();
  if (!Number.isFinite(t) || t <= 0) return '—';
  return new Date(iso).toLocaleString();
}

function topicCategory(interest: string): string {
  const i = (interest || '').toLowerCase();
  if (/sport|physical|fitness|coach/.test(i)) return 'Sports & wellness';
  if (/design|ui|ux|figma/.test(i)) return 'Design';
  if (/aptitude|reasoning|verbal|numerical/.test(i)) return 'Aptitude';
  if (/data|analy|ml|ai|science/.test(i)) return 'Data & AI';
  if (/security|cyber/.test(i)) return 'Security';
  return 'Technical';
}

const MAX_QUIZ_INSIGHT_ROWS = 50;
/** Poll interval (ms) — keeps behaviour coach in sync with new attempts. */
const LIVE_REFRESH_MS = 2500;

function normalizeTopicKey(interest: string | undefined): string {
  return (interest || 'General').trim().toLowerCase() || 'general';
}

/** Map score % to a 1–5 “signal” for display (not user input). */
function scoreToImpliedRating(scorePct: number): number {
  if (scorePct >= 88) return 5;
  if (scorePct >= 72) return 4;
  if (scorePct >= 55) return 3;
  if (scorePct >= 38) return 2;
  return 1;
}

function scoreRecommendation(scorePct: number, topic: string, level: string): string {
  const cleanTopic = (topic || 'this topic').trim() || 'this topic';
  const cleanLevel = (level || 'current level').trim() || 'current level';

  if (scorePct >= 95) {
    return `Outstanding (${scorePct}%). Move to harder ${cleanTopic} challenges and timed problem-solving drills.`;
  }
  if (scorePct >= 85) {
    return `Great work (${scorePct}%). Attempt one higher-difficulty ${cleanTopic} quiz and review only missed concepts.`;
  }
  if (scorePct >= 75) {
    return `Strong progress (${scorePct}%). Repeat ${cleanLevel} once, then step up difficulty in ${cleanTopic}.`;
  }
  if (scorePct >= 65) {
    return `Good base (${scorePct}%). Revisit weak questions and practice 2 focused exercises in ${cleanTopic}.`;
  }
  if (scorePct >= 50) {
    return `Developing (${scorePct}%). Stay at ${cleanLevel}, revise fundamentals, then retake a short quiz.`;
  }
  if (scorePct >= 35) {
    return `Needs reinforcement (${scorePct}%). Move one level easier and practice core ${cleanTopic} concepts first.`;
  }
  return `Critical support needed (${scorePct}%). Restart with beginner ${cleanTopic} practice and guided examples.`;
}

interface AttemptBehaviorCtx {
  /** Same topic, a more recently completed attempt (newer row above this one). */
  newerSameTopicScore: number | null;
  /** Same topic, next older attempt in history within this window. */
  olderSameTopicScore: number | null;
  /** Minutes between this attempt and the next older same-topic attempt (if any). */
  minutesSinceOlderSameTopic: number | null;
}

/** `rows` must be newest-first (same as recentForInsights). */
function buildAttemptBehaviorCtx(rows: QuizAttempt[], index: number): AttemptBehaviorCtx {
  const cur = rows[index];
  const key = normalizeTopicKey(cur.interest);
  let newerSameTopicScore: number | null = null;
  for (let j = index - 1; j >= 0; j--) {
    if (normalizeTopicKey(rows[j].interest) === key) {
      newerSameTopicScore = attemptPercentScore(rows[j]);
      break;
    }
  }
  let olderSameTopicScore: number | null = null;
  let olderRow: QuizAttempt | null = null;
  for (let j = index + 1; j < rows.length; j++) {
    if (normalizeTopicKey(rows[j].interest) === key) {
      olderSameTopicScore = attemptPercentScore(rows[j]);
      olderRow = rows[j];
      break;
    }
  }
  let minutesSinceOlderSameTopic: number | null = null;
  if (olderRow?.completedAt && cur.completedAt) {
    const t0 = new Date(cur.completedAt).getTime();
    const t1 = new Date(olderRow.completedAt).getTime();
    if (Number.isFinite(t0) && Number.isFinite(t1) && t0 > t1) {
      minutesSinceOlderSameTopic = Math.round((t0 - t1) / 60000);
    }
  }
  return { newerSameTopicScore, olderSameTopicScore, minutesSinceOlderSameTopic };
}

function behaviorFeedbackLines(
  attempt: QuizAttempt,
  scorePct: number,
  ctx: AttemptBehaviorCtx,
): string[] {
  const topic = (attempt.interest || 'This quiz').trim() || 'This quiz';
  const level = attempt.level || 'your level';
  const lines: string[] = [];

  if (ctx.newerSameTopicScore != null) {
    const d = scorePct - ctx.newerSameTopicScore;
    if (d >= 10) {
      lines.push(`Up ${d}% vs your last quiz on this topic—momentum is building.`);
    } else if (d <= -10) {
      lines.push(`Down ${Math.abs(d)}% vs your last quiz on this topic—open Results and note recurring misses.`);
    } else {
      lines.push(
        `Within ${Math.abs(d) < 5 ? 'a tight' : 'a'} band vs your last same-topic quiz (${ctx.newerSameTopicScore}% → ${scorePct}%).`,
      );
    }
  } else if (ctx.olderSameTopicScore != null) {
    const d = scorePct - ctx.olderSameTopicScore;
    if (Math.abs(d) >= 8) {
      lines.push(
        d >= 0
          ? `Up ${d}% vs your earlier quiz on this topic in this window.`
          : `Down ${Math.abs(d)}% vs your earlier quiz on this topic in this window.`,
      );
    }
  }

  if (ctx.olderSameTopicScore != null && ctx.minutesSinceOlderSameTopic != null) {
    if (ctx.minutesSinceOlderSameTopic <= 90) {
      lines.push(
        `Same topic again after ~${ctx.minutesSinceOlderSameTopic} min—short spacing can help lock in skills if you mix in review.`,
      );
    } else if (ctx.minutesSinceOlderSameTopic >= 1440) {
      lines.push(
        `It's been ~${Math.round(ctx.minutesSinceOlderSameTopic / 1440)} day(s) since your prior quiz on this topic—good spacing for retention.`,
      );
    }
  }

  if (scorePct >= 85) {
    lines.push(`Strong performance on ${topic} at ${level}.`);
    lines.push('Next step: add one harder quiz or a new subtopic so skills stay sharp.');
  } else if (scorePct >= 65) {
    lines.push(`Solid work on ${topic} (${level}).`);
    lines.push('Review missed items in Results, then run a similar quiz to reinforce weak spots.');
  } else if (scorePct >= 45) {
    lines.push(`You're building familiarity with ${topic} at ${level}.`);
    lines.push('Spend a bit more time on core concepts before moving up in difficulty.');
  } else {
    lines.push(`${topic} was challenging this round—that's useful signal.`);
    lines.push('Try a short review or one easier quiz until scores stabilize, then return to this level.');
  }
  if (attempt.quizType) {
    lines.push(`Format: ${String(attempt.quizType).replace(/_/g, ' ')}.`);
  }
  return lines;
}

function AutoQuizInsightCard({
  attempt,
  scorePct,
  ctx,
}: {
  attempt: QuizAttempt;
  scorePct: number;
  ctx: AttemptBehaviorCtx;
}) {
  const implied = scoreToImpliedRating(scorePct);
  const lines = behaviorFeedbackLines(attempt, scorePct, ctx);
  const recommendation = scoreRecommendation(scorePct, attempt.interest || 'this topic', attempt.level || 'current level');
  return (
    <div className="mt-3 space-y-2 rounded-lg border border-indigo-100 bg-indigo-50/40 px-3 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-indigo-800">Live behaviour insight</span>
        <span className="text-xs text-slate-600">(updates with your recent pattern)</span>
        <div className="flex gap-0.5" aria-hidden title={`Implied strength from score: ${implied} of 5`}>
          {[1, 2, 3, 4, 5].map((r) => (
            <span key={r} className={`text-base leading-none ${r <= implied ? 'text-amber-500' : 'text-slate-300'}`}>
              ★
            </span>
          ))}
        </div>
      </div>
      <div className="rounded-md border border-blue-200 bg-blue-50 px-3 py-2 text-sm text-blue-900">
        <span className="font-semibold">Score recommendation:</span> {recommendation}
      </div>
      <ul className="list-disc list-inside space-y-1 text-sm text-slate-700">
        {lines.map((line, i) => (
          <li key={i}>{line}</li>
        ))}
      </ul>
    </div>
  );
}

const RecentQuizzes: React.FC = () => {
  const { isAuthenticated, user, logout } = useStore();
  const navigate = useNavigate();
  const [attempts, setAttempts] = useState<QuizAttempt[]>([]);
  const [performance, setPerformance] = useState<UserPerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<Date | null>(null);
  const [liveRefreshing, setLiveRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [topicFilter, setTopicFilter] = useState('all');
  const mountedRef = useRef(true);

  const load = useCallback(
    async (background = false) => {
      if (background) setLiveRefreshing(true);
      try {
        setError(null);
        const [histRes, graphRes, perfRes] = await Promise.allSettled([
          getQuizHistory(120),
          getQuizHistoryGraph(0),
          getUserPerformance(),
        ]);

        const fromHist = histRes.status === 'fulfilled' ? histRes.value : [];
        const fromGraph = graphRes.status === 'fulfilled' ? graphRes.value : [];

        if (histRes.status === 'rejected' && graphRes.status === 'rejected') {
          throw histRes.reason;
        }

        const rows = mergeAttemptsById([fromHist, fromGraph]);
        if (mountedRef.current) {
          setAttempts(rows);
          setLastUpdatedAt(new Date());
          if (perfRes.status === 'fulfilled') {
            setPerformance(perfRes.value);
          } else if (perfRes.status === 'rejected') {
            setPerformance(null);
            const pp = parseApiError(perfRes.reason, 'Could not load performance.');
            if (
              pp.status === 401 ||
              (pp.code &&
                ['INVALID_TOKEN', 'INVALID_HEADER', 'TOKEN_EXPIRED', 'INVALID_TOKEN_CONTEXT', 'NO_TOKEN'].includes(pp.code))
            ) {
              await logout().catch(() => undefined);
              navigate('/login', { replace: true, state: { from: '/quizzes/recent', message: pp.message } });
              return;
            }
          }
        }
      } catch (e: unknown) {
        const p = parseApiError(e, 'Could not load quiz history.');
        if (p.status === 401) {
          await logout().catch(() => undefined);
          navigate('/login', { replace: true, state: { from: '/quizzes/recent', message: p.message } });
          return;
        }
        if (mountedRef.current) setError(p.message);
      } finally {
        if (mountedRef.current) {
          setLoading(false);
          if (background) setLiveRefreshing(false);
        }
      }
    },
    [logout, navigate],
  );

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (isAuthenticated && user) void load(false);
  }, [isAuthenticated, user, load]);

  useEffect(() => {
    if (!isAuthenticated || !user) return;
    const id = window.setInterval(() => {
      void load(true);
    }, LIVE_REFRESH_MS);
    return () => window.clearInterval(id);
  }, [isAuthenticated, user, load]);

  useEffect(() => {
    if (!isAuthenticated || !user) return;
    const onFocus = () => void load(true);
    const onVis = () => {
      if (document.visibilityState === 'visible') void load(true);
    };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVis);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, [isAuthenticated, user, load]);

  const recentAttemptsOldestFirst = useMemo(
    () =>
      [...attempts].sort((a, b) => new Date(a.completedAt).getTime() - new Date(b.completedAt).getTime()),
    [attempts],
  );

  const sortedNewestFirst = useMemo(
    () => [...attempts].sort((a, b) => new Date(b.completedAt).getTime() - new Date(a.completedAt).getTime()),
    [attempts],
  );

  const availableTopicOptions = useMemo(() => {
    const set = new Set<string>();
    for (const a of sortedNewestFirst) {
      const topic = (a.interest || 'General').trim() || 'General';
      set.add(topic);
    }
    return ['all', ...Array.from(set).sort((a, b) => a.localeCompare(b))];
  }, [sortedNewestFirst]);

  const filteredNewestFirst = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return sortedNewestFirst.filter((a) => {
      const topic = (a.interest || 'General').trim() || 'General';
      if (topicFilter !== 'all' && topic !== topicFilter) return false;
      if (!q) return true;
      const hay = [
        topic,
        a.level || '',
        a.quizType || '',
        String(Math.round(attemptPercentScore(a))),
      ]
        .join(' ')
        .toLowerCase();
      return hay.includes(q);
    });
  }, [sortedNewestFirst, searchQuery, topicFilter]);

  const recentForInsights = useMemo(
    () => filteredNewestFirst.slice(0, MAX_QUIZ_INSIGHT_ROWS),
    [filteredNewestFirst],
  );

  const recentAttemptsSummary = useMemo(() => {
    const rows = recentForInsights;
    if (rows.length === 0) return null;
    const scores = rows.map(attemptPercentScore);
    const avg = Math.round(scores.reduce((s, x) => s + x, 0) / scores.length);
    const newest = scores[0];
    const oldestInBatch = scores[scores.length - 1];
    let trend: string;
    if (rows.length >= 4) {
      const half = Math.max(1, Math.floor(scores.length / 2));
      const recentAvg = scores.slice(0, half).reduce((s, x) => s + x, 0) / half;
      const olderSlice = scores.slice(half);
      const olderAvg = olderSlice.reduce((s, x) => s + x, 0) / Math.max(1, olderSlice.length);
      if (recentAvg > olderAvg + 5) {
        trend = 'Your latest attempts are scoring higher than earlier ones in this window.';
      } else if (recentAvg < olderAvg - 5) {
        trend =
          'Your newest attempts are a bit lower than older ones in this window—a good time for a short review.';
      } else {
        trend = 'Scores in this window are fairly consistent from attempt to attempt.';
      }
    } else if (newest >= oldestInBatch) {
      trend = 'Your most recent score is at or above the oldest attempt in this list.';
    } else {
      trend = 'Your most recent score is below the oldest in this list—consider revisiting that topic.';
    }
    const weakTopics = rows
      .map((r) => ({
        interest: (r.interest || 'General').trim() || 'General',
        score: attemptPercentScore(r),
      }))
      .filter((x) => x.score < 60)
      .slice(0, 4);
    return { avg, trend, count: rows.length, newest, weakTopics };
  }, [recentForInsights]);

  /** Top-of-section lines: merges live window stats + server performance analysis. */
  const realtimeBehaviorCoach = useMemo(() => {
    const lines: string[] = [];
    const latest = recentForInsights[0];
    if (latest) {
      const s = attemptPercentScore(latest);
      lines.push(
        `Latest activity: ${(latest.interest || 'Quiz').trim() || 'Quiz'} · ${s}% · ${formatAttemptDateTime(latest.completedAt)}.`,
      );
    }
    if (recentAttemptsSummary) {
      lines.push(
        `Window average ${recentAttemptsSummary.avg}% across ${recentAttemptsSummary.count} attempt${recentAttemptsSummary.count === 1 ? '' : 's'} — ${recentAttemptsSummary.trend}`,
      );
    }
    const recs = performance?.analysis?.recommendations?.filter((r) => String(r).trim()) || [];
    for (const r of recs.slice(0, 2)) {
      lines.push(String(r));
    }
    const strengths = performance?.analysis?.strengths?.slice(0, 2) || [];
    for (const st of strengths) {
      if (st?.interest) {
        lines.push(`Strength signal: ${st.interest} (avg ${Math.round(st.score)}% over ${st.quizzes} quiz(es)).`);
      }
    }
    const weaknesses = performance?.analysis?.weaknesses?.slice(0, 1) || [];
    for (const w of weaknesses) {
      if (w?.interest) {
        lines.push(`Watch area: ${w.interest} (avg ${Math.round(w.score)}%) — add one focused retry quiz.`);
      }
    }
    return lines.slice(0, 6);
  }, [recentForInsights, recentAttemptsSummary, performance]);

  const groupedAverages = useMemo(
    () =>
      Object.entries(performance?.byInterest || {}).map(([interest, stats]) => ({
        interest,
        averageScore: stats.averageScore,
        totalQuizzes: stats.totalQuizzes,
      })),
    [performance],
  );

  const performanceInsightSummary = useMemo(() => {
    const strengths = performance?.analysis?.strengths || [];
    const weaknesses = performance?.analysis?.weaknesses || [];
    const recommendations = performance?.analysis?.recommendations || [];
    const codingSuggestions = performance?.analysis?.codingSuggestions || [];
    const improvementTopics = performance?.analysis?.improvementTopics || [];

    let trendLabel = 'Stable';
    let trendText = 'No strong performance shift detected yet.';
    if (recentAttemptsSummary) {
      const trendRaw = (recentAttemptsSummary.trend || '').toLowerCase();
      if (trendRaw.includes('higher') || trendRaw.includes('at or above') || trendRaw.includes('consistent')) {
        trendLabel = trendRaw.includes('consistent') ? 'Stable' : 'Improving';
        trendText = recentAttemptsSummary.trend;
      } else if (trendRaw.includes('lower') || trendRaw.includes('below') || trendRaw.includes('dipped')) {
        trendLabel = 'Declining';
        trendText = recentAttemptsSummary.trend;
      } else {
        trendText = recentAttemptsSummary.trend;
      }
    }

    return {
      strengths,
      weaknesses,
      recommendations,
      codingSuggestions,
      improvementTopics,
      trendLabel,
      trendText,
    };
  }, [performance, recentAttemptsSummary]);

  const averagesByCategory = useMemo(() => {
    const m = new Map<string, { sum: number; w: number; n: number }>();
    for (const row of groupedAverages) {
      const cat = topicCategory(row.interest);
      if (!m.has(cat)) m.set(cat, { sum: 0, w: 0, n: 0 });
      const g = m.get(cat)!;
      const weight = Math.max(1, row.totalQuizzes);
      g.sum += row.averageScore * weight;
      g.w += weight;
      g.n += row.totalQuizzes;
    }
    return Array.from(m.entries()).map(([category, v]) => ({
      category,
      avg: v.w ? Math.round(v.sum / v.w) : 0,
      quizzes: v.n,
    }));
  }, [groupedAverages]);

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: '/quizzes/recent' }} replace />;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 pt-24 pb-12">
        <div className="max-w-6xl mx-auto px-4">
          <LoadingSkeleton variant="card" className="mb-4" />
          <LoadingSkeleton variant="card" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 pt-24 pb-12">
      <div className="max-w-6xl mx-auto px-4">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Recent quizzes</h1>
            <p className="text-slate-600 text-sm mt-1">
              All attempts as a live score graph (oldest → newest). Refreshes about every {LIVE_REFRESH_MS / 1000}s and when
              you return to this tab.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/quizzes"
              className="px-4 py-2 rounded-xl border border-slate-200 bg-white text-slate-800 text-sm font-medium hover:bg-slate-50"
            >
              ← Quiz hub
            </Link>
            <Link
              to="/dashboard"
              className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700"
            >
              Dashboard
            </Link>
            <Link
              to="/feedback"
              className="px-4 py-2 rounded-xl border border-slate-200 bg-white text-slate-800 text-sm font-medium hover:bg-slate-50"
            >
              General feedback
            </Link>
          </div>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-sm">{error}</div>
        )}

        {recentAttemptsOldestFirst.length > 0 ? (
          <div className="mb-6 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
              <h2 className="text-xl font-bold text-slate-900">All recent quizzes — graph</h2>
              <div className="text-right">
                <div className="text-xs text-slate-500">{recentAttemptsOldestFirst.length} stored attempts</div>
                <div className="text-[11px] text-emerald-600 flex items-center justify-end gap-1.5">
                  <span
                    className={`inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 ${liveRefreshing ? 'animate-pulse' : ''}`}
                    aria-hidden
                  />
                  <span>
                    Real-time
                    {liveRefreshing ? ' • updating…' : lastUpdatedAt ? ` • updated ${lastUpdatedAt.toLocaleTimeString()}` : ''}
                  </span>
                </div>
              </div>
            </div>
            <div className="border border-slate-100 rounded-xl px-3 py-3 bg-slate-50/50 overflow-x-auto">
              <div
                className="h-48 flex items-end gap-2"
                style={{ minWidth: `${Math.max(520, recentAttemptsOldestFirst.length * 28)}px` }}
              >
                {recentAttemptsOldestFirst.map((attempt, idx) => {
                  const score = attemptPercentScore(attempt);
                  const barClass =
                    score >= 80
                      ? 'bg-gradient-to-t from-emerald-500 to-emerald-400'
                      : score >= 60
                        ? 'bg-gradient-to-t from-amber-500 to-amber-400'
                        : 'bg-gradient-to-t from-rose-500 to-rose-400';
                  return (
                    <div key={`recent-graph-${attempt.id}`} className="w-6 h-full flex-shrink-0 flex flex-col items-center">
                      <span className="text-[10px] text-slate-500 mb-1">{Math.round(score)}</span>
                      <div className="w-full flex-1 flex items-end">
                        <div
                          className={`w-full rounded-t-md ${barClass}`}
                          style={{ height: `${Math.max(8, score)}%` }}
                          title={`#${idx + 1} • ${attempt.interest || 'General'} • ${score}% • ${formatAttemptDateTime(attempt.completedAt)}`}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <p className="mt-2 text-xs text-slate-500">
              Each bar is one attempt; height is score %. Hover for topic and date. Scroll horizontally for long history.
            </p>
          </div>
        ) : (
          !error && (
            <div className="mb-6 rounded-2xl border border-dashed border-slate-200 bg-white p-10 text-center text-slate-600 text-sm">
              No attempts yet. Complete a quiz from the quiz hub to see your graph here.
            </div>
          )
        )}

        {sortedNewestFirst.length > 0 && (
          <div className="mb-6 bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
              <div>
                <h2 className="text-xl font-bold text-slate-900">Insights on recent quizzes</h2>
                <p className="text-sm text-slate-600 mt-1">
                  Live coaching from your last {recentForInsights.length} attempt
                  {recentForInsights.length === 1 ? '' : 's'} (up to {MAX_QUIZ_INSIGHT_ROWS}), same-topic momentum, and
                  server-side performance hints. Updates when new attempts sync (~{LIVE_REFRESH_MS / 1000}s).
                </p>
              </div>
              <Link
                to="/feedback"
                className="text-sm font-medium text-indigo-600 hover:text-indigo-800 whitespace-nowrap shrink-0"
              >
                Send general feedback →
              </Link>
            </div>

            <div className="mb-4 grid md:grid-cols-3 gap-3">
              <div className="md:col-span-2">
                <label htmlFor="recent-quiz-search" className="block text-xs font-semibold text-slate-600 mb-1">
                  Search quizzes / topics
                </label>
                <input
                  id="recent-quiz-search"
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by topic, level, quiz type, score..."
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div>
                <label htmlFor="recent-topic-filter" className="block text-xs font-semibold text-slate-600 mb-1">
                  Topic filter
                </label>
                <select
                  id="recent-topic-filter"
                  value={topicFilter}
                  onChange={(e) => setTopicFilter(e.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  {availableTopicOptions.map((topic) => (
                    <option key={topic} value={topic}>
                      {topic === 'all' ? 'All topics' : topic}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {filteredNewestFirst.length === 0 && (
              <div className="mb-4 rounded-xl border border-dashed border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                No quizzes match this search/filter.
              </div>
            )}

            {realtimeBehaviorCoach.length > 0 && (
              <div className="mb-5 rounded-xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-teal-50/80 px-4 py-3">
                <p className="text-xs font-bold uppercase tracking-wide text-emerald-800 flex flex-wrap items-center gap-2">
                  Real-time behaviour coach
                  {lastUpdatedAt && (
                    <span className="font-normal text-emerald-700/90 normal-case">
                      · data {liveRefreshing ? 'refreshing' : 'as of'} {lastUpdatedAt.toLocaleTimeString()}
                    </span>
                  )}
                </p>
                <ul className="mt-2 space-y-1.5 text-sm text-emerald-950/90 list-disc list-inside">
                  {realtimeBehaviorCoach.map((line, idx) => (
                    <li key={idx}>{line}</li>
                  ))}
                </ul>
              </div>
            )}

            {recentAttemptsSummary && (
              <div className="mb-5 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                <p className="font-semibold text-slate-900">Overall (this window)</p>
                <p className="mt-1">
                  Average score <span className="font-bold text-indigo-700">{recentAttemptsSummary.avg}%</span> across{' '}
                  {recentAttemptsSummary.count} attempt{recentAttemptsSummary.count === 1 ? '' : 's'}. Latest:{' '}
                  <span className="font-semibold tabular-nums">{recentAttemptsSummary.newest}%</span>.
                </p>
                <p className="mt-2 text-slate-600">{recentAttemptsSummary.trend}</p>
                {recentAttemptsSummary.weakTopics.length > 0 && (
                  <p className="mt-2 text-slate-600">
                    Topics under 60% in this list:{' '}
                    {Array.from(new Set(recentAttemptsSummary.weakTopics.map((w) => w.interest))).join(', ')}.
                  </p>
                )}
              </div>
            )}

            <div className="mb-5 grid md:grid-cols-3 gap-3">
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                <p className="text-xs font-bold uppercase tracking-wide text-emerald-800">Strengths</p>
                {performanceInsightSummary.strengths.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-sm text-emerald-900">
                    {performanceInsightSummary.strengths.slice(0, 3).map((s) => (
                      <li key={`strength-${s.interest}`}>
                        {s.interest} - {Math.round(s.score)}% ({s.quizzes} quiz{s.quizzes === 1 ? '' : 'zes'})
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-emerald-900/80">Complete more quizzes to detect strong topics.</p>
                )}
              </div>

              <div className="rounded-xl border border-rose-200 bg-rose-50 p-4">
                <p className="text-xs font-bold uppercase tracking-wide text-rose-800">Weak Areas</p>
                {performanceInsightSummary.weaknesses.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-sm text-rose-900">
                    {performanceInsightSummary.weaknesses.slice(0, 3).map((w) => (
                      <li key={`weak-${w.interest}`}>
                        {w.interest} - {Math.round(w.score)}% ({w.quizzes} quiz{w.quizzes === 1 ? '' : 'zes'})
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-sm text-rose-900/80">No major weak area detected right now.</p>
                )}
              </div>

              <div className="rounded-xl border border-indigo-200 bg-indigo-50 p-4">
                <p className="text-xs font-bold uppercase tracking-wide text-indigo-800">Progress Trend</p>
                <p className="mt-2 text-sm font-semibold text-indigo-900">{performanceInsightSummary.trendLabel}</p>
                <p className="mt-1 text-sm text-indigo-900/90">{performanceInsightSummary.trendText}</p>
              </div>
            </div>

            {performanceInsightSummary.recommendations.length > 0 && (
              <div className="mb-5 rounded-xl border border-blue-200 bg-blue-50 p-4">
                <p className="text-xs font-bold uppercase tracking-wide text-blue-800">Improvement Suggestions</p>
                <ul className="mt-2 list-disc list-inside space-y-1 text-sm text-blue-900">
                  {performanceInsightSummary.recommendations.slice(0, 5).map((r, idx) => (
                    <li key={`perf-rec-${idx}`}>{r}</li>
                  ))}
                </ul>
              </div>
            )}

            {(performanceInsightSummary.codingSuggestions.length > 0 ||
              performanceInsightSummary.improvementTopics.length > 0) && (
              <div className="mb-5 rounded-xl border border-violet-200 bg-violet-50 p-4">
                <p className="text-xs font-bold uppercase tracking-wide text-violet-800">Coding Improvement Suggestions</p>
                {performanceInsightSummary.codingSuggestions.length > 0 && (
                  <ul className="mt-2 list-disc list-inside space-y-1 text-sm text-violet-900">
                    {performanceInsightSummary.codingSuggestions.slice(0, 5).map((item, idx) => (
                      <li key={`coding-suggestion-${idx}`}>{item}</li>
                    ))}
                  </ul>
                )}
                {performanceInsightSummary.improvementTopics.length > 0 && (
                  <p className="mt-3 text-sm text-violet-900/90">
                    Recommended practice topics: {performanceInsightSummary.improvementTopics.slice(0, 5).join(', ')}.
                  </p>
                )}
              </div>
            )}

            <ul className="space-y-5">
              {recentForInsights.map((a, i) => (
                <li
                  key={`quiz-insight-${a.id}`}
                  className="rounded-xl border border-slate-100 bg-slate-50/40 p-4 sm:p-5"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2 mb-1">
                    <p className="font-semibold text-slate-900">{a.interest || 'Quiz'}</p>
                    <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
                      <span className="tabular-nums font-semibold text-indigo-700">{attemptPercentScore(a)}%</span>
                      <span>{a.level}</span>
                      <span className="text-xs">{formatAttemptDateTime(a.completedAt)}</span>
                      <Link to={`/quiz/results/${a.id}`} className="text-indigo-600 font-medium hover:text-indigo-800">
                        Results
                      </Link>
                    </div>
                  </div>
                  <AutoQuizInsightCard
                    attempt={a}
                    scorePct={attemptPercentScore(a)}
                    ctx={buildAttemptBehaviorCtx(recentForInsights, i)}
                  />
                </li>
              ))}
            </ul>
          </div>
        )}

        {groupedAverages.length > 0 && (
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">By topic (from your interests)</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {groupedAverages.map((group) => (
                <div key={group.interest} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">{topicCategory(group.interest)}</p>
                  <p className="text-sm font-semibold text-slate-900 mt-1">{group.interest}</p>
                  <p className="text-2xl font-bold text-indigo-600 mt-1">{group.averageScore}%</p>
                  <p className="text-xs text-slate-500 mt-1">{group.totalQuizzes} quizzes</p>
                </div>
              ))}
            </div>
            {averagesByCategory.length > 0 && (
              <div className="mt-6">
                <h3 className="text-lg font-bold text-slate-900 mb-3">Grouped averages</h3>
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {averagesByCategory.map((row) => (
                    <div key={row.category} className="rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
                      <p className="text-xs font-bold uppercase tracking-wide text-indigo-800">{row.category}</p>
                      <p className="text-2xl font-bold text-indigo-900 mt-1">{row.avg}%</p>
                      <p className="text-xs text-indigo-700/80">{row.quizzes} quiz attempt(s) in this bucket</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {sortedNewestFirst.length > 0 && (
          <details className="bg-white rounded-2xl border border-slate-200 overflow-hidden group">
            <summary className="px-5 py-4 cursor-pointer text-sm font-medium text-slate-700 hover:bg-slate-50 list-none flex items-center justify-between gap-2">
              <span>Attempt list &amp; result links</span>
              <span className="text-xs font-normal text-slate-500 group-open:hidden">Show</span>
              <span className="text-xs font-normal text-slate-500 hidden group-open:inline">Hide</span>
            </summary>
            <div className="border-t border-slate-100 divide-y divide-slate-100">
              {sortedNewestFirst.map((a) => (
                <div key={a.id} className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div>
                    <p className="font-semibold text-slate-900">{a.interest || 'Quiz'}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {formatAttemptDateTime(a.completedAt)} · {a.level} · {topicCategory(a.interest || '')}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-indigo-700 tabular-nums">{attemptPercentScore(a)}%</span>
                    <Link
                      to={`/quiz/results/${a.id}`}
                      className="text-sm font-medium text-indigo-600 hover:text-indigo-800"
                    >
                      Results
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
};

export default RecentQuizzes;
