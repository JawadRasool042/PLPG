import React, { useEffect, useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';
import {
  submitFeedback,
  getMyFeedback,
  type FeedbackCategory,
  type FeedbackRecord,
} from '../../services/feedbackService';

const CATEGORIES: FeedbackCategory[] = [
  'General',
  'Quiz Quality',
  'Learning Path',
  'UI/UX',
  'Bug Report',
  'Feature Request',
];
const RATINGS = [1, 2, 3, 4, 5];

const STATUS_LABELS: Record<string, { label: string; classes: string }> = {
  new: { label: 'New', classes: 'bg-blue-100 text-blue-700' },
  in_review: { label: 'In Review', classes: 'bg-amber-100 text-amber-700' },
  resolved: { label: 'Resolved', classes: 'bg-emerald-100 text-emerald-700' },
  dismissed: { label: 'Dismissed', classes: 'bg-slate-100 text-slate-600' },
};

const Feedback: React.FC = () => {
  const { isAuthenticated, user } = useStore();
  const navigate = useNavigate();
  const [form, setForm] = useState<{ category: FeedbackCategory; rating: number; subject: string; message: string }>(
    { category: 'General', rating: 0, subject: '', message: '' }
  );
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<FeedbackRecord[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const loadHistory = async () => {
    if (!isAuthenticated) return;
    try {
      setHistoryLoading(true);
      const items = await getMyFeedback(10);
      setHistory(items);
    } catch (err) {
      console.warn('Failed to load feedback history', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    void loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated]);

  if (!isAuthenticated || !user) return <Navigate to="/login" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.rating || !form.message.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await submitFeedback({
        category: form.category,
        rating: form.rating,
        subject: form.subject.trim() || undefined,
        message: form.message.trim(),
        page: window.location.pathname,
      });
      setSubmitted(true);
      void loadHistory();
    } catch (err: any) {
      setError(err?.message || 'Failed to submit feedback. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12 flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-sm border border-slate-200 p-10 text-center">
          <div className="w-20 h-20 bg-emerald-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-3">Thank You! 🎉</h2>
          <p className="text-slate-600 mb-8">Your feedback has been submitted. We appreciate you helping us improve!</p>
          <div className="flex gap-3">
            <button
              onClick={() => { setSubmitted(false); setForm({ category: 'General', rating: 0, subject: '', message: '' }); }}
              className="flex-1 px-4 py-3 border border-slate-200 text-slate-700 rounded-xl font-medium hover:bg-slate-50 transition-colors"
            >
              Send More
            </button>
            <button
              onClick={() => {
                if (window.confirm('Go back to Home?')) {
                  navigate('/home');
                }
              }}
              className="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
            >
              Back to Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Send Feedback 💬</h1>
          <p className="text-slate-600">Help us improve your learning experience</p>
        </div>

        <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
          <form onSubmit={handleSubmit} className="space-y-6">

            {/* Inline error */}
            {error && (
              <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-xl px-4 py-3 text-sm">
                {error}
              </div>
            )}

            {/* Category */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Category</label>
              <div className="flex flex-wrap gap-2">
                {CATEGORIES.map(cat => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setForm(f => ({ ...f, category: cat }))}
                    className={`px-4 py-2 rounded-xl text-sm font-medium border transition-all ${
                      form.category === cat
                        ? 'bg-indigo-600 text-white border-indigo-600'
                        : 'bg-white text-slate-600 border-slate-200 hover:border-indigo-300'
                    }`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            </div>

            {/* Rating */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Overall Rating <span className="text-rose-500">*</span>
              </label>
              <div className="flex gap-2">
                {RATINGS.map(r => (
                  <button
                    key={r}
                    type="button"
                    onClick={() => setForm(f => ({ ...f, rating: r }))}
                    className={`text-3xl transition-transform hover:scale-110 ${r <= form.rating ? 'opacity-100' : 'opacity-30'}`}
                  >
                    ⭐
                  </button>
                ))}
                {form.rating > 0 && (
                  <span className="ml-2 text-sm text-slate-500 self-center">
                    {['', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent'][form.rating]}
                  </span>
                )}
              </div>
            </div>

            {/* Subject */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Subject</label>
              <input
                type="text"
                value={form.subject}
                onChange={e => setForm(f => ({ ...f, subject: e.target.value }))}
                placeholder="Brief subject (optional)"
                className="w-full px-4 py-3 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              />
            </div>

            {/* Message */}
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                Message <span className="text-rose-500">*</span>
              </label>
              <textarea
                value={form.message}
                onChange={e => setForm(f => ({ ...f, message: e.target.value }))}
                placeholder="Tell us what you think, what's working well, or what could be improved..."
                rows={5}
                required
                className="w-full px-4 py-3 border border-slate-200 rounded-xl text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
              />
              <p className="text-xs text-slate-400 mt-1">{form.message.length}/500 characters</p>
            </div>

            {/* Submit */}
            <div className="flex gap-3 pt-2">
              <button
                type="button"
                onClick={() => {
                  if (window.confirm('Go back to Home?')) {
                    navigate('/home');
                  }
                }}
                className="flex-1 px-6 py-3 border border-slate-200 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting || !form.rating || !form.message.trim()}
                className="flex-1 px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {submitting ? 'Sending...' : 'Send Feedback'}
              </button>
            </div>
          </form>
        </div>

        {/* My Feedback History */}
        <div className="mt-8 bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold text-slate-900">Your Recent Feedback</h2>
            <button
              type="button"
              onClick={() => void loadHistory()}
              className="text-sm text-indigo-600 hover:underline font-medium"
            >
              {historyLoading ? 'Refreshing...' : 'Refresh'}
            </button>
          </div>

          {historyLoading && history.length === 0 ? (
            <p className="text-sm text-slate-500">Loading...</p>
          ) : history.length === 0 ? (
            <p className="text-sm text-slate-500">
              You haven't submitted any feedback yet. Use the form above to share your thoughts.
            </p>
          ) : (
            <ul className="space-y-3">
              {history.map(item => {
                const status = STATUS_LABELS[item.status] || STATUS_LABELS.new;
                return (
                  <li
                    key={item.id}
                    className="rounded-xl border border-slate-200 p-4 hover:border-indigo-200 transition-colors"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                          {item.category}
                        </span>
                        {item.rating > 0 && (
                          <span className="text-xs text-amber-500">{'⭐'.repeat(item.rating)}</span>
                        )}
                      </div>
                      <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${status.classes}`}>
                        {status.label}
                      </span>
                    </div>
                    {item.subject && (
                      <p className="font-semibold text-slate-900 mb-1">{item.subject}</p>
                    )}
                    <p className="text-sm text-slate-600 whitespace-pre-wrap">{item.message}</p>
                    {item.adminNote && (
                      <div className="mt-3 bg-emerald-50 border border-emerald-100 rounded-lg p-3">
                        <p className="text-xs font-semibold text-emerald-700 mb-1">Admin response</p>
                        <p className="text-sm text-emerald-800 whitespace-pre-wrap">{item.adminNote}</p>
                      </div>
                    )}
                    <p className="mt-2 text-xs text-slate-400">
                      {item.createdAt ? new Date(item.createdAt).toLocaleString() : ''}
                    </p>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
};

export default Feedback;
