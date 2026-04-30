import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Navigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import { getQuizAttempt, getUserPerformance, type QuizAttempt, type UserPerformance } from '../../services/quizService';

const QuizResults: React.FC = () => {
    const { attemptId } = useParams<{ attemptId: string }>();
    const navigate = useNavigate();
    const { isAuthenticated, user } = useStore();

    const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
    const [performance, setPerformance] = useState<UserPerformance | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (isAuthenticated && attemptId) {
            loadResults();
        }
    }, [isAuthenticated, attemptId]);

    const loadResults = async () => {
        try {
            setLoading(true);
            const [attemptData, perfData] = await Promise.all([
                getQuizAttempt(attemptId!),
                getUserPerformance(),
            ]);
            setAttempt(attemptData);
            setPerformance(perfData);
        } catch (error: any) {
            alert(error.message || 'Failed to load results');
            navigate('/quizzes');
        } finally {
            setLoading(false);
        }
    };

    // Auth check
    if (!isAuthenticated || !user) {
        return <Navigate to="/login" replace />;
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-slate-50 pt-24 pb-12">
                <div className="max-w-6xl mx-auto px-4">
                    <div className="text-center py-12">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
                        <p className="mt-4 text-slate-600">Loading results...</p>
                    </div>
                </div>
            </div>
        );
    }

    if (!attempt) {
        return null;
    }

    const scorePercentage = attempt.score;
    const scoreColor = scorePercentage >= 80 ? 'green' : scorePercentage >= 60 ? 'yellow' : 'red';

    return (
        <div className="min-h-screen bg-slate-50 pt-24 pb-12">
            <div className="max-w-6xl mx-auto px-4">
                {/* Score Header */}
                <div className={`bg-gradient-to-br ${scoreColor === 'green' ? 'from-green-600 to-emerald-600' :
                    scoreColor === 'yellow' ? 'from-yellow-600 to-amber-600' :
                        'from-red-600 to-rose-600'
                    } rounded-2xl shadow-xl p-8 mb-6 text-white text-center`}>
                    <div className="mb-4">
                        {scoreColor === 'green' ? (
                            <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                            </svg>
                        ) : scoreColor === 'yellow' ? (
                            <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                        ) : (
                            <svg className="w-16 h-16 mx-auto" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                            </svg>
                        )}
                    </div>
                    <h1 className="text-4xl font-bold mb-2">{scorePercentage}%</h1>
                    <p className="text-xl mb-1">
                        {scoreColor === 'green' ? 'Excellent Work!' : scoreColor === 'yellow' ? 'Good Job!' : 'Keep Practicing!'}
                    </p>
                    <p className="text-lg opacity-90">
                        You got {attempt.correctCount} out of {attempt.totalQuestions} questions correct
                    </p>
                </div>

                <div className="grid lg:grid-cols-3 gap-6 mb-6">
                    {/* Quiz Info */}
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                        <h3 className="text-sm font-semibold text-slate-700 mb-4">Quiz Details</h3>
                        <div className="space-y-3">
                            <div>
                                <p className="text-xs text-slate-500">Subject</p>
                                <p className="text-base font-semibold text-slate-900">{attempt.interest}</p>
                            </div>
                            <div>
                                <p className="text-xs text-slate-500">Difficulty</p>
                                <p className="text-base font-semibold text-slate-900">{attempt.level}</p>
                            </div>
                            <div>
                                <p className="text-xs text-slate-500">Completed</p>
                                <p className="text-base text-slate-700">{new Date(attempt.completedAt).toLocaleString()}</p>
                            </div>
                        </div>
                    </div>

                    {/* Performance Insights */}
                    {performance && performance.byInterest[attempt.interest] && (
                        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                            <h3 className="text-sm font-semibold text-slate-700 mb-4">{attempt.interest} Performance</h3>
                            <div className="space-y-3">
                                <div>
                                    <p className="text-xs text-slate-500">Total Quizzes</p>
                                    <p className="text-base font-semibold text-slate-900">
                                        {performance.byInterest[attempt.interest].totalQuizzes}
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-slate-500">Average Score</p>
                                    <p className="text-base font-semibold text-slate-900">
                                        {performance.byInterest[attempt.interest].averageScore}%
                                    </p>
                                </div>
                                <div>
                                    <p className="text-xs text-slate-500">Best Score</p>
                                    <p className="text-base font-semibold text-slate-900">
                                        {performance.byInterest[attempt.interest].bestScore}%
                                    </p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                        <h3 className="text-sm font-semibold text-slate-700 mb-4">What's Next?</h3>
                        <div className="space-y-3">
                            <button
                                onClick={() => navigate('/quizzes')}
                                className="w-full px-4 py-3 bg-indigo-600 text-white rounded-lg font-medium hover:bg-indigo-700 transition-colors"
                            >
                                Browse More Quizzes
                            </button>
                            <button
                                onClick={() => window.location.reload()}
                                className="w-full px-4 py-3 border-2 border-indigo-600 text-indigo-600 rounded-lg font-medium hover:bg-indigo-50 transition-colors"
                            >
                                Retake This Quiz
                            </button>
                            <button
                                onClick={() => navigate('/profile')}
                                className="w-full px-4 py-3 border-2 border-slate-300 text-slate-700 rounded-lg font-medium hover:bg-slate-50 transition-colors"
                            >
                                View Profile
                            </button>
                        </div>
                    </div>
                </div>

                {/* Recommendations */}
                {performance && performance.analysis && performance.analysis.recommendations.length > 0 && (
                    <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-6">
                        <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center gap-2">
                            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                            </svg>
                            Recommendations
                        </h3>
                        <ul className="space-y-2">
                            {performance.analysis.recommendations.map((rec, idx) => (
                                <li key={idx} className="text-blue-800 flex items-start gap-2">
                                    <span className="text-blue-600 mt-1">•</span>
                                    <span>{rec}</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

                {/* Question Review */}
                <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
                    <h2 className="text-xl font-bold text-slate-900 mb-6">Question Review</h2>
                    <div className="space-y-6">
                        {attempt.results && attempt.results.map((result, idx) => (
                            <div
                                key={idx}
                                className={`p-5 rounded-xl border-2 ${result.isCorrect
                                    ? 'border-green-200 bg-green-50'
                                    : 'border-red-200 bg-red-50'
                                    }`}
                            >
                                {/* Question Number and Status */}
                                <div className="flex items-start justify-between mb-3">
                                    <h3 className="font-semibold text-slate-900">Question {idx + 1}</h3>
                                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${result.isCorrect
                                        ? 'bg-green-600 text-white'
                                        : 'bg-red-600 text-white'
                                        }`}>
                                        {result.isCorrect ? '✓ Correct' : '✗ Incorrect'}
                                    </span>
                                </div>

                                {/* Question Text */}
                                <p className="text-slate-900 mb-4">{result.question}</p>

                                {/* Options */}
                                <div className="space-y-2 mb-4">
                                    {result.options.map((option, optIdx) => {
                                        const letter = option.charAt(0);
                                        const isUserAnswer = letter === result.userAnswer;
                                        const isCorrectAnswer = letter === result.correctAnswer;

                                        return (
                                            <div
                                                key={optIdx}
                                                className={`p-3 rounded-lg border ${isCorrectAnswer
                                                    ? 'border-green-500 bg-green-100'
                                                    : isUserAnswer && !result.isCorrect
                                                        ? 'border-red-500 bg-red-100'
                                                        : 'border-slate-200 bg-white'
                                                    }`}
                                            >
                                                <div className="flex items-center gap-2">
                                                    {isCorrectAnswer && (
                                                        <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                                                        </svg>
                                                    )}
                                                    {isUserAnswer && !result.isCorrect && (
                                                        <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
                                                            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                                                        </svg>
                                                    )}
                                                    <span className={`${isCorrectAnswer ? 'font-semibold text-green-900' :
                                                        isUserAnswer && !result.isCorrect ? 'font-semibold text-red-900' :
                                                            'text-slate-700'
                                                        }`}>
                                                        {option}
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>

                                {/* Explanation */}
                                <div className="bg-white rounded-lg p-4 border border-slate-200">
                                    <p className="text-sm font-semibold text-slate-700 mb-1">Explanation:</p>
                                    <p className="text-sm text-slate-600">{result.explanation}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default QuizResults;
