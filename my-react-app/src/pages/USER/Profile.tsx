import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import ErrorState from '../../components/ErrorState';
import { API_BASE_URL, asFetchNetworkError } from '../../config/apiBase';
import { getUserProfile } from '../../services/authService';
import {
  getQuizHistory,
  getUserPerformance,
  type QuizAttempt,
  type UserPerformance,
} from '../../services/quizService';

interface ProfileData {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  bio: string | null;
  avatar: string | null;
  date_of_birth: string | null;
  location: string | null;
  role: string;
  learning_level: 'Beginner' | 'Intermediate' | 'Advanced';
  learning_goals: string[];
  weekly_availability_hours: number | null;
  content_format: 'Video' | 'Text' | 'Projects' | 'Mixed';
  focus_domains: string[];
  is_email_verified: boolean;
  created_at: string;
}

const learningGoalOptions = ['Career growth', 'Skill upgrade', 'Exam prep', 'Research', 'Certification'];
const focusDomainOptions = ['AI', 'Web Development', 'Data Science', 'Cloud', 'Cybersecurity', 'Product', 'Design'];

type LearningSyncState = 'idle' | 'saving' | 'saved' | 'error';

type TimelineRow = {
  id: string;
  title: string;
  detail: string;
  at: Date;
};

function learningFieldsSignature(fd: {
  learning_level: string;
  learning_goals: string[];
  weekly_availability_hours: number | string;
  content_format: string;
  focus_domains: string[];
}) {
  const hours =
    fd.weekly_availability_hours === '' || fd.weekly_availability_hours === undefined
      ? null
      : Number(fd.weekly_availability_hours);
  return JSON.stringify({
    learning_level: fd.learning_level,
    learning_goals: [...fd.learning_goals].sort(),
    weekly_availability_hours: hours,
    content_format: fd.content_format,
    focus_domains: [...fd.focus_domains].sort(),
  });
}

