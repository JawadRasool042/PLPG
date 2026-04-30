import React, { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import { getUserPerformance, getQuizHistory, type UserPerformance, type QuizAttempt } from '../../services/quizService';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import EmptyState from '../../components/EmptyState';

const Dashboard: React.FC = () => {
  const { isAuthenticated, user, hasCompletedOnboarding, userInterests } = useStore();
  const navigate = useNavigate();
  const [performance, setPerformance] = useState<UserPerformance | null>(null);
  const [history, setHistory] = useState<QuizAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [dismissedMotivation, setDismissedMotivation] = useState(false);

  // Motivational messages pool
  const motivationalMessages = [
    { emoji: '🚀', text: 'Keep going! Every quiz you complete brings you closer to mastery.', color: 'from-indigo-500 to-purple-600' },
    { emoji: '🌟', text: "You're doing great! Consistency is the key to learning success.", color: 'from-emerald-500 to-teal-600' },
    { emoji: '💡', text: 'New knowledge unlocked! Your brain is growing stronger every day.', color: 'from-amber-500 to-orange-600' },
    { emoji: '🎯', text: "Stay focused! You're on the right path to achieving your goals.", color: 'from-rose-500 to-pink-600' },
    { emoji: '🏆', text: 'Champions are made through daily practice. Keep it up!', color: 'from-blue-500 to-indigo-600' },
  ];
  const todayMsg = motivationalMessages[new Date().getDay() % motivationalMessages.length];

  useEffect(() => {
    if (isAuthenticated && user) {
      loadData();
    }
  }, [isAuthenticated, user]);

  const loadData = async () => {
    try {
      const [perf, hist] = await Promise.allSettled([
        getUserPerformance(),
        getQuizHistory(5),
      ]);
      if (perf.status === 'fulfilled') setPerformance(perf.value);
      if (hist.status === 'fulfilled') setHistory(hist.value);
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Generate personalized learning path based on interests
  const getLearningPath = () => {
    if (!userInterests) return [];
    const primary = userInterests.primaryInterest;
    const paths: Record<string, { steps: string[]; icon: string }> = {
      'AI & Machine Learning': { icon: '🤖', steps: ['Python Basics', 'Data Structures', 'Statistics', 'ML Algorithms', 'Deep Learning', 'Projects'] },
      'Web Development': { icon: '🌐', steps: ['HTML & CSS', 'JavaScript', 'React/Vue', 'Node.js', 'Databases', 'Deploy'] },
      'Data Science': { icon: '📊', steps: ['Python', 'Pandas & NumPy', 'Data Viz', 'Statistics', 'ML Models', 'Capstone'] },
      'Cybersecurity': { icon: '🔐', steps: ['Networking', 'Linux Basics', 'Ethical Hacking', 'Cryptography', 'Pen Testing', 'Certifications'] },
      'Coding': { icon: '💻', steps: ['Programming Basics', 'Algorithms', 'Data Structures', 'OOP', 'Design Patterns', 'Projects'] },
      'Mobile Development': { icon: '📱', steps: ['UI/UX Basics', 'React Native', 'APIs', 'State Management', 'Testing', 'Publish'] },
      'Cloud Computing': { icon: '☁️', steps: ['Cloud Basics', 'AWS/Azure', 'Networking', 'DevOps', 'Security', 'Certifications'] },
      'Game Development': { icon: '🎮', steps: ['Game Design', 'Unity/Unreal', 'C# Basics', 'Physics', '3D Modeling', 'Publish'] },
    };
    return paths[primary] || { icon: '📚', steps: ['Fundamentals', 'Core Concepts', 'Practice', 'Projects', 'Advanced', 'Mastery'] };
  };

  const learningPath = getLearningPath();
  const completedSteps = performance ? Math.min(Math.floor(performance.overallStats.totalQuizzes / 2), (learningPath as any).steps?.length ?? 0) : 0;

  // Download final results as text file
  const handleDownloadResults = () => {
    if (!performance || !user) return;
    const lines = [
      `PERSONALIZED LEARNING PATH GENERATOR`,
      `Final Results Report`,
      `Generated: ${new Date().toLocaleString()}`,
      ``,
      `Student: ${user.firstName} ${user.lastName}`,
      `Email: ${user.email}`,
      ``,
      `=== PERFORMANCE SUMMARY ===`,
      `Total Quizzes Taken: ${performance.overallStats.totalQuizzes}`,
      `Average Score: ${performance.overallStats.averageScore}%`,
      `Best Score: ${performance.overallStats.bestScore}%`,
      `Total Questions Answered: ${performance.overallStats.totalQuestions}`,
      `Correct Answers: ${performance.overallStats.totalCorrect}`,
      `Overall Accuracy: ${performance.overallStats.totalQuestions > 0 ? Math.round((performance.overallStats.totalCorrect / performance.overallStats.totalQuestions) * 100) : 0}%`,
      ``,
      `=== LEARNING INTERESTS ===`,
      userInterests ? `Primary Interest: ${userInterests.primaryInterest} (${Math.round(userInterests.confidence)}% confidence)` : 'Not assessed yet',
      ...(userInterests?.allInterests.slice(0, 5).map(i => `  - ${i.domain}: ${Math.round(i.confidence * 100)}%`) ?? []),
      ``,
      `=== PERFORMANCE BY TOPIC ===`,
      ...Object.entries(performance.byInterest).map(([topic, stats]) =>
        `${topic}: ${stats.averageScore}% avg (${stats.totalQuizzes} quizzes)`
      ),
      ``,
      `=== STRENGTHS ===`,
      ...(performance.analysis.strengths.map(s => `  ✓ ${s.interest}: ${s.score}%`)),
      ``,
      `=== AREAS TO IMPROVE ===`,
      ...(performance.analysis.weaknesses.map(w => `  ✗ ${w.interest}: ${w.score}%`)),
      ``,
      `=== RECOMMENDATIONS ===`,
      ...(performance.analysis.recommendations.map(r => `  • ${r}`)),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${user.firstName}_${user.lastName}_results.txt`;
    document.body.appendChild(a);
    a.click();
    URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  // If not authenticated, redirect to login
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: '/dashboard' }} replace />;
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
          <h1 className="text-4xl font-bold text-slate-900 mb-2">
            Welcome back, {user.firstName}! 👋
          </h1>
          <p className="text-lg text-slate-600">
            Your personalized learning dashboard
          </p>
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
                <h2 className="text-2xl font-bold mb-3">
                  🎯 Start Your Learning Journey
                </h2>
                <p className="text-indigo-100 mb-6 text-lg leading-relaxed">
                  Welcome to your dashboard! Let's personalize your experience. Start with the <strong>Interest Checker</strong> to tell us what topics you enjoy. We'll generate a short, personalized quiz from your choices. Complete it to unlock a tailored learning path designed just for you.
                </p>
                <div className="flex flex-wrap gap-4">
                  <button
                    onClick={() => navigate('/interest-check')}
                    className="px-8 py-4 bg-white text-indigo-600 rounded-xl font-semibold hover:bg-indigo-50 transition-all shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center gap-3"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                    Take Interest Assessment
                  </button>
                  <div className="flex items-center gap-2 text-indigo-100">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-sm">Takes only 5 minutes</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Completed Onboarding - Show Interests */}
        {hasCompletedOnboarding && userInterests && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8">
            <div className="flex items-start justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-900 mb-2">
                  Your Learning Profile
                </h2>
                <p className="text-slate-600">
                  Based on your interest assessment
                </p>
              </div>
              <button
                onClick={() => navigate('/interest-check')}
                className="px-4 py-2 text-indigo-600 hover:bg-indigo-50 rounded-lg font-medium transition-colors flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Retake Assessment
              </button>
              <button
                onClick={() => navigate('/learning-path')}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg font-medium transition-colors flex items-center gap-2 hover:bg-indigo-700"
              >
                View Full Path →
              </button>            </div>

            <div className="grid md:grid-cols-2 gap-6">
              {/* Primary Interest */}
              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-100">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-12 h-12 bg-indigo-600 rounded-xl flex items-center justify-center">
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-sm text-indigo-600 font-medium">Primary Interest</p>
                    <h3 className="text-xl font-bold text-slate-900">{userInterests.primaryInterest}</h3>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 bg-white rounded-full h-3 overflow-hidden">
                    <div 
                      className="bg-gradient-to-r from-indigo-600 to-purple-600 h-full rounded-full transition-all"
                      style={{ width: `${Math.round(userInterests.confidence)}%` }}
                    ></div>
                  </div>
                  <span className="text-sm font-semibold text-indigo-600">
                    {Math.round(userInterests.confidence)}%
                  </span>
                </div>
              </div>

              {/* Top Interests */}
              <div className="bg-slate-50 rounded-xl p-6 border border-slate-200">
                <h3 className="text-sm font-semibold text-slate-700 mb-4">Your Top Interests</h3>
                <div className="space-y-3">
                  {userInterests.allInterests.slice(0, 3).map((interest, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <span className="text-slate-900 font-medium">{interest.domain}</span>
                      <span className="text-sm text-slate-600">
                        {Math.round(interest.confidence * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Motivational Message (#12) */}
        {!dismissedMotivation && (
          <div className={`bg-gradient-to-r ${todayMsg.color} rounded-2xl p-6 mb-8 text-white relative`}>
            <button
              onClick={() => setDismissedMotivation(true)}
              className="absolute top-4 right-4 text-white/70 hover:text-white text-xl leading-none"
            >×</button>
            <div className="flex items-center gap-4">
              <span className="text-4xl">{todayMsg.emoji}</span>
              <div>
                <p className="text-sm font-medium text-white/80 mb-1">Daily Motivation</p>
                <p className="text-lg font-semibold">{todayMsg.text}</p>
              </div>
            </div>
          </div>
        )}

        {/* Personalized Learning Path (#5) */}
        {hasCompletedOnboarding && userInterests && (learningPath as any).steps && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-900">
                  {(learningPath as any).icon} Your Learning Path
                </h2>
                <p className="text-slate-600 mt-1">Personalized for <strong>{userInterests.primaryInterest}</strong></p>
              </div>
              <button
                onClick={() => navigate('/quizzes')}
                className="px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors"
              >
                Continue Learning →
              </button>
            </div>
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              {(learningPath as any).steps.map((step: string, i: number) => (
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
                    <span className={`text-xs font-medium text-center w-16 ${i <= completedSteps ? 'text-slate-700' : 'text-slate-400'}`}>
                      {step}
                    </span>
                  </div>
                  {i < (learningPath as any).steps.length - 1 && (
                    <div className={`flex-shrink-0 h-0.5 w-8 mt-[-16px] ${i < completedSteps ? 'bg-emerald-400' : 'bg-slate-200'}`} />
                  )}
                </React.Fragment>
              ))}
            </div>
            <div className="mt-4 flex items-center gap-3">
              <div className="flex-1 bg-slate-100 rounded-full h-2">
                <div
                  className="bg-gradient-to-r from-indigo-500 to-emerald-500 h-2 rounded-full transition-all"
                  style={{ width: `${(completedSteps / (learningPath as any).steps.length) * 100}%` }}
                />
              </div>
              <span className="text-sm font-semibold text-slate-700">
                {completedSteps}/{(learningPath as any).steps.length} completed
              </span>
            </div>
          </div>
        )}

        {/* Resume Lessons (#6) */}
        {history.length > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-2xl font-bold text-slate-900">📖 Resume Where You Left Off</h2>
              <button onClick={() => navigate('/quizzes')} className="text-sm text-indigo-600 hover:underline font-medium">
                View All →
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
                      <p className="font-semibold text-slate-900">{attempt.interest}</p>
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

        {/* Quick Actions */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          {/* Take Quiz */}
          <button
            onClick={() => navigate('/quizzes')}
            className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 hover:shadow-lg transition-all text-left group"
          >
            <div className="w-14 h-14 bg-indigo-100 rounded-xl flex items-center justify-center mb-4 group-hover:bg-indigo-600 transition-colors">
              <svg className="w-7 h-7 text-indigo-600 group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2">Take a Quiz</h3>
            <p className="text-slate-600">Test your knowledge and track your progress</p>
          </button>

          {/* View Profile */}
          <button
            onClick={() => navigate('/profile')}
            className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 hover:shadow-lg transition-all text-left group"
          >
            <div className="w-14 h-14 bg-purple-100 rounded-xl flex items-center justify-center mb-4 group-hover:bg-purple-600 transition-colors">
              <svg className="w-7 h-7 text-purple-600 group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2">Your Profile</h3>
            <p className="text-slate-600">Manage your account and preferences</p>
          </button>

          {/* Settings */}
          <button
            onClick={() => navigate('/settings')}
            className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 hover:shadow-lg transition-all text-left group"
          >
            <div className="w-14 h-14 bg-slate-100 rounded-xl flex items-center justify-center mb-4 group-hover:bg-slate-600 transition-colors">
              <svg className="w-7 h-7 text-slate-600 group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2">Settings</h3>
            <p className="text-slate-600">Customize your learning experience</p>
          </button>

          {/* Send Feedback */}
          <button
            onClick={() => navigate('/feedback')}
            className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 hover:shadow-lg transition-all text-left group"
          >
            <div className="w-14 h-14 bg-emerald-100 rounded-xl flex items-center justify-center mb-4 group-hover:bg-emerald-600 transition-colors">
              <svg className="w-7 h-7 text-emerald-600 group-hover:text-white transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-slate-900 mb-2">Send Feedback</h3>
            <p className="text-slate-600">Share your thoughts and suggestions</p>
          </button>
        </div>

        {/* Performance Overview and Learning Curve Chart */}
        {performance && performance.overallStats.totalQuizzes > 0 && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8">
              <h2 className="text-2xl font-bold text-slate-900 mb-6">Your Performance</h2>
              
              <div className="grid md:grid-cols-4 gap-6 mb-8">
                <div className="text-center">
                  <div className="w-16 h-16 bg-indigo-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <svg className="w-8 h-8 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <p className="text-3xl font-bold text-slate-900 mb-1">
                    {performance.overallStats.totalQuizzes}
                  </p>
                  <p className="text-sm text-slate-600">Quizzes Taken</p>
                </div>

                <div className="text-center">
                  <div className="w-16 h-16 bg-green-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <p className="text-3xl font-bold text-slate-900 mb-1">
                    {performance.overallStats.averageScore}%
                  </p>
                  <p className="text-sm text-slate-600">Average Score</p>
                </div>

                <div className="text-center">
                  <div className="w-16 h-16 bg-yellow-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <svg className="w-8 h-8 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                    </svg>
                  </div>
                  <p className="text-3xl font-bold text-slate-900 mb-1">
                    {performance.overallStats.bestScore}%
                  </p>
                  <p className="text-sm text-slate-600">Best Score</p>
                </div>

                <div className="text-center">
                  <div className="w-16 h-16 bg-purple-100 rounded-2xl flex items-center justify-center mx-auto mb-3">
                    <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <p className="text-3xl font-bold text-slate-900 mb-1">
                    {performance.overallStats.totalQuestions > 0
                      ? Math.round((performance.overallStats.totalCorrect / performance.overallStats.totalQuestions) * 100)
                      : 0}%
                  </p>
                  <p className="text-sm text-slate-600">Accuracy</p>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => navigate('/quizzes')}
                  className="flex-1 px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
                >
                  View All Quizzes
                </button>
                <button
                  onClick={handleDownloadResults}
                  className="flex items-center gap-2 px-6 py-3 border border-slate-200 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors"
                  title="Download Final Results"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  Download Results
                </button>
              </div>
            </div>
        )}

        {/* Learning Curve Chart - Show for all users with completed onboarding */}
        {hasCompletedOnboarding && (
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-2xl font-bold text-slate-900 mb-2">Learning Progress</h2>
                <p className="text-slate-600">Your performance trend over time</p>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center gap-2 px-3 py-1.5 bg-green-50 text-green-700 rounded-lg text-sm font-medium">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                  Improving
                </span>
              </div>
            </div>

            {/* Chart Container */}
            <div className="relative h-80 bg-gradient-to-br from-slate-50 to-indigo-50 rounded-xl p-6 pb-12 border border-slate-200">
              {/* Y-axis labels */}
              <div className="absolute left-2 top-6 bottom-12 w-10 flex flex-col justify-between text-xs text-slate-500">
                <span>100%</span>
                <span>75%</span>
                <span>50%</span>
                <span>25%</span>
                <span>0%</span>
              </div>

              {/* Chart area */}
              <div className="ml-14 mr-4 h-full pb-8 relative">
                {/* Grid lines */}
                <div className="absolute inset-0 flex flex-col justify-between pb-8">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <div key={i} className="border-t border-slate-200"></div>
                  ))}
                </div>

                {/* SVG Line Chart */}
                <svg className="absolute inset-0 w-full pb-8" style={{ height: 'calc(100% - 2rem)' }} viewBox="0 0 100 100" preserveAspectRatio="none">
                  {/* Gradient definition */}
                  <defs>
                    <linearGradient id="lineGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#6366f1" />
                      <stop offset="100%" stopColor="#a855f7" />
                    </linearGradient>
                    <linearGradient id="areaGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                      <stop offset="0%" stopColor="#6366f1" stopOpacity="0.3" />
                      <stop offset="100%" stopColor="#a855f7" stopOpacity="0.05" />
                    </linearGradient>
                  </defs>

                  {/* Area under curve */}
                  <path
                    d="M 0 20 L 14.28 25 L 28.56 30 L 42.84 35 L 57.12 45 L 71.4 50 L 85.68 65 L 100 80 L 100 100 L 0 100 Z"
                    fill="url(#areaGradient)"
                  />

                  {/* Line */}
                  <path
                    d="M 0 20 L 14.28 25 L 28.56 30 L 42.84 35 L 57.12 45 L 71.4 50 L 85.68 65 L 100 80"
                    fill="none"
                    stroke="url(#lineGradient)"
                    strokeWidth="0.8"
                    vectorEffect="non-scaling-stroke"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>

                {/* Data points - positioned absolutely */}
                <div className="absolute inset-0 pb-8" style={{ height: 'calc(100% - 2rem)' }}>
                  {[
                    { x: 0, y: 20, label: 'Week 1' },
                    { x: 14.28, y: 25, label: 'Week 2' },
                    { x: 28.56, y: 30, label: 'Week 3' },
                    { x: 42.84, y: 35, label: 'Week 4' },
                    { x: 57.12, y: 45, label: 'Week 5' },
                    { x: 71.4, y: 50, label: 'Week 6' },
                    { x: 85.68, y: 65, label: 'Week 7' },
                    { x: 100, y: 80, label: 'Week 8' },
                  ].map((point, i) => (
                    <div
                      key={i}
                      className="absolute"
                      style={{
                        left: `${point.x}%`,
                        top: `${point.y}%`,
                        transform: 'translate(-50%, -50%)'
                      }}
                    >
                      <div className="w-3 h-3 bg-white border-2 border-indigo-600 rounded-full hover:w-4 hover:h-4 transition-all cursor-pointer shadow-sm"></div>
                    </div>
                  ))}
                </div>

                {/* X-axis labels */}
                <div className="absolute bottom-0 left-0 right-0 flex justify-between text-xs text-slate-500">
                  <span>Week 1</span>
                  <span>Week 2</span>
                  <span>Week 3</span>
                  <span>Week 4</span>
                  <span>Week 5</span>
                  <span>Week 6</span>
                  <span>Week 7</span>
                  <span>Week 8</span>
                </div>
              </div>
            </div>

            {/* Legend and Stats */}
            <div className="mt-8 grid md:grid-cols-3 gap-4">
              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl p-4 border border-indigo-100">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900">+15%</p>
                    <p className="text-xs text-slate-600">Improvement</p>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border border-green-100">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900">8</p>
                    <p className="text-xs text-slate-600">Week Streak</p>
                  </div>
                </div>
              </div>

              <div className="bg-gradient-to-br from-yellow-50 to-orange-50 rounded-xl p-4 border border-yellow-100">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-yellow-600 rounded-lg flex items-center justify-center">
                    <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-slate-900">85%</p>
                    <p className="text-xs text-slate-600">This Week</p>
                  </div>
                </div>
              </div>
            </div>

             
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
            title="Ready to Start Learning?"
            description="You've completed your interest assessment! Now it's time to test your knowledge with personalized quizzes."
            actionLabel="Browse Quizzes"
            onAction={() => navigate('/quizzes')}
          />
        )}
      </div>
    </div>
  );
};

export default Dashboard;
