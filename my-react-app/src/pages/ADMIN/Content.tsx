import React, { useState } from 'react';
import { BookOpen, Plus, Search, X, Pencil, Trash2 } from 'lucide-react';

interface ContentItem {
  id: string;
  title: string;
  category: string;
  description: string;
  status: 'published' | 'draft';
  createdAt: string;
}

const CATEGORIES = ['Mathematics', 'Science', 'Language', 'Programming', 'Data Science', 'AI/ML'];

const Content: React.FC = () => {
  const [search, setSearch] = useState('');
  const [filterCategory, setFilterCategory] = useState('all');
  const [showModal, setShowModal] = useState(false);
  const [editItem, setEditItem] = useState<ContentItem | null>(null);
  const [items, setItems] = useState<ContentItem[]>([
    { id: '1', title: 'Intro to Python', category: 'Programming', description: 'Beginner Python course', status: 'published', createdAt: '2025-01-10' },
    { id: '2', title: 'Machine Learning Basics', category: 'AI/ML', description: 'Fundamentals of ML', status: 'published', createdAt: '2025-02-05' },
    { id: '3', title: 'Data Analysis with Pandas', category: 'Data Science', description: 'Learn pandas for data analysis', status: 'draft', createdAt: '2025-03-01' },
  ]);

  const [form, setForm] = useState({ title: '', category: CATEGORIES[0], description: '', status: 'draft' as 'published' | 'draft' });

  const filtered = items.filter(i => {
    const matchSearch = i.title.toLowerCase().includes(search.toLowerCase()) || i.description.toLowerCase().includes(search.toLowerCase());
    const matchCat = filterCategory === 'all' || i.category === filterCategory;
    return matchSearch && matchCat;
  });

  const openAdd = () => {
    setEditItem(null);
    setForm({ title: '', category: CATEGORIES[0], description: '', status: 'draft' });
    setShowModal(true);
  };

  const openEdit = (item: ContentItem) => {
    setEditItem(item);
    setForm({ title: item.title, category: item.category, description: item.description, status: item.status });
    setShowModal(true);
  };

  const handleSave = () => {
    if (!form.title.trim()) return;
    if (editItem) {
      setItems(prev => prev.map(i => i.id === editItem.id ? { ...i, ...form } : i));
    } else {
      setItems(prev => [...prev, { id: Date.now().toString(), ...form, createdAt: new Date().toISOString().split('T')[0] }]);
    }
    setShowModal(false);
  };

  const handleDelete = (id: string) => {
    if (confirm('Delete this content item?')) {
      setItems(prev => prev.filter(i => i.id !== id));
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Manage learning content</p>
          <h1 className="text-3xl font-bold text-slate-900 mt-1">Content Library</h1>
          <p className="text-sm text-slate-600 mt-1">{items.length} total items</p>
        </div>
        <button onClick={openAdd} className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors">
          <Plus className="h-4 w-4" />
          Add Content
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="h-5 w-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
          <input
            className="w-full pl-12 pr-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
            placeholder="Search content..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select
          value={filterCategory}
          onChange={(e) => setFilterCategory(e.target.value)}
          className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500"
        >
          <option value="all">All Categories</option>
          {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {/* Table */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <div className="p-12 text-center">
            <BookOpen className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-600 font-medium">No content found</p>
          </div>
        ) : (
          <table className="w-full">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Title</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Category</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Created</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-slate-700 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map(item => (
                <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4">
                    <p className="font-semibold text-slate-900">{item.title}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{item.description}</p>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100">
                      {item.category}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${item.status === 'published' ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                      {item.status === 'published' ? '✓ Published' : '⏳ Draft'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-slate-600">{item.createdAt}</td>
                  <td className="px-6 py-4 text-right">
                    <div className="inline-flex items-center gap-2">
                      <button onClick={() => openEdit(item)} className="p-2 rounded-lg hover:bg-slate-100 text-slate-600 transition-colors" title="Edit">
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button onClick={() => handleDelete(item.id)} className="p-2 rounded-lg hover:bg-rose-50 text-rose-600 transition-colors" title="Delete">
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

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200">
              <h3 className="text-lg font-bold text-slate-900">{editItem ? 'Edit Content' : 'Add Content'}</h3>
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
                  placeholder="Content title"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Category</label>
                <select
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                  value={form.category}
                  onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
                >
                  {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
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
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Status</label>
                <select
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500"
                  value={form.status}
                  onChange={e => setForm(f => ({ ...f, status: e.target.value as 'published' | 'draft' }))}
                >
                  <option value="draft">Draft</option>
                  <option value="published">Published</option>
                </select>
              </div>
            </div>
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-slate-200">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50">
                Cancel
              </button>
              <button onClick={handleSave} className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700">
                {editItem ? 'Save Changes' : 'Add Content'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Content;
