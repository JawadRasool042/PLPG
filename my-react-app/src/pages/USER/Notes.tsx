import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useStore } from '../../store/useStore';

const API = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api';
const TOKEN_KEY = 'plpg_access_token';

const apiFetch = async (path: string) => {
  const res = await fetch(`${API}${path}`, {
    headers: { Authorization: `Bearer ${localStorage.getItem(TOKEN_KEY)}` }
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
};

interface NoteSection {
  heading: string;
  text: string;
  key_points: string[];
}

interface Note {
  _id: string;
  interest: string;
  topic: string;
  order: number;
  emoji: string;
  readTime: string;
  summary: string;
  content?: NoteSection[];
}

const INTEREST_COLORS: Record<string, string> = {
  'AI/ML': 'from-purple-500 to-indigo-600',
  'Web Development': 'from-blue-500 to-cyan-600',
  'Cybersecurity': 'from-red-500 to-rose-600',
  'Data Science': 'from-green-500 to-emerald-600',
  'Mobile Development': 'from-orange-500 to-amber-600',
  'Cloud Computing': 'from-sky-500 to-blue-600',
  'Game Development': 'from-violet-500 to-purple-600',
  'Coding': 'from-slate-600 to-gray-700',
};

const Notes: React.FC = () => {
  const { isAuthenticated, userInterests } = useStore();
  const navigate = useNavigate();
  const [notes, setNotes] = useState<Note[]>([]);
  const [readIds, setReadIds] = useState<string[]>([]);
  const [selectedNote, setSelectedNote] = useState<Note | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeInterest, setActiveInterest] = useState<string>('all');

  useEffect(() => {
    if (!isAuthenticated) { navigate('/login'); return; }
    loadNotes();
  }, [isAuthenticated]);

  const loadNotes = async () => {
    try {
      const [notesRes, progressRes] = await Promise.all([
        apiFetch('/notes'),
        apiFetch('/notes/progress/me')
      ]);
      setNotes(notesRes.data || []);
      setReadIds(progressRes.readNoteIds || []);

      // Default to user's primary interest
      if (userInterests?.primaryInterest) {
        const mapped = mapInterest(userInterests.primaryInterest);
        setActiveInterest(mapped);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const openNote = async (note: Note) => {
    try {
      const res = await apiFetch(`/notes/${note._id}`);
      setSelectedNote(res.data);
      if (!readIds.includes(note._id)) {
        setReadIds(prev => [...prev, note._id]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const mapInterest = (primary: string) => {
    const map: Record<string, string> = {
      'AI & Machine Learning': 'AI/ML',
      'Artificial Intelligence': 'AI/ML',
    };
    return map[primary] || primary;
  };

  const interests = ['all', ...Array.from(new Set(notes.map(n => n.interest)))];
  const filtered = activeInterest === 'all' ? notes : notes.filter(n => n.interest === activeInterest);
  const grouped = filtered.reduce((acc, note) => {
    if (!acc[note.interest]) acc[note.interest] = [];
    acc[note.interest].push(note);
    return acc;
  }, {} as Record<string, Note[]>);

  const totalRead = notes.filter(n => readIds.includes(n._id)).length;

  if (loading) return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 flex items-center justify-center">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-slate-600">Loading notes...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50 pt-24 pb-12">
      <div className="max-w-6xl mx-auto px-4">

        {/* Header */}
        <div className="mb-8 flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">📚 Learning Notes</h1>
            <p className="text-slate-600 mt-1">Study these notes before taking quizzes to improve your score</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-indigo-600">{totalRead}/{notes.length}</p>
            <p className="text-sm text-slate-500">notes read</p>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-semibold text-slate-700">Overall Progress</span>
            <span className="text-sm font-bold text-indigo-600">{notes.length > 0 ? Math.round((totalRead / notes.length) * 100) : 0}%</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-3">
            <div
              className="bg-gradient-to-r from-indigo-500 to-purple-500 h-3 rounded-full transition-all duration-500"
              style={{ width: `${notes.length > 0 ? (totalRead / notes.length) * 100 : 0}%` }}
            />
          </div>
          {totalRead === notes.length && notes.length > 0 && (
            <p className="text-sm text-emerald-600 font-semibold mt-2">🎉 All notes read! You're ready for quizzes.</p>
          )}
        </div>

        {/* Interest Filter Tabs */}
        <div className="flex gap-2 flex-wrap mb-6">
          {interests.map(interest => (
            <button
              key={interest}
              onClick={() => setActiveInterest(interest)}
              className={`px-4 py-2 rounded-full text-sm font-semibold transition-all ${
                activeInterest === interest
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-white text-slate-600 border border-slate-200 hover:border-indigo-300'
              }`}
            >
              {interest === 'all' ? '📚 All Topics' : interest}
            </button>
          ))}
        </div>

        {/* Notes Grid */}
        {Object.entries(grouped).map(([interest, interestNotes]) => (
          <div key={interest} className="mb-8">
            <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r ${INTEREST_COLORS[interest] || 'from-slate-500 to-slate-600'} text-white text-sm font-bold mb-4`}>
              {interest}
              <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs">
                {interestNotes.filter(n => readIds.includes(n._id)).length}/{interestNotes.length} read
              </span>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {interestNotes.map(note => {
                const isRead = readIds.includes(note._id);
                return (
                  <button
                    key={note._id}
                    onClick={() => openNote(note)}
                    className={`text-left bg-white rounded-2xl border-2 p-5 hover:shadow-md transition-all ${
                      isRead ? 'border-emerald-200 bg-emerald-50/30' : 'border-slate-200 hover:border-indigo-300'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <span className="text-3xl">{note.emoji}</span>
                      {isRead ? (
                        <span className="text-xs font-bold text-emerald-600 bg-emerald-100 px-2 py-1 rounded-full">✓ Read</span>
                      ) : (
                        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded-full">{note.readTime}</span>
                      )}
                    </div>
                    <h3 className="font-bold text-slate-900 mb-2 leading-tight">{note.topic}</h3>
                    <p className="text-sm text-slate-500 leading-relaxed">{note.summary}</p>
                    <div className="mt-3 flex items-center gap-1 text-indigo-600 text-sm font-semibold">
                      <span>Read note</span>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))}

        {/* CTA */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 rounded-2xl p-6 text-white flex items-center justify-between">
          <div>
            <h3 className="font-bold text-lg">Ready to test your knowledge?</h3>
            <p className="text-indigo-100 text-sm mt-1">Take quizzes based on what you've learned</p>
          </div>
          <button
            onClick={() => navigate('/quizzes')}
            className="px-6 py-3 bg-white text-indigo-600 rounded-xl font-bold hover:bg-indigo-50 transition-colors"
          >
            Take Quiz →
          </button>
        </div>
      </div>

      {/* Note Detail Modal */}
      {selectedNote && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={() => setSelectedNote(null)}>
          <div
            className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className={`bg-gradient-to-r ${INTEREST_COLORS[selectedNote.interest] || 'from-indigo-500 to-purple-600'} p-6 text-white rounded-t-2xl`}>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-4xl">{selectedNote.emoji}</span>
                  <div>
                    <p className="text-white/70 text-sm">{selectedNote.interest}</p>
                    <h2 className="text-xl font-bold">{selectedNote.topic}</h2>
                  </div>
                </div>
                <button onClick={() => setSelectedNote(null)} className="w-8 h-8 bg-white/20 rounded-lg flex items-center justify-center hover:bg-white/30 transition-colors">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <p className="text-white/80 text-sm mt-3">{selectedNote.summary}</p>
            </div>

            {/* Modal Content */}
            <div className="p-6 space-y-6">
              {selectedNote.content?.map((section, i) => (
                <div key={i}>
                  <h3 className="text-lg font-bold text-slate-900 mb-2 flex items-center gap-2">
                    <span className="w-6 h-6 bg-indigo-100 text-indigo-600 rounded-full flex items-center justify-center text-xs font-bold">{i + 1}</span>
                    {section.heading}
                  </h3>
                  <p className="text-slate-700 leading-relaxed mb-3">{section.text}</p>
                  <div className="bg-indigo-50 rounded-xl p-4 border border-indigo-100">
                    <p className="text-xs font-bold text-indigo-600 uppercase tracking-wide mb-2">Key Points</p>
                    <ul className="space-y-1.5">
                      {section.key_points.map((point, j) => (
                        <li key={j} className="flex items-start gap-2 text-sm text-slate-700">
                          <span className="text-indigo-500 mt-0.5 flex-shrink-0">•</span>
                          {point}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}

              {/* Footer */}
              <div className="flex gap-3 pt-2 border-t border-slate-200">
                <button
                  onClick={() => setSelectedNote(null)}
                  className="flex-1 py-3 border border-slate-200 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors"
                >
                  Close
                </button>
                <button
                  onClick={() => { setSelectedNote(null); navigate('/quizzes'); }}
                  className="flex-1 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
                >
                  Take Quiz on {selectedNote.interest} →
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Notes;
