import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchLogs } from '../../services/admin/logs';
import { adminRealtimeQueryOptions } from '../../services/admin/realtime';
import type { AuditLogRow } from '../../services/admin/types';
import {
  Search,
  ShieldAlert,
  Loader2,
  Filter,
  X,
  Download,
  ChevronLeft,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from 'lucide-react';
import { exportLogsCsv } from '../../services/admin/logs';

const LogsPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'success' | 'failure'>('all');
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['admin-logs', page, search, filterStatus],
    queryFn: () => fetchLogs({ page, limit: 15, action: search || undefined }),
    ...adminRealtimeQueryOptions,
  });

  const rows = data?.data || [];
  const pagination = data?.pagination;

  const filteredRows = useMemo(() => {
    if (filterStatus === 'all') return rows;
    return rows.filter((log: AuditLogRow) => log.status === filterStatus);
  }, [rows, filterStatus]);

  const formatDate = (date: string) =>
    new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });

  const formatTime = (date: string) =>
    new Date(date).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

  return (
    <div className="space-y-5">
      {/* Page intro */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">
            Audit logs
          </h2>
          <p className="text-sm text-slate-600 mt-1.5 max-w-xl">
            Immutable record of every administrative action and authentication event.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={`inline-flex items-center gap-2 h-9 px-3 rounded-lg border text-sm font-medium transition-colors ${
              showFilters || filterStatus !== 'all'
                ? 'bg-slate-900 border-slate-900 text-white hover:bg-slate-800'
                : 'border-slate-200 bg-white text-slate-700 hover:bg-slate-50 hover:border-slate-300'
            }`}
          >
            <Filter className="h-4 w-4" />
            <span className="hidden sm:inline">Filters</span>
            {filterStatus !== 'all' && (
              <span className="inline-flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-white/90 text-slate-900 text-[10px] font-bold">
                1
              </span>
            )}
          </button>
          <button
            onClick={async () => {
              const blob = await exportLogsCsv();
              const url = window.URL.createObjectURL(blob);
              const a = document.createElement('a');
              a.href = url;
              a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
              document.body.appendChild(a);
              a.click();
              window.URL.revokeObjectURL(url);
              document.body.removeChild(a);
            }}
            className="inline-flex items-center gap-2 h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors"
          >
            <Download className="h-4 w-4" />
            <span className="hidden sm:inline">Export</span>
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5 animate-in fade-in slide-in-from-top-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-900">Filters</h3>
            <button
              onClick={() => setShowFilters(false)}
              className="p-1 hover:bg-slate-100 rounded-md transition-colors"
              aria-label="Close filters"
            >
              <X className="h-4 w-4 text-slate-500" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                Status
              </label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="mt-1.5 w-full h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition"
              >
                <option value="all">All Events</option>
                <option value="success">Success Only</option>
                <option value="failure">Failed Only</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => {
                  setFilterStatus('all');
                  setSearch('');
                }}
                className="w-full h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors"
              >
                Reset
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search Bar */}
      <div className="relative">
        <Search className="h-4 w-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
        <input
          className="w-full h-11 pl-10 pr-4 rounded-lg border border-slate-200 bg-white text-sm text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition"
          placeholder="Search by action, resource, or admin..."
          value={search}
          onChange={(e) => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
      </div>

      {/* Error State */}
      {isError && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-rose-600 flex-shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-semibold text-rose-900">Failed to load logs</p>
            <p className="text-xs text-rose-700 mt-0.5">
              {error instanceof Error ? error.message : 'An error occurred'}
            </p>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-slate-50/60 border-b border-slate-100">
              <tr>
                <th className="px-5 py-3 text-left text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Action
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Resource
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Admin
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Timestamp
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  IP Address
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                      <span className="text-sm text-slate-600">Loading logs...</span>
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading && filteredRows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-16 text-center">
                    <p className="text-sm font-medium text-slate-700">No logs found</p>
                    <p className="text-xs text-slate-500 mt-1">
                      Try adjusting your search or filters
                    </p>
                  </td>
                </tr>
              )}
              {filteredRows.map((log: AuditLogRow, idx: number) => {
                const ok = log.status === 'success';
                return (
                  <tr
                    key={log.id || log._id || `log-${idx}`}
                    className="hover:bg-slate-50/70 transition-colors"
                  >
                    <td className="px-5 py-3.5">
                      <p className="text-sm font-semibold text-slate-900">{log.action}</p>
                      {log.description && (
                        <p className="text-[11px] text-slate-500 mt-0.5 line-clamp-1">
                          {log.description}
                        </p>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 text-xs font-medium">
                        {log.resource}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-2">
                        <div className="h-7 w-7 rounded-full bg-gradient-to-br from-slate-200 to-slate-300 text-slate-700 flex items-center justify-center text-[11px] font-semibold flex-shrink-0">
                          {log.admin?.name?.[0]?.toUpperCase() ?? 'A'}
                        </div>
                        <div className="min-w-0">
                          <p className="text-xs font-medium text-slate-900 truncate">
                            {log.admin?.name ?? 'Unknown'}
                          </p>
                          <p className="text-[11px] text-slate-500 truncate">
                            {log.admin?.email ?? '—'}
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-medium border ${
                          ok
                            ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                            : 'bg-rose-50 border-rose-200 text-rose-700'
                        }`}
                      >
                        {ok ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
                        {ok ? 'Success' : 'Failed'}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <p className="text-sm text-slate-900 tabular-nums">
                        {formatDate(log.createdAt)}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5 tabular-nums">
                        {formatTime(log.createdAt)}
                      </p>
                    </td>
                    <td className="px-5 py-3.5">
                      <p className="text-xs font-mono text-slate-600">{log.ipAddress ?? '—'}</p>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      {pagination && pagination.pages > 1 && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3">
          <div className="text-xs text-slate-600">
            Page{' '}
            <span className="font-semibold text-slate-900 tabular-nums">{pagination.page}</span> of{' '}
            <span className="font-semibold text-slate-900 tabular-nums">{pagination.pages}</span>
            <span className="text-slate-400 mx-1.5">•</span>
            <span className="font-semibold text-slate-900 tabular-nums">{pagination.total}</span>{' '}
            total
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="h-8 px-3 inline-flex items-center gap-1 rounded-md border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(pagination.pages, p + 1))}
              disabled={page === pagination.pages}
              className="h-8 px-3 inline-flex items-center gap-1 rounded-md border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Security Info Banner */}
      <div className="rounded-xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-4 flex items-start gap-3">
        <div className="h-9 w-9 rounded-lg bg-blue-50 text-blue-600 ring-1 ring-blue-100 flex items-center justify-center flex-shrink-0">
          <ShieldAlert className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900">Audit trail security</p>
          <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">
            Every administrative action is immutably recorded with timestamp, IP address, user
            agent, and status for compliance and forensic review.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
