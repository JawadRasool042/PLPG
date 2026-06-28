import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight, BookOpen, Check, Clock, Route } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { cn } from '../../lib/utils';
import { generateRoadmap, type RoadmapResponse } from '../../services/learningIntelligenceService';
import { getUserPerformance, type UserPerformance } from '../../services/quizService';
import { canContinueLearning, type RemediationStatus } from '../../services/remediationService';
import {
  buildRoadmapScoresPayload,
  getEffectivePrimaryInterest,
  getInterestAssessmentDisplay,
  getPercentage,
  ratedDomainsFromScores,
} from '../../utils/interestDisplay';
import { hasCompletedDomainQuiz } from '../../utils/learningPathGate';
import { computePathProgression, getDomainPerfSnapshot, resolveCurrentPhase } from '../../utils/learningPathProgress';
import {
  getRoadmapStageBlock,
  ROADMAP_PHASE_KEYS,
  ROADMAP_PHASE_LABELS,
} from '../../utils/roadmapTopics';

/** Icons/colors only — all roadmap, course, and career text comes from the API. */
const DOMAIN_SHELL: Record<string, { icon: string; color: string }> = {
  'AI & Machine Learning': { icon: '🤖', color: 'from-purple-500 to-indigo-600' },
  'Web Development': { icon: '🌐', color: 'from-blue-500 to-cyan-600' },
  Cybersecurity: { icon: '🔐', color: 'from-red-500 to-rose-600' },
  'Data Science': { icon: '📊', color: 'from-green-500 to-emerald-600' },
  'Mobile Development': { icon: '📱', color: 'from-orange-500 to-amber-600' },
  'Cloud Computing': { icon: '☁️', color: 'from-sky-500 to-blue-600' },
  'Game Development': { icon: '🎮', color: 'from-violet-500 to-purple-600' },
  Coding: { icon: '💻', color: 'from-slate-600 to-gray-700' },
  'Physical Games / Sports': { icon: '🏅', color: 'from-emerald-500 to-teal-600' },
};

function normalizeDomain(value: string): string {
  const key = (value || '').trim().toLowerCase();
  const domainMap: Record<string, string> = {
    'ai/ml': 'AI & Machine Learning',
    'ai & machine learning': 'AI & Machine Learning',
    'artificial intelligence': 'AI & Machine Learning',
    'machine learning': 'AI & Machine Learning',
    'web dev': 'Web Development',
    'web development': 'Web Development',
    'cyber security': 'Cybersecurity',
    cybersecurity: 'Cybersecurity',
    'data science': 'Data Science',
    'mobile development': 'Mobile Development',
    'cloud computing': 'Cloud Computing',
    'game development': 'Game Development',
    'physical games / sports': 'Physical Games / Sports',
    sports: 'Physical Games / Sports',
    coding: 'Coding',
  };
  return domainMap[key] || value;
}

function resolveShell(primary: string) {
  if (DOMAIN_SHELL[primary]) return DOMAIN_SHELL[primary];
  const alt = Object.keys(DOMAIN_SHELL).find((k) => k.toLowerCase() === primary.toLowerCase());
  if (alt) return DOMAIN_SHELL[alt];
  return {
    icon: '📘',
    color: 'from-indigo-500 to-purple-600',
  };
}

/** Mirrors backend quiz_caliber.recommended_difficulty_from_scores for live badge updates. */
function recommendedDifficultyFromScores(avgScore: number, recent: number[]): string {
  const recentAvg = recent.length ? recent.reduce((a, b) => a + b, 0) / recent.length : avgScore;
  const blended = avgScore * 0.4 + recentAvg * 0.6;
  if (blended < 45) return 'beginner';
  if (blended < 72) return 'intermediate';
  return 'advanced';
}

function domainPerformanceStats(
  performance: UserPerformance | null | undefined,
  domain: string,
): { avg: number; recent: number[]; attempts: number } {
  if (!performance) return { avg: 0, recent: [], attempts: 0 };
  const target = normalizeDomain(domain).toLowerCase();
  let topicStats: UserPerformance['byInterest'][string] | undefined = performance.byInterest?.[domain];
  if (!topicStats && performance.byInterest) {
    const match = Object.entries(performance.byInterest).find(
      ([key]) => normalizeDomain(key).toLowerCase() === target,
    );
    topicStats = match?.[1];
  }
  const avg = topicStats?.averageScore ?? performance.overallStats?.averageScore ?? 0;
  const attempts = topicStats?.totalQuizzes ?? performance.overallStats?.totalQuizzes ?? 0;
  const recent = (performance.recentScores || [])
    .filter((r) => !r.interest || normalizeDomain(r.interest).toLowerCase() === target)
    .map((r) => r.score)
    .slice(0, 5);
  return { avg, recent, attempts };
}

const LIVE_PERF_POLL_MS = 5000;

