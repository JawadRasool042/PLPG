import React, { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  MessageSquare,
  Star,
  RefreshCw,
  Search,
  Trash2,
  Save,
  Loader2,
  Inbox,
  CheckCircle2,
  XCircle,
  Clock,
} from 'lucide-react';
import {
  fetchAllFeedback,
  fetchFeedbackStats,
  updateFeedbackStatus,
  deleteFeedback,
  type FeedbackPagination,
} from '../../services/admin/feedback';
import type { FeedbackRecord, FeedbackStatus } from '../../services/feedbackService';
import { adminRealtimeQueryOptions } from '../../services/admin/realtime';

const STATUSES: { value: FeedbackStatus | ''; label: string }[] = [
  { value: '', label: 'All Statuses' },
  { value: 'new', label: 'New' },
  { value: 'in_review', label: 'In Review' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'dismissed', label: 'Dismissed' },
];

const CATEGORIES = [
  '',
  'General',
  'Quiz Quality',
  'Learning Path',
  'UI/UX',
  'Bug Report',
  'Feature Request',
];

const STATUS_BADGE: Record<FeedbackStatus, string> = {
  new: 'bg-blue-100 text-blue-700',
  in_review: 'bg-amber-100 text-amber-700',
  resolved: 'bg-emerald-100 text-emerald-700',
  dismissed: 'bg-slate-200 text-slate-600',
};

const STATUS_ICON: Record<FeedbackStatus, React.ComponentType<{ className?: string }>> = {
  new: Inbox,
  in_review: Clock,
  resolved: CheckCircle2,
  dismissed: XCircle,
};

