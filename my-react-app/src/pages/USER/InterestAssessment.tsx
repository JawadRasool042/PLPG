import React, { useEffect, useState, useCallback, useRef } from 'react';
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

// ===================================================================
// Constants & Types
// ===================================================================
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

const DOMAIN_COLORS: Record<InterestDomain, string> = {
  'Coding': 'from-blue-500 to-blue-600',
  'Web Development': 'from-purple-500 to-purple-600',
  'Game Development': 'from-pink-500 to-pink-600',
  'Cybersecurity': 'from-red-500 to-red-600',
  'Data Science': 'from-green-500 to-green-600',
  'Mobile Development': 'from-orange-500 to-orange-600',
  'Cloud Computing': 'from-cyan-500 to-cyan-600',
  'AI & Machine Learning': 'from-indigo-500 to-indigo-600',
  'Physical Games / Sports': 'from-emerald-500 to-emerald-600',
};

/** Default each domain to 0/10 until the learner moves a slider. */
const defaultScores: InterestScores = DOMAINS.reduce(
  (acc, d) => ({ ...acc, [d]: 0 }),
  {} as InterestScores,
);

const KNOWN_TAGS = [
  'HTML/CSS',
  'Bootstrap',
  'JavaScript',
  'Python Basics',
  'React Basics',
  'Git/GitHub',
  'SQL Basics',
  'Networking Fundamentals',
];

const WANT_TAGS = [
  'Python',
  'React',
  'Node.js APIs',
  'Cybersecurity Basics',
  'Data Science',
  'Cloud Computing',
  'Game Development',
  'Machine Learning',
];

interface FormErrors {
  name?: string;
  email?: string;
  interests?: string;
}

interface DomainInteractionMetric {
  sliderChanges: number;
  firstInteractionAt: number | null;
  lastInteractionAt: number | null;
}