const LearningPath: React.FC = () => {
  const { userInterests, isAuthenticated, user } = useStore();
  const navigate = useNavigate();
  const location = useLocation();
  const justCompletedDomain =
    (location.state as { mixedAttempt?: { domain?: string } } | null)?.mixedAttempt?.domain ?? null;
  const forceLearningPathRegenerate = Boolean(justCompletedDomain);
  const effectivePrimary = useMemo(() => getEffectivePrimaryInterest(userInterests), [userInterests]);
  const interestDisplay = useMemo(() => getInterestAssessmentDisplay(userInterests), [userInterests]);
  const roadmapScoresPayload = useMemo(
    () => buildRoadmapScoresPayload(userInterests?.domainScores),
    [userInterests?.domainScores],
  );
  const domainScoresSignature = useMemo(
    () => JSON.stringify(userInterests?.domainScores ?? {}),
    [userInterests?.domainScores],
  );
  const [activeTab, setActiveTab] = useState<'roadmap' | 'courses' | 'careers' | 'resume'>('roadmap');
  const [apiRoadmap, setApiRoadmap] = useState<RoadmapResponse | null>(null);
  const [roadmapLoading, setRoadmapLoading] = useState(false);
  const [roadmapError, setRoadmapError] = useState<string | null>(null);
  const [quizPerformance, setQuizPerformance] = useState<UserPerformance | null>(null);
  const [perfLoading, setPerfLoading] = useState(true);
  const [remediationGate, setRemediationGate] = useState<RemediationStatus | null>(null);
  const [remediationGateLoading, setRemediationGateLoading] = useState(true);
  const learningInputs = useMemo(
    () => ({
      weeklyHours: 5,
      learningStyle: 'mixed',
      engagementScore: interestDisplay.confidenceRatio || 0.5,
    }),
    [interestDisplay.confidenceRatio],
  );

  useEffect(() => {
    if (!isAuthenticated) navigate('/login');
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    void canContinueLearning()
      .then((data) => {
        if (!cancelled) setRemediationGate(data.canContinue === false ? {
          passed: false,
          needsRemediation: true,
          canContinue: false,
          passingScore: data.passingScore,
          activeLock: data.activeLock,
        } : null);
      })
      .catch(() => {
        if (!cancelled) setRemediationGate(null);
      })
      .finally(() => {
        if (!cancelled) setRemediationGateLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  useEffect(() => {
    const primaryInterest = effectivePrimary;
    if (!primaryInterest) {
      setPerfLoading(false);
      return;
    }

    let cancelled = false;

    const loadPerf = (showLoading = false) => {
      if (showLoading) setPerfLoading(true);
      void getUserPerformance()
        .then((data) => {
          if (!cancelled) setQuizPerformance(data);
        })
        .catch(() => {
          if (!cancelled) setQuizPerformance(null);
        })
        .finally(() => {
          if (!cancelled && showLoading) setPerfLoading(false);
        });
    };

    loadPerf(true);

    const pollId = window.setInterval(() => loadPerf(false), LIVE_PERF_POLL_MS);
    const onFocus = () => loadPerf(false);
    const onVisibility = () => {
      if (document.visibilityState === 'visible') loadPerf(false);
    };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibility);

    return () => {
      cancelled = true;
      window.clearInterval(pollId);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [effectivePrimary]);

  const liveQuizDifficulty = useMemo(() => {
    if (!effectivePrimary || !quizPerformance) return null;
    const { avg, recent } = domainPerformanceStats(
      quizPerformance,
      normalizeDomain(effectivePrimary),
    );
    if (!avg && !recent.length) return null;
    return recommendedDifficultyFromScores(avg, recent);
  }, [effectivePrimary, quizPerformance]);

  const primaryMatchPct = useMemo(() => {
    const rated = ratedDomainsFromScores(userInterests?.domainScores);
    if (rated.length) return getPercentage(rated[0].score);
    if (interestDisplay.confidencePct > 0) return interestDisplay.confidencePct;
    return 0;
  }, [userInterests?.domainScores, interestDisplay.confidencePct]);

  const quizUnlocked = useMemo(() => {
    if (!effectivePrimary) return false;
    return hasCompletedDomainQuiz(quizPerformance, normalizeDomain(effectivePrimary), {
      justCompletedDomain: justCompletedDomain,
    });
  }, [effectivePrimary, quizPerformance, justCompletedDomain]);

  useEffect(() => {
    const primaryInterest = effectivePrimary;
    if (!primaryInterest || !quizUnlocked) return;
    const domain = normalizeDomain(primaryInterest);

    const loadRoadmap = async () => {
      try {
        setRoadmapError(null);
        const ratedRows = ratedDomainsFromScores(userInterests?.domainScores);
        const secondaryRaw = (ratedRows.length
          ? ratedRows.map((r) => normalizeDomain(r.domain))
          : (userInterests?.allInterests || [])
              .filter((i) => (i.confidence ?? 0) > 0)
              .map((i) => normalizeDomain(i.domain))
        )
          .filter((d, idx, arr) => d && d !== domain && arr.indexOf(d) === idx)
          .slice(0, 3);

        const performance = quizPerformance;

        const topicStats = performance?.byInterest?.[domain];
        const quizCaliber = {
          attempt_count: topicStats?.totalQuizzes ?? performance?.overallStats?.totalQuizzes ?? 0,
          average_score: topicStats?.averageScore ?? performance?.overallStats?.averageScore ?? 0,
          best_score: topicStats?.bestScore ?? performance?.overallStats?.bestScore ?? 0,
          recent_scores: (performance?.recentScores || [])
            .filter((r) => normalizeDomain(r.interest) === domain || !r.interest)
            .map((r) => r.score)
            .slice(0, 5),
          mastery_level: (topicStats?.averageScore ?? performance?.overallStats?.averageScore ?? 0) / 100,
        };

        const data = await generateRoadmap({
          domain,
          primary_interest: domain,
          secondary_domains: secondaryRaw,
          user_id: user?.id,
          force_regenerate: forceLearningPathRegenerate,
          quiz_caliber: quizCaliber,
          user: {
            weekly_availability_hours: learningInputs.weeklyHours,
            learning_style: learningInputs.learningStyle,
            known: userInterests?.assessmentContext?.known || '',
            want: userInterests?.assessmentContext?.want || '',
            goals: userInterests?.assessmentContext?.goals || '',
            learning_goals: userInterests?.assessmentContext?.goals || '',
            assessment_tags: userInterests?.assessmentTags || [],
          },
          engagement_score: learningInputs.engagementScore,
          interest_strength: interestDisplay.confidenceRatio,
          weak_areas: performance?.analysis?.improvementTopics || performance?.analysis?.weaknesses?.map((w) => w.interest) || [],
          ...(roadmapScoresPayload ? { scores: roadmapScoresPayload } : {}),
        });
        setApiRoadmap(data);
        const refreshError =
          (data.metadata as { refresh_error?: string } | undefined)?.refresh_error ||
          (data.stale ? 'Live refresh failed; showing your last saved learning path.' : null);
        setRoadmapError(refreshError);
      } catch (err: unknown) {
        setApiRoadmap(null);
        const msg = err instanceof Error ? err.message : 'Failed to load personalized roadmap';
        setRoadmapError(msg);
      } finally {
        setRoadmapLoading(false);
      }
    };

    setRoadmapLoading(true);
    void loadRoadmap();
    return () => undefined;
  }, [
    effectivePrimary,
    quizUnlocked,
    domainScoresSignature,
    user?.id,
    forceLearningPathRegenerate,
  ]);

  const hasPrimaryInterest = Boolean(effectivePrimary);
  const roadmapFromApi = apiRoadmap?.roadmap || {};

  const roadmapPhases = useMemo(() => {
    type StageBlock = {
      topics?: string[];
      all_topics?: string[];
      duration_days?: number;
      duration_label?: string;
      stage_projects?: string[];
      pakistan_focus?: string;
      local_milestones?: string[];
      market_skills?: string[];
    };
    const r = roadmapFromApi as Record<string, StageBlock | undefined>;
    const keys = ROADMAP_PHASE_KEYS;
    const out: {
      phase: string;
      topics: string[];
      duration: string;
      pakistanFocus?: string;
      milestones: string[];
      marketSkills: string[];
      projects: string[];
    }[] = [];
    keys.forEach((k) => {
      const block = getRoadmapStageBlock(r as Record<string, unknown>, k) as StageBlock | undefined;
      const full = block?.all_topics?.filter((t) => typeof t === 'string' && t.trim());
      const short = block?.topics?.filter((t) => typeof t === 'string' && t.trim());
      const topics = (full?.length ? full : short) || [];
      if (!topics.length) return;
      const label =
        typeof block?.duration_label === 'string' && block.duration_label.trim()
          ? block.duration_label.trim()
          : block?.duration_days != null
            ? `${block.duration_days} days`
            : '—';
      const duration = label === '—' ? 'Duration: —' : `Duration: ${label}`;
      out.push({
        phase: ROADMAP_PHASE_LABELS[k],
        topics,
        duration,
        pakistanFocus: block?.pakistan_focus?.trim() || undefined,
        milestones: (block?.local_milestones || []).filter((m) => typeof m === 'string' && m.trim()),
        marketSkills: (block?.market_skills || []).filter((s) => typeof s === 'string' && s.trim()),
        projects: (block?.stage_projects || []).filter((p) => typeof p === 'string' && p.trim()),
      });
    });
    if (!out.length && roadmapLoading) {
      out.push({
        phase: 'Generating',
        topics: ['Building your Pakistan-focused roadmap from quiz performance and interests…'],
        duration: 'Duration: —',
        milestones: [],
        marketSkills: [],
        projects: [],
      });
    } else if (!out.length && roadmapError) {
      out.push({
        phase: 'Unavailable',
        topics: [roadmapError],
        duration: 'Duration: —',
        milestones: [],
        marketSkills: [],
        projects: [],
      });
    }
    return out;
  }, [roadmapFromApi, roadmapLoading, roadmapError]);

  /** Domains the user rated > 0 in the interest checker (not the full ML ranking list). */
  const ratedInterestDomains = useMemo(() => {
    const fromScores = ratedDomainsFromScores(userInterests?.domainScores).map((r) => ({
      domain: normalizeDomain(r.domain),
      score: r.score,
    }));
    if (fromScores.length) return fromScores;
    return (userInterests?.allInterests || [])
      .filter((i) => (i.confidence ?? 0) > 0)
      .map((i) => ({
        domain: normalizeDomain(i.domain),
        score: Math.round((i.confidence ?? 0) * 10),
      }))
      .filter((item, idx, arr) => item.domain && arr.findIndex((x) => x.domain === item.domain) === idx)
      .sort((a, b) => b.score - a.score);
  }, [userInterests?.domainScores, userInterests?.allInterests]);

  if (!hasPrimaryInterest) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="text-6xl mb-4">🎯</div>
          <h2 className="text-2xl font-bold text-slate-900 mb-3">No Learning Path Yet</h2>
          <p className="text-slate-600 mb-6">Complete the Interest Assessment first to get your personalized learning path.</p>
          <button
            onClick={() => navigate('/quizzes/interest-check')}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
          >
            Take Interest Assessment
          </button>
        </div>
      </div>
    );
  }

  const primary = normalizeDomain(effectivePrimary);

  if (perfLoading || remediationGateLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto px-4">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4" />
          <p className="text-slate-600">Checking your quiz progress…</p>
        </div>
      </div>
    );
  }

  if (remediationGate?.activeLock) {
    const lock = remediationGate.activeLock;
    const attemptId = lock.attemptId;
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-amber-50 pt-24 pb-12 flex items-center justify-center">
        <div className="text-center max-w-lg mx-auto px-4">
          <div className="text-6xl mb-4">📚</div>
          <h2 className="text-2xl font-bold text-slate-900 mb-3">Complete remediation before continuing</h2>
          <p className="text-slate-600 mb-2">
            Your last quiz score on <strong>{lock.interest}</strong> was {lock.score}% — you need{' '}
            {remediationGate.passingScore}% to unlock the next lesson.
          </p>
          <p className="text-sm text-slate-500 mb-8">
            Study the personalized guide for that quiz, then retake it with the same questions.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            {attemptId && (
              <button
                type="button"
                onClick={() => navigate(`/remediation/${attemptId}`)}
                className="px-6 py-3 bg-amber-600 text-white rounded-xl font-semibold hover:bg-amber-700 transition-colors"
              >
                Study Remediation Lesson
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (!quizUnlocked) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12 flex items-center justify-center">
        <div className="text-center max-w-lg mx-auto px-4">
          <div className="text-6xl mb-4">📝</div>
          <h2 className="text-2xl font-bold text-slate-900 mb-3">Take a quiz to unlock your path</h2>
          <p className="text-slate-600 mb-2">
            Your <strong>{primary}</strong> Roadmap, Courses, Careers, and Resume are generated by OpenAI after you
            complete at least one quiz.
          </p>
          <p className="text-sm text-slate-500 mb-8">
            Step 1: Interest assessment ✓ &nbsp;→&nbsp; Step 2: Quiz on {primary} &nbsp;→&nbsp; Step 3: Personalized
            learning path
          </p>
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              type="button"
              onClick={() =>
                navigate('/ai-quiz', {
                  state: { topic: primary, difficulty: 'basic' },
                })
              }
              className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
            >
              Take {primary} quiz
            </button>
            <button
              type="button"
              onClick={() => navigate('/quizzes')}
              className="px-6 py-3 bg-white text-indigo-700 border border-indigo-200 rounded-xl font-semibold hover:bg-indigo-50 transition-colors"
            >
              Quiz hub
            </button>
          </div>
        </div>
      </div>
    );
  }
  const shell = resolveShell(primary);

  const adaptiveState = (roadmapFromApi?.adaptive_state || {}) as Record<string, number | string>;

  const courseLink = (q: string) => `https://www.google.com/search?q=${encodeURIComponent(q)}`;

  type CourseJob = {
    title: string;
    employer_type?: string;
    city?: string;
    salary_pkr?: string;
    employment_type?: string;
    why_recommended?: string;
    skills_match?: string[];
  };

  const parseCourseJobs = (raw: unknown): CourseJob[] => {
    if (!Array.isArray(raw)) return [];
    return raw
      .filter((j): j is Record<string, unknown> => j != null && typeof j === 'object')
      .map((j) => ({
        title: String(j.title || 'Role'),
        employer_type: j.employer_type ? String(j.employer_type) : undefined,
        city: j.city ? String(j.city) : undefined,
        salary_pkr: j.salary_pkr ? String(j.salary_pkr) : undefined,
        employment_type: j.employment_type ? String(j.employment_type) : undefined,
        why_recommended: j.why_recommended ? String(j.why_recommended) : undefined,
        skills_match: Array.isArray(j.skills_match) ? j.skills_match.map(String) : [],
      }))
      .filter((j) => j.title);
  };

  const courseCards = (roadmapFromApi?.resources?.course_cards as Array<Record<string, unknown>>) || [];
  const renderedCourses = courseCards.length
    ? courseCards.map((card) => {
        const name = String(card.name || 'Course');
        const platform = String(card.platform || 'OpenAI recommendation');
        const urlHint = String(card.url_hint || '');
        const query = urlHint || `${name} ${primary}`;
        return {
          name,
          platform,
          url: urlHint.startsWith('http') ? urlHint : courseLink(query),
          free: card.free !== false,
          difficulty: String(card.difficulty || ''),
          language: card.language ? String(card.language) : undefined,
          pricePkr: card.price_pkr_hint ? String(card.price_pkr_hint) : undefined,
          pakistanRelevance: card.pakistan_relevance ? String(card.pakistan_relevance) : undefined,
          relatedJobs: parseCourseJobs(card.related_pakistani_jobs),
        };
      })
    : ((roadmapFromApi?.resources?.courses as string[]) || []).map((name) => ({
        name,
        platform: 'Pakistan-accessible learning resource',
        url: courseLink(`${name} ${primary} Pakistan DigiSkills Udemy`),
        free: true,
        difficulty: '',
        language: undefined,
        pricePkr: 'Free',
        pakistanRelevance: undefined,
        relatedJobs: [] as CourseJob[],
      }));

  const secondaryInsights = (apiRoadmap?.secondary_insights || {}) as Record<
    string,
    { recommended_courses?: string[] }
  >;

  /** AI course picks for other rated interests only (excludes primary + unrated domains). */
  const coursesByInterest = ratedInterestDomains
    .filter((item) => item.domain !== primary)
    .map((item) => {
      const pack =
        secondaryInsights[item.domain] ||
        secondaryInsights[normalizeDomain(item.domain)] ||
        Object.entries(secondaryInsights).find(
          ([key]) => normalizeDomain(key).toLowerCase() === item.domain.toLowerCase(),
        )?.[1];
      const names = (pack?.recommended_courses || []).filter(
        (name) => typeof name === 'string' && name.trim(),
      );
      return {
        domain: item.domain,
        score: item.score,
        courses: names.map((name) => ({
          name,
          platform: 'Pakistan-accessible',
          url: courseLink(`${name} ${item.domain} Pakistan`),
          free: true,
        })),
      };
    })
    .filter((group) => group.courses.length > 0);

  const recommendedQuizDifficulty =
    apiRoadmap?.recommended_quiz_difficulty ||
    apiRoadmap?.quiz_caliber?.recommended_quiz_difficulty ||
    liveQuizDifficulty ||
    (roadmapLoading ? '…' : 'beginner');

  const CAREER_LEVEL_ORDER: Record<string, number> = { beginner: 0, intermediate: 1, advanced: 2 };

  const careerPayload = apiRoadmap?.career_paths;
  type RenderedCareer = {
    title: string;
    level: 'beginner' | 'intermediate' | 'advanced';
    progressStatus: 'achieved' | 'current' | 'upcoming';
    recommended: boolean;
    tags: string[];
    progressNote?: string;
  };

  const parseCareer = (c: Record<string, unknown>): RenderedCareer => {
    const title = String(c.title || c.role || 'Career option');
    const levelRaw = String(c.level || 'intermediate').toLowerCase();
    const level = (['beginner', 'intermediate', 'advanced'].includes(levelRaw)
      ? levelRaw
      : 'intermediate') as RenderedCareer['level'];
    const statusRaw = String(c.progress_status || '').toLowerCase();
    const progressStatus = (['achieved', 'current', 'upcoming'].includes(statusRaw)
      ? statusRaw
      : 'current') as RenderedCareer['progressStatus'];
    const tags: string[] = [];
    if (c.industry != null && String(c.industry)) tags.push(`Industry · ${String(c.industry)}`);
    if (c.salary_range != null && String(c.salary_range)) tags.push(`Salary · ${String(c.salary_range)}`);
    if (c.growth_potential != null && String(c.growth_potential)) tags.push(`Growth · ${String(c.growth_potential)}`);
    const skills = Array.isArray(c.required_skills) ? c.required_skills : [];
    for (const s of skills.slice(0, 4)) tags.push(typeof s === 'string' ? s : String(s));
    return {
      title,
      level,
      progressStatus,
      recommended: Boolean(c.recommended),
      tags: tags.filter(Boolean),
      progressNote: c.progress_note ? String(c.progress_note) : undefined,
    };
  };

  let dynamicCareers: RenderedCareer[] = [];
  let careerGlobalTags: string[] = [];

  const careersDetailed = apiRoadmap?.careers_detailed;
  if (Array.isArray(careersDetailed) && careersDetailed.length > 0) {
    dynamicCareers = careersDetailed.map((c) => parseCareer(c as unknown as Record<string, unknown>));
  } else if (Array.isArray(careerPayload) && careerPayload.length > 0) {
    dynamicCareers = careerPayload.map((c: Record<string, unknown>) => parseCareer(c));
  } else if (careerPayload && typeof careerPayload === 'object' && !Array.isArray(careerPayload)) {
    const cp = careerPayload as Record<string, unknown>;
    if (Array.isArray(cp.roles)) {
      if (typeof cp.salary_range === 'string' && cp.salary_range) careerGlobalTags.push(`Salary band · ${cp.salary_range}`);
      if (typeof cp.market_demand === 'number') careerGlobalTags.push(`Market demand · ${cp.market_demand}/10`);
      const userLevel = String(apiRoadmap?.user_career_level || recommendedQuizDifficulty || 'beginner').toLowerCase();
      dynamicCareers = (cp.roles as string[]).map((role: string, i: number) => ({
        title: role,
        level: (i % 3 === 0 ? 'beginner' : i % 3 === 1 ? 'intermediate' : 'advanced') as RenderedCareer['level'],
        progressStatus: 'current' as const,
        recommended: false,
        tags: [],
      }));
      dynamicCareers = dynamicCareers.map((c) => {
        const cRank = CAREER_LEVEL_ORDER[c.level] ?? 1;
        const uRank = CAREER_LEVEL_ORDER[userLevel] ?? 0;
        return {
          ...c,
          progressStatus: (cRank < uRank ? 'achieved' : cRank === uRank ? 'current' : 'upcoming') as RenderedCareer['progressStatus'],
          recommended: cRank === uRank,
        };
      });
    }
  }

  const userCareerLevel = (apiRoadmap?.user_career_level ||
    recommendedQuizDifficulty ||
    'beginner') as 'beginner' | 'intermediate' | 'advanced';

  const careersByLevel: Record<'beginner' | 'intermediate' | 'advanced', RenderedCareer[]> = {
    beginner: [],
    intermediate: [],
    advanced: [],
  };
  for (const career of dynamicCareers) {
    careersByLevel[career.level]?.push(career);
  }

  const renderedCareers = dynamicCareers;
  const resumeOutline = apiRoadmap?.resume_outline;
  const roadmapSummaryPakistan =
    typeof (roadmapFromApi as { roadmap_summary_pakistan?: string }).roadmap_summary_pakistan === 'string'
      ? (roadmapFromApi as { roadmap_summary_pakistan: string }).roadmap_summary_pakistan.trim()
      : '';

  const courseMarketRegion = apiRoadmap?.market_region || apiRoadmap?.metadata?.market_region || apiRoadmap?.metadata?.course_market;
  const careerMarketRegion = courseMarketRegion;
  const careerSalaryCurrency = apiRoadmap?.salary_currency || apiRoadmap?.metadata?.salary_currency;

  const headerBlurb =
    resumeOutline?.headline ||
    (roadmapLoading ? 'Generating your personalized learning path…' : `Live ${primary} path from the learning API.`);

  const totalPhases = Math.max(roadmapPhases.length, 1);
  const domainPerf = getDomainPerfSnapshot(quizPerformance, primary);
  const currentPhase = resolveCurrentPhase(totalPhases, domainPerf, adaptiveState);
  const careerTargetCount = renderedCareers.length;
  const progression = computePathProgression(totalPhases, currentPhase, domainPerf);

  const tabList = ['roadmap', 'courses', 'careers', 'resume'] as const;

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-50 via-white to-indigo-50/80 pt-20 pb-10 sm:pt-24 sm:pb-12">
      <div className="mx-auto w-full min-w-0 px-4 sm:px-6 lg:px-10 xl:px-14 2xl:px-16">
        <div className={`bg-gradient-to-r ${shell.color} rounded-2xl p-5 sm:p-8 mb-8 text-white`}>
          <div className="flex flex-col sm:flex-row items-start gap-4 sm:gap-6">
            <div className="text-5xl sm:text-6xl">{shell.icon}</div>
            <div className="flex-1">
              <p className="text-white/70 text-sm font-medium mb-1">Your Personalized Learning Path</p>
              <h1 className="text-2xl sm:text-3xl font-bold mb-2">{primary}</h1>
              <p className="text-white/80 leading-relaxed">{headerBlurb}</p>
              <div className="flex flex-wrap items-center gap-2 sm:gap-4 mt-4">
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm font-medium">
                  🎯 {primaryMatchPct}% match
                </span>
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm font-medium">
                  📚 {currentPhase}/{totalPhases} phases
                </span>
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm font-medium">
                  💼 {careerTargetCount} career targets
                </span>
                <span className="bg-white/20 px-3 py-1 rounded-full text-sm font-medium capitalize">
                  📝 Quiz level · {recommendedQuizDifficulty}
                </span>
              </div>
            </div>
          </div>
        </div>

        {roadmapLoading && (
          <div className="bg-white rounded-xl border border-slate-200 p-4 mb-6 text-sm text-slate-600">
            Loading live roadmap, careers, and resume hints for <strong>{primary}</strong>…
          </div>
        )}

        {roadmapError && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 mb-6 text-sm text-amber-800">
            {apiRoadmap?.stale
              ? 'Showing your last saved learning path. Live refresh is temporarily unavailable — try again in a few minutes.'
              : `Could not load your learning path (${roadmapError}). Check that the backend is running and OPENAI_API_KEY is set, then reload this page.`}
          </div>
        )}

        {!!roadmapFromApi?.next_step && (
          <div className="mb-6 bg-white rounded-2xl border border-slate-200 p-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Why this next step</p>
            <h3 className="mt-1 text-lg font-bold text-slate-900">
              {(roadmapFromApi.next_step as { type?: string }).type}: {(roadmapFromApi.next_step as { title?: string }).title}
            </h3>
            <p className="mt-2 text-sm text-slate-600">{(roadmapFromApi.next_step as { why?: string }).why}</p>
            {!!roadmapFromApi?.explainability?.reason_summary && (
              <ul className="mt-3 space-y-1 text-xs text-slate-500">
                {((roadmapFromApi.explainability as { reason_summary?: string[] }).reason_summary || []).map((line, idx) => (
                  <li key={idx}>• {line}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        <div className="-mx-1 mb-6 flex gap-1 overflow-x-auto overscroll-x-contain rounded-xl border border-violet-200/70 bg-gradient-to-r from-violet-50/90 via-indigo-50/80 to-violet-50/90 p-1 shadow-sm sm:mx-0 sm:flex-wrap sm:overflow-visible">
          {tabList.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={cn(
                'shrink-0 snap-start rounded-lg px-4 py-2.5 text-sm font-semibold capitalize transition-all sm:flex-1 sm:min-w-[100px] sm:px-2',
                activeTab === tab
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/20 ring-1 ring-indigo-500/30'
                  : 'border border-violet-100/90 bg-white/75 text-slate-700 shadow-sm hover:border-violet-200 hover:bg-violet-100/80 hover:text-violet-950',
              )}
            >
              {tab === 'roadmap'
                ? '🗺️ Roadmap'
                : tab === 'courses'
                  ? '📚 Courses'
                  : tab === 'careers'
                    ? '💼 Careers'
                    : '📄 Resume'}
            </button>
          ))}
        </div>

        {activeTab === 'roadmap' && (
          <div className="w-full space-y-6 sm:space-y-8">
            <header className="border-b border-slate-200/90 pb-6">
              <div className="min-w-0 space-y-2">
                <div className="flex items-center gap-2 text-violet-800">
                  <Route className="h-4 w-4 shrink-0 opacity-90" aria-hidden />
                  <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-800/85 sm:text-xs">
                    Learning sequence
                  </span>
                </div>
                <h2 className="text-balance font-display text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl xl:text-4xl">
                  Road map
                </h2>
                {(roadmapSummaryPakistan || courseMarketRegion) && (
                  <p className="text-sm leading-relaxed text-slate-600 max-w-3xl">
                    {roadmapSummaryPakistan ||
                      `Structured path for the ${courseMarketRegion || 'Pakistan'} job market — local IT firms, freelancing, and remote roles.`}
                  </p>
                )}
              </div>
            </header>

            <div className="grid w-full min-w-0 items-start gap-6 lg:grid-cols-[minmax(260px,340px)_minmax(0,1fr)] lg:gap-8 xl:grid-cols-[minmax(280px,380px)_minmax(0,1fr)] xl:gap-10">
              <aside className="flex min-w-0 flex-col gap-5 lg:sticky lg:top-24 lg:self-start">
                <div className="relative overflow-hidden rounded-2xl border border-slate-200/90 bg-white/90 p-4 shadow-sm ring-1 ring-slate-900/[0.04] backdrop-blur-md sm:p-5">
                  <div
                    className="pointer-events-none absolute -right-16 -top-20 h-48 w-48 rounded-full bg-violet-500/[0.07] blur-3xl"
                    aria-hidden
                  />
                  <div
                    className="pointer-events-none absolute -bottom-24 -left-12 h-40 w-40 rounded-full bg-indigo-500/[0.06] blur-3xl"
                    aria-hidden
                  />
                  <p className="relative text-sm leading-relaxed text-slate-700 sm:text-[0.9375rem]">
                    <span className="font-semibold text-slate-900">{primary}</span>
                    <span className="text-slate-600">
                      {' '}
                      — milestones from basic to expert, scoped for {courseMarketRegion || 'Pakistan'} employability (Rozee.pk, local IT, Upwork/Fiverr).
                    </span>
                  </p>
                </div>

                <div className="rounded-2xl border border-slate-200/90 bg-white/90 p-4 shadow-sm sm:p-5">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
                    <span className="shrink-0 text-xs font-medium tabular-nums text-slate-600 sm:text-sm">
                      Path progress{' '}
                      <span className="font-semibold text-slate-900">{Math.round(progression * 100)}%</span>
                    </span>
                    <div className="h-2 min-h-[8px] w-full flex-1 overflow-hidden rounded-full bg-slate-200/90 shadow-inner sm:min-w-0">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-violet-600 via-violet-500 to-indigo-600 transition-[width] duration-700 ease-out motion-reduce:transition-none"
                        style={{ width: `${Math.min(100, Math.max(0, Math.round(progression * 100)))}%` }}
                        role="progressbar"
                        aria-valuenow={Math.round(progression * 100)}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label="Roadmap completion"
                      />
                    </div>
                  </div>
                  <p className="mt-3 text-center text-xs text-slate-500 sm:text-left">
                    {currentPhase} of {totalPhases} stages active
                  </p>
                </div>
              </aside>

              <ol className="min-w-0 space-y-4 sm:space-y-5">
              {roadmapPhases.map((phase, i) => {
                const isDone = i < currentPhase - 1;
                const isCurrent = i === currentPhase - 1;
                return (
                  <li key={i} className="list-none">
                    <article
                      className={cn(
                        'motion-safe:animate-slide-up motion-safe:[animation-fill-mode:both] motion-reduce:animate-none',
                        'group/card relative flex gap-3 overflow-hidden rounded-2xl border bg-white/90 p-4 shadow-sm backdrop-blur-sm transition-all duration-300 sm:gap-5 sm:p-6',
                        'motion-safe:opacity-0 motion-reduce:opacity-100',
                        'hover:-translate-y-0.5 hover:border-violet-200/90 hover:shadow-lg hover:shadow-violet-500/[0.06]',
                        isCurrent &&
                          'border-violet-300/80 ring-1 ring-violet-500/[0.12] shadow-md shadow-violet-500/[0.04]',
                        isDone && 'border-slate-200/90',
                        !isCurrent && !isDone && 'border-slate-200/70 hover:opacity-100 sm:opacity-90',
                      )}
                      style={{ animationDelay: `${i * 70}ms` }}
                    >
                      <div
                        className="pointer-events-none absolute inset-0 bg-gradient-to-br from-violet-500/[0.04] via-transparent to-indigo-500/[0.03] opacity-0 transition-opacity duration-300 group-hover/card:opacity-100"
                        aria-hidden
                      />
                      <div className="relative flex shrink-0 flex-col items-center">
                        <div
                          className={cn(
                            'relative flex h-11 w-11 items-center justify-center rounded-full text-sm font-bold text-white shadow-md transition-transform duration-300 group-hover/card:scale-[1.03]',
                            isDone && 'bg-gradient-to-br from-emerald-600 to-teal-600 ring-2 ring-emerald-100/80',
                            isCurrent && !isDone && 'bg-gradient-to-br from-violet-600 to-indigo-600 ring-2 ring-violet-200/90',
                            !isCurrent && !isDone && 'bg-gradient-to-br from-slate-400 to-slate-500 ring-2 ring-slate-200/80',
                          )}
                          aria-hidden
                        >
                          {isDone ? <Check className="h-5 w-5" strokeWidth={2.5} /> : i + 1}
                        </div>
                        {i < roadmapPhases.length - 1 && (
                          <div
                            className={cn(
                              'mt-2 w-px flex-1 min-h-[2.25rem] bg-gradient-to-b sm:min-h-[2.5rem]',
                              isDone ? 'from-emerald-200 via-slate-200 to-slate-200' : 'from-violet-300/80 via-violet-100 to-slate-200/90',
                            )}
                            aria-hidden
                          />
                        )}
                      </div>
                      <div className="relative min-w-0 flex-1 pb-0.5">
                        <div className="mb-3 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                          <h3 className="text-lg font-bold tracking-tight text-slate-900 sm:text-xl">{phase.phase}</h3>
                          {isCurrent && (
                            <span className="rounded-md border border-violet-200/80 bg-violet-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-violet-900 sm:text-[11px]">
                              Current focus
                            </span>
                          )}
                          {isDone && (
                            <span className="rounded-md border border-emerald-200/80 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-900 sm:text-[11px]">
                              Complete
                            </span>
                          )}
                        </div>
                        <p className="mb-5 flex items-start gap-2 text-sm text-slate-600">
                          <Clock className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" aria-hidden />
                          <span>{phase.duration}</span>
                        </p>
                        {phase.pakistanFocus && (
                          <p className="mb-4 rounded-lg border border-emerald-100 bg-emerald-50/80 px-3 py-2 text-xs leading-relaxed text-emerald-950">
                            🇵🇰 {phase.pakistanFocus}
                          </p>
                        )}
                        <div className="mb-1 flex items-center gap-2">
                          <BookOpen className="h-3.5 w-3.5 text-violet-600/90" aria-hidden />
                          <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600 sm:text-xs">
                            Topics
                          </p>
                        </div>
                        <div className="mb-5 flex flex-wrap gap-2">
                          {phase.topics.map((topic: string, j: number) => (
                            <span
                              key={j}
                              className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-violet-200/70 bg-violet-50/90 px-2.5 py-1.5 text-xs font-medium text-violet-950 transition-colors duration-200 hover:border-violet-300 hover:bg-violet-50"
                            >
                              <span className="truncate">{topic}</span>
                            </span>
                          ))}
                        </div>
                        {phase.marketSkills.length > 0 && (
                          <>
                            <div className="mb-1 mt-4 flex items-center gap-2">
                              <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600 sm:text-xs">
                                In-demand in Pakistan
                              </p>
                            </div>
                            <div className="mb-5 flex flex-wrap gap-2">
                              {phase.marketSkills.map((skill, j) => (
                                <span
                                  key={j}
                                  className="inline-flex rounded-lg border border-emerald-200/70 bg-emerald-50/90 px-2.5 py-1.5 text-xs font-medium text-emerald-950"
                                >
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </>
                        )}
                        {phase.projects.length > 0 && (
                          <>
                            <div className="mb-1 flex items-center gap-2">
                              <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600 sm:text-xs">
                                Portfolio projects
                              </p>
                            </div>
                            <ul className="mb-5 list-disc space-y-1 pl-4 text-xs text-slate-600">
                              {phase.projects.map((project, j) => (
                                <li key={j}>{project}</li>
                              ))}
                            </ul>
                          </>
                        )}
                        {phase.milestones.length > 0 && (
                          <>
                            <div className="mb-1 flex items-center gap-2">
                              <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600 sm:text-xs">
                                Local milestones
                              </p>
                            </div>
                            <ul className="mb-1 list-disc space-y-1 pl-4 text-xs text-slate-600">
                              {phase.milestones.map((milestone, j) => (
                                <li key={j}>{milestone}</li>
                              ))}
                            </ul>
                          </>
                        )}
                      </div>
                    </article>
                  </li>
                );
              })}
              </ol>
            </div>

            <div className="flex justify-center border-t border-slate-200/80 pt-6 sm:pt-8">
              <button
                type="button"
                onClick={() =>
                  navigate('/ai-quiz', {
                    state: {
                      topic: primary,
                      difficulty:
                        recommendedQuizDifficulty === 'beginner'
                          ? 'basic'
                          : recommendedQuizDifficulty === 'advanced'
                            ? 'advanced'
                            : 'intermediate',
                    },
                  })
                }
                className="group/btn inline-flex w-full min-h-[48px] max-w-md items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-indigo-600 px-6 py-3.5 text-sm font-semibold text-white shadow-md shadow-violet-500/20 transition-all duration-300 hover:from-violet-500 hover:to-indigo-500 hover:shadow-lg hover:shadow-violet-500/25 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-600 sm:max-w-none sm:w-auto sm:min-w-[220px] sm:px-8"
              >
                Take {recommendedQuizDifficulty} quiz for {primary}
                <ArrowRight
                  className="h-4 w-4 shrink-0 transition-transform duration-300 group-hover/btn:translate-x-0.5"
                  aria-hidden
                />
              </button>
            </div>
          </div>
        )}

        {activeTab === 'courses' && (
          <div className="space-y-5">
            {!!renderedCourses.length && (
              <div className="bg-white rounded-2xl border border-slate-200 p-4 sm:p-5">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  {primary} — Pakistan-focused courses for your profile
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Courses picked for learners in {courseMarketRegion || 'Pakistan'} — DigiSkills, Coursera, Udemy, Urdu/English YouTube, and other accessible platforms. Match: {getPercentage(ratedInterestDomains.find((r) => r.domain === primary)?.score ?? interestDisplay.confidenceRatio * 10)}%.
                </p>
                <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                  {renderedCourses.map((course, i) => (
                    <div
                      key={`${course.name}-${i}`}
                      className="rounded-xl border border-slate-200 p-4 bg-white hover:border-indigo-300 hover:shadow-sm transition-all"
                    >
                      <a
                        href={course.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="group block"
                      >
                        <div className="flex items-start justify-between mb-2 gap-2">
                          <div className="flex flex-wrap gap-1">
                            <span className="text-[11px] font-bold px-2 py-1 rounded-full bg-green-100 text-green-700">
                              {course.free ? 'Free' : 'Paid'}
                            </span>
                            {course.language && (
                              <span className="text-[11px] font-medium px-2 py-1 rounded-full bg-sky-100 text-sky-800">
                                {course.language}
                              </span>
                            )}
                          </div>
                          <svg className="w-4 h-4 shrink-0 text-slate-400 group-hover:text-indigo-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                          </svg>
                        </div>
                        <h3 className="font-bold text-slate-900 mb-1 group-hover:text-indigo-600 transition-colors">{course.name}</h3>
                        <p className="text-sm text-slate-500">{course.platform}</p>
                        {course.pricePkr && (
                          <p className="text-xs font-medium text-emerald-700 mt-1">{course.pricePkr}</p>
                        )}
                        {course.pakistanRelevance && (
                          <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">{course.pakistanRelevance}</p>
                        )}
                      </a>
                      {course.relatedJobs.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-slate-100">
                          <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-700 mb-2">
                            🇵🇰 Jobs after this course
                          </p>
                          <ul className="space-y-2">
                            {course.relatedJobs.slice(0, 3).map((job, ji) => (
                              <li key={`${job.title}-${ji}`} className="rounded-lg bg-emerald-50/80 border border-emerald-100 px-2.5 py-2">
                                <p className="text-xs font-semibold text-slate-900">{job.title}</p>
                                <p className="text-[11px] text-slate-600 mt-0.5">
                                  {[job.city, job.employer_type].filter(Boolean).join(' · ')}
                                </p>
                                {job.salary_pkr && (
                                  <p className="text-[11px] font-medium text-emerald-800 mt-0.5">{job.salary_pkr}</p>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!renderedCourses.length && !coursesByInterest.length && !roadmapLoading && (
              <div className="bg-white rounded-2xl border border-slate-200 p-6 text-slate-600 text-sm">
                No courses yet — OpenAI will generate recommendations for your rated interests when your learning path loads.
              </div>
            )}

            {coursesByInterest.map((group, idx) => (
              <div key={`${group.domain}-${idx}`} className="bg-white rounded-2xl border border-slate-200 p-4 sm:p-5">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-1 sm:gap-2 mb-3">
                  <h3 className="text-base sm:text-lg font-bold text-slate-900">{group.domain}</h3>
                  <span className="text-xs text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full w-fit">
                    Your rating: {getPercentage(group.score)}%
                  </span>
                </div>
                <p className="text-xs text-slate-500 mb-3">Also rated in your interest check — AI-picked courses for this domain.</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                  {group.courses.map((course, i) => (
                    <a
                      key={`${group.domain}-${course.name}-${i}`}
                      href={course.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="rounded-xl border border-slate-200 p-4 hover:border-indigo-300 hover:shadow-sm transition-all group bg-white"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <span className="text-[11px] font-bold px-2 py-1 rounded-full bg-green-100 text-green-700">Search</span>
                        <svg className="w-4 h-4 text-slate-400 group-hover:text-indigo-600 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                        </svg>
                      </div>
                      <h4 className="font-bold text-slate-900 mb-1 group-hover:text-indigo-600 transition-colors">{course.name}</h4>
                      <p className="text-sm text-slate-500">{course.platform}</p>
                    </a>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'careers' && (
          <div className="space-y-4">
            {(careerMarketRegion || careerSalaryCurrency) && (
              <p className="text-xs text-slate-500">
                Salaries and roles reflect the {careerMarketRegion || 'Pakistan'} job market
                {careerSalaryCurrency ? ` (${careerSalaryCurrency})` : ''}
                {apiRoadmap?.cached ? ', loaded from your saved learning path.' : ', generated for your profile.'}
                {' '}Your progress level: <span className="font-semibold capitalize text-indigo-700">{userCareerLevel}</span>
              </p>
            )}
            {careerGlobalTags.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {careerGlobalTags.map((t) => (
                  <span key={t} className="text-xs font-medium bg-slate-100 text-slate-800 px-3 py-1.5 rounded-full border border-slate-200">
                    {t}
                  </span>
                ))}
              </div>
            )}
            {!renderedCareers.length && (
              <div className="bg-white rounded-2xl border border-slate-200 p-6 text-slate-600 text-sm">
                Career cards are generated when the roadmap API returns — ensure the backend is running and try again.
              </div>
            )}
            {(['beginner', 'intermediate', 'advanced'] as const).map((level) => {
              const levelCareers = careersByLevel[level];
              if (!levelCareers.length) return null;
              const isUserLevel = level === userCareerLevel;
              const levelLabel = level.charAt(0).toUpperCase() + level.slice(1);
              return (
                <div key={level} className="space-y-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="text-base font-bold text-slate-900">{levelLabel} careers</h3>
                    {isUserLevel && (
                      <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-[11px] font-semibold text-indigo-800 border border-indigo-200">
                        Your level · based on quiz progress
                      </span>
                    )}
                    {level !== userCareerLevel && CAREER_LEVEL_ORDER[level] < (CAREER_LEVEL_ORDER[userCareerLevel] ?? 0) && (
                      <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-[11px] font-medium text-emerald-800 border border-emerald-200">
                        Achieved path
                      </span>
                    )}
                    {level !== userCareerLevel && CAREER_LEVEL_ORDER[level] > (CAREER_LEVEL_ORDER[userCareerLevel] ?? 0) && (
                      <span className="rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-medium text-slate-600 border border-slate-200">
                        Up next
                      </span>
                    )}
                  </div>
                  <div className="grid sm:grid-cols-2 gap-4">
                    {levelCareers.map((career, i) => (
                      <div
                        key={`${level}-${career.title}-${i}`}
                        className={cn(
                          'bg-white rounded-2xl border p-6',
                          career.progressStatus === 'current' ? 'border-indigo-300 ring-1 ring-indigo-100' : 'border-slate-200',
                          career.progressStatus === 'achieved' && 'opacity-90',
                        )}
                      >
                        <div className="flex items-center gap-3 mb-2">
                          <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${shell.color} flex items-center justify-center text-white text-lg`}>
                            💼
                          </div>
                          <div className="min-w-0">
                            <h4 className="font-bold text-slate-900 leading-snug">{career.title}</h4>
                            <p className="text-[11px] capitalize text-slate-500">{levelLabel}</p>
                          </div>
                        </div>
                        {career.progressNote && (
                          <p className="text-xs text-indigo-700 mb-2 leading-relaxed">{career.progressNote}</p>
                        )}
                        {career.tags.length > 0 ? (
                          <div className="flex flex-wrap gap-2 mt-3">
                            {career.tags.map((tag) => (
                              <span
                                key={`${career.title}-${tag}`}
                                className="text-xs bg-indigo-50 text-indigo-800 px-2.5 py-1 rounded-full border border-indigo-100 font-medium"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-slate-500 mt-2">Aligned role for your {levelLabel.toLowerCase()} stage.</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}

          </div>
        )}

        {activeTab === 'resume' && (
          <div className="space-y-4">
            <div className="bg-white rounded-2xl border border-slate-200 p-6">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Live resume outline</p>
              <h3 className="mt-2 text-xl font-bold text-slate-900">{resumeOutline?.headline || 'Profile-driven resume guidance'}</h3>
              {!!resumeOutline?.keywords?.length && (
                <div className="flex flex-wrap gap-2 mt-4">
                  {resumeOutline.keywords.map((kw) => (
                    <span key={kw} className="text-xs bg-slate-100 text-slate-800 px-2.5 py-1 rounded-full border border-slate-200">
                      {kw}
                    </span>
                  ))}
                </div>
              )}
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                {(resumeOutline?.bullets || []).map((b, idx) => (
                  <li key={idx} className="flex gap-2">
                    <span className="text-indigo-500 font-bold">•</span>
                    <span>{b}</span>
                  </li>
                ))}
              </ul>
              {!resumeOutline?.bullets?.length && (
                <p className="mt-3 text-sm text-slate-500">Complete your assessment fields (known / want / goals) and reload — bullets are built from that context.</p>
              )}
            </div>
          </div>
        )}

        <div className="mt-8 bg-white rounded-2xl border border-slate-200 p-4 sm:p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h3 className="font-bold text-slate-900">Ready to test your knowledge?</h3>
            <p className="text-sm text-slate-500 mt-1">Take quizzes tailored to your {primary} interest</p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={() => {
                if (window.confirm('Go back to Home?')) {
                  navigate('/home');
                }
              }}
              className="px-4 py-2 border border-slate-200 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors"
            >
              Home
            </button>
            <button
              onClick={() => navigate('/quizzes')}
              className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
            >
              Take Quiz →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LearningPath;
