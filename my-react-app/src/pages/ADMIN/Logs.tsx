import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchLogs } from '../../services/admin/logs';
import type { AuditLogRow } from '../../services/admin/types';
import { Search, ShieldAlert, Loader2, Filter, X, Download } from 'lucide-react';

const LogsPage: React.FC = () => {
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'success' | 'failed'>('all');
  const [showFilters, setShowFilters] = useState(false);

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['admin-logs', page, search, filterStatus],
    queryFn: () => fetchLogs({ page, limit: 15, action: search || undefined }),
  });

  const rows = data?.data || [];
  const pagination = data?.pagination;

  // Filter data
  const filteredRows = useMemo(() => {
    if (filterStatus === 'all') return rows;
    return rows.filter((log: AuditLogRow) => log.status === filterStatus);
  }, [rows, filterStatus]);

  const getStatusBadge = (status: string) => {
    if (status === 'success') {
      return {
        label: 'Success',
        color: 'bg-emerald-50 border-emerald-200 text-emerald-700',
        icon: '✓',
      };
    }
    return {
      label: 'Failed',
      color: 'bg-rose-50 border-rose-200 text-rose-700',
      icon: '✕',
    };
  };

  const formatDate = (date: string) => {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatTime = (date: string) => {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Immutable audit trail</p>
          <h1 className="text-3xl font-bold text-slate-900 mt-1">Audit Logs</h1>
          <p className="text-slate-600 mt-2">Complete record of all admin actions and system events</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <Filter className="h-4 w-4" />
            Filters
            {filterStatus !== 'all' && (
              <span className="ml-1 inline-flex items-center justify-center h-5 w-5 rounded-full bg-indigo-600 text-white text-xs font-bold">
                1
              </span>
            )}
          </button>
          <button className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors">
            <Download className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-50 to-white p-4 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-slate-900">Filters</h3>
            <button
              onClick={() => setShowFilters(false)}
              className="p-1 hover:bg-slate-200 rounded-lg transition-colors"
            >
              <X className="h-4 w-4 text-slate-500" />
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Status Filter */}
            <div>
              <label className="text-xs font-semibold text-slate-700 uppercase tracking-wide">Status</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="all">All Events</option>
                <option value="success">Success Only</option>
                <option value="failed">Failed Only</option>
              </select>
            </div>

            {/* Reset Filters */}
            <div className="flex items-end">
              <button
                onClick={() => {
                  setFilterStatus('all');
                  setSearch('');
                }}
                className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Reset Filters
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Search Bar */}
      <div className="relative">
        <Search className="h-5 w-5 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
        <input
          className="w-full pl-12 pr-4 py-3 rounded-xl border border-slate-200 bg-white text-slate-900 placeholder-slate-400 focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
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
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 flex items-start gap-3">
          <div className="text-rose-600 mt-0.5">⚠️</div>
          <div>
            <p className="font-semibold text-rose-900">Failed to load logs</p>
            <p className="text-sm text-rose-700 mt-1">{error instanceof Error ? error.message : 'An error occurred'}</p>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gradient-to-r from-slate-50 to-slate-100 border-b border-slate-200">
              <tr>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Action</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Resource</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Admin</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Timestamp</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">IP Address</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                      <span className="text-slate-600">Loading logs...</span>
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading && filteredRows.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="space-y-2">
                      <p className="text-slate-600 font-medium">No logs found</p>
                      <p className="text-sm text-slate-500">Try adjusting your search or filters</p>
                    </div>
                  </td>
                </tr>
              )}
              {filteredRows.map((log: AuditLogRow) => {
                const status = getStatusBadge(log.status);
                return (
                  <tr key={log._id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div>
                        <p className="font-semibold text-slate-900">{log.action}</p>
                        <p className="text-xs text-slate-500 mt-1">{log.description}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-3 py-1 rounded-full bg-slate-100 text-slate-700 text-sm font-medium">
                        {log.resource}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="h-8 w-8 rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 text-white flex items-center justify-center text-xs font-semibold">
                          {log.admin?.name?.[0] ?? 'A'}
                        </div>
                        <div>
                          <p className="text-sm font-medium text-slate-900">{log.admin?.name ?? 'Unknown'}</p>
                          <p className="text-xs text-slate-500">{log.admin?.email ?? '—'}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${status.color}`}>
                        <span>{status.icon}</span>
                        {status.label}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-slate-900">{formatDate(log.createdAt)}</p>
                        <p className="text-xs text-slate-500 mt-1">{formatTime(log.createdAt)}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-sm font-mono text-slate-600">{log.ipAddress ?? '—'}</p>
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
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4">
          <div className="text-sm text-slate-600">
            Page <span className="font-semibold text-slate-900">{pagination.page}</span> of{' '}
            <span className="font-semibold text-slate-900">{pagination.pages}</span> •{' '}
            <span className="font-semibold text-slate-900">{pagination.total}</span> total logs
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              ← Previous
            </button>
            <button
              onClick={() => setPage((p) => Math.min(pagination.pages, p + 1))}
              disabled={page === pagination.pages}
              className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* Security Info Banner */}
      <div className="rounded-2xl border border-blue-200 bg-blue-50 p-4 flex items-start gap-3">
        <ShieldAlert className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-blue-900">Audit Trail Security</p>
          <p className="text-sm text-blue-700 mt-1">
            Every admin action is immutably recorded with timestamp, IP address, user agent, and status for compliance and security purposes.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LogsPage;
