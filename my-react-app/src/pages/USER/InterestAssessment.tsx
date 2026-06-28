import React, { useEffect, useState, useCallback, useMemo } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import type { InterestDomain, InterestScores, AnalysisResponse } from '../../services/interestService';
import { submitInterestAssessment, checkInterestApiHealth, resolveTie } from '../../services/interestService';
import {
  buildAllInterestsFromSlidersAndRanked,
  collectAssessmentTags,
  getPercentage,
  primaryStrengthFromSliders,
} from '../../utils/interestDisplay';
import { parseApiError } from '../../services/apiError';

const DOMAINS: InterestDomain[] = [
  'Coding',
  'Web Development',
  'Game Development',
  'Cybersecurity',
  'Data Science',
  'Mobile Development',
  'Cloud Computing',
  'AI & Machine Learning',
  'Physical Games / Sports',
];

const DOMAIN_ICONS: Record<InterestDomain, string> = {
  'Coding': '💻',
  'Web Development': '🌐',
  'Game Development': '🎮',
  'Cybersecurity': '🔐',
  'Data Science': '📊',
  'Mobile Development': '📱',
  'Cloud Computing': '☁️',
  'AI & Machine Learning': '🤖',
  'Physical Games / Sports': '⚽',
};

const defaultScores: InterestScores = DOMAINS.reduce(
  (acc, d) => ({ ...acc, [d]: 0 }),
  {} as InterestScores,
);

/** Group domains so users pick areas first, then rate only what they care about. */
const DOMAIN_CATEGORIES: {
  id: string;
  title: string;
  domains: InterestDomain[];
}[] = [
  {
    id: 'build',
    title: 'Software & applications',
    domains: ['Coding', 'Web Development', 'Mobile Development', 'Game Development'],
  },
  {
    id: 'data',
    title: 'Data & artificial intelligence',
    domains: ['Data Science', 'AI & Machine Learning'],
  },
  {
    id: 'infra',
    title: 'Security & cloud infrastructure',
    domains: ['Cybersecurity', 'Cloud Computing'],
  },
  {
    id: 'other',
    title: 'Sports & physical activity',
    domains: ['Physical Games / Sports'],
  },
];

const CATEGORY_ICONS: Record<string, string> = {
  build: '💻',
  data: '📊',
  infra: '🔐',
  other: '⚽',
};

type AssessmentStep = 1 | 2 | 3;
type CategoryPickerView = 'categories' | 'domains';

interface DomainInteractionMetric {
  sliderChanges: number;
  firstInteractionAt: number | null;
  lastInteractionAt: number | null;
}

