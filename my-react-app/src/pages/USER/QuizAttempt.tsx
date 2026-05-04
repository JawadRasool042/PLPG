import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Navigate, useLocation } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import { getQuiz, submitQuiz, submitMixedQuizAttempt, type Quiz, type MixedQuestion } from '../../services/quizService';

interface QuizData {
  isMixed: boolean;
  totalQuestions: number;
  domain?: string;
  difficulty?: string;
  level?: string;
  interest?: string;
  questions: MixedQuestion[] | Quiz['questions'];
  id?: string;
}

const QuizAttempt: React.FC = () => {
  const { quizId } = useParams<{ quizId: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user } = useStore();

  const [quiz, setQuiz] = useState<QuizData | null>(null);
  const [loading, setLoading] = useState(true);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [answers, setAnswers] = useState<Record<number, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);

  useEffect(() => {
    if (isAuthenticated && quizId) {
      loadQuiz();
    }
  }, [isAuthenticated, quizId]);

  const loadQuiz = async () => {
    try {
      setLoading(true);
      // If a quiz payload was passed via navigation state, use it (supports mixed quizzes)
      const stateQuiz: any = (location && (location.state as any)?.quiz) || null;
      if (stateQuiz) {
        // Detect mixed quiz by presence of question_count or first question having a "type"
        const isMixed = !!(stateQuiz.question_count || (stateQuiz.questions && stateQuiz.questions[0] && stateQuiz.questions[0].type));
        if (isMixed) {
          setQuiz({
            isMixed: true,
            totalQuestions: stateQuiz.question_count || stateQuiz.questions.length,
            domain: stateQuiz.domain,
            difficulty: stateQuiz.difficulty,
            questions: stateQuiz.questions,
            id: stateQuiz.id || stateQuiz.quiz_id,
          });
          return;
        }
        // Otherwise treat as legacy quiz payload
        if (stateQuiz.questions) {
          setQuiz({
            isMixed: false,
            totalQuestions: stateQuiz.totalQuestions || stateQuiz.questions.length,
            level: stateQuiz.level || stateQuiz.difficulty,
            interest: stateQuiz.interest || stateQuiz.domain,
            questions: stateQuiz.questions,
            id: stateQuiz.id || stateQuiz.quiz_id,
          });
          return;
        }
      }

      // Fallback: fetch legacy quiz by id
      if (quizId) {
        const quizData = await getQuiz(quizId!);
        setQuiz({
          isMixed: false,
          totalQuestions: quizData.totalQuestions,
          level: quizData.level,
          interest: quizData.interest,
          questions: quizData.questions,
          id: quizData.id,
        });
      }
    } catch (error: any) {
      alert(error.message || 'Failed to load quiz');
      navigate('/quizzes');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswerSelect = (answer: string) => {
    if (!quiz) return;
    const question: any = (quiz.questions as any[])[currentQuestion];
    const key = quiz.isMixed ? Number(question?.id ?? currentQuestion) : currentQuestion;
    setAnswers({
      ...answers,
      [key]: answer,
    });
  };

  const handleShortAnswerChange = (answer: string) => {
    if (!quiz) return;
    const question: any = (quiz.questions as any[])[currentQuestion];
    const key = quiz.isMixed ? Number(question?.id ?? currentQuestion) : currentQuestion;
    setAnswers({
      ...answers,
      [key]: answer,
    });
  };

  const handleNext = () => {
    if (quiz && currentQuestion < quiz.totalQuestions - 1) {
      setCurrentQuestion(currentQuestion + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion(currentQuestion - 1);
    }
  };

  const handleSubmit = async () => {
    if (!quiz) return;

    // Check if all questions are answered
    const unanswered = [];
    for (let i = 0; i < quiz.totalQuestions; i++) {
      const q: any = (quiz.questions as any[])[i];
      const key = quiz.isMixed ? Number(q?.id ?? i) : i;
      if (!answers[key] || answers[key].trim() === '') {
        unanswered.push(i + 1);
      }
    }

    if (unanswered.length > 0) {
      const confirm = window.confirm(
        `You haven't answered ${unanswered.length} question(s). Do you want to submit anyway?`
      );
      if (!confirm) return;
    }

    try {
      setSubmitting(true);
      let attempt;
      
      if (quiz.isMixed) {
        attempt = await submitMixedQuizAttempt(
          quiz.id!,
          answers,
          quiz.domain!,
          quiz.difficulty!,
          user!.id
        );
        // Mixed-quiz flow: continue to learning path (roadmap is generated server-side on demand).
        navigate(`/learning-path`, { state: { mixedAttempt: attempt } });
      } else {
        attempt = await submitQuiz(quizId!, answers);
        navigate(`/quiz/results/${attempt.id}`);
      }
    } catch (error: any) {
      alert(error.message || 'Failed to submit quiz');
    } finally {
      setSubmitting(false);
      setShowConfirmation(false);
    }
  };

  // Auth check
  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 pt-24 pb-12">
        <div className="max-w-4xl mx-auto px-4">
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
            <p className="mt-4 text-slate-600">Loading quiz...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!quiz) {
    return null;
  }

  const question = quiz.questions[currentQuestion];
  const progress = ((currentQuestion + 1) / quiz.totalQuestions) * 100;
  const isLastQuestion = currentQuestion === quiz.totalQuestions - 1;

  return (
    <div className="min-h-screen bg-slate-50 pt-24 pb-12">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">{quiz.isMixed ? quiz.domain : quiz.interest}</h1>
              <p className="text-sm text-slate-600">Level: {quiz.isMixed ? quiz.difficulty : quiz.level}</p>
            </div>
            <div className="text-right">
              <p className="text-sm text-slate-600">Question</p>
              <p className="text-2xl font-bold text-indigo-600">{currentQuestion + 1}/{quiz.totalQuestions}</p>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-slate-200 rounded-full h-2">
            <div
              className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        </div>

        {/* Question Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-6">
          <h2 className="text-xl font-semibold text-slate-900 mb-6">
            {(question as any).type === 'scenario' && (question as any).scenario_context ? (
              <span>
                <span className="block text-sm text-slate-500 mb-2">Scenario</span>
                <span className="block whitespace-pre-wrap">{(question as any).scenario_context}</span>
                <span className="block mt-4">{(question as any).q}</span>
              </span>
            ) : (
              (question as any).q
            )}
          </h2>

          {/* Mixed open-answer questions */}
          {quiz.isMixed && (((question as any).type === 'short_answer') || ((question as any).type === 'scenario')) ? (
            <div>
              <textarea
                value={answers[Number((question as any).id)] || ''}
                onChange={(e) => handleShortAnswerChange(e.target.value)}
                rows={5}
                className="w-full rounded-xl border border-slate-200 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition resize-none"
                placeholder="Type your answer..."
              />
              <p className="text-xs text-slate-500 mt-2">
                Tip: include key terms and explain briefly.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {(question as any).options.map((option: string, idx: number) => {
                const isTF = quiz.isMixed && (question as any).type === 'true_false';
                const letter = isTF ? option : option.charAt(0); // True/False uses full label
                const answerKey = quiz.isMixed ? Number((question as any).id) : currentQuestion;
                const isSelected = answers[answerKey] === letter;

                return (
                  <button
                    key={idx}
                    onClick={() => handleAnswerSelect(letter)}
                    className={`w-full text-left p-4 rounded-xl border-2 transition-all ${isSelected
                      ? 'border-indigo-600 bg-indigo-50'
                      : 'border-slate-200 hover:border-indigo-300 bg-white'
                      }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${isSelected
                        ? 'border-indigo-600 bg-indigo-600'
                        : 'border-slate-300'
                        }`}>
                        {isSelected && (
                          <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          </svg>
                        )}
                      </div>
                      <span className={`text-base ${isSelected ? 'text-indigo-900 font-medium' : 'text-slate-700'}`}>
                        {option}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between">
          <button
            onClick={handlePrevious}
            disabled={currentQuestion === 0}
            className="px-6 py-3 border-2 border-slate-300 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            Previous
          </button>

          {isLastQuestion ? (
            <button
              onClick={() => setShowConfirmation(true)}
              disabled={submitting}
              className="px-8 py-3 bg-green-600 text-white rounded-xl font-semibold hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {submitting ? 'Submitting...' : 'Submit Quiz'}
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </button>
          ) : (
            <button
              onClick={handleNext}
              className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors flex items-center gap-2"
            >
              Next
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
          )}
        </div>

        {/* Question Status Grid */}
        <div className="mt-8 bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="text-sm font-semibold text-slate-700 mb-3">Question Status</h3>
          <div className="grid grid-cols-10 gap-2">
            {Array.from({ length: quiz.totalQuestions }).map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentQuestion(idx)}
                className={`w-10 h-10 rounded-lg font-medium text-sm transition-all ${idx === currentQuestion
                  ? 'bg-indigo-600 text-white'
                  : answers[idx]
                    ? 'bg-green-100 text-green-700 border-2 border-green-300'
                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                  }`}
              >
                {idx + 1}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {showConfirmation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <h3 className="text-xl font-bold text-slate-900 mb-2">Submit Quiz?</h3>
            <p className="text-slate-600 mb-6">
              Are you sure you want to submit your quiz? You won't be able to change your answers after submission.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirmation(false)}
                className="flex-1 px-4 py-3 border-2 border-slate-300 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50"
              >
                {submitting ? 'Submitting...' : 'Submit'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default QuizAttempt;