// ===================================================================
// Step Indicator Component
// ===================================================================
interface StepIndicatorProps {
  currentStep: number;
  totalSteps: number;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ currentStep, totalSteps }) => {
  const steps = [
    { num: 1, label: 'Personal Info' },
    { num: 2, label: 'Rate Interests' },
    { num: 3, label: 'Get Results' },
  ];

  const stateClass = (stepNum: number) => {
    if (currentStep === stepNum) return 'bg-indigo-600 text-white ring-4 ring-indigo-200 shadow-md scale-110';
    if (currentStep > stepNum) return 'bg-emerald-600 text-white';
    return 'bg-slate-200 text-slate-500';
  };

  const connectorClass = (afterStepNum: number) => {
    if (currentStep > afterStepNum) return 'bg-indigo-600';
    if (currentStep === afterStepNum) return 'bg-gradient-to-r from-indigo-600 to-slate-200';
    return 'bg-slate-200';
  };

  return (
    <div className="mb-8">
      <div className="flex justify-center mb-4">
        <span
          className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-slate-900 text-white text-xs font-bold tracking-wide uppercase"
          aria-current="step"
        >
          Step {currentStep} of {totalSteps}
          <span className="font-normal normal-case text-white/80">
            — {steps.find((s) => s.num === currentStep)?.label}
          </span>
        </span>
      </div>
      <div className="flex items-center justify-center">
        {steps.map((step, idx) => (
          <React.Fragment key={step.num}>
            <div className="flex flex-col items-center max-w-[110px]">
              <div
                className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${stateClass(step.num)}`}
              >
                {currentStep > step.num ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  step.num
                )}
              </div>
              <span
                className={`mt-2 text-xs font-semibold text-center leading-tight ${currentStep === step.num ? 'text-indigo-700' : currentStep > step.num ? 'text-emerald-700' : 'text-slate-400'
                  }`}
              >
                {step.label}
              </span>
              <span
                className={`mt-1 text-[10px] font-bold uppercase tracking-wide text-center ${
                  currentStep > step.num
                    ? 'text-emerald-600'
                    : currentStep === step.num
                      ? 'text-indigo-600'
                      : 'text-slate-400'
                }`}
              >
                {currentStep > step.num ? 'Completed' : currentStep === step.num ? 'Current step' : 'Pending'}
              </span>
            </div>
            {idx < steps.length - 1 && (
              <div
                className={`w-12 sm:w-20 h-1.5 mx-1 sm:mx-2 rounded-full transition-all duration-300 ${connectorClass(step.num)}`}
                aria-hidden
              />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
};

// ===================================================================
// How It Works Panel
// ===================================================================
const HowItWorksPanel: React.FC = () => {
  const steps = [
    {
      icon: '📝',
      title: 'Enter Your Details',
      description: 'Provide your name, email, and rate your interest across different tech domains.',
    },
    {
      icon: '🚀',
      title: 'Submit to API',
      description: 'Your interest scores are securely sent to our Flask backend for analysis.',
    },
    {
      icon: '🧠',
      title: 'ML Prediction',
      description: 'Our trained RandomForest model analyzes your preferences and predicts the best domain.',
    },
    {
      icon: '🎯',
      title: 'Get Recommendations',
      description: 'Receive personalized learning paths, courses, and project suggestions.',
    },
  ];

  return (
    <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl border border-slate-200 p-6 shadow-sm">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
          <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h3 className="text-lg font-bold text-slate-900">How It Works</h3>
      </div>
      <div className="space-y-4">
        {steps.map((step, idx) => (
          <div key={idx} className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 bg-white rounded-lg shadow-sm flex items-center justify-center text-lg">
              {step.icon}
            </div>
            <div>
              <h4 className="font-semibold text-slate-800 text-sm">{step.title}</h4>
              <p className="text-xs text-slate-600 mt-0.5">{step.description}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="mt-5 p-3 bg-indigo-50 rounded-xl border border-indigo-100">
        <p className="text-xs text-indigo-700">
          <span className="font-semibold">💡 Tip:</span> Be honest with your ratings! The more accurate your input,
          the better your personalized recommendations will be.
        </p>
      </div>
    </div>
  );
};

// ===================================================================
// Interest Check completion roadmap (sidebar)
// ===================================================================
interface CompletionRoadmapPanelProps {
  currentStep: number;
}

const CompletionRoadmapPanel: React.FC<CompletionRoadmapPanelProps> = ({ currentStep }) => {
  const items = [
    { step: 1, title: 'Personal details', body: 'Name, email, optional skill tags (what you know / want to learn).' },
    { step: 2, title: 'Rate domains', body: 'Move at least one slider above 0 so the model can rank interests.' },
    { step: 3, title: 'Results & save', body: 'Primary interest and recommendations are stored on your profile when analysis succeeds.' },
  ];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
      <h3 className="font-bold text-slate-900 mb-1 flex items-center gap-2">
        <span className="text-lg">🗺️</span> Interest Check roadmap
      </h3>
      <p className="text-xs text-slate-600 mb-4">
        Follow these steps to unlock personalized quizzes and your learning path.{' '}
        <span className="font-semibold text-slate-800">Learning goals</span> in step 1 (or later in Settings) are{' '}
        <span className="font-semibold text-indigo-700">optional</span> — they refine recommendations but do not block quizzes or path generation.
      </p>
      <ol className="space-y-3">
        {items.map((item) => {
          const done = currentStep > item.step;
          const active = currentStep === item.step;
          return (
            <li
              key={item.step}
              className={`flex gap-3 rounded-xl border px-3 py-2.5 text-sm ${active ? 'border-indigo-300 bg-indigo-50/80' : done ? 'border-emerald-200 bg-emerald-50/50' : 'border-slate-100 bg-slate-50'
                }`}
            >
              <span
                className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${active ? 'bg-indigo-600 text-white' : done ? 'bg-emerald-600 text-white' : 'bg-slate-200 text-slate-600'
                  }`}
              >
                {done ? '✓' : item.step}
              </span>
              <div>
                <p className="font-semibold text-slate-900">{item.title}</p>
                <p className="text-xs text-slate-600 mt-0.5">{item.body}</p>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
};

// ===================================================================
// Interest Slider Component
// ===================================================================
interface InterestSliderProps {
  domain: InterestDomain;
  value: number;
  onChange: (value: number) => void;
}

const InterestSlider: React.FC<InterestSliderProps> = ({ domain, value, onChange }) => {
  const getValueLabel = (val: number) => {
    if (val === 0) return 'No interest (default)';
    if (val <= 2) return 'Low interest';
    if (val <= 4) return 'Slightly interested';
    if (val <= 6) return 'Moderately interested';
    if (val <= 8) return 'Very interested';
    return 'Strong interest';
  };

  return (
    <div className="group p-4 rounded-xl border border-slate-200 bg-white hover:border-indigo-200 hover:shadow-md transition-all duration-200">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xl">{DOMAIN_ICONS[domain]}</span>
          <span className="font-semibold text-slate-800">{domain}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={`text-xs px-2 py-1 rounded-full ${value >= 7 ? 'bg-green-100 text-green-700' :
              value >= 4 ? 'bg-yellow-100 text-yellow-700' :
                value === 0 ? 'bg-slate-100 text-slate-500 border border-slate-200' :
                'bg-slate-100 text-slate-600'
            }`}>
            {getValueLabel(value)}
          </span>
          <span className={`text-lg font-bold bg-gradient-to-r ${DOMAIN_COLORS[domain]} bg-clip-text text-transparent`}>
            {value}
          </span>
        </div>
      </div>
      <div className="relative">
        <input
          type="range"
          min={0}
          max={10}
          step={1}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600 
            [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-5 [&::-webkit-slider-thumb]:h-5 
            [&::-webkit-slider-thumb]:bg-indigo-600 [&::-webkit-slider-thumb]:rounded-full 
            [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:cursor-grab
            [&::-webkit-slider-thumb]:hover:bg-indigo-700 [&::-webkit-slider-thumb]:transition-colors"
        />
        <div className="flex justify-between text-[10px] text-slate-400 mt-1 px-1">
          <span>0</span>
          <span>5</span>
          <span>10</span>
        </div>
      </div>
    </div>
  );
};

// ===================================================================
// Results Panel Component
// ===================================================================
interface ResultsPanelProps {
  result: AnalysisResponse;
  sliderScores: InterestScores;
}

const ResultsPanel: React.FC<ResultsPanelProps> = ({ result, sliderScores }) => {
  const navigate = useNavigate();
  const primarySlider = Math.max(0, Number(sliderScores[result.primary_interest as InterestDomain] ?? 0));
  const primaryIntensityPct = getPercentage(primarySlider);
  const recommendationTags = Array.from(
    new Set([
      result.primary_interest,
      ...(result.recommendation.skill_roadmap?.flatMap((r) => r.topics || []).slice(0, 6) || []),
      ...(result.recommendation.career_paths?.flatMap((c) => c.required_skills || []).slice(0, 6) || []),
    ].filter(Boolean))
  ).slice(0, 8);

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 flex gap-3 text-emerald-900">
        <span className="text-xl flex-shrink-0" aria-hidden>
          ✓
        </span>
        <div>
          <p className="font-semibold text-sm">Step 1 complete — interest check saved</p>
          <p className="text-xs text-emerald-800/90 mt-0.5">
            Your ratings, tags, and assessment context were saved to your profile. Next: take a quiz on{' '}
            <span className="font-medium">{result.primary_interest}</span> to unlock your personalized learning path
            (roadmap, courses, careers, and résumé).
          </p>
        </div>
      </div>

      {/* Primary Recommendation Card */}
      <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl p-6 text-white shadow-xl">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center">
            <span className="text-2xl">{DOMAIN_ICONS[result.primary_interest as InterestDomain] || '🎯'}</span>
          </div>
          <div>
            <p className="text-sm text-white/80">Your Primary Interest</p>
            <h3 className="text-2xl font-bold">{result.primary_interest}</h3>
          </div>
        </div>
        <p className="text-xs text-white/75 mb-2">
          Your rating <strong>{primarySlider}/10</strong> → <strong>{primaryIntensityPct}%</strong> (every domain: (rating ÷ 10) × 100)
        </p>
        <div className="flex items-center gap-2 mb-4">
          <div className="flex-1 h-2 bg-white/20 rounded-full overflow-hidden">
            <div
              className="h-full bg-white rounded-full transition-all duration-500"
              style={{ width: `${primaryIntensityPct}%` }}
            />
          </div>
          <span className="text-sm font-semibold">{primaryIntensityPct}%</span>
        </div>
        <p className="text-sm text-white/90">{result.recommendation.justification}</p>
      </div>

      {/* Explainable Reasoning */}
      <div className="bg-blue-50 rounded-xl border border-blue-200 p-5">
        <div className="flex items-center gap-3 mb-3">
          <span className="text-2xl">🧠</span>
          <h4 className="font-bold text-blue-900">Why This Match?</h4>
        </div>
        <p className="text-sm text-slate-700">{result.ranked_interests[0]?.reason}</p>
      </div>

      {recommendationTags.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h4 className="font-bold text-slate-900 mb-3 flex items-center gap-2">
            <span className="text-lg">🏷️</span> Recommendation Tags
          </h4>
          <div className="flex flex-wrap gap-2">
            {recommendationTags.map((tag) => (
              <span key={tag} className="text-xs bg-indigo-50 text-indigo-700 border border-indigo-200 px-2.5 py-1 rounded-full">
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Learning Approach */}
      {result.recommendation.learning_approach && (
        <div className="p-5 rounded-xl border border-blue-200 bg-blue-50">
          <div className="flex items-center gap-3 mb-3">
            <span className="text-2xl">💻</span>
            <h4 className="font-bold text-blue-900">{result.recommendation.learning_approach.type === 'physical' ? 'Physical Learning Path' : 'Digital Learning Path'}</h4>
          </div>
          <p className="text-sm text-slate-600 mb-3">{result.recommendation.learning_approach.message}</p>
          <ul className="space-y-1.5">
            {result.recommendation.learning_approach.suggestions.map((s, i) => (
              <li key={i} className="text-sm text-slate-700 flex items-start gap-2">
                <span className="text-indigo-500 mt-0.5">•</span> {s}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Ranked Interests */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h4 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
          <span className="text-lg">🏆</span> Your Interest Rankings
        </h4>
        <p className="text-xs text-slate-500 mb-3">
          Each bar uses your slider for that domain: (rating ÷ 10) × 100. Ranking order still follows the model.
        </p>
        <div className="space-y-3">
          {result.ranked_interests.map((interest, idx) => (
            (() => {
              const w = Math.max(0, Number(sliderScores[interest.name as InterestDomain] ?? 0));
              const pct =
                w > 0
                  ? getPercentage(w)
                  : Math.min(
                      100,
                      Math.max(
                        0,
                        Number.parseFloat(String(interest.percentage || '0').replace('%', '')) || 0,
                      ),
                    );
              return (
            <div key={interest.name}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-700 flex items-center gap-2">
                  <span>{DOMAIN_ICONS[interest.name as InterestDomain] || '📌'}</span>
                  {interest.name} (#{idx + 1})
                </span>
                <span className={`font-semibold ${idx === 0 ? 'text-indigo-600' : 'text-slate-500'}`}>
                  {pct}% <span className="font-normal text-slate-400">({w}/10)</span>
                </span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${idx === 0 ? 'bg-gradient-to-r from-indigo-500 to-purple-500' : 'bg-slate-300'
                    }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">{interest.reason}</p>
            </div>
              );
            })()
          ))}
        </div>
      </div>

      {/* Action buttons: single vertical stack */}
      <div className="flex flex-col gap-3 items-center w-full max-w-2xl mx-auto">
        <button
          type="button"
          onClick={() => navigate('/quizzes')}
          className="w-full max-w-sm py-3 px-6 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition shadow-lg shadow-indigo-200/80 flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Take quiz to unlock your learning path
        </button>
        <p className="text-sm text-slate-500 text-center max-w-sm">
          After your first quiz, OpenAI will generate your Roadmap, Courses, Careers, and Resume for your selected
          domain.
        </p>
        <button
          type="button"
          onClick={() => {
            if (window.confirm('Do you really want to go to dashboard')) {
              navigate('/dashboard');
            }
          }}
          className="w-full max-w-sm py-3 px-6 bg-white text-indigo-700 font-semibold rounded-xl border-2 border-indigo-200 hover:border-indigo-400 hover:bg-indigo-50 transition flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
          Go to Dashboard
        </button>
      </div>
    </div>
  );
};

// ===================================================================
// Main Component
// ===================================================================
const InterestAssessment: React.FC = () => {
  const { user, isAuthenticated, setOnboardingComplete, logout } = useStore();
  const navigate = useNavigate();

  const handleAuthFailure = useCallback(async () => {
    try {
      await logout();
    } catch {
      // Ignore logout API failures; we still redirect to login.
    }
    navigate('/login', {
      replace: true,
      state: {
        from: '/quizzes/interest-check',
        message: 'Your session is invalid or expired. Please log in again.',
      },
    });
  }, [logout, navigate]);

  // Form state
  const [currentStep, setCurrentStep] = useState(1);
  const [scores, setScores] = useState<InterestScores>({ ...defaultScores });
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [selectedKnownTags, setSelectedKnownTags] = useState<string[]>([]);
  const [selectedWantTags, setSelectedWantTags] = useState<string[]>([]);
  const goals = '';
  const [errors, setErrors] = useState<FormErrors>({});

  // API state
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  
  // Tie detection state
  const [showTieResolution, setShowTieResolution] = useState(false);
  const [tieCandidates, setTieCandidates] = useState<string[]>([]);
  const [tieResolvingLoading, setTieResolvingLoading] = useState(false);
  const [domainMetrics, setDomainMetrics] = useState<Record<InterestDomain, DomainInteractionMetric>>(
    DOMAINS.reduce((acc, domain) => {
      acc[domain] = { sliderChanges: 0, firstInteractionAt: null, lastInteractionAt: null };
      return acc;
    }, {} as Record<InterestDomain, DomainInteractionMetric>)
  );
  const [step2StartedAt, setStep2StartedAt] = useState<number | null>(null);
  const textInteractionRef = useRef<number>(0);

  const known = selectedKnownTags.join(', ');
  const want = selectedWantTags.join(', ');

  const toggleKnownTag = useCallback((tag: string) => {
    setSelectedKnownTags((prev) => {
      const lower = tag.toLowerCase();
      const has = prev.some((t) => t.toLowerCase() === lower);
      if (has) return prev.filter((t) => t.toLowerCase() !== lower);
      return [...prev, tag];
    });
    textInteractionRef.current += 1;
  }, []);

  const toggleWantTag = useCallback((tag: string) => {
    setSelectedWantTags((prev) => {
      const lower = tag.toLowerCase();
      const has = prev.some((t) => t.toLowerCase() === lower);
      if (has) return prev.filter((t) => t.toLowerCase() !== lower);
      return [...prev, tag];
    });
    textInteractionRef.current += 1;
  }, []);

  // Initialize form with user data
  useEffect(() => {
    if (user) {
      setName(`${user.firstName || ''} ${user.lastName || ''}`.trim());
      setEmail(user.email || '');
    }
  }, [user]);

  // Check API health
  useEffect(() => {
    const pingApi = async () => {
      try {
        await checkInterestApiHealth();
        setApiStatus('online');
      } catch (err) {
        console.error('API health check failed:', err);
        setApiStatus('offline');
      }
    };
    pingApi();

    // Recheck every 30 seconds
    const interval = setInterval(pingApi, 30000);
    return () => clearInterval(interval);
  }, []);

  // Redirect if not authenticated
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ message: 'Please log in to access this page.' }} replace />;
  }

  // Validate step 1
  const validateStep1 = useCallback((): boolean => {
    const newErrors: FormErrors = {};

    if (!name.trim()) {
      newErrors.name = 'Name is required';
    }

    if (!email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      newErrors.email = 'Please enter a valid email address';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [name, email]);

  // Handle next step
  const handleNextStep = () => {
    if (currentStep === 1 && validateStep1()) {
      setCurrentStep(2);
      setStep2StartedAt(Date.now());
    }
  };

  // Handle previous step
  const handlePrevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  // Handle score change
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

  // Reset all scores
  const handleReset = () => {
    setScores({ ...defaultScores });
    setResult(null);
    setApiError(null);
    setCurrentStep(1);
    setErrors({});
    setSelectedKnownTags([]);
    setSelectedWantTags([]);
  };

  // Submit assessment
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const hasAtLeastOneInterest = DOMAINS.some((domain) => Number(scores[domain]) > 0);
    if (!hasAtLeastOneInterest) {
      setApiError('Please rate at least one domain above 0 before generating your learning path.');
      return;
    }

    if (apiStatus === 'offline') {
      setApiError('The API is currently offline. Please ensure the Flask server is running.');
      return;
    }

    setLoading(true);
    setApiError(null);

    try {
      const payload = {
        user: { name, email, known, want, goals },
        scores,
        save_results: true,
        behavioral_data: DOMAINS.reduce((acc, domain) => {
          const metric = domainMetrics[domain];
          const startedAt = metric.firstInteractionAt ?? step2StartedAt ?? Date.now();
          const endedAt = metric.lastInteractionAt ?? Date.now();
          const timeSpentMinutes = Math.max(0, (endedAt - startedAt) / 60000);
          const interestScore = Number(scores[domain] || 0);
          const hasInteraction = metric.sliderChanges > 0;
          const interactionIntensity = Math.min(10, metric.sliderChanges + (interestScore >= 7 ? 2 : 0));
          acc[domain] = {
            time_spent_minutes: Number(timeSpentMinutes.toFixed(2)),
            quiz_performance: interestScore, // proxy until quiz behavior arrives
            click_frequency: hasInteraction ? interactionIntensity : 0,
            // Do not inject synthetic repeat activity for untouched zero-score domains.
            repeat_selection: hasInteraction ? (metric.sliderChanges > 1 ? 8 : 4) : 0,
            completion_rate: interestScore / 10,
            skips: interestScore <= 3 ? 1 : 0,
            saves: hasInteraction && interestScore >= 8 ? 1 : 0,
            engagement_depth: hasInteraction
              ? Math.min(10, (interestScore * 0.7) + (metric.sliderChanges * 0.6))
              : 0,
          };
          return acc;
        }, {} as Record<string, any>),
        historical_data: [
          {
            domain: DOMAINS.reduce((best, d) => (scores[d] > scores[best] ? d : best), DOMAINS[0]),
            score: Math.max(...DOMAINS.map((d) => scores[d])),
            date: new Date().toISOString(),
          },
        ],
      };

      const assessmentTags = collectAssessmentTags(known, want, goals);
      const data = await submitInterestAssessment({
        ...payload,
        tags: assessmentTags,
      });
      setResult(data);

      // Check if tie was detected
      if (data.tie_detected.is_tie) {
        setShowTieResolution(true);
        setTieCandidates(data.tie_detected.tie_candidates);
        console.info('Tie detected - showing resolution prompt');
      } else {
        // No tie, proceed to results
        setCurrentStep(3);
        
        // Update store with onboarding completion
        setOnboardingComplete({
          primaryInterest: data.primary_interest,
          confidence: primaryStrengthFromSliders(data.primary_interest, scores as Record<string, number>),
          allInterests: buildAllInterestsFromSlidersAndRanked(data.ranked_interests, scores as Record<string, number>),
          domainScores: { ...scores },
          completedAt: new Date().toISOString(),
          assessmentContext: {
            known,
            want,
            goals,
          },
          assessmentTags: collectAssessmentTags(known, want, goals),
          realtimeSignals: {
            totalTimeSpentSec: step2StartedAt ? Math.floor((Date.now() - step2StartedAt) / 1000) : undefined,
            domainsInteracted: DOMAINS.filter((d) => (domainMetrics[d]?.sliderChanges || 0) > 0).length,
          },
        });
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

  // Handle tie resolution
  const handleTieResolution = async (selectedDomain: string) => {
    setTieResolvingLoading(true);
    try {
      await resolveTie(selectedDomain, result ? {
        ranked_interests: result.ranked_interests,
        tie_detected: result.tie_detected,
      } : undefined);
      setShowTieResolution(false);
      
      // Update result with user decision
      let updatedResult = result;
      if (result) {
        updatedResult = { ...result, primary_interest: selectedDomain };
        setResult(updatedResult);
      }
      
      setCurrentStep(3);
      
      // Update store
      setOnboardingComplete({
        primaryInterest: selectedDomain,
        confidence: primaryStrengthFromSliders(selectedDomain, scores as Record<string, number>),
        allInterests: buildAllInterestsFromSlidersAndRanked(
          updatedResult?.ranked_interests || [],
          scores as Record<string, number>,
        ),
        domainScores: { ...scores },
        completedAt: new Date().toISOString(),
        assessmentContext: {
          known,
          want,
          goals,
        },
        assessmentTags: collectAssessmentTags(known, want, goals),
        realtimeSignals: {
          totalTimeSpentSec: step2StartedAt ? Math.floor((Date.now() - step2StartedAt) / 1000) : undefined,
          domainsInteracted: DOMAINS.filter((d) => (domainMetrics[d]?.sliderChanges || 0) > 0).length,
        },
      });
    } catch (err: unknown) {
      const parsed = parseApiError(err, 'Failed to resolve tie');
      const errorMessage = parsed.message;
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
      if (errorMessage.toLowerCase().includes('no pending interest analysis')) {
        setShowTieResolution(false);
        setCurrentStep(2);
        setApiError('We could not find your pending tie session. Please submit once more, then select your preferred domain.');
      } else {
        setApiError(parsed.code ? `${errorMessage} [${parsed.code}]` : errorMessage);
      }
    } finally {
      setTieResolvingLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50 pt-20 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header Section */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-indigo-100 rounded-full text-indigo-700 text-sm font-semibold mb-4">
            <span className="relative flex h-2 w-2">
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${apiStatus === 'online' ? 'bg-green-400' : apiStatus === 'offline' ? 'bg-red-400' : 'bg-yellow-400'
                }`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${apiStatus === 'online' ? 'bg-green-500' : apiStatus === 'offline' ? 'bg-red-500' : 'bg-yellow-500'
                }`}></span>
            </span>
            {apiStatus === 'online' ? 'ML API Online' : apiStatus === 'offline' ? 'ML API Offline' : 'Checking API...'}
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-3">
            Personalized Learning Path Checker
          </h1>
          <p className="text-slate-600 max-w-2xl mx-auto text-lg">
            Rate your interest across key tech domains and get tailored recommendations
            powered by our trained RandomForest machine learning model.
          </p>
        </div>

        {/* Step Indicator */}
        <StepIndicator currentStep={currentStep} totalSteps={3} />

        {/* Main Content */}
        <div className="grid lg:grid-cols-3 gap-8">
          {/* Form Section */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl shadow-lg border border-slate-200 overflow-hidden">
              {/* Step 1: Personal Information */}
              {currentStep === 1 && (
                <div className="p-6 sm:p-8">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
                      <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-slate-900">Personal Information</h2>
                      <p className="text-sm text-slate-500">Tell us a bit about yourself</p>
                    </div>
                  </div>

                  <div className="space-y-5">
                    {/* Name Field */}
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-2">
                        Full Name <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="text"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        className={`w-full rounded-xl border ${errors.name ? 'border-red-300 bg-red-50' : 'border-slate-200'} px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition`}
                        placeholder="Enter your full name"
                      />
                      {errors.name && (
                        <p className="mt-1.5 text-sm text-red-600 flex items-center gap-1">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                          {errors.name}
                        </p>
                      )}
                    </div>

                    {/* Email Field */}
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-2">
                        Email Address <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className={`w-full rounded-xl border ${errors.email ? 'border-red-300 bg-red-50' : 'border-slate-200'} px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition`}
                        placeholder="you@example.com"
                      />
                      {errors.email && (
                        <p className="mt-1.5 text-sm text-red-600 flex items-center gap-1">
                          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                          </svg>
                          {errors.email}
                        </p>
                      )}
                    </div>

                    {/* What do you know — tags only */}
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-2">
                        What do you already know?
                      </label>
                      <div className="flex flex-wrap gap-1.5 sm:gap-2">
                        {KNOWN_TAGS.map((tag) => {
                          const selected = selectedKnownTags.some((t) => t.toLowerCase() === tag.toLowerCase());
                          return (
                            <button
                              key={tag}
                              type="button"
                              onClick={() => toggleKnownTag(tag)}
                              className={`inline-flex items-center max-w-full px-2 py-1 sm:px-2.5 text-[11px] sm:text-xs leading-none font-medium rounded-full border transition ${
                                selected
                                  ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                                  : 'bg-indigo-50 text-indigo-700 border-indigo-200 hover:bg-indigo-100'
                              }`}
                            >
                              {tag}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* What do you want to learn — tags only */}
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-2">
                        What do you want to learn?
                      </label>
                      <div className="flex flex-wrap gap-1.5 sm:gap-2">
                        {WANT_TAGS.map((tag) => {
                          const selected = selectedWantTags.some((t) => t.toLowerCase() === tag.toLowerCase());
                          return (
                            <button
                              key={tag}
                              type="button"
                              onClick={() => toggleWantTag(tag)}
                              className={`inline-flex items-center max-w-full px-2 py-1 sm:px-2.5 text-[11px] sm:text-xs leading-none font-medium rounded-full border transition ${
                                selected
                                  ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
                                  : 'bg-emerald-50 text-emerald-700 border-emerald-200 hover:bg-emerald-100'
                              }`}
                            >
                              {tag}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* Next Button */}
                    <button
                      type="button"
                      onClick={handleNextStep}
                      className="w-full py-3.5 px-6 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition shadow-lg shadow-indigo-200 flex items-center justify-center gap-2"
                    >
                      Continue to Interest Rating
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}

              {/* Step 2: Interest Rating */}
              {currentStep === 2 && (
                <form onSubmit={handleSubmit} className="p-6 sm:p-8">
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 bg-indigo-100 rounded-xl flex items-center justify-center">
                        <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
                        </svg>
                      </div>
                      <div>
                        <h2 className="text-xl font-bold text-slate-900">Rate Your Interests</h2>
                      <p className="text-sm text-slate-500">Score each domain from 0 (No interest) to 10 (High)</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setScores({ ...defaultScores })}
                      className="text-sm text-indigo-600 font-semibold hover:text-indigo-700 flex items-center gap-1"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Reset to 0
                    </button>
                  </div>

                  <div className="grid sm:grid-cols-2 gap-4 mb-6">
                    {DOMAINS.map((domain) => (
                      <InterestSlider
                        key={domain}
                        domain={domain}
                        value={scores[domain]}
                        onChange={(value) => handleScoreChange(domain, value)}
                      />
                    ))}
                  </div>

                  {/* API Error */}
                  {apiError && (
                    <div className="mb-6 p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 flex items-start gap-3">
                      <svg className="w-5 h-5 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                      </svg>
                      <div>
                        <p className="font-semibold">Error</p>
                        <p className="text-sm">{apiError}</p>
                      </div>
                    </div>
                  )}

                  {/* Action Buttons */}
                  <div className="flex flex-col sm:flex-row gap-3">
                    <button
                      type="button"
                      onClick={handlePrevStep}
                      className="px-6 py-3 border-2 border-slate-200 text-slate-700 font-semibold rounded-xl hover:bg-slate-50 transition flex items-center justify-center gap-2"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 17l-5-5m0 0l5-5m-5 5h12" />
                      </svg>
                      Back
                    </button>
                    <button
                      type="submit"
                      disabled={loading || apiStatus === 'offline'}
                      className="flex-1 py-3 px-6 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-semibold rounded-xl hover:from-indigo-700 hover:to-purple-700 transition shadow-lg shadow-indigo-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {loading ? (
                        <>
                          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Analyzing Your Interests...
                        </>
                      ) : (
                        <>
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                          </svg>
                          Generate My Learning Path
                        </>
                      )}
                    </button>
                  </div>
                </form>
              )}

              {/* Step 3: Results */}
              {currentStep === 3 && result && (
                <div className="p-6 sm:p-8">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 bg-green-100 rounded-xl flex items-center justify-center">
                      <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-slate-900">Your Personalized Results</h2>
                      <p className="text-sm text-slate-500">Based on your interest ratings</p>
                    </div>
                  </div>
                  <ResultsPanel result={result} sliderScores={scores} />
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            <CompletionRoadmapPanel currentStep={currentStep} />
            <HowItWorksPanel />

            {/* User Summary Card */}
            {currentStep >= 2 && (
              <div className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm">
                <h3 className="font-bold text-slate-900 mb-3 flex items-center gap-2">
                  <span className="text-lg">👤</span> Your Profile
                </h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Name:</span>
                    <span className="font-medium text-slate-700">{name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Email:</span>
                    <span className="font-medium text-slate-700 truncate ml-2">{email}</span>
                  </div>
                  {known && (
                    <div className="pt-2 border-t border-slate-100">
                      <span className="text-slate-500">Already knows:</span>
                      <p className="font-medium text-slate-700 mt-0.5">{known}</p>
                    </div>
                  )}
                  {want && (
                    <div className="pt-2 border-t border-slate-100">
                      <span className="text-slate-500">Wants to learn:</span>
                      <p className="font-medium text-slate-700 mt-0.5">{want}</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Reset Button */}
            {currentStep > 1 && (
              <button
                onClick={handleReset}
                className="w-full py-3 px-4 border border-slate-200 text-slate-600 font-medium rounded-xl hover:bg-slate-50 transition flex items-center justify-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Start Over
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tie Resolution Modal */}
      {showTieResolution && result && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6 animate-in fade-in scale-95">
            <div className="mb-4">
              <div className="w-12 h-12 bg-amber-100 rounded-xl flex items-center justify-center mb-3">
                <span className="text-2xl">⚖️</span>
              </div>
              <h3 className="text-xl font-bold text-slate-900">We Found a Tie!</h3>
              <p className="text-sm text-slate-500 mt-1">
                Your top interests are very close. Help us prioritize by choosing your primary interest:
              </p>
            </div>

            <div className="space-y-2 mb-6">
              {tieCandidates.map((candidate) => (
                <button
                  key={candidate}
                  onClick={() => handleTieResolution(candidate)}
                  disabled={tieResolvingLoading}
                  className="w-full p-4 text-left border-2 border-slate-200 rounded-xl hover:border-indigo-500 hover:bg-indigo-50 transition disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <span className="text-2xl">{DOMAIN_ICONS[candidate as InterestDomain] || '📌'}</span>
                      <span className="font-semibold text-slate-900">{candidate}</span>
                    </span>
                    {tieResolvingLoading && (
                      <svg className="animate-spin w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    )}
                  </div>
                </button>
              ))}
            </div>

            <p className="text-xs text-slate-500 text-center">
              You can update this preference in your profile later.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default InterestAssessment;
