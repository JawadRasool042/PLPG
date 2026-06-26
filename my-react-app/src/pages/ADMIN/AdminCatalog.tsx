import React, { useCallback, useEffect, useState } from 'react';
import {
  Briefcase,
  BookOpen,
  Route,
  GitBranch,
  Database,
  Plus,
  Pencil,
  Trash2,
  Loader2,
  RefreshCw,
} from 'lucide-react';
import {
  fetchCareers,
  createCareer,
  updateCareer,
  deleteCareer,
  fetchCourses,
  createCourse,
  updateCourse,
  deleteCourse,
  fetchRoadmaps,
  createRoadmap,
  updateRoadmap,
  deleteRoadmap,
  fetchRules,
  createRule,
  updateRule,
  deleteRule,
  seedCatalog,
  CATALOG_CATEGORIES,
  CATALOG_LEVELS,
  type CareerRow,
  type CourseRow,
  type RoadmapRow,
  type RuleRow,
} from '../../services/admin/catalog';

type Tab = 'careers' | 'courses' | 'roadmaps' | 'rules';

const asString = (v: unknown): string => (v == null ? '' : String(v).trim());
const asOptionalString = (v: unknown): string | undefined => {
  const s = asString(v);
  return s || undefined;
};

const AdminCatalog: React.FC = () => {
  const [tab, setTab] = useState<Tab>('careers');
  const [loading, setLoading] = useState(false);
  const [careers, setCareers] = useState<CareerRow[]>([]);
  const [courses, setCourses] = useState<CourseRow[]>([]);
  const [roadmaps, setRoadmaps] = useState<RoadmapRow[]>([]);
  const [rules, setRules] = useState<RuleRow[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (tab === 'careers') setCareers((await fetchCareers()).items);
      if (tab === 'courses') setCourses((await fetchCourses()).items);
      if (tab === 'roadmaps') setRoadmaps((await fetchRoadmaps()).items);
      if (tab === 'rules') setRules((await fetchRules()).items);
    } finally {
      setLoading(false);
    }
  }, [tab]);

  useEffect(() => {
    load();
  }, [load]);

  const openCreate = () => {
    setEditId(null);
    setForm({
      category: CATALOG_CATEGORIES[0],
      level: 'Beginner',
      title: '',
      description: '',
      requiredSkills: '',
      skillsCovered: '',
      steps: '',
      provider: '',
      duration: '',
      url: '',
      minimumScore: 0,
      careers: '',
      courses: '',
      roadmapId: '',
      salaryRange: '',
      demandScore: 70,
    });
    setModalOpen(true);
  };

  const openEdit = (item: Record<string, unknown>) => {
    setEditId(String(item.id));
    setForm({
      ...item,
      requiredSkills: ((item.requiredSkills as string[]) || []).join(', '),
      skillsCovered: ((item.skillsCovered as string[]) || []).join(', '),
      steps: ((item.steps as string[]) || []).join('\n'),
      careers: ((item.careers as string[]) || []).join(', '),
      courses: ((item.courses as string[]) || []).join(', '),
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    const splitList = (v: unknown) =>
      String(v || '')
        .split(/[,\n]/)
        .map((s) => s.trim())
        .filter(Boolean);

    try {
      if (tab === 'careers') {
        const payload: Partial<CareerRow> = {
          title: asString(form.title),
          category: asString(form.category),
          level: asString(form.level),
          description: asString(form.description),
          requiredSkills: splitList(form.requiredSkills),
          salaryRange: asOptionalString(form.salaryRange),
          demandScore: Number(form.demandScore) || 70,
        };
        if (editId) await updateCareer(editId, payload);
        else await createCareer(payload);
      } else if (tab === 'courses') {
        const payload: Partial<CourseRow> = {
          title: asString(form.title),
          provider: asString(form.provider),
          category: asString(form.category),
          level: asString(form.level),
          duration: asOptionalString(form.duration),
          url: asOptionalString(form.url),
          skillsCovered: splitList(form.skillsCovered),
        };
        if (editId) await updateCourse(editId, payload);
        else await createCourse(payload);
      } else if (tab === 'roadmaps') {
        const payload: Partial<RoadmapRow> = {
          title: asString(form.title),
          category: asString(form.category),
          level: asString(form.level),
          steps: splitList(form.steps),
          estimatedDuration: asOptionalString(form.estimatedDuration),
        };
        if (editId) await updateRoadmap(editId, payload);
        else await createRoadmap(payload);
      } else if (tab === 'rules') {
        const payload: Partial<RuleRow> = {
          category: asString(form.category),
          level: asString(form.level),
          minimumScore: Number(form.minimumScore) || 0,
          careers: splitList(form.careers),
          courses: splitList(form.courses),
          roadmapId: asOptionalString(form.roadmapId),
          priority: Number(form.priority) || 0,
        };
        if (editId) await updateRule(editId, payload);
        else await createRule(payload);
      }
      setModalOpen(false);
      load();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Save failed');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this item?')) return;
    if (tab === 'careers') await deleteCareer(id);
    if (tab === 'courses') await deleteCourse(id);
    if (tab === 'roadmaps') await deleteRoadmap(id);
    if (tab === 'rules') await deleteRule(id);
    load();
  };

  const handleSeed = async () => {
    if (!confirm('Seed recommendation catalog? Existing items are kept unless forced.')) return;
    await seedCatalog(false);
    load();
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'careers', label: 'Careers', icon: <Briefcase className="h-4 w-4" /> },
    { id: 'courses', label: 'Courses', icon: <BookOpen className="h-4 w-4" /> },
    { id: 'roadmaps', label: 'Roadmaps', icon: <Route className="h-4 w-4" /> },
    { id: 'rules', label: 'Rules', icon: <GitBranch className="h-4 w-4" /> },
  ];

  const rows =
    tab === 'careers' ? careers : tab === 'courses' ? courses : tab === 'roadmaps' ? roadmaps : rules;

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Recommendation Catalog</h1>
          <p className="text-slate-600 text-sm mt-1">
            Manage careers, courses, roadmaps, and matching rules — no code changes required.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleSeed}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm border rounded-lg hover:bg-slate-50"
          >
            <Database className="h-4 w-4" />
            Seed catalog
          </button>
          <button
            type="button"
            onClick={openCreate}
            className="inline-flex items-center gap-2 px-3 py-2 text-sm bg-slate-900 text-white rounded-lg hover:bg-slate-800"
          >
            <Plus className="h-4 w-4" />
            Add {tab.slice(0, -1)}
          </button>
        </div>
      </div>

      <div className="flex gap-1 border-b border-slate-200 overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`inline-flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 -mb-px whitespace-nowrap ${
              tab === t.id
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
        </div>
      ) : (
        <div className="rounded-xl border border-slate-200 overflow-hidden bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-4 py-3 font-medium">Title / Category</th>
                <th className="px-4 py-3 font-medium">Level</th>
                <th className="px-4 py-3 font-medium hidden md:table-cell">Details</th>
                <th className="px-4 py-3 font-medium w-24">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                    No items yet. Seed the catalog or add one manually.
                  </td>
                </tr>
              )}
              {rows.map((row) => (
                <tr key={row.id} className="hover:bg-slate-50/50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900">
                      {'title' in row ? row.title : row.category}
                    </p>
                    <p className="text-xs text-slate-500">{row.category}</p>
                  </td>
                  <td className="px-4 py-3">{row.level}</td>
                  <td className="px-4 py-3 hidden md:table-cell text-slate-600 truncate max-w-xs">
                    {'description' in row && row.description
                      ? row.description
                      : 'steps' in row
                        ? `${(row.steps as string[]).length} steps`
                        : 'minimumScore' in row
                          ? `Min score: ${row.minimumScore}`
                          : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1">
                      <button
                        type="button"
                        onClick={() => openEdit(row as unknown as Record<string, unknown>)}
                        className="p-1.5 rounded hover:bg-slate-100 text-slate-600"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(row.id)}
                        className="p-1.5 rounded hover:bg-red-50 text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <button
        type="button"
        onClick={load}
        className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900"
      >
        <RefreshCw className="h-4 w-4" />
        Reload
      </button>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto p-6 space-y-4">
            <h2 className="text-lg font-semibold">
              {editId ? 'Edit' : 'Add'} {tab.slice(0, -1)}
            </h2>

            <label className="block text-sm">
              Category
              <select
                className="mt-1 w-full border rounded-lg px-3 py-2"
                value={String(form.category || '')}
                onChange={(e) => setForm({ ...form, category: e.target.value })}
              >
                {CATALOG_CATEGORIES.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </label>

            <label className="block text-sm">
              Level
              <select
                className="mt-1 w-full border rounded-lg px-3 py-2"
                value={String(form.level || 'Beginner')}
                onChange={(e) => setForm({ ...form, level: e.target.value })}
              >
                {CATALOG_LEVELS.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </label>

            {(tab === 'careers' || tab === 'courses' || tab === 'roadmaps') && (
              <label className="block text-sm">
                Title
                <input
                  className="mt-1 w-full border rounded-lg px-3 py-2"
                  value={String(form.title || '')}
                  onChange={(e) => setForm({ ...form, title: e.target.value })}
                />
              </label>
            )}

            {tab === 'careers' && (
              <>
                <label className="block text-sm">
                  Description
                  <textarea
                    className="mt-1 w-full border rounded-lg px-3 py-2"
                    rows={2}
                    value={String(form.description || '')}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  Required skills (comma-separated)
                  <input
                    className="mt-1 w-full border rounded-lg px-3 py-2"
                    value={String(form.requiredSkills || '')}
                    onChange={(e) => setForm({ ...form, requiredSkills: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  Salary range
                  <input
                    className="mt-1 w-full border rounded-lg px-3 py-2"
                    value={String(form.salaryRange || '')}
                    onChange={(e) => setForm({ ...form, salaryRange: e.target.value })}
                  />
                </label>
              </>
            )}

            {tab === 'courses' && (
              <>
                <label className="block text-sm">
                  Provider
                  <input
                    className="mt-1 w-full border rounded-lg px-3 py-2"
                    value={String(form.provider || '')}
                    onChange={(e) => setForm({ ...form, provider: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  URL
                  <input
                    className="mt-1 w-full border rounded-lg px-3 py-2"
                    value={String(form.url || '')}
                    onChange={(e) => setForm({ ...form, url: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  Skills covered (comma-separated)
                  <input
                    className="mt-1 w-full border rounded-lg px-3 py-2"
                    value={String(form.skillsCovered || '')}
                    onChange={(e) => setForm({ ...form, skillsCovered: e.target.value })}
                  />
                </label>
              </>
            )}

            {tab === 'roadmaps' && (
              <>
                <label className="block text-sm">
                  Steps (one per line)
                  <textarea
                    className="mt-1 w-full border rounded-lg px-3 py-2 font-mono text-xs"
                    rows={6}
                    value={String(form.steps || '')}
                    onChange={(e) => setForm({ ...form, steps: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  Estimated duration
                  <input
                    className="mt-1 w-full border rounded-lg px-3 py-2"
                    value={String(form.estimatedDuration || '')}
                    onChange={(e) => setForm({ ...form, estimatedDuration: e.target.value })}
                  />
                </label>
              </>
            )}

            {tab === 'rules' && (
              <>
                <label className="block text-sm">
                  Minimum quiz score
                  <input
                    type="number"
                    className="mt-1 w-full border rounded-lg px-3 py-2"
                    value={Number(form.minimumScore) || 0}
                    onChange={(e) => setForm({ ...form, minimumScore: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  Career IDs (comma-separated)
                  <input
                    className="mt-1 w-full border rounded-lg px-3 py-2 font-mono text-xs"
                    value={String(form.careers || '')}
                    onChange={(e) => setForm({ ...form, careers: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  Course IDs (comma-separated)
                  <input
                    className="mt-1 w-full border rounded-lg px-3 py-2 font-mono text-xs"
                    value={String(form.courses || '')}
                    onChange={(e) => setForm({ ...form, courses: e.target.value })}
                  />
                </label>
                <label className="block text-sm">
                  Roadmap ID
                  <input
                    className="mt-1 w-full border rounded-lg px-3 py-2 font-mono text-xs"
                    value={String(form.roadmapId || '')}
                    onChange={(e) => setForm({ ...form, roadmapId: e.target.value })}
                  />
                </label>
              </>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setModalOpen(false)}
                className="px-4 py-2 text-sm border rounded-lg hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                className="px-4 py-2 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminCatalog;
