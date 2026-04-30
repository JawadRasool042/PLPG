import React, { useState } from 'react';
import { Shield, Plus, Search, X, Pencil, Trash2 } from 'lucide-react';

interface LearningPath {
  id: string;
  title: string;
  domain: string;
  level: 'Beginner' | 'Intermediate' | 'Advanced';
  description: string;
  status: 'active' | 'draft';
  steps: number;
  createdAt: string;
}

const DOMAINS = ['AI/ML', 'Web Development', 'Data Science', 'Cybersecurity', 'Cloud Computing', 'Mobile Development'];
const LEVELS = ['Beginner', 'Intermediate', 'Advanced'] as const;

const LearningPaths: React.FC = () => {
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState<LearningPath | null>(null);
  const [paths, setPaths] = useState<LearningPath[]>([
    { id: '1', title: 'AI/ML Beginner Track', domain: 'AI/ML', level: 'Beginner', description: 'Start your AI journey', status: 'active', steps: 8, createdAt: '2025-01-15' },
    { id: '2', title: 'Full Stack Web Dev', domain: 'Web Development', level: 'Intermediate', description: 'React + Node.js path', status: 'active', steps: 12, createdAt: '2025-02-10' },
    { id: '3', title: 'Data Science Pro', domain: 'Data Science', level: 'Advanced', description: 'Advanced data analysis', status: 'draft', steps: 10, createdAt: '2025-03-05' },
  ]);

  const [form, setForm] = useState({ title: '', domain: DOMAINS[0], level: 'Beginner' as typeof LEVELS[number], description: '', status: 'draft' as 'active' | 'draft', steps: 5 });

  const filtered = paths.filter(p =>
    p.title.toLowerCase().includes(search.toLowerCase()) ||
    p.domain.toLowerCase().includes(search.toLowerCase())
  );

  const openAdd = () => {
    setEditItem(null);
    setForm({ title: '', domain: DOMAINS[0], level: 'Beginner', description: '', status: 'draft', steps: 5 });
    setShowModal(true);
  };

  const openEdit = (item: LearningPath) => {
    setEditItem(item);
    setForm({ title: item.title, domain: item.domain, level: item.level, description: item.description, status: item.status, steps: item.steps });
    setShowModal(true);
  };

  const handleSave = () => {
    if (!form.title.trim()) return;
    if (editItem) {
      setPaths(prev => prev.map(p => p.id === editItem.id ? { ...p, ...form } : p));
    } else {
      setPaths(prev => [...prev, { id: Date.now().toString(), ...form, createdAt: new Date().toISOString().split('T')[0] }]);
    }
    setShowModal(false);
  };

  const handleDelete = (id: string) => {
    if (confirm('Delete this learning path?')) {
      setPaths(prev => prev.filter(p => p.id !== id));
    }
  };

  const levelColor = (level: string) => {
    if (level === 'Beginner') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (level === 'Intermediate') return 'bg-amber-50 text-amber-700 border-amber-200';
    return 'bg-rose-50 text-rose-700 border-rose-200';
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Manage learning paths</p>
          <h1 className="text-3xl font-bold text-slate-900 mt-1">Learning Paths</h1>
          <p className="text-sm text-slate-600 mt-1">{paths.length} total paths</p>
        </div>
        <button onClick={openAdd} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors">
          <Plus className="h-4 w-4" />
          Create Path
        </button>
      </div>

      <div className="relative">
        <Search className="h-5 w-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
        <input
          className="w-full pl-12 pr-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
          placeholder="Search learning paths..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <Shield className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-600 font-medium">No learning paths found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Path</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Domain</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Level</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Steps</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-slate-700 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map(path => (
                <tr key={path.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <p className="font-semibold text-slate-900">{path.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{path.description}</p>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {path.domain}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${levelColor(path.level)}`}>
                      {path.level}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-700 font-medium">{path.steps} steps</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${path.status === 'active' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                      {path.status === 'active' ? '✓ Active' : '⏳ Draft'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="inline-flex items-center gap-2">
                      <button onClick={() => openEdit(path)} className="p-2 rounded-lg hover:bg-slate-100 text-slate-600 transition-colors">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => handleDelete(path.id)} className="p-2 rounded-lg hover:bg-rose-50 text-rose-600 transition-colors">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-bold text-slate-900">{editItem ? 'Edit Learning Path' : 'Create Learning Path'}</h3>
              <button onClick={() => setShowModal(false)} className="p-2 hover:bg-slate-100 rounded-lg">
                <X className="h-5 w-5 text-slate-500" />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Title</label>
                <input
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  value={form.title}
                  onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
                  placeholder="Path title"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Domain</label>
                  <select
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                    value={form.domain}
                    onChange={e => setForm(f => ({ ...f, domain: e.target.value }))}
                  >
                    {DOMAINS.map(d => <option key={d} value={d}>{d}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Level</label>
                  <select
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                    value={form.level}
                    onChange={e => setForm(f => ({ ...f, level: e.target.value as typeof LEVELS[number] }))}
                  >
                    {LEVELS.map(l => <option key={l} value={l}>{l}</option>)}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                <textarea
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 resize-none"
                  rows={3}
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  placeholder="Brief description"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Steps</label>
                  <input
                    type="number"
                    min={1}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                    value={form.steps}
                    onChange={e => setForm(f => ({ ...f, steps: parseInt(e.target.value) || 1 }))}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
                  <select
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                    value={form.status}
                    onChange={e => setForm(f => ({ ...f, status: e.target.value as 'active' | 'draft' }))}
                  >
                    <option value="draft">Draft</option>
                    <option value="active">Active</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-200">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50">
                Cancel
              </button>
              <button onClick={handleSave} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700">
                {editItem ? 'Save Changes' : 'Create Path'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default LearningPaths;
