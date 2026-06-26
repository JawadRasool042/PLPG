import React, { useEffect, useState } from 'react';
import { useNavigate, useParams, Navigate } from 'react-router-dom';
import {
  AlertCircle,
  BookOpen,
  ListChecks,
  RotateCcw,
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import {
  extractLessonContent,
  getOrCreateRemediationLesson,
  getQuestionSections,
  getQuickRevision,
  getRetakeQuizId,
  markRemediationLessonStudied,
  type RemediationQuestionSection,
  type RemediationStatus,
} from '../../services/remediationService';
import { formatLessonExplanation } from '../../utils/lessonExplanation';

function sectionExplanation(section: RemediationQuestionSection): string {
  return section.explanation?.trim() || '';
}

const RemediationLessonPage: React.FC = () => {
  const { attemptId } = useParams<{ attemptId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user } = useStore();

  const [status, setStatus] = useState<RemediationStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [markingStudied, setMarkingStudied] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !attemptId) return;

    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getOrCreateRemediationLesson(attemptId);
        if (cancelled) return;
        setStatus(data);
        if (data.passed) {
          navigate(`/quiz/results/${attemptId}`, { replace: true });
        }
      } catch (err: unknown) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load remediation lesson');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, attemptId, navigate]);

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50 pt-24 pb-12">
        <div className="max-w-4xl mx-auto px-4 text-center py-16">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto" />
          <p className="mt-4 text-slate-600">Generating your personalized study guide…</p>
          <p className="mt-2 text-sm text-slate-500">
            Each section is organized by the topic your quiz question tested.
          </p>
        </div>
      </div>
    );
  }

  if (error || !status) {
    return (
      <div className="min-h-screen bg-slate-50 pt-24 pb-12">
        <div className="max-w-4xl mx-auto px-4">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
            <AlertCircle className="w-10 h-10 text-red-500 mx-auto mb-3" />
            <p className="text-red-800">{error || 'Lesson not available'}</p>
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="mt-4 px-4 py-2 text-sm font-medium text-red-700 border border-red-300 rounded-lg hover:bg-red-100"
            >
              Go back
            </button>
          </div>
        </div>
      </div>
    );
  }

  const lesson = extractLessonContent(status);
  const questionSections = getQuestionSections(lesson);
  const quickRevision = getQuickRevision(lesson);
  const retakeQuizId = getRetakeQuizId(status);
  const passingScore = status.passingScore ?? 70;

  const handleRetake = async () => {
    if (!status.lessonId || !retakeQuizId) return;
    try {
      setMarkingStudied(true);
      await markRemediationLessonStudied(status.lessonId);
      navigate(`/quiz/${retakeQuizId}`, {
        state: { remediationRetake: true, sourceAttemptId: attemptId },
      });
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Could not start retake');
    } finally {
      setMarkingStudied(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 pt-24 pb-12">
      <div className="max-w-4xl mx-auto px-4">
        <div className="bg-gradient-to-br from-amber-500 to-orange-600 rounded-2xl shadow-xl p-8 mb-6 text-white">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-white/20 rounded-xl">
              <BookOpen className="w-8 h-8" />
            </div>
            <div className="flex-1">
              <p className="text-amber-100 text-sm font-medium uppercase tracking-wide mb-1">
                Remediation lesson
              </p>
              <h1 className="text-3xl font-bold mb-2">{lesson?.title || 'Study before retaking'}</h1>
              <p className="text-amber-50/95 leading-relaxed">
                {lesson?.summary ||
                  'Review the concepts below — they are scoped strictly to the quiz you just took.'}
              </p>
              <p className="mt-3 text-sm text-amber-100">
                Your score: <strong>{Math.round(status.score ?? 0)}%</strong> · Passing:{' '}
                <strong>{passingScore}%</strong>
              </p>
            </div>
          </div>
        </div>

        {questionSections.length > 0 ? (
          <div className="space-y-6 mb-6">
            {questionSections.map((section) => (
              <section
                key={section.question_index}
                className={`bg-white rounded-xl shadow-sm border p-6 ${
                  section.is_correct ? 'border-emerald-200' : 'border-amber-200'
                }`}
              >
                <div className="flex flex-wrap items-center gap-2 mb-3">
                  <h2 className="text-xl font-bold text-slate-900">{section.topic}</h2>
                  <span
                    className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                      section.is_correct
                        ? 'bg-emerald-100 text-emerald-800'
                        : 'bg-amber-100 text-amber-800'
                    }`}
                  >
                    {section.is_correct ? 'Correct' : 'Needs review'}
                  </span>
                </div>

                <p className="text-sm font-medium text-slate-500 mb-2">
                  Quiz question {(section.question_index ?? 0) + 1}
                </p>
                <p className="font-medium text-slate-900 mb-4 leading-relaxed">{section.question}</p>

                <div className="grid sm:grid-cols-2 gap-3 text-sm mb-4">
                  <div
                    className={`rounded-lg p-3 ${
                      section.is_correct ? 'bg-slate-50 border border-slate-200' : 'bg-red-50 border border-red-100'
                    }`}
                  >
                    <span className="font-semibold text-slate-700">Your answer: </span>
                    <span className="text-slate-900">{section.your_answer || '—'}</span>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-100 rounded-lg p-3">
                    <span className="font-semibold text-emerald-800">Correct answer: </span>
                    <span className="text-emerald-900">{section.correct_answer || '—'}</span>
                  </div>
                </div>

                <div className="bg-slate-50 border border-slate-200 rounded-lg p-5">
                  <p className="text-sm font-semibold text-slate-900 mb-3">Explanation</p>
                  {sectionExplanation(section) ? (
                    <div>{formatLessonExplanation(sectionExplanation(section))}</div>
                  ) : (
                    <p className="text-sm text-slate-500 italic">
                      Explanation is being generated. Reload this page in a moment.
                    </p>
                  )}
                </div>
              </section>
            ))}
          </div>
        ) : (
          <section className="bg-amber-50 border border-amber-200 rounded-xl p-6 mb-6 text-center">
            <p className="text-amber-900 mb-4">Could not load lesson content for this attempt.</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-amber-600 text-white rounded-lg font-medium hover:bg-amber-700"
            >
              Reload lesson
            </button>
          </section>
        )}

        {quickRevision.length > 0 && (
          <section className="bg-indigo-50 border border-indigo-200 rounded-xl p-6 mb-6">
            <h2 className="text-lg font-bold text-indigo-900 mb-3 flex items-center gap-2">
              <ListChecks className="w-5 h-5" />
              Quick revision
            </h2>
            <ul className="space-y-2">
              {quickRevision.map((item, idx) => (
                <li key={idx} className="text-indigo-900 flex items-start gap-2">
                  <span className="font-bold text-indigo-600">{idx + 1}.</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <p className="text-sm text-slate-600">
            When you are ready, retake the <strong>exact same quiz</strong> to continue your learning
            path.
          </p>
          <button
            type="button"
            onClick={() => void handleRetake()}
            disabled={!retakeQuizId || markingStudied}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg font-semibold hover:bg-indigo-700 disabled:opacity-50 transition-colors shrink-0"
          >
            <RotateCcw className="w-4 h-4" />
            {markingStudied ? 'Starting retake…' : 'Retake quiz'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RemediationLessonPage;
