import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import type { InterestDomain, InterestScores, AnalysisResponse } from '../../services/interestService';
import { submitInterestAssessment, checkInterestApiHealth, resolveTie } from '../../services/interestService';

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

const defaultScores: InterestScores = {
  Coding: 5,
  'Web Development': 5,
  'Game Development': 5,
  Cybersecurity: 5,
  'Data Science': 5,
  'Mobile Development': 5,
  'Cloud Computing': 5,
  'AI & Machine Learning': 5,
  'Physical Games / Sports': 5,
};

interface FormErrors {
  name?: string;
  email?: string;
  interests?: string;
}

// ===================================================================
// Step Indicator Component
// ===================================================================
interface StepIndicatorProps {
  currentStep: number;
  totalSteps: number;
}

const StepIndicator: React.FC<StepIndicatorProps> = ({ currentStep }) => {
  const steps = [
    { num: 1, label: 'Personal Info' },
    { num: 2, label: 'Rate Interests' },
    { num: 3, label: 'Get Results' },
  ];

  return (
    <div className="flex items-center justify-center mb-8">
      {steps.map((step, idx) => (
        <React.Fragment key={step.num}>
          <div className="flex flex-col items-center">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-semibold transition-all duration-300 ${currentStep >= step.num
                  ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-200'
                  : 'bg-slate-200 text-slate-500'
                }`}
            >
              {currentStep > step.num ? (
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              ) : (
                step.num
              )}
            </div>
            <span className={`mt-2 text-xs font-medium ${currentStep >= step.num ? 'text-indigo-600' : 'text-slate-400'}`}>
              {step.label}
            </span>
          </div>
          {idx < steps.length - 1 && (
            <div
              className={`w-16 sm:w-24 h-1 mx-2 rounded-full transition-all duration-300 ${currentStep > step.num ? 'bg-indigo-600' : 'bg-slate-200'
                }`}
            />
          )}
        </React.Fragment>
      ))}
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
// Interest Slider Component
// ===================================================================
interface InterestSliderProps {
  domain: InterestDomain;
  value: number;
  onChange: (value: number) => void;
}

const InterestSlider: React.FC<InterestSliderProps> = ({ domain, value, onChange }) => {
  const getValueLabel = (val: number) => {
    if (val <= 2) return 'Not Interested';
    if (val <= 4) return 'Slightly Interested';
    if (val <= 6) return 'Moderately Interested';
    if (val <= 8) return 'Very Interested';
    return 'Passionate';
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
          min={1}
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
          <span>1</span>
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
}

const ResultsPanel: React.FC<ResultsPanelProps> = ({ result }) => {
  const navigate = useNavigate();

  return (
    <div className="space-y-6">
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
        <div className="flex items-center gap-2 mb-4">
          <div className="flex-1 h-2 bg-white/20 rounded-full overflow-hidden">
            <div
              className="h-full bg-white rounded-full transition-all duration-500"
              style={{ width: `${parseFloat(result.ranked_interests[0]?.confidence || '0')}%` }}
            />
          </div>
          <span className="text-sm font-semibold">{result.ranked_interests[0]?.confidence}</span>
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
        <div className="space-y-3">
          {result.ranked_interests.map((interest, idx) => (
            <div key={interest.name}>
              <div className="flex justify-between text-sm mb-1">
                <span className="text-slate-700 flex items-center gap-2">
                  <span>{DOMAIN_ICONS[interest.name as InterestDomain] || '📌'}</span>
                  {interest.name} (#{idx + 1})
                </span>
                <span className={`font-semibold ${idx === 0 ? 'text-indigo-600' : 'text-slate-500'}`}>
                  {interest.percentage}%
                </span>
              </div>
              <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${idx === 0 ? 'bg-gradient-to-r from-indigo-500 to-purple-500' : 'bg-slate-300'
                    }`}
                  style={{ width: interest.percentage }}
                />
              </div>
              <p className="text-xs text-slate-500 mt-1">{interest.reason}</p>
            </div>
          ))}
        </div>
        <div className="mt-4 p-3 bg-green-50 rounded-lg border border-green-200 text-xs text-green-800">
          <span className="font-semibold">✓ Validation:</span> {result.data_validation.total_percentage}% total
        </div>
      </div>

      {/* Career Paths */}
      {result.recommendation.career_paths && result.recommendation.career_paths.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h4 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
            <span className="text-lg">💼</span> Recommended Career Paths
          </h4>
          <div className="space-y-3">
            {result.recommendation.career_paths.slice(0, 3).map((career, idx) => (
              <div key={idx} className="p-4 bg-gradient-to-r from-indigo-50 to-purple-50 rounded-lg border border-indigo-100">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h5 className="font-semibold text-slate-900">{career.title}</h5>
                    <p className="text-xs text-slate-600 mt-1">
                      Industry: {career.industry} • Growth: {career.growth_potential}
                    </p>
                  </div>
                  {career.salary_range && (
                    <span className="text-xs font-semibold text-green-600 bg-green-100 px-2 py-1 rounded">
                      {career.salary_range}
                    </span>
                  )}
                </div>
                {career.required_skills && career.required_skills.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {career.required_skills.slice(0, 3).map((skill, i) => (
                      <span key={i} className="text-xs bg-white text-slate-700 px-2 py-1 rounded border border-slate-200">
                        {skill}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Skill Roadmap */}
      {result.recommendation.skill_roadmap && result.recommendation.skill_roadmap.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h4 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
            <span className="text-lg">🛣️</span> Skill Development Roadmap
          </h4>
          <div className="space-y-3">
            {result.recommendation.skill_roadmap.map((level, idx) => (
              <div key={idx} className="border border-slate-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-8 h-8 bg-indigo-600 text-white rounded-full flex items-center justify-center text-sm font-bold">
                    {idx + 1}
                  </div>
                  <h5 className="font-semibold text-slate-900">{level.level}</h5>
                </div>
                <p className="text-sm text-slate-600 mb-2">Duration: {level.duration}</p>
                {level.topics && level.topics.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {level.topics.map((topic, i) => (
                      <span key={i} className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded">
                        {topic}
                      </span>
                    ))}
                  </div>
                )}
                {level.projects && level.projects.length > 0 && (
                  <div className="mt-3">
                    <p className="text-xs font-semibold text-slate-700 mb-1">Projects</p>
                    <div className="flex flex-wrap gap-1">
                      {level.projects.map((project, i) => (
                        <span key={i} className="text-xs bg-slate-100 text-slate-700 px-2 py-1 rounded">
                          {project}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row gap-3">
        <button
          onClick={() => navigate('/profile')}
          className="flex-1 py-3 px-6 bg-indigo-600 text-white font-semibold rounded-xl hover:bg-indigo-700 transition shadow-lg shadow-indigo-200 flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          </svg>
          Go to Dashboard
        </button>
        <button
          onClick={() => navigate('/quizzes')}
          className="flex-1 py-3 px-6 bg-white text-indigo-600 font-semibold rounded-xl border-2 border-indigo-200 hover:border-indigo-300 hover:bg-indigo-50 transition flex items-center justify-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Start Learning
        </button>
      </div>
    </div>
  );
};

// ===================================================================
// Main Component
// ===================================================================
const InterestAssessment: React.FC = () => {
  const { user, isAuthenticated, setOnboardingComplete } = useStore();

  // Form state
  const [currentStep, setCurrentStep] = useState(1);
  const [scores, setScores] = useState<InterestScores>({ ...defaultScores });
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [known, setKnown] = useState('');
  const [want, setWant] = useState('');
  const [goals, setGoals] = useState('');
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
  };

  // Reset all scores
  const handleReset = () => {
    setScores({ ...defaultScores });
    setResult(null);
    setApiError(null);
    setCurrentStep(1);
    setErrors({});
  };

  // Submit assessment
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

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
      };

      const data = await submitInterestAssessment(payload);
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
          confidence: parseFloat(data.ranked_interests[0]?.confidence || '0') / 100,
          allInterests: data.ranked_interests.map(r => ({
            domain: r.name,
            confidence: parseFloat(r.percentage) / 100
          })),
          completedAt: new Date().toISOString(),
        });
      }
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Something went wrong. Please try again.';
      setApiError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  // Handle tie resolution
  const handleTieResolution = async (selectedDomain: string) => {
    setTieResolvingLoading(true);
    try {
      await resolveTie(selectedDomain);
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
        confidence: parseFloat(updatedResult?.ranked_interests.find(r => r.name === selectedDomain)?.confidence || '0') / 100,
        allInterests: updatedResult?.ranked_interests.map(r => ({
          domain: r.name,
          confidence: parseFloat(r.percentage) / 100
        })) || [],
        completedAt: new Date().toISOString(),
      });
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to resolve tie';
      setApiError(errorMessage);
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

                    {/* What do you know */}
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-2">
                        What do you already know? <span className="text-slate-400">(optional)</span>
                      </label>
                      <input
                        type="text"
                        value={known}
                        onChange={(e) => setKnown(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                        placeholder="I know responsive design with Bootstrap"
                      />
                    </div>

                    {/* What do you want to learn */}
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-2">
                        What do you want to learn? <span className="text-slate-400">(optional)</span>
                      </label>
                      <input
                        type="text"
                        value={want}
                        onChange={(e) => setWant(e.target.value)}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition"
                        placeholder="I want to build REST APIs with Node.js"
                      />
                    </div>

                    {/* Learning Goals */}
                    <div>
                      <label className="block text-sm font-semibold text-slate-700 mb-2">
                        Learning Goals <span className="text-slate-400">(optional)</span>
                      </label>
                      <textarea
                        value={goals}
                        onChange={(e) => setGoals(e.target.value)}
                        rows={3}
                        className="w-full rounded-xl border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition resize-none"
                        placeholder="Become a full-stack developer in 6 months"
                      />
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
                        <p className="text-sm text-slate-500">Score each domain from 1 (Low) to 10 (High)</p>
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
                      Reset to 5
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
                  <ResultsPanel result={result} />
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
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