const AdminFeedback: React.FC = () => {
  const queryClient = useQueryClient();

  const [filters, setFilters] = useState({
    status: '' as FeedbackStatus | '',
    category: '',
    search: '',
  });
  const [page, setPage] = useState(1);

  const [activeId, setActiveId] = useState<string | null>(null);
  const [draftStatus, setDraftStatus] = useState<FeedbackStatus>('in_review');
  const [draftNote, setDraftNote] = useState('');
  const [savingId, setSavingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const {
    data: listData,
    isLoading: loading,
    isFetching: listFetching,
    isError,
    error,
    refetch: refetchList,
  } = useQuery({
    queryKey: ['admin-feedback-list', page, filters.status, filters.category, filters.search.trim()],
    queryFn: () =>
      fetchAllFeedback({
        page,
        limit: 25,
        status: filters.status,
        category: filters.category,
        search: filters.search.trim() || undefined,
      }),
    ...adminRealtimeQueryOptions,
  });

  const {
    data: stats,
    isFetching: statsFetching,
    refetch: refetchStats,
  } = useQuery({
    queryKey: ['admin-feedback-stats'],
    queryFn: () => fetchFeedbackStats(30),
    ...adminRealtimeQueryOptions,
  });

  const items: FeedbackRecord[] = listData?.data || [];
  const pagination: FeedbackPagination = listData?.pagination || {
    page: 1,
    limit: 25,
    total: 0,
    totalPages: 0,
  };
  const activeItem = useMemo(
    () => items.find((i) => i.id === activeId) || null,
    [items, activeId]
  );

  const handleSelect = (item: FeedbackRecord) => {
    setActiveId(item.id);
    setDraftStatus(item.status);
    setDraftNote(item.adminNote || '');
  };

  const handleSave = async () => {
    if (!activeItem) return;
    setSavingId(activeItem.id);
    try {
      await updateFeedbackStatus(activeItem.id, {
        status: draftStatus,
        adminNote: draftNote,
      });
      await queryClient.invalidateQueries({ queryKey: ['admin-feedback-list'] });
      await queryClient.invalidateQueries({ queryKey: ['admin-feedback-stats'] });
    } catch (err: any) {
      alert(err?.response?.data?.message || err?.message || 'Failed to update feedback');
    } finally {
      setSavingId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this feedback permanently?')) return;
    setDeletingId(id);
    try {
      await deleteFeedback(id);
      if (activeId === id) setActiveId(null);
      await queryClient.invalidateQueries({ queryKey: ['admin-feedback-list'] });
      await queryClient.invalidateQueries({ queryKey: ['admin-feedback-stats'] });
    } catch (err: any) {
      alert(err?.response?.data?.message || err?.message || 'Failed to delete feedback');
    } finally {
      setDeletingId(null);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <MessageSquare className="h-6 w-6 text-indigo-600" />
            User Feedback
          </h1>
          <p className="text-sm text-slate-500 mt-1">
            Manage user submissions, respond, and track resolution status.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => {
              void refetchList();
              void refetchStats();
            }}
            className="inline-flex items-center gap-2 h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className={`h-4 w-4 ${listFetching || statsFetching ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total feedback"
          value={stats?.total ?? '—'}
          icon={<Inbox className="h-4 w-4" />}
        />
        <StatCard
          label="Last 30 days"
          value={stats?.recent ?? '—'}
          icon={<Clock className="h-4 w-4" />}
        />
        <StatCard
          label="Average rating"
          value={
            stats?.ratingCount
              ? `${stats.averageRating.toFixed(1)} ★`
              : '—'
          }
          icon={<Star className="h-4 w-4" />}
        />
        <StatCard
          label="Open (new + in review)"
          value={
            stats
              ? (stats.byStatus?.new || 0) + (stats.byStatus?.in_review || 0)
              : '—'
          }
          icon={<MessageSquare className="h-4 w-4" />}
        />
      </div>

      {/* Filters */}
      <form
        onSubmit={handleSearchSubmit}
        className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col md:flex-row gap-3"
      >
        <div className="flex-1 flex items-center gap-2 border border-slate-200 rounded-lg px-3">
          <Search className="h-4 w-4 text-slate-400" />
          <input
            type="search"
            placeholder="Search subject, message, email..."
            value={filters.search}
            onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))}
            className="flex-1 py-2 text-sm bg-transparent outline-none"
          />
        </div>
        <select
          value={filters.status}
          onChange={(e) => {
            setPage(1);
            setFilters((f) => ({ ...f, status: e.target.value as FeedbackStatus | '' }));
          }}
          className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white"
        >
          {STATUSES.map((s) => (
            <option key={s.value || 'all'} value={s.value}>
              {s.label}
            </option>
          ))}
        </select>
        <select
          value={filters.category}
          onChange={(e) => {
            setPage(1);
            setFilters((f) => ({ ...f, category: e.target.value }));
          }}
          className="border border-slate-200 rounded-lg px-3 py-2 text-sm bg-white"
        >
          {CATEGORIES.map((c) => (
            <option key={c || 'all'} value={c}>
              {c || 'All Categories'}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="h-10 px-4 rounded-lg bg-slate-900 text-white text-sm font-medium hover:bg-slate-800"
        >
          Apply
        </button>
      </form>

      {isError && (
        <div className="bg-rose-50 border border-rose-200 text-rose-700 rounded-xl px-4 py-3 text-sm">
          {(error as any)?.response?.data?.message || (error as Error)?.message || 'Failed to load feedback'}
        </div>
      )}

      <div className="grid lg:grid-cols-5 gap-4">
        {/* List */}
        <div className="lg:col-span-3 bg-white border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between text-sm">
            <span className="font-semibold text-slate-700">
              {pagination.total} result{pagination.total === 1 ? '' : 's'}
            </span>
            {pagination.totalPages > 1 && (
              <div className="flex items-center gap-1">
                <button
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="px-2 py-1 rounded-md border border-slate-200 text-slate-600 disabled:opacity-50"
                >
                  Prev
                </button>
                <span className="px-2 text-slate-500">
                  {page} / {pagination.totalPages}
                </span>
                <button
                  disabled={page >= pagination.totalPages}
                  onClick={() => setPage((p) => Math.min(pagination.totalPages, p + 1))}
                  className="px-2 py-1 rounded-md border border-slate-200 text-slate-600 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </div>

          {loading ? (
            <div className="p-10 text-center text-slate-500">
              <Loader2 className="h-5 w-5 animate-spin inline mr-2" />
              Loading feedback...
            </div>
          ) : items.length === 0 ? (
            <div className="p-10 text-center text-slate-500">No feedback found.</div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {items.map((item) => {
                const StatusIcon = STATUS_ICON[item.status] || Inbox;
                const isActive = item.id === activeId;
                return (
                  <li key={item.id}>
                    <button
                      onClick={() => handleSelect(item)}
                      className={`w-full text-left px-4 py-3 hover:bg-slate-50 transition-colors ${
                        isActive ? 'bg-indigo-50/60' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                              {item.category}
                            </span>
                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium ${
                                STATUS_BADGE[item.status]
                              }`}
                            >
                              <StatusIcon className="h-3 w-3" />
                              {item.status.replace('_', ' ')}
                            </span>
                            {item.rating > 0 && (
                              <span className="text-xs text-amber-500">
                                {'★'.repeat(item.rating)}
                              </span>
                            )}
                          </div>
                          {item.subject && (
                            <p className="font-semibold text-slate-900 truncate">
                              {item.subject}
                            </p>
                          )}
                          <p className="text-sm text-slate-600 line-clamp-2 mt-0.5">
                            {item.message}
                          </p>
                          <p className="text-[11px] text-slate-400 mt-1.5">
                            {item.userName || item.userEmail || 'Anonymous'} •{' '}
                            {item.createdAt
                              ? new Date(item.createdAt).toLocaleString()
                              : ''}
                          </p>
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            void handleDelete(item.id);
                          }}
                          className="p-1.5 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors"
                          title="Delete"
                          disabled={deletingId === item.id}
                        >
                          {deletingId === item.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {/* Detail / Reply */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-5">
          {!activeItem ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-500 py-16">
              <MessageSquare className="h-8 w-8 mb-2 text-slate-300" />
              <p className="text-sm">Select a feedback entry to view and respond.</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <div className="flex items-center gap-2 mb-1.5">
                  <span className="text-xs font-semibold uppercase tracking-wide text-indigo-600">
                    {activeItem.category}
                  </span>
                  {activeItem.rating > 0 && (
                    <span className="text-xs text-amber-500">
                      {'★'.repeat(activeItem.rating)}
                    </span>
                  )}
                </div>
                {activeItem.subject && (
                  <h3 className="text-base font-bold text-slate-900">
                    {activeItem.subject}
                  </h3>
                )}
                <p className="text-xs text-slate-400 mt-1">
                  {activeItem.userName || activeItem.userEmail || 'Anonymous'} •{' '}
                  {activeItem.createdAt
                    ? new Date(activeItem.createdAt).toLocaleString()
                    : ''}
                </p>
              </div>

              <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-sm text-slate-700 whitespace-pre-wrap">
                {activeItem.message}
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Status
                </label>
                <select
                  value={draftStatus}
                  onChange={(e) => setDraftStatus(e.target.value as FeedbackStatus)}
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="new">New</option>
                  <option value="in_review">In Review</option>
                  <option value="resolved">Resolved</option>
                  <option value="dismissed">Dismissed</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Admin response (visible to user)
                </label>
                <textarea
                  rows={4}
                  value={draftNote}
                  onChange={(e) => setDraftNote(e.target.value)}
                  placeholder="Optional reply that will appear in the user's feedback history."
                  className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm resize-none"
                />
              </div>

              <button
                onClick={() => void handleSave()}
                disabled={savingId === activeItem.id}
                className="w-full inline-flex items-center justify-center gap-2 h-10 px-4 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-50"
              >
                {savingId === activeItem.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                Save changes
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const StatCard: React.FC<{
  label: string;
  value: number | string;
  icon: React.ReactNode;
}> = ({ label, value, icon }) => (
  <div className="bg-white border border-slate-200 rounded-xl p-4">
    <div className="flex items-center justify-between mb-1">
      <span className="text-xs font-medium text-slate-500">{label}</span>
      <span className="h-7 w-7 inline-flex items-center justify-center rounded-md bg-slate-100 text-slate-600">
        {icon}
      </span>
    </div>
    <p className="text-2xl font-bold text-slate-900">{value}</p>
  </div>
);

export default AdminFeedback;