const StepIndicator: React.FC<{ step: AssessmentStep }> = ({ step }) => {
  const steps = [
    { num: 1, label: 'Domain selection' },
    { num: 2, label: 'Interest rating' },
    { num: 3, label: 'Results' },
  ];

  return (
    <div className="flex items-center justify-center gap-2 sm:gap-3 mb-4">
      {steps.map((s, idx) => (
        <React.Fragment key={s.num}>
          <div className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                step === s.num
                  ? 'bg-indigo-600 text-white'
                  : step > s.num
                    ? 'bg-emerald-600 text-white'
                    : 'bg-slate-200 text-slate-500'
              }`}
            >
              {step > s.num ? '✓' : s.num}
            </div>
            <span
              className={`text-sm font-medium hidden sm:inline ${
                step === s.num ? 'text-indigo-700' : step > s.num ? 'text-emerald-700' : 'text-slate-500'
              }`}
            >
              {s.label}
            </span>
          </div>
          {idx < steps.length - 1 && (
            <div
              className={`w-8 sm:w-14 h-1 rounded-full ${
                step > s.num ? 'bg-indigo-600' : 'bg-slate-200'
              }`}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

const DomainPickChip: React.FC<{
  domain: InterestDomain;
  selected: boolean;
  onToggle: () => void;
}> = ({ domain, selected, onToggle }) => (
  <button
    type="button"
    onClick={onToggle}
    className={`inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border transition ${
      selected
        ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
        : 'bg-white text-slate-700 border-slate-200 hover:border-indigo-300 hover:bg-indigo-50'
    }`}
  >
    <span>{DOMAIN_ICONS[domain]}</span>
    <span className="truncate">{domain}</span>
  </button>
);

const CategoryCard: React.FC<{
  title: string;
  icon: string;
  selectedCount: number;
  onOpen: () => void;
}> = ({ title, icon, selectedCount, onOpen }) => (
  <button
    type="button"
    onClick={onOpen}
    className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-200 bg-white hover:border-indigo-300 hover:bg-indigo-50/40 transition text-left"
  >
    <span className="text-lg shrink-0" aria-hidden>{icon}</span>
    <div className="flex-1 min-w-0">
      <p className="font-medium text-slate-900 text-sm">{title}</p>
      {selectedCount > 0 && (
        <p className="text-xs text-indigo-600 mt-0.5">{selectedCount} selected</p>
      )}
    </div>
    <svg className="w-5 h-5 text-slate-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  </button>
);

const SearchIcon: React.FC = () => (
  <svg
    className="w-4 h-4 text-slate-400"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
    aria-hidden
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth={2}
      d="M21 21l-4.35-4.35M11 18a7 7 0 100-14 7 7 0 000 14z"
    />
  </svg>
);

/** Heat-style palette: low → high interest (1–10). */
const SCORE_COLORS: Record<number, string> = {
  1: '#94a3b8',
  2: '#f87171',
  3: '#fb923c',
  4: '#fbbf24',
  5: '#facc15',
  6: '#a3e635',
  7: '#4ade80',
  8: '#22c55e',
  9: '#10b981',
  10: '#059669',
};

const RATING_SCALE = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] as const;

const InterestRatingCard: React.FC<{
  domain: InterestDomain;
  value: number;
  onChange: (value: number) => void;
}> = ({ domain, value, onChange }) => (
  <div className="rounded-xl border border-slate-200 bg-white p-3 sm:p-4">
    <div className="flex items-center justify-between gap-3 mb-3">
      <div className="flex items-center gap-2 min-w-0">
        <span className="text-lg shrink-0" aria-hidden>{DOMAIN_ICONS[domain]}</span>
        <p className="font-semibold text-slate-900 text-sm truncate">{domain}</p>
      </div>
      {value > 0 && (
        <div
          className="shrink-0 w-9 h-9 rounded-lg flex items-center justify-center text-base font-bold tabular-nums text-white shadow-sm"
          style={{ backgroundColor: SCORE_COLORS[value] }}
          aria-hidden
        >
          {value}
        </div>
      )}
    </div>

    <div className="grid grid-cols-5 sm:grid-cols-10 gap-1.5" role="group" aria-label={`Rate interest in ${domain}`}>
      {RATING_SCALE.map((score) => {
        const selected = value >= score;
        const isActive = value === score;
        const color = SCORE_COLORS[score];
        return (
          <button
            key={score}
            type="button"
            onClick={() => onChange(score)}
            className={`h-9 sm:h-10 rounded-lg text-xs sm:text-sm font-bold transition-all duration-150 ${
              selected
                ? 'text-white shadow-sm'
                : 'bg-slate-50 text-slate-600 border border-slate-200 hover:border-slate-300'
            } ${isActive ? 'ring-2 ring-offset-1 scale-[1.04]' : ''}`}
            style={{
              backgroundColor: selected ? color : undefined,
              ...(isActive ? { boxShadow: `0 0 0 2px white, 0 0 0 4px ${color}` } : {}),
            }}
            aria-label={`${score} out of 10`}
            aria-pressed={isActive}
          >
            {score}
          </button>
        );
      })}
    </div>
  </div>
);

const simplifyJustification = (text: string, primaryInterest: string): string => {
  const trimmed = text.trim();
  if (!trimmed || /hybrid intelligence/i.test(trimmed)) {
    return `Based on your ratings, ${primaryInterest} is your top pick.`;
  }
  return trimmed;
};

const ResultsPanel: React.FC<{ result: AnalysisResponse; sliderScores: InterestScores }> = ({
  result,
  sliderScores,
}) => {
  const navigate = useNavigate();
  const primarySlider = Math.max(0, Number(sliderScores[result.primary_interest as InterestDomain] ?? 0));
  const primaryIntensityPct = getPercentage(primarySlider);

  const ratedDomains = result.ranked_interests.filter(
    (interest) => Number(sliderScores[interest.name as InterestDomain] ?? 0) > 0,
  );
  const showRatingsBreakdown = ratedDomains.length > 1;

  return (
    <div className="space-y-4">
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-emerald-900 text-sm">
        All set! Take a quiz in <strong>{result.primary_interest}</strong> to open your learning path.
      </div>

      <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-xl p-4 sm:p-5 text-white shadow-lg">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-2xl">{DOMAIN_ICONS[result.primary_interest as InterestDomain] || '🎯'}</span>
          <div>
            <p className="text-xs text-white/80">Primary interest</p>
            <h3 className="text-xl font-bold leading-tight">{result.primary_interest}</h3>
          </div>
        </div>
        <div className="flex items-center gap-2 mb-2">
          <div className="flex-1 h-2 bg-white/20 rounded-full overflow-hidden">
            <div className="h-full bg-white rounded-full" style={{ width: `${primaryIntensityPct}%` }} />
          </div>
          <span className="text-sm font-semibold shrink-0">{primaryIntensityPct}%</span>
        </div>
        {result.recommendation.justification && (
          <p className="text-sm text-white/90 leading-snug">
            {simplifyJustification(result.recommendation.justification, result.primary_interest)}
          </p>
        )}
      </div>

      {showRatingsBreakdown && (
        <div className="rounded-xl border border-slate-200 p-4">
          <h4 className="font-semibold text-slate-900 text-sm mb-3">All domain ratings</h4>
          <div className="space-y-2.5">
            {ratedDomains.map((interest, idx) => {
              const w = Math.max(0, Number(sliderScores[interest.name as InterestDomain] ?? 0));
              const pct = w > 0 ? getPercentage(w) : 0;
              return (
                <div key={interest.name}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-slate-700 flex items-center gap-2 min-w-0">
                      <span className="shrink-0">{DOMAIN_ICONS[interest.name as InterestDomain] || '📌'}</span>
                      <span className="truncate">{interest.name}</span>
                    </span>
                    <span className={`font-semibold shrink-0 ${idx === 0 ? 'text-indigo-600' : 'text-slate-500'}`}>
                      {pct}%
                    </span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${idx === 0 ? 'bg-indigo-500' : 'bg-slate-300'}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div className="flex flex-col gap-2 pt-1">
        <button
          type="button"
          onClick={() => navigate('/quizzes')}
          className="w-full py-2.5 px-6 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition"
        >
          Continue to quizzes
        </button>
        <button
          type="button"
          onClick={() => navigate('/home')}
          className="w-full py-2.5 px-6 bg-white text-slate-700 font-semibold rounded-lg border border-slate-200 hover:bg-slate-50 transition"
        >
          Home
        </button>
      </div>
    </div>
  );
};

const InterestAssessment: React.FC = () => {
  const { user, isAuthenticated, setOnboardingComplete, logout } = useStore();
  const navigate = useNavigate();

  const profileName = useMemo(
    () => `${user?.firstName || ''} ${user?.lastName || ''}`.trim(),
    [user?.firstName, user?.lastName],
  );
  const profileEmail = user?.email || '';

  const handleAuthFailure = useCallback(async () => {
    try {
      await logout();
    } catch {
      // ignore
    }
    navigate('/login', {
      replace: true,
      state: {
        from: '/quizzes/interest-check',
        message: 'Your session expired. Please log in again.',
      },
    });
  }, [logout, navigate]);

  const [assessmentStep, setAssessmentStep] = useState<AssessmentStep>(1);
  const [categoryPickerView, setCategoryPickerView] = useState<CategoryPickerView>('categories');
  const [activeCategoryId, setActiveCategoryId] = useState<string | null>(null);
  const [selectedDomains, setSelectedDomains] = useState<InterestDomain[]>([]);
  const [scores, setScores] = useState<InterestScores>({ ...defaultScores });
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [showTieResolution, setShowTieResolution] = useState(false);
  const [tieCandidates, setTieCandidates] = useState<string[]>([]);
  const [tieResolvingLoading, setTieResolvingLoading] = useState(false);
  const [domainMetrics, setDomainMetrics] = useState<Record<InterestDomain, DomainInteractionMetric>>(
    DOMAINS.reduce((acc, domain) => {
      acc[domain] = { sliderChanges: 0, firstInteractionAt: null, lastInteractionAt: null };
      return acc;
    }, {} as Record<InterestDomain, DomainInteractionMetric>),
  );
  const [assessmentStartedAt, setAssessmentStartedAt] = useState<number | null>(null);
  const [domainSearch, setDomainSearch] = useState('');

  const domainSearchResults = useMemo(() => {
    const q = domainSearch.trim().toLowerCase();
    if (!q) return [];
    const results: { categoryId: string; categoryTitle: string; domain: InterestDomain }[] = [];
    for (const cat of DOMAIN_CATEGORIES) {
      for (const domain of cat.domains) {
        if (cat.title.toLowerCase().includes(q) || domain.toLowerCase().includes(q)) {
          results.push({ categoryId: cat.id, categoryTitle: cat.title, domain });
        }
      }
    }
    return results;
  }, [domainSearch]);

  const known = '';
  const want = '';
  const goals = '';

  useEffect(() => {
    setAssessmentStartedAt(Date.now());
  }, []);

  useEffect(() => {
    const pingApi = async () => {
      try {
        await checkInterestApiHealth();
        setApiStatus('online');
      } catch {
        setApiStatus('offline');
      }
    };
    pingApi();
    const interval = setInterval(pingApi, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleScoreChange = (domain: InterestDomain, value: number) => {
    setScores((prev) => ({ ...prev, [domain]: value }));
    setDomainMetrics((prev) => {
      const now = Date.now();
      const current = prev[domain];
      return {
        ...prev,
        [domain]: {
          sliderChanges: current.sliderChanges + 1,
          firstInteractionAt: current.firstInteractionAt ?? now,
          lastInteractionAt: now,
        },
      };
    });
  };

  const toggleDomainSelection = (domain: InterestDomain) => {
    setApiError(null);
    setSelectedDomains((prev) => {
      const has = prev.includes(domain);
      if (has) {
        setScores((s) => ({ ...s, [domain]: 0 }));
        setDomainMetrics((m) => ({
          ...m,
          [domain]: { sliderChanges: 0, firstInteractionAt: null, lastInteractionAt: null },
        }));
        return prev.filter((d) => d !== domain);
      }
      return [...prev, domain];
    });
  };

  const handleContinueToRate = () => {
    if (selectedDomains.length === 0) {
      setApiError('Please select at least one domain.');
      return;
    }
    setApiError(null);
    setAssessmentStep(2);
  };

  const handleReset = () => {
    setScores({ ...defaultScores });
    setResult(null);
    setApiError(null);
    setAssessmentStep(1);
    setCategoryPickerView('categories');
    setActiveCategoryId(null);
    setSelectedDomains([]);
    setDomainSearch('');
    setAssessmentStartedAt(Date.now());
    setDomainMetrics(
      DOMAINS.reduce((acc, domain) => {
        acc[domain] = { sliderChanges: 0, firstInteractionAt: null, lastInteractionAt: null };
        return acc;
      }, {} as Record<InterestDomain, DomainInteractionMetric>),
    );
  };

  const persistOnboarding = (data: AnalysisResponse, primary: string) => {
    setOnboardingComplete({
      primaryInterest: primary,
      confidence: primaryStrengthFromSliders(primary, scores as Record<string, number>),
      allInterests: buildAllInterestsFromSlidersAndRanked(data.ranked_interests, scores as Record<string, number>),
      domainScores: { ...scores },
      completedAt: new Date().toISOString(),
      assessmentContext: { known, want, goals },
      assessmentTags: collectAssessmentTags(known, want, goals),
      realtimeSignals: {
        totalTimeSpentSec: assessmentStartedAt
          ? Math.floor((Date.now() - assessmentStartedAt) / 1000)
          : undefined,
        domainsInteracted: DOMAINS.filter((d) => (domainMetrics[d]?.sliderChanges || 0) > 0).length,
      },
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!profileName || !profileEmail) {
      setApiError('Profile name or email is missing. Update your profile or log in again.');
      return;
    }

    const hasAtLeastOneInterest = selectedDomains.some((domain) => Number(scores[domain]) > 0);
    if (!hasAtLeastOneInterest) {
      setApiError('Set a rating above 0 for at least one selected domain.');
      return;
    }

    if (apiStatus === 'offline') {
      setApiError('Unable to connect to the server. Please try again later.');
      return;
    }

    setLoading(true);
    setApiError(null);

    try {
      const payload = {
        user: { name: profileName, email: profileEmail, known, want, goals },
        scores,
        save_results: true,
        behavioral_data: DOMAINS.reduce((acc, domain) => {
          const metric = domainMetrics[domain];
          const startedAt = metric.firstInteractionAt ?? assessmentStartedAt ?? Date.now();
          const endedAt = metric.lastInteractionAt ?? Date.now();
          const timeSpentMinutes = Math.max(0, (endedAt - startedAt) / 60000);
          const interestScore = Number(scores[domain] || 0);
          const hasInteraction = metric.sliderChanges > 0;
          const interactionIntensity = Math.min(10, metric.sliderChanges + (interestScore >= 7 ? 2 : 0));
          acc[domain] = {
            time_spent_minutes: Number(timeSpentMinutes.toFixed(2)),
            quiz_performance: interestScore,
            click_frequency: hasInteraction ? interactionIntensity : 0,
            repeat_selection: hasInteraction ? (metric.sliderChanges > 1 ? 8 : 4) : 0,
            completion_rate: interestScore / 10,
            skips: interestScore <= 3 ? 1 : 0,
            saves: hasInteraction && interestScore >= 8 ? 1 : 0,
            engagement_depth: hasInteraction
              ? Math.min(10, interestScore * 0.7 + metric.sliderChanges * 0.6)
              : 0,
          };
          return acc;
        }, {} as Record<string, Record<string, number | boolean>>),
        historical_data: [
          {
            domain: DOMAINS.reduce((best, d) => (scores[d] > scores[best] ? d : best), DOMAINS[0]),
            score: Math.max(...DOMAINS.map((d) => scores[d])),
            date: new Date().toISOString(),
          },
        ],
      };

      const data = await submitInterestAssessment({
        ...payload,
        tags: collectAssessmentTags(known, want, goals),
      });
      setResult(data);

      if (data.tie_detected.is_tie) {
        setShowTieResolution(true);
        setTieCandidates(data.tie_detected.tie_candidates);
      } else {
        setAssessmentStep(3);
        persistOnboarding(data, data.primary_interest);
      }
    } catch (err: unknown) {
      const parsed = parseApiError(err, 'Something went wrong. Please try again.');
      if (
        parsed.status === 401 ||
        parsed.code === 'INVALID_TOKEN' ||
        parsed.code === 'TOKEN_EXPIRED' ||
        parsed.code === 'INVALID_TOKEN_CONTEXT' ||
        parsed.code === 'NO_TOKEN'
      ) {
        await handleAuthFailure();
        return;
      }
      setApiError(parsed.code ? `${parsed.message} [${parsed.code}]` : parsed.message);
    } finally {
      setLoading(false);
    }
  };

  const handleTieResolution = async (selectedDomain: string) => {
    setTieResolvingLoading(true);
    try {
      await resolveTie(
        selectedDomain,
        result
          ? { ranked_interests: result.ranked_interests, tie_detected: result.tie_detected }
          : undefined,
      );
      setShowTieResolution(false);
      const updatedResult = result ? { ...result, primary_interest: selectedDomain } : null;
      if (updatedResult) setResult(updatedResult);
      setAssessmentStep(3);
      persistOnboarding(updatedResult || result!, selectedDomain);
    } catch (err: unknown) {
      const parsed = parseApiError(err, 'Failed to resolve tie');
      if (
        parsed.status === 401 ||
        parsed.code === 'INVALID_TOKEN' ||
        parsed.code === 'TOKEN_EXPIRED' ||
        parsed.code === 'INVALID_TOKEN_CONTEXT' ||
        parsed.code === 'NO_TOKEN'
      ) {
        await handleAuthFailure();
        return;
      }
      if (parsed.message.toLowerCase().includes('no pending interest analysis')) {
        setShowTieResolution(false);
        setAssessmentStep(2);
        setApiError('Session expired. Submit your ratings again, then pick your preferred domain.');
      } else {
        setApiError(parsed.code ? `${parsed.message} [${parsed.code}]` : parsed.message);
      }
    } finally {
      setTieResolvingLoading(false);
    }
  };

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ message: 'Please log in to access this page.' }} replace />;
  }

  const activeCategory = activeCategoryId
    ? DOMAIN_CATEGORIES.find((c) => c.id === activeCategoryId)
    : null;

  const countSelectedInCategory = (categoryId: string) => {
    const cat = DOMAIN_CATEGORIES.find((c) => c.id === categoryId);
    if (!cat) return 0;
    return cat.domains.filter((d) => selectedDomains.includes(d)).length;
  };

  return (
    <div className="w-full min-w-0 bg-gradient-to-br from-slate-50 via-white to-indigo-50 py-4 sm:py-6 pb-24">
      <div className="max-w-3xl mx-auto px-4 sm:px-6">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 text-center mb-3">
          Interest assessment
        </h1>

        <StepIndicator step={assessmentStep} />

        <div className="bg-white rounded-xl shadow-md border border-slate-200">
          {assessmentStep === 1 && categoryPickerView === 'categories' && (
            <div className="p-4 sm:p-5 flex flex-col gap-4">
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
                <p className="text-sm text-slate-600 sm:flex-1">
                  Select a category to choose domains.
                </p>
                <div className="relative w-full sm:w-64 shrink-0">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none">
                    <SearchIcon />
                  </span>
                  <input
                    type="search"
                    value={domainSearch}
                    onChange={(e) => setDomainSearch(e.target.value)}
                    placeholder="Search domains…"
                    className="w-full rounded-lg border border-slate-200 pl-9 pr-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    aria-label="Search domains"
                  />
                </div>
              </div>

              {domainSearch.trim() !== '' && (
                <div className="border border-slate-200 rounded-lg overflow-hidden">
                  {domainSearchResults.length === 0 ? (
                    <p className="px-4 py-3 text-sm text-slate-500">No matching domains.</p>
                  ) : (
                    domainSearchResults.map(({ categoryTitle, domain }) => {
                      const selected = selectedDomains.includes(domain);
                      return (
                        <button
                          key={domain}
                          type="button"
                          onClick={() => toggleDomainSelection(domain)}
                          className={`w-full text-left px-4 py-3 border-b border-slate-100 last:border-0 transition ${
                            selected ? 'bg-indigo-50' : 'hover:bg-slate-50'
                          }`}
                        >
                          <p className="text-xs text-slate-500">{categoryTitle}</p>
                          <p className="text-sm font-medium text-slate-900 flex items-center gap-2 mt-0.5">
                            <span>{DOMAIN_ICONS[domain]}</span>
                            <span>{domain}</span>
                            {selected && (
                              <span className="text-xs font-semibold text-indigo-600 ml-auto">Selected</span>
                            )}
                          </p>
                        </button>
                      );
                    })
                  )}
                </div>
              )}

              {!domainSearch.trim() && (
              <div className="space-y-2">
                {DOMAIN_CATEGORIES.map((cat) => (
                  <CategoryCard
                    key={cat.id}
                    title={cat.title}
                    icon={CATEGORY_ICONS[cat.id] || '📁'}
                    selectedCount={countSelectedInCategory(cat.id)}
                    onOpen={() => {
                      setApiError(null);
                      setActiveCategoryId(cat.id);
                      setCategoryPickerView('domains');
                    }}
                  />
                ))}
              </div>
              )}

              {apiError && (
                <div className="p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                  {apiError}
                </div>
              )}

              <button
                type="button"
                onClick={handleContinueToRate}
                disabled={selectedDomains.length === 0}
                className="w-full py-2.5 px-6 bg-indigo-600 text-white font-semibold rounded-lg hover:bg-indigo-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            </div>
          )}

          {assessmentStep === 1 && categoryPickerView === 'domains' && activeCategory && (
            <div className="p-4 sm:p-5">
              <button
                type="button"
                onClick={() => {
                  setCategoryPickerView('categories');
                  setActiveCategoryId(null);
                  setApiError(null);
                }}
                className="flex items-center gap-1 text-sm text-indigo-600 font-medium hover:text-indigo-700 mb-4"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                All categories
              </button>

              <h2 className="text-lg font-semibold text-slate-900 mb-1">{activeCategory.title}</h2>
              <p className="text-sm text-slate-600 mb-5">Select the domains you want to rate.</p>

              <div className="flex flex-wrap gap-2 mb-6">
                {activeCategory.domains.map((domain) => (
                  <DomainPickChip
                    key={domain}
                    domain={domain}
                    selected={selectedDomains.includes(domain)}
                    onToggle={() => toggleDomainSelection(domain)}
                  />
                ))}
              </div>

              <button
                type="button"
                onClick={() => {
                  setCategoryPickerView('categories');
                  setActiveCategoryId(null);
                }}
                className="w-full py-3 px-6 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition"
              >
                Done
              </button>
            </div>
          )}

          {assessmentStep === 2 && (
            <form onSubmit={handleSubmit} className="p-4 sm:p-5">
              <div className="flex items-center justify-between gap-4 mb-4">
                <p className="text-sm font-medium text-slate-800">Rate your interest</p>
                <button
                  type="button"
                  onClick={() => {
                    setAssessmentStep(1);
                    setCategoryPickerView('categories');
                    setActiveCategoryId(null);
                    setDomainSearch('');
                    setApiError(null);
                  }}
                  className="text-sm text-indigo-600 font-medium hover:text-indigo-700 shrink-0"
                >
                  Edit selection
                </button>
              </div>

              <div className="space-y-3 mb-6">
                {selectedDomains.map((domain) => (
                  <InterestRatingCard
                    key={domain}
                    domain={domain}
                    value={scores[domain]}
                    onChange={(value) => handleScoreChange(domain, value)}
                  />
                ))}
              </div>

              {apiError && (
                <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
                  {apiError}
                </div>
              )}

              {apiStatus === 'offline' && (
                <p className="mb-4 text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
                  Unable to connect to the server. Please try again later.
                </p>
              )}

              <button
                type="submit"
                disabled={loading || apiStatus === 'offline'}
                className="w-full py-3 px-6 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? 'Processing…' : 'Submit assessment'}
              </button>
            </form>
          )}

          {assessmentStep === 3 && result && (
            <div className="p-4 sm:p-5">
              <div className="flex justify-end mb-3">
                <button
                  type="button"
                  onClick={handleReset}
                  className="text-sm text-slate-500 hover:text-slate-700"
                >
                  Restart assessment
                </button>
              </div>
              <ResultsPanel result={result} sliderScores={scores} />
            </div>
          )}
        </div>
      </div>

      {showTieResolution && result && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <h3 className="text-lg font-bold text-slate-900 mb-1">Pick your main focus</h3>
            <p className="text-sm text-slate-600 mb-4">
              You gave the same rating to more than one domain. Choose which one matters most.
            </p>
            <div className="space-y-2">
              {tieCandidates.map((candidate) => (
                <button
                  key={candidate}
                  type="button"
                  onClick={() => handleTieResolution(candidate)}
                  disabled={tieResolvingLoading}
                  className="w-full p-3 text-left border border-slate-200 rounded-xl hover:border-indigo-500 hover:bg-indigo-50 transition disabled:opacity-50 flex items-center gap-2"
                >
                  <span>{DOMAIN_ICONS[candidate as InterestDomain] || '📌'}</span>
                  <span className="font-semibold text-slate-900">{candidate}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default InterestAssessment;
