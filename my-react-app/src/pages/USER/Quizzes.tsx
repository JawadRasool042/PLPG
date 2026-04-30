import React, { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import {
  getQuizHistory,
  getUserPerformance,
  generateQuiz,
  type QuizAttempt,
  type UserPerformance,
} from '../../services/quizService';
import LoadingSkeleton from '../../components/LoadingSkeleton';
import EmptyState from '../../components/EmptyState';

const Quizzes: React.FC = () => {
  const { isAuthenticated, user, hasCompletedOnboarding, userInterests } = useStore();
  const navigate = useNavigate();

  const [history, setHistory] = useState<QuizAttempt[]>([]);
  const [performance, setPerformance] = useState<UserPerformance | null>(null);
  const [loading, setLoading] = useState(true);
  const [generatingQuiz, setGeneratingQuiz] = useState(false);
  const primaryInterest = userInterests?.primaryInterest;

  useEffect(() => {
    if (isAuthenticated && user) {
      loadData();
    }
  }, [isAuthenticated, user]);

  const loadData = async () => {
    try {
      setLoading(true);
      console.log('Loading quiz data...');

      const [hist, perf] = await Promise.all([
        getQuizHistory(10),
        getUserPerformance(),
      ]);

      console.log('History received:', hist);
      console.log('Performance received:', perf);

      setHistory(hist);
      setPerformance(perf);
    } catch (error: any) {
      console.error('Error loading quiz data:', error);
      console.error('Error details:', error.response?.data || error.message);
      alert(`Failed to load quiz data: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleStartQuiz = async () => {
    try {
      setGeneratingQuiz(true);
      if (!primaryInterest) {
        alert('Please complete the interest assessment first.');
        return;
      }
      const quiz = await generateQuiz(primaryInterest, 'Beginner');
      navigate(`/quiz/${quiz.id}`);
    } catch (error: any) {
      alert(error.message || 'Failed to generate quiz');
    } finally {
      setGeneratingQuiz(false);
    }
  };

  // If not authenticated, redirect to login
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" state={{ from: '/quizzes', message: 'Please log in to access quizzes.' }} replace />;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 pt-24 pb-12">
        <div className="max-w-6xl mx-auto px-4">
          {/* Welcome Section Skeleton */}
          <LoadingSkeleton variant="card" className="mb-6" />
          
          {/* Interest Check Status Skeleton */}
          <LoadingSkeleton variant="card" className="mb-6" />
          
          {/* Performance Overview Skeleton */}
          <LoadingSkeleton variant="card" className="mb-6" />
          
          {/* Available Quizzes Skeleton */}
          <div className="mb-6">
            <div className="h-8 bg-slate-200 rounded-lg w-48 mb-4 animate-pulse"></div>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              <LoadingSkeleton variant="card" count={6} />
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 pt-24 pb-12">
      <div className="max-w-6xl mx-auto px-4">
        {/* Welcome Section */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-6">
          <h1 className="text-2xl font-bold text-slate-900 mb-2">
            Welcome back, {user.firstName}! 👋
          </h1>
          <p className="text-slate-600">
            Your personalized quiz dashboard
          </p>
        </div>

        {/* Interest Check Status */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${hasCompletedOnboarding
                  ? 'bg-green-100 text-green-600'
                  : 'bg-amber-100 text-amber-600'
                  }`}>
                  {hasCompletedOnboarding ? (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  )}
                </div>
                <h2 className="text-xl font-semibold text-slate-900">
                  {hasCompletedOnboarding ? 'Interest Assessment Complete' : 'Complete Your Interest Assessment'}
                </h2>
              </div>

              {hasCompletedOnboarding && userInterests ? (
                <div className="ml-13">
                  <p className="text-slate-600 mb-4">
                    Your primary interest: <span className="font-semibold text-indigo-600">{userInterests.primaryInterest}</span>
                    <span className="text-slate-500 ml-2">({Math.round(userInterests.confidence)}% confidence)</span>
                  </p>
                  <div className="flex flex-wrap gap-2 mb-4">
                    {userInterests.allInterests.slice(0, 3).map((interest, index) => (
                      <span
                        key={index}
                        className="px-3 py-1 bg-indigo-50 text-indigo-700 rounded-full text-sm font-medium"
                      >
                        {interest.domain}
                      </span>
                    ))}
                  </div>
                  <button
                    onClick={() => navigate('/interest-check')}
                    className="text-indigo-600 hover:text-indigo-700 font-medium text-sm flex items-center gap-1"
                  >
                    Retake Assessment
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </button>
                </div>
              ) : (
                <div className="ml-13">
                  <p className="text-slate-600 mb-4">
                    Take a quick assessment to discover your learning interests and get personalized recommendations.
                  </p>
                  <button
                    onClick={() => navigate('/interest-check')}
                    className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors flex items-center gap-2"
                  >
                    Start Interest Assessment
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Performance Overview */}
        {performance && performance.overallStats.totalQuizzes > 0 && (
          <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl shadow-lg p-8 mb-6 text-white">
            <h2 className="text-xl font-bold mb-6">Your Performance</h2>
            <div className="grid md:grid-cols-4 gap-6">
              <div>
                <p className="text-indigo-200 text-sm mb-1">Total Quizzes</p>
                <p className="text-3xl font-bold">{performance.overallStats.totalQuizzes}</p>
              </div>
              <div>
                <p className="text-indigo-200 text-sm mb-1">Average Score</p>
                <p className="text-3xl font-bold">{performance.overallStats.averageScore}%</p>
              </div>
              <div>
                <p className="text-indigo-200 text-sm mb-1">Best Score</p>
                <p className="text-3xl font-bold">{performance.overallStats.bestScore}%</p>
              </div>
              <div>
                <p className="text-indigo-200 text-sm mb-1">Accuracy</p>
                <p className="text-3xl font-bold">
                  {performance.overallStats.totalQuestions > 0
                    ? Math.round((performance.overallStats.totalCorrect / performance.overallStats.totalQuestions) * 100)
                    : 0}%
                </p>
              </div>
            </div>
          </div>
        )}

        {/* AI-Generated Quiz */}
        <div className="mb-6">
          <h2 className="text-2xl font-bold text-slate-900 mb-4">AI-Generated Quiz</h2>

          {hasCompletedOnboarding && primaryInterest ? (
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <div className="flex items-center justify-between flex-col sm:flex-row gap-4">
                <div>
                  <p className="text-sm text-slate-500">Based on your assessment</p>
                  <h3 className="text-xl font-semibold text-slate-900 mt-1">
                    {primaryInterest}
                  </h3>
                  <p className="text-xs text-slate-500 mt-2">
                    Quiz is generated in real time using DeepSeek.
                  </p>
                </div>
                <button
                  onClick={handleStartQuiz}
                  disabled={generatingQuiz}
                  className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {generatingQuiz ? 'Generating...' : 'Generate AI Quiz'}
                </button>
              </div>
            </div>
          ) : (
            <EmptyState
              icon={
                <svg className="w-16 h-16 sm:w-20 sm:h-20 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              }
              title="Complete Interest Assessment"
              description="We need your interest profile to generate a personalized AI quiz."
              actionLabel="Start Assessment"
              onAction={() => navigate('/interest-check')}
            />
          )}
        </div>

        {/* Recent Quiz History */}
        {history.length > 0 && (
          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">Recent Quizzes</h2>
            <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
              <table className="w-full">
                <thead className="bg-slate-50 border-b border-slate-200">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase">Interest</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase">Level</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase">Score</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-slate-700 uppercase">Date</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {history.map((attempt) => (
                    <tr key={attempt.id} className="hover:bg-slate-50 cursor-pointer" onClick={() => navigate(`/quiz/results/${attempt.id}`)}>
                      <td className="px-6 py-4 text-sm text-slate-900">{attempt.interest}</td>
                      <td className="px-6 py-4 text-sm text-slate-600">{attempt.level}</td>
                      <td className="px-6 py-4">
                        <span className={`inline-flex px-3 py-1 rounded-full text-sm font-medium ${attempt.score >= 80 ? 'bg-green-100 text-green-700' :
                          attempt.score >= 60 ? 'bg-yellow-100 text-yellow-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                          {attempt.score}% ({attempt.correctCount}/{attempt.totalQuestions})
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-slate-600">
                        {new Date(attempt.completedAt).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default Quizzes;