function formatRelativeTime(at: Date): string {
  const sec = Math.floor((Date.now() - at.getTime()) / 1000);
  if (sec < 45) return 'Just now';
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  if (sec < 86400 * 7) return `${Math.floor(sec / 86400)}d ago`;
  return at.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

/** Maps quiz volume + average score into a single learning tier (persisted on profile). */
function deriveLearningLevelFromPerformance(
  attempts: QuizAttempt[],
  perf: UserPerformance | null,
): { level: 'Beginner' | 'Intermediate' | 'Advanced'; detail: string } {
  const sorted = [...attempts].sort(
    (a, b) => new Date(b.completedAt).getTime() - new Date(a.completedAt).getTime(),
  );
  const scores = sorted
    .map((a) => (typeof a.score === 'number' && !Number.isNaN(a.score) ? a.score : NaN))
    .filter((s) => !Number.isNaN(s));
  const avgFromAttempts = scores.length ? scores.reduce((a, b) => a + b, 0) / scores.length : NaN;
  const avgOverall = perf?.overallStats?.averageScore;
  const avg = Number.isFinite(avgFromAttempts) ? avgFromAttempts : (avgOverall ?? 0);
  const totalReported = perf?.overallStats?.totalQuizzes ?? 0;
  const sampleCount = Math.max(totalReported, scores.length, sorted.length);

  if (sampleCount === 0) {
    return {
      level: 'Beginner',
      detail: 'No quiz history yet — level stays Beginner until you complete attempts.',
    };
  }

  if (sampleCount >= 10 && avg >= 80) {
    return {
      level: 'Advanced',
      detail: `${Math.round(avg)}% average across ${sampleCount}+ quizzes — advanced track.`,
    };
  }
  if (sampleCount >= 6 && avg >= 74) {
    return {
      level: 'Advanced',
      detail: `${Math.round(avg)}% average with ${sampleCount} attempts — strong mastery signals.`,
    };
  }
  if (sampleCount >= 4 && avg >= 62) {
    return {
      level: 'Intermediate',
      detail: `${Math.round(avg)}% average over ${sampleCount} quizzes — intermediate pacing.`,
    };
  }
  if (sampleCount >= 2 && avg >= 52) {
    return {
      level: 'Intermediate',
      detail: `${Math.round(avg)}% average — progressing; keep practicing to reach advanced.`,
    };
  }
  return {
    level: 'Beginner',
    detail: `${Math.round(avg)}% average (${sampleCount} quiz${sampleCount === 1 ? '' : 'zes'}) — beginner support until scores lift.`,
  };
}

function attemptsToTimelineRows(attempts: QuizAttempt[]): TimelineRow[] {
  return attempts.map((a) => {
    const at = a.completedAt ? new Date(a.completedAt) : new Date();
    const typeLabel =
      a.quizType === 'ai' || a.quizType === 'ai_quiz'
        ? 'Completed AI quiz'
        : a.quizType === 'strict'
          ? 'Completed quiz'
          : 'Completed quiz';
    const detail = [a.interest, a.level, typeof a.score === 'number' ? `${Math.round(a.score)}%` : '']
      .filter(Boolean)
      .join(' · ');
    return {
      id: `quiz-${a.id}`,
      title: typeLabel,
      detail: detail || 'Quiz attempt',
      at: Number.isNaN(at.getTime()) ? new Date() : at,
    };
  });
}

// Countries list including Pakistan
const countries = [
  'Pakistan', 'Afghanistan', 'Albania', 'Algeria', 'Argentina', 'Australia', 'Austria', 'Bangladesh', 
  'Belgium', 'Brazil', 'Canada', 'China', 'Denmark', 'Egypt', 'Finland', 'France', 'Germany', 'Greece', 
  'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Italy', 'Japan', 'Jordan', 'Kenya', 'Kuwait', 
  'Malaysia', 'Mexico', 'Morocco', 'Netherlands', 'New Zealand', 'Nigeria', 'Norway', 'Oman', 
  'Philippines', 'Poland', 'Portugal', 'Qatar', 'Russia', 'Saudi Arabia', 'Singapore', 'South Africa', 
  'South Korea', 'Spain', 'Sri Lanka', 'Sweden', 'Switzerland', 'Thailand', 'Turkey', 'UAE', 
  'United Kingdom', 'United States', 'Vietnam'
].sort();

const Profile: React.FC = () => {
  const navigate = useNavigate();
  const { isAuthenticated } = useStore();

  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    bio: '',
    location: '',
    date_of_birth: '',
    learning_level: 'Beginner' as 'Beginner' | 'Intermediate' | 'Advanced',
    learning_goals: [] as string[],
    weekly_availability_hours: '' as number | string,
    content_format: 'Mixed' as 'Video' | 'Text' | 'Projects' | 'Mixed',
    focus_domains: [] as string[],
  });

  const [locationSuggestions, setLocationSuggestions] = useState<string[]>([]);
  const [showLocationDropdown, setShowLocationDropdown] = useState(false);

  const [quizTimelineRows, setQuizTimelineRows] = useState<TimelineRow[]>([]);
  const [attemptsForLevel, setAttemptsForLevel] = useState<QuizAttempt[]>([]);
  const [perfSnapshot, setPerfSnapshot] = useState<UserPerformance | null>(null);
  const [learningSignalsLoaded, setLearningSignalsLoaded] = useState(false);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [learningSyncState, setLearningSyncState] = useState<LearningSyncState>('idle');
  const [learningSyncMessage, setLearningSyncMessage] = useState('');
  const [lastLearningSyncBanner, setLastLearningSyncBanner] = useState<{ at: Date; detail: string } | null>(null);

  const lastSyncedLearningSig = useRef<string | null>(null);
  const learningSaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refreshLearningAndTimeline = useCallback(async () => {
    try {
      setTimelineLoading(true);
      const [attemptsRes, perfRes] = await Promise.allSettled([
        getQuizHistory(40),
        getUserPerformance(),
      ]);
      const attempts = attemptsRes.status === 'fulfilled' ? attemptsRes.value : [];
      const perf = perfRes.status === 'fulfilled' ? perfRes.value : null;
      setAttemptsForLevel(attempts);
      setPerfSnapshot(perf);
      setQuizTimelineRows(attemptsToTimelineRows(attempts.slice(0, 12)));
    } catch {
      setQuizTimelineRows([]);
      setAttemptsForLevel([]);
      setPerfSnapshot(null);
    } finally {
      setTimelineLoading(false);
      setLearningSignalsLoaded(true);
    }
  }, []);

  const performanceLearning = useMemo(
    () => deriveLearningLevelFromPerformance(attemptsForLevel, perfSnapshot),
    [attemptsForLevel, perfSnapshot],
  );

  useEffect(() => {
    if (!profile?.id) return;
    setFormData((prev) =>
      prev.learning_level === performanceLearning.level
        ? prev
        : { ...prev, learning_level: performanceLearning.level },
    );
  }, [performanceLearning.level, profile?.id]);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }
    fetchProfile();
  }, [isAuthenticated, navigate]);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      setError('');
      const data = (await getUserProfile()) as ProfileData;
      setProfile(data);
      setFormData({
        first_name: data.first_name || '',
        last_name: data.last_name || '',
        phone: data.phone || '',
        bio: data.bio || '',
        location: data.location || '',
        date_of_birth: data.date_of_birth ? String(data.date_of_birth).split('T')[0] : '',
        learning_level: (data.learning_level as ProfileData['learning_level']) || 'Beginner',
        learning_goals: data.learning_goals || [],
        weekly_availability_hours: data.weekly_availability_hours ?? '',
        content_format: (data.content_format as ProfileData['content_format']) || 'Mixed',
        focus_domains: data.focus_domains || [],
      });
      lastSyncedLearningSig.current = learningFieldsSignature({
        learning_level: data.learning_level || 'Beginner',
        learning_goals: data.learning_goals || [],
        weekly_availability_hours: data.weekly_availability_hours ?? '',
        content_format: data.content_format || 'Mixed',
        focus_domains: data.focus_domains || [],
      });
    } catch (err: unknown) {
      const e = asFetchNetworkError(err instanceof Error ? err : new Error(String(err)));
      setError(e.message || 'Failed to load profile');
      const msg = e.message.toLowerCase();
      if (
        msg.includes('not authenticated') ||
        msg.includes('token refresh') ||
        msg.includes('token has expired') ||
        msg.includes('invalid token') ||
        msg.includes('access token required')
      ) {
        navigate('/login');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    
    // Phone number validation - only allow digits and limit to 11
    if (name === 'phone') {
      const digitsOnly = value.replace(/\D/g, '');
      if (digitsOnly.length <= 11) {
        setFormData((prev) => ({ ...prev, [name]: digitsOnly }));
      }
      return;
    }
    
    // Location autocomplete
    if (name === 'location') {
      setFormData((prev) => ({ ...prev, [name]: value }));
      if (value.trim().length > 0) {
        const filtered = countries.filter(country =>
          country.toLowerCase().includes(value.toLowerCase())
        );
        setLocationSuggestions(filtered);
        setShowLocationDropdown(true);
      } else {
        setLocationSuggestions([]);
        setShowLocationDropdown(false);
      }
      return;
    }
    
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const selectLocation = (location: string) => {
    setFormData((prev) => ({ ...prev, location }));
    setShowLocationDropdown(false);
    setLocationSuggestions([]);
  };

  const toggleArrayValue = (key: 'learning_goals' | 'focus_domains', value: string) => {
    setFormData((prev) => {
      const exists = prev[key].includes(value);
      const updated = exists ? prev[key].filter((v) => v !== value) : [...prev[key], value];
      return { ...prev, [key]: updated };
    });
  };

  useEffect(() => {
    if (!profile?.id || !isAuthenticated) return;
    void refreshLearningAndTimeline();
    const interval = window.setInterval(() => void refreshLearningAndTimeline(), 45_000);
    const onVis = () => {
      if (document.visibilityState === 'visible') void refreshLearningAndTimeline();
    };
    document.addEventListener('visibilitychange', onVis);
    return () => {
      window.clearInterval(interval);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, [profile?.id, isAuthenticated, refreshLearningAndTimeline]);

  useEffect(() => {
    if (!profile || !isAuthenticated) return;

    const sig = learningFieldsSignature(formData);
    if (lastSyncedLearningSig.current === sig) return;

    if (learningSaveTimer.current) clearTimeout(learningSaveTimer.current);
    learningSaveTimer.current = window.setTimeout(async () => {
      const token = localStorage.getItem('plpg_access_token');
      if (!token) return;

      const weeklyRaw = formData.weekly_availability_hours;
      const weekly =
        weeklyRaw === '' || weeklyRaw === undefined ? null : Number(weeklyRaw);
      if (weekly !== null && (Number.isNaN(weekly) || weekly < 0 || weekly > 80)) {
        setLearningSyncState('error');
        setLearningSyncMessage('Weekly hours must be between 0 and 80.');
        return;
      }

      setLearningSyncState('saving');
      setLearningSyncMessage('');

      try {
        const response = await fetch(`${API_BASE_URL}/profile`, {
          method: 'PUT',
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            learning_level: formData.learning_level,
            content_format: formData.content_format,
            weekly_availability_hours: weekly,
            learning_goals: formData.learning_goals,
            focus_domains: formData.focus_domains,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            typeof errorData.detail === 'string' ? errorData.detail : 'Could not save learning preferences',
          );
        }

        const data = await response.json();
        const user = data.user as ProfileData;
        setProfile(user);
        setFormData((prev) => ({
          ...prev,
          learning_level: user.learning_level,
          learning_goals: user.learning_goals || [],
          weekly_availability_hours: user.weekly_availability_hours ?? '',
          content_format: user.content_format,
          focus_domains: user.focus_domains || [],
        }));

        lastSyncedLearningSig.current = learningFieldsSignature({
          learning_level: user.learning_level,
          learning_goals: user.learning_goals || [],
          weekly_availability_hours: user.weekly_availability_hours ?? '',
          content_format: user.content_format,
          focus_domains: user.focus_domains || [],
        });

        setLearningSyncState('saved');
        const detail = [
          user.learning_level,
          user.content_format,
          `${user.weekly_availability_hours ?? 0}h/wk`,
          user.learning_goals?.length ? `${user.learning_goals.length} goals` : null,
          user.focus_domains?.length ? `${user.focus_domains.length} focus areas` : null,
        ]
          .filter(Boolean)
          .join(' · ');
        setLastLearningSyncBanner({ at: new Date(), detail });
        void refreshLearningAndTimeline();
        window.setTimeout(() => setLearningSyncState('idle'), 2200);
      } catch (err: unknown) {
        setLearningSyncState('error');
        setLearningSyncMessage(err instanceof Error ? err.message : 'Save failed');
      }
    }, 700);

    return () => {
      if (learningSaveTimer.current) {
        window.clearTimeout(learningSaveTimer.current);
        learningSaveTimer.current = null;
      }
    };
  }, [
    profile,
    isAuthenticated,
    formData.learning_level,
    formData.content_format,
    formData.weekly_availability_hours,
    formData.learning_goals,
    formData.focus_domains,
    refreshLearningAndTimeline,
  ]);

  const mergedTimelineRows = useMemo(() => {
    const rows: TimelineRow[] = [...quizTimelineRows];
    if (lastLearningSyncBanner) {
      rows.push({
        id: 'learning-sync',
        title: 'Learning profile synced',
        detail: lastLearningSyncBanner.detail,
        at: lastLearningSyncBanner.at,
      });
    }
    return rows.sort((a, b) => b.at.getTime() - a.at.getTime()).slice(0, 14);
  }, [quizTimelineRows, lastLearningSyncBanner]);

  const handleSave = async () => {
    try {
      setSaving(true);
      setError('');
      setSuccess('');

      const token = localStorage.getItem('plpg_access_token');

      const response = await fetch(`${API_BASE_URL}/profile`, {
        method: 'PUT',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          weekly_availability_hours:
            formData.weekly_availability_hours === '' ? null : Number(formData.weekly_availability_hours),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update profile');
      }

      const data = await response.json();
      const user = data.user as ProfileData;
      setProfile(user);
      lastSyncedLearningSig.current = learningFieldsSignature({
        learning_level: user.learning_level,
        learning_goals: user.learning_goals || [],
        weekly_availability_hours: user.weekly_availability_hours ?? '',
        content_format: user.content_format,
        focus_domains: user.focus_domains || [],
      });
      setIsEditing(false);
      setSuccess('Changes saved.');
      setTimeout(() => setSuccess(''), 2500);
    } catch (err: any) {
      setError(err.message || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    if (profile) {
      setFormData({
        first_name: profile.first_name || '',
        last_name: profile.last_name || '',
        phone: profile.phone || '',
        bio: profile.bio || '',
        location: profile.location || '',
        date_of_birth: profile.date_of_birth ? profile.date_of_birth.split('T')[0] : '',
        learning_level: profile.learning_level || 'Beginner',
        learning_goals: profile.learning_goals || [],
        weekly_availability_hours: profile.weekly_availability_hours ?? '',
        content_format: profile.content_format || 'Mixed',
        focus_domains: profile.focus_domains || [],
      });
      lastSyncedLearningSig.current = learningFieldsSignature({
        learning_level: profile.learning_level || 'Beginner',
        learning_goals: profile.learning_goals || [],
        weekly_availability_hours: profile.weekly_availability_hours ?? '',
        content_format: profile.content_format || 'Mixed',
        focus_domains: profile.focus_domains || [],
      });
    }
    setIsEditing(false);
    setError('');
  };

  const getInitials = () => {
    if (!profile) return '?';
    return `${profile.first_name?.[0] || ''}${profile.last_name?.[0] || ''}`.toUpperCase() || '?';
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const completenessScore = () => {
    const fields = [
      formData.first_name,
      formData.last_name,
      profile?.email,
      formData.phone,
      formData.bio,
      formData.location,
      formData.date_of_birth,
      formData.learning_level,
      formData.content_format,
      formData.weekly_availability_hours,
    ];

    const lists = [formData.learning_goals, formData.focus_domains];

    const filled = fields.filter(Boolean).length + lists.reduce((acc, list) => acc + (list.length > 0 ? 1 : 0), 0);
    const total = fields.length + lists.length;
    return Math.min(100, Math.round((filled / total) * 100));
  };

  // Loading State
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 py-8 sm:py-12 md:py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          {/* Header Section Skeleton */}
          <div className="mb-8 sm:mb-12 md:mb-16 grid gap-6 lg:grid-cols-[2fr,1fr] items-start">
            <LoadingSkeleton variant="card" />
            <div className="grid gap-3 sm:gap-4">
              <LoadingSkeleton variant="card" count={3} />
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
            {/* Sidebar Skeleton */}
            <aside className="lg:col-span-1">
              <LoadingSkeleton variant="card" />
            </aside>

            {/* Main Content Skeleton */}
            <div className="lg:col-span-2 space-y-6 sm:space-y-8">
              <LoadingSkeleton variant="card" count={3} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error State
  if (error && !profile) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 flex items-center justify-center p-4">
        <ErrorState
          title="Unable to Load Profile"
          message="We couldn't retrieve your profile information. Please try again."
          onRetry={fetchProfile}
          onGoBack={() => navigate('/')}
          showRetry={true}
          showGoBack={true}
          icon="error"
        />
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-100 py-8 sm:py-12 md:py-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        {/* Header Section */}
        <div className="mb-8 sm:mb-12 md:mb-16 grid gap-6 lg:grid-cols-[2fr,1fr] items-start">
          <div className="bg-white rounded-2xl p-6 sm:p-8 shadow-lg border border-slate-100 hover:shadow-xl transition-shadow duration-300 transform hover:-translate-y-1 transition-transform">
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4 sm:gap-6">
              <div className="flex-1">
                <p className="text-xs sm:text-sm font-semibold text-indigo-600 uppercase tracking-wider mb-2">Profile & Account</p>
                <h1 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight text-slate-900 mb-2">Welcome back, {profile.first_name}</h1>
                <p className="text-sm sm:text-base text-slate-600 leading-relaxed max-w-2xl">Manage your identity, learning preferences, and account controls in one place.</p>
              </div>
              <div className="rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600 text-white px-4 sm:px-6 py-3 sm:py-4 shadow-lg transform hover:scale-105 transition-transform duration-300">
                <div className="text-xs uppercase tracking-widest opacity-90 font-semibold">Completion</div>
                <div className="text-3xl sm:text-4xl font-bold mt-1">{completenessScore()}%</div>
              </div>
            </div>
            <div className="mt-6 h-2.5 w-full rounded-full bg-slate-200 overflow-hidden">
              <div className="h-full bg-gradient-to-r from-indigo-600 to-purple-600 transition-all duration-500 ease-out" style={{ width: `${completenessScore()}%` }} />
            </div>
            <div className="mt-6 flex flex-wrap gap-2 sm:gap-3">
              {[
                { label: 'Content', value: formData.content_format },
                { label: 'Availability', value: `${formData.weekly_availability_hours || 'Set'}/week` }
              ].map((item, idx) => (
                <span key={idx} className="inline-flex items-center gap-2 px-3 sm:px-4 py-2 bg-gradient-to-r from-indigo-50 to-purple-50 text-slate-700 rounded-full text-xs sm:text-sm font-medium border border-indigo-100 hover:border-indigo-300 transition-colors duration-200">
                  <span className="w-2 h-2 rounded-full bg-indigo-600"></span>
                  {item.label}: {item.value}
                </span>
              ))}
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid gap-3 sm:gap-4">
            {[
              { icon: '📊', label: 'Learning level', value: formData.learning_level, color: 'from-indigo-500 to-purple-600' },
              { icon: '✓', label: 'Verification', value: profile.is_email_verified ? 'Verified' : 'Pending', color: profile.is_email_verified ? 'from-green-500 to-emerald-600' : 'from-amber-500 to-orange-600' },
              { icon: '👤', label: 'Account role', value: profile.role, color: 'from-slate-500 to-slate-600' }
            ].map((stat, idx) => (
              <div key={idx} className="bg-white rounded-xl p-4 sm:p-5 shadow-md border border-slate-100 hover:shadow-lg hover:border-slate-200 transition-all duration-300 transform hover:-translate-y-1">
                <div className="flex items-center gap-3 sm:gap-4">
                  <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg bg-gradient-to-br ${stat.color} flex items-center justify-center text-lg sm:text-xl shadow-md`}>
                    {stat.icon}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs sm:text-sm text-slate-600 font-medium">{stat.label}</p>
                    <p className="text-sm sm:text-base font-bold text-slate-900 truncate">{stat.value}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Success Message */}
        {success && (
          <div className="mb-6 sm:mb-8 flex items-start gap-3 sm:gap-4 rounded-xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-green-50 px-4 sm:px-6 py-3 sm:py-4 text-emerald-900 shadow-md animate-in fade-in slide-in-from-top-2 duration-300">
            <svg className="h-5 w-5 sm:h-6 sm:w-6 flex-shrink-0 mt-0.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="font-semibold text-sm sm:text-base">{success}</span>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 sm:mb-8 flex items-start gap-3 sm:gap-4 rounded-xl border border-rose-200 bg-gradient-to-r from-rose-50 to-red-50 px-4 sm:px-6 py-3 sm:py-4 text-rose-900 shadow-md animate-in fade-in slide-in-from-top-2 duration-300">
            <svg className="h-5 w-5 sm:h-6 sm:w-6 flex-shrink-0 mt-0.5 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M4.93 4.93l14.14 14.14M3 12a9 9 0 1118 0 9 9 0 01-18 0z" />
            </svg>
            <span className="font-semibold text-sm sm:text-base">{error}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 sm:gap-8">
          {/* Sidebar */}
          <aside className="lg:col-span-1 space-y-6">
            <div className="bg-white border border-slate-100 rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
              <div className="flex flex-col sm:flex-row sm:items-start gap-4 sm:gap-6">
                {profile.avatar ? (
                  <img src={profile.avatar} alt="Profile" className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl object-cover shadow-md" />
                ) : (
                  <div className="w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-indigo-600 to-purple-600 text-white flex items-center justify-center text-2xl sm:text-3xl font-bold shadow-md">
                    {getInitials()}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg sm:text-xl font-bold text-slate-900">{profile.first_name} {profile.last_name}</h3>
                  <p className="text-sm text-slate-600 truncate">{profile.email}</p>
                  <div className="flex flex-wrap gap-2 mt-3">
                    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold">{profile.role}</span>
                    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${profile.is_email_verified ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'}`}>
                      {profile.is_email_verified ? '✓ Verified' : '⚠ Unverified'}
                    </span>
                  </div>
                </div>
              </div>

              <dl className="mt-6 space-y-3 text-sm border-t border-slate-100 pt-6">
                {[
                  { label: 'Member since', value: formatDate(profile.created_at) },
                  { label: 'Email status', value: profile.is_email_verified ? 'Verified' : 'Unverified' },
                  { label: 'User ID', value: profile.id.slice(0, 8) + '...' }
                ].map((item, idx) => (
                  <div key={idx} className="flex justify-between items-start">
                    <dt className="text-slate-600 font-medium">{item.label}</dt>
                    <dd className="text-slate-900 font-semibold text-right">{item.value}</dd>
                  </div>
                ))}
              </dl>

              <div className="mt-6 flex gap-2 sm:gap-3">
                {!isEditing ? (
                  <button onClick={() => setIsEditing(true)} className="flex-1 px-4 py-2.5 sm:py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-lg hover:from-indigo-700 hover:to-purple-700 shadow-md hover:shadow-lg transform transition-all duration-200 hover:scale-105 font-semibold text-sm sm:text-base">
                    Edit Profile
                  </button>
                ) : (
                  <>
                    <button onClick={handleSave} disabled={saving} className="flex-1 px-4 py-2.5 sm:py-3 bg-gradient-to-r from-emerald-600 to-green-600 text-white rounded-lg hover:from-emerald-700 hover:to-green-700 shadow-md hover:shadow-lg transform transition-all duration-200 hover:scale-105 font-semibold text-sm sm:text-base disabled:opacity-60 disabled:cursor-not-allowed">
                      {saving ? 'Saving…' : 'Save'}
                    </button>
                    <button onClick={handleCancel} className="px-4 py-2.5 sm:py-3 border-2 border-slate-300 text-slate-700 rounded-lg hover:bg-slate-50 hover:border-slate-400 transition-all duration-200 font-semibold text-sm sm:text-base">
                      Cancel
                    </button>
                  </>
                )}
              </div>
            </div>
          </aside>

          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6 sm:space-y-8">
            <section className="bg-white border border-slate-100 rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
              <div className="mb-6">
                <h2 className="text-xl sm:text-2xl font-bold text-slate-900">Identity</h2>
                <p className="text-sm text-slate-600 mt-2">Keep your personal information accurate and up-to-date.</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                {[
                  { name: 'first_name', label: 'First name', type: 'text' },
                  { name: 'last_name', label: 'Last name', type: 'text' },
                ].map((field) => (
                  <div key={field.name}>
                    <label className="block text-sm font-semibold text-slate-900 mb-2">{field.label}</label>
                    <input
                      type={field.type}
                      name={field.name}
                      value={formData[field.name as keyof typeof formData] as string}
                      onChange={handleInputChange}
                      disabled={!isEditing}
                      className="w-full rounded-lg border-2 border-slate-200 px-4 py-3 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all duration-200 disabled:bg-slate-50 disabled:cursor-not-allowed"
                    />
                  </div>
                ))}
                
                {/* Phone Number Field with Validation */}
                <div>
                  <label className="block text-sm font-semibold text-slate-900 mb-2">
                    Phone
                    <span className="text-xs text-slate-500 ml-2">(Max 11 digits)</span>
                  </label>
                  <input
                    type="tel"
                    name="phone"
                    value={formData.phone}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    placeholder="03001234567"
                    maxLength={11}
                    className="w-full rounded-lg border-2 border-slate-200 px-4 py-3 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all duration-200 disabled:bg-slate-50 disabled:cursor-not-allowed"
                  />
                  {formData.phone && (
                    <p className="text-xs text-slate-500 mt-1">
                      {formData.phone.length}/11 digits
                    </p>
                  )}
                </div>

                {/* Location Field with Autocomplete */}
                <div className="relative">
                  <label className="block text-sm font-semibold text-slate-900 mb-2">Location</label>
                  <input
                    type="text"
                    name="location"
                    value={formData.location}
                    onChange={handleInputChange}
                    onFocus={() => {
                      if (formData.location && locationSuggestions.length > 0) {
                        setShowLocationDropdown(true);
                      }
                    }}
                    onBlur={() => {
                      // Delay to allow click on suggestion
                      setTimeout(() => setShowLocationDropdown(false), 200);
                    }}
                    disabled={!isEditing}
                    placeholder="Enter country name"
                    className="w-full rounded-lg border-2 border-slate-200 px-4 py-3 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all duration-200 disabled:bg-slate-50 disabled:cursor-not-allowed"
                  />
                  
                  {/* Location Dropdown */}
                  {showLocationDropdown && locationSuggestions.length > 0 && isEditing && (
                    <div className="absolute z-10 w-full mt-1 bg-white border-2 border-indigo-200 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                      {locationSuggestions.map((location, index) => (
                        <button
                          key={index}
                          type="button"
                          onClick={() => selectLocation(location)}
                          className="w-full text-left px-4 py-2.5 hover:bg-indigo-50 transition-colors duration-150 text-sm text-slate-700 hover:text-indigo-700 font-medium border-b border-slate-100 last:border-0"
                        >
                          {location}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-900 mb-2">Date of birth</label>
                  <input
                    type="date"
                    name="date_of_birth"
                    value={formData.date_of_birth}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    className="w-full rounded-lg border-2 border-slate-200 px-4 py-3 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all duration-200 disabled:bg-slate-50 disabled:cursor-not-allowed"
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="block text-sm font-semibold text-slate-900 mb-2">Bio</label>
                  <textarea
                    name="bio"
                    value={formData.bio}
                    onChange={handleInputChange}
                    disabled={!isEditing}
                    rows={3}
                    className="w-full rounded-lg border-2 border-slate-200 px-4 py-3 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all duration-200 disabled:bg-slate-50 disabled:cursor-not-allowed"
                    placeholder="Brief professional summary"
                  />
                </div>
              </div>
            </section>

            <section className="bg-white border border-slate-100 rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 space-y-6">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <h2 className="text-xl sm:text-2xl font-bold text-slate-900">Learning Profile</h2>
                  <p className="text-sm text-slate-600 mt-2">
                    Learning level is set automatically from your quiz scores and volume. Other preferences here still
                    save instantly — no need to press Save.
                  </p>
                </div>
                <div className="flex shrink-0 flex-col items-start gap-1 sm:items-end">
                  {learningSyncState === 'saving' && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-800">
                      <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-indigo-500" aria-hidden />
                      Saving…
                    </span>
                  )}
                  {learningSyncState === 'saved' && (
                    <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-800">
                      Saved to account
                    </span>
                  )}
                  {learningSyncState === 'error' && learningSyncMessage && (
                    <span className="max-w-xs rounded-lg bg-rose-50 px-3 py-1.5 text-xs font-medium text-rose-800">
                      {learningSyncMessage}
                    </span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                <div>
                  <label className="mb-2 flex flex-wrap items-center gap-2 text-sm font-semibold text-slate-900">
                    Learning level
                    <span className="rounded-md bg-violet-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-800">
                      System
                    </span>
                  </label>
                  <div className="min-h-[52px] rounded-lg border-2 border-violet-200/90 bg-gradient-to-br from-violet-50/80 to-slate-50 px-4 py-3">
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-base font-bold text-slate-900">{formData.learning_level}</p>
                        <p className="mt-1 text-xs leading-relaxed text-slate-600">{performanceLearning.detail}</p>
                      </div>
                      {timelineLoading && !learningSignalsLoaded ? (
                        <span className="shrink-0 text-xs font-medium text-violet-700">Analyzing…</span>
                      ) : null}
                    </div>
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-900 mb-2">Content format</label>
                  <select
                    value={formData.content_format}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        content_format: e.target.value as ProfileData['content_format'],
                      }))
                    }
                    className="w-full rounded-lg border-2 border-slate-200 px-4 py-3 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all duration-200"
                  >
                    {(['Video', 'Text', 'Projects', 'Mixed'] as const).map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-semibold text-slate-900 mb-2">Weekly availability (hours)</label>
                  <input
                    type="number"
                    min={0}
                    max={80}
                    value={formData.weekly_availability_hours}
                    onChange={(e) => setFormData((prev) => ({ ...prev, weekly_availability_hours: e.target.value }))}
                    className="w-full rounded-lg border-2 border-slate-200 px-4 py-3 text-sm focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 transition-all duration-200"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-3">Learning goals</label>
                <div className="flex flex-wrap gap-2">
                  {learningGoalOptions.map((goal) => {
                    const active = formData.learning_goals.includes(goal);
                    return (
                      <button
                        key={goal}
                        type="button"
                        onClick={() => toggleArrayValue('learning_goals', goal)}
                        className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] ${
                          active
                            ? 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-md ring-2 ring-indigo-200/60'
                            : 'bg-slate-100 text-slate-700 hover:bg-slate-200 ring-2 ring-transparent'
                        }`}
                      >
                        {goal}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-900 mb-3">Focus domains</label>
                <div className="flex flex-wrap gap-2">
                  {focusDomainOptions.map((domain) => {
                    const active = formData.focus_domains.includes(domain);
                    return (
                      <button
                        key={domain}
                        type="button"
                        onClick={() => toggleArrayValue('focus_domains', domain)}
                        className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 transform hover:scale-[1.02] active:scale-[0.98] ${
                          active
                            ? 'bg-gradient-to-r from-emerald-600 to-green-600 text-white shadow-md ring-2 ring-emerald-200/60'
                            : 'bg-slate-100 text-slate-700 hover:bg-slate-200 ring-2 ring-transparent'
                        }`}
                      >
                        {domain}
                      </button>
                    );
                  })}
                </div>
              </div>
            </section>

            <section className="bg-white border border-slate-100 rounded-2xl p-6 sm:p-8 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
              <div className="mb-6">
                <h2 className="text-xl sm:text-2xl font-bold text-slate-900">Account Summary</h2>
                <p className="text-sm text-slate-600 mt-2">Core account metadata and verification status.</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-6">
                {[
                  { label: 'Email', value: profile.email, status: profile.is_email_verified ? 'Verified' : 'Pending' },
                  { label: 'Role', value: profile.role },
                  { label: 'User ID', value: profile.id.slice(0, 12) + '...' },
                  { label: 'Member since', value: formatDate(profile.created_at) }
                ].map((item, idx) => (
                  <div key={idx} className="p-4 rounded-lg bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 hover:border-slate-300 transition-colors duration-200">
                    <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider mb-1">{item.label}</p>
                    <p className="text-sm sm:text-base font-bold text-slate-900 truncate">{item.value}</p>
                    {item.status && <p className="text-xs text-slate-600 mt-1">{item.status}</p>}
                  </div>
                ))}
              </div>
            </section>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="bg-white border border-slate-100 rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Recent activity</p>
                    <h3 className="text-lg font-bold text-slate-900 mt-1">Learning timeline</h3>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold ${
                      timelineLoading || learningSyncState === 'saving'
                        ? 'bg-violet-100 text-violet-800'
                        : 'bg-indigo-100 text-indigo-700'
                    }`}
                  >
                    <span
                      className={`h-2 w-2 rounded-full ${
                        timelineLoading || learningSyncState === 'saving' ? 'animate-pulse bg-rose-500' : 'bg-emerald-500'
                      }`}
                      aria-hidden
                    />
                    Live
                  </span>
                </div>
                <div className="space-y-4">
                  {mergedTimelineRows.length === 0 && !timelineLoading && (
                    <p className="text-sm text-slate-500 pl-6">
                      No activity yet. Finish a quiz or adjust your learning profile — updates appear here in real time.
                    </p>
                  )}
                  {mergedTimelineRows.map((item) => (
                    <div key={item.id} className="flex items-start gap-3 pb-4 border-b border-slate-100 last:border-0 last:pb-0">
                      <div className="mt-1.5 h-3 w-3 rounded-full bg-gradient-to-br from-indigo-600 to-purple-600 flex-shrink-0" aria-hidden />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-slate-900">{item.title}</p>
                        <p className="text-xs text-slate-600 mt-0.5 break-words">{item.detail}</p>
                      </div>
                      <p className="text-xs text-slate-500 flex-shrink-0 tabular-nums">{formatRelativeTime(item.at)}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-white border border-slate-100 rounded-2xl p-6 shadow-lg hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 flex flex-col">
                <div className="mb-4">
                  <p className="text-xs font-semibold text-slate-600 uppercase tracking-wider">Quick links</p>
                  <h3 className="text-lg font-bold text-slate-900 mt-1">Account & learning</h3>
                </div>
                <div className="grid grid-cols-2 gap-3 flex-1">
                  <button
                    onClick={() => navigate('/settings')}
                    className="px-4 py-3 rounded-lg bg-gradient-to-r from-indigo-50 to-purple-50 text-indigo-700 font-semibold text-sm hover:from-indigo-100 hover:to-purple-100 border border-indigo-200 hover:border-indigo-300 transition-all duration-200 transform hover:scale-105"
                  >
                    ⚙️ Settings
                  </button>
                  <button
                    onClick={() => navigate('/quizzes')}
                    className="px-4 py-3 rounded-lg bg-gradient-to-r from-emerald-50 to-green-50 text-emerald-700 font-semibold text-sm hover:from-emerald-100 hover:to-green-100 border border-emerald-200 hover:border-emerald-300 transition-all duration-200 transform hover:scale-105"
                  >
                    📝 Quizzes
                  </button>
                </div>
                <div className="mt-4 rounded-lg bg-gradient-to-r from-indigo-50 to-purple-50 text-indigo-900 px-4 py-3 text-xs sm:text-sm border border-indigo-200">
                  <p className="font-semibold">💡 Pro tip</p>
                  <p className="mt-1">Keep your preferences fresh for better recommendations.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
