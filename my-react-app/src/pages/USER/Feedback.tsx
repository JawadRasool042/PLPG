import React, { useState } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';

const CATEGORIES = ['General', 'Quiz Quality', 'Learning Path', 'UI/UX', 'Bug Report', 'Feature Request'];
const RATINGS = [1, 2, 3, 4, 5];

const Feedback: React.FC = () => {
  const { isAuthenticated, user } = useStore();
  const navigate = useNavigate();
  const [form, setForm] = useState({ category: 'General', rating: 0, subject: '', message: '' });
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  if (!isAuthenticated || !user) return <Navigate to="/login" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.rating || !form.message.trim()) return;
    setSubmitting(true);
    // Simulate API call
    await new Promise(r => setTimeout(r, 800));
    setSubmitted(true);
    setSubmitting(false);
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
              onClick={() => navigate('/dashboard')}
              className="flex-1 px-4 py-3 bg-indigo-600 text-white rounded-xl font-medium hover:bg-indigo-700 transition-colors"
            >
              Back to Dashboard
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
                onClick={() => navigate('/dashboard')}
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
      </div>
    </div>
  );
};

export default Feedback;
