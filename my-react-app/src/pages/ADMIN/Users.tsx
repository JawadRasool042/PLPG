import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminRealtimeQueryOptions } from '../../services/admin/realtime';
import {
  fetchUsers,
  fetchUserDetails,
  changeUserRole,
  resetUserPassword,
  suspendUser,
  activateUser,
  deleteUser,
  exportUsersCsv,
} from '../../services/admin/users';
import type { UserRow } from '../../services/admin/types';
import {
  Search,
  ShieldBan,
  Loader2,
  Download,
  Filter,
  X,
  Eye,
  Trash2,
  RefreshCw,
  UserCheck,
  CheckCircle2,
  Clock,
  Ban,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
} from 'lucide-react';

type StatusKey = 'verified' | 'pending' | 'suspended';

const statusMeta: Record<StatusKey, { label: string; class: string; Icon: React.FC<any> }> = {
  verified: {
    label: 'Verified',
    class: 'bg-emerald-50 border-emerald-200 text-emerald-700',
    Icon: CheckCircle2,
  },
  pending: {
    label: 'Pending',
    class: 'bg-amber-50 border-amber-200 text-amber-700',
    Icon: Clock,
  },
  suspended: {
    label: 'Suspended',
    class: 'bg-rose-50 border-rose-200 text-rose-700',
    Icon: Ban,
  },
};

const UsersPage: React.FC = () => {
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [sortBy, setSortBy] = useState<'name' | 'email' | 'created'>('created');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [filterStatus, setFilterStatus] = useState<'all' | 'verified' | 'pending' | 'suspended'>('all');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedUser, setSelectedUser] = useState<UserRow | null>(null);
  const [showUserModal, setShowUserModal] = useState(false);
  const [userDetails, setUserDetails] = useState<any>(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [showRoleDialog, setShowRoleDialog] = useState(false);
  const [newRole, setNewRole] = useState<'Student' | 'Teacher'>('Student');

  const queryClient = useQueryClient();

  const { data, isLoading, isError, error, refetch, isFetching } = useQuery({
    queryKey: ['admin-users', page, search, sortBy, sortOrder, filterStatus],
    queryFn: () =>
      fetchUsers({
        page,
        limit: 10,
        search,
        status: filterStatus !== 'all' ? filterStatus : undefined,
        sortBy,
        sortOrder,
      }),
    ...adminRealtimeQueryOptions,
  });

  const suspendMutation = useMutation({
    mutationFn: (userId: string) => suspendUser(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  const activateMutation = useMutation({
    mutationFn: (userId: string) => activateUser(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-users'] }),
  });

  const roleChangeMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) => changeUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setShowRoleDialog(false);
    },
  });

  const passwordResetMutation = useMutation({
    mutationFn: (userId: string) => resetUserPassword(userId),
  });

  const handleExportCSV = async () => {
    try {
      const blob = await exportUsersCsv();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `users-export-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to export users');
    }
  };

  const handleSuspendUser = async (userId: string) => {
    if (confirm('Are you sure you want to suspend this user?')) {
      try {
        await suspendMutation.mutateAsync(userId);
        alert('User suspended successfully');
      } catch (err) {
        console.error('Suspend failed:', err);
        alert('Failed to suspend user');
      }
    }
  };

  const handleActivateUser = async (userId: string) => {
    if (confirm('Are you sure you want to activate this user?')) {
      try {
        await activateMutation.mutateAsync(userId);
        alert('User activated successfully');
      } catch (err) {
        console.error('Activate failed:', err);
        alert('Failed to activate user');
      }
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      try {
        await deleteMutation.mutateAsync(userId);
        alert('User deleted successfully');
      } catch (err) {
        console.error('Delete failed:', err);
        alert('Failed to delete user');
      }
    }
  };

  const handleViewUser = async (user: UserRow) => {
    setSelectedUser(user);
    setShowUserModal(true);
    setLoadingDetails(true);
    try {
      const details = await fetchUserDetails(user._id);
      setUserDetails(details);
    } catch (err) {
      console.error('Failed to fetch user details:', err);
      alert('Failed to load user details');
    } finally {
      setLoadingDetails(false);
    }
  };

  const handleChangeRole = async () => {
    if (!selectedUser) return;
    try {
      await roleChangeMutation.mutateAsync({ userId: selectedUser._id, role: newRole });
      alert(`Role changed to ${newRole} successfully`);
      setShowUserModal(false);
    } catch (err) {
      console.error('Role change failed:', err);
      alert('Failed to change role');
    }
  };

  const handleResetPassword = async (userId: string) => {
    if (confirm('Send password reset email to this user?')) {
      try {
        const result = await passwordResetMutation.mutateAsync(userId);
        alert(`Password reset email sent! Reset link: ${result.resetLink}`);
      } catch (err) {
        console.error('Password reset failed:', err);
        alert('Failed to send password reset email');
      }
    }
  };

  const rows = data?.data || [];
  const pagination = data?.pagination;

  const filteredAndSortedRows = useMemo(() => {
    if (!Array.isArray(rows)) return [];
    return [...rows];
  }, [rows]);

  const getStatusKey = (user: UserRow): StatusKey => {
    if (user.suspended || user.status === 'suspended') return 'suspended';
    if (user.emailVerified || user.status === 'verified') return 'verified';
    return 'pending';
  };

  const formatDate = (date: string | undefined) => {
    if (!date) return '—';
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatFullName = (user: UserRow) => {
    if (user.name && user.name !== 'N/A') return user.name;
    const firstName = user.firstName || '';
    const lastName = user.lastName || '';
    const fullName = `${firstName} ${lastName}`.trim();
    return fullName || 'N/A';
  };

  return (
    <div className="space-y-5">
      {/* Page intro */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">
            Users
          </h2>
          <p className="text-sm text-slate-600 mt-1.5">
            <span className="font-medium text-slate-800 tabular-nums">
              {pagination?.total ?? 0}
            </span>{' '}
            total users
            <span className="text-slate-400 mx-1.5">•</span>
            <span className="tabular-nums">{filteredAndSortedRows.length}</span> displayed
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-2 h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-60 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
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
            onClick={handleExportCSV}
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

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                Status
              </label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="mt-1.5 w-full h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition"
              >
                <option value="all">All Users</option>
                <option value="verified">Verified Only</option>
                <option value="pending">Pending Verification</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                Sort By
              </label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="mt-1.5 w-full h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition"
              >
                <option value="name">Name</option>
                <option value="email">Email</option>
                <option value="created">Created Date</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                Order
              </label>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as any)}
                className="mt-1.5 w-full h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition"
              >
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={() => {
                  setFilterStatus('all');
                  setSortBy('created');
                  setSortOrder('desc');
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
          placeholder="Search by name, email, or ID..."
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
            <p className="text-sm font-semibold text-rose-900">Failed to load users</p>
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
                  Name
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Email
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-5 py-3 text-left text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Joined
                </th>
                <th className="px-5 py-3 text-right text-[11px] font-semibold text-slate-600 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                      <span className="text-sm text-slate-600">Loading users...</span>
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading && filteredAndSortedRows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-16 text-center">
                    <p className="text-sm font-medium text-slate-700">No users found</p>
                    <p className="text-xs text-slate-500 mt-1">Try adjusting your search or filters</p>
                  </td>
                </tr>
              )}
              {filteredAndSortedRows.map((user: UserRow) => {
                const key = getStatusKey(user);
                const meta = statusMeta[key];
                const StatusIcon = meta.Icon;
                return (
                  <tr key={user._id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="h-9 w-9 rounded-full bg-gradient-to-br from-slate-200 to-slate-300 text-slate-700 flex items-center justify-center font-semibold text-sm flex-shrink-0">
                          {formatFullName(user).charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="text-sm font-semibold text-slate-900 truncate">
                            {formatFullName(user)}
                          </p>
                          <p className="text-[11px] text-slate-500 font-mono truncate">
                            {user._id.slice(0, 12)}…
                          </p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5">
                      <p className="text-sm text-slate-900">{user.email}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {(user as any).isEmailVerified || user.emailVerified
                          ? 'Verified'
                          : 'Pending verification'}
                      </p>
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium border ${meta.class}`}
                      >
                        <StatusIcon className="h-3 w-3" />
                        {meta.label}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <p className="text-sm text-slate-900 tabular-nums">
                        {formatDate(user.createdAt)}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5">
                        {user.createdAt
                          ? `${Math.floor(
                              (Date.now() - new Date(user.createdAt).getTime()) /
                                (1000 * 60 * 60 * 24)
                            )} days ago`
                          : '—'}
                      </p>
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <div className="inline-flex items-center gap-1">
                        <button
                          onClick={() => handleViewUser(user)}
                          className="inline-flex items-center gap-1 h-8 px-2.5 text-xs font-medium rounded-md border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors"
                          title="View details"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          <span className="hidden lg:inline">View</span>
                        </button>
                        {key !== 'suspended' ? (
                          <button
                            onClick={() => handleSuspendUser(user._id)}
                            disabled={suspendMutation.isPending}
                            className="inline-flex items-center gap-1 h-8 px-2.5 text-xs font-medium rounded-md border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors disabled:opacity-60"
                            title="Suspend user"
                          >
                            <ShieldBan className="h-3.5 w-3.5" />
                            <span className="hidden lg:inline">Suspend</span>
                          </button>
                        ) : (
                          <button
                            onClick={() => handleActivateUser(user._id)}
                            disabled={activateMutation.isPending}
                            className="inline-flex items-center gap-1 h-8 px-2.5 text-xs font-medium rounded-md border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors disabled:opacity-60"
                            title="Reactivate user"
                          >
                            <UserCheck className="h-3.5 w-3.5" />
                            <span className="hidden lg:inline">Activate</span>
                          </button>
                        )}
                        <button
                          onClick={() => handleDeleteUser(user._id)}
                          disabled={deleteMutation.isPending}
                          className="h-8 w-8 inline-flex items-center justify-center rounded-md border border-transparent hover:border-rose-200 hover:bg-rose-50 text-rose-600 transition-colors disabled:opacity-60"
                          title="Delete user"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
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
              className="h-8 w-8 inline-flex items-center justify-center rounded-md border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, pagination.pages) }, (_, i) => {
                const pageNum = i + 1;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`h-8 min-w-[32px] px-2 rounded-md text-xs font-semibold transition-colors tabular-nums ${
                      page === pageNum
                        ? 'bg-slate-900 text-white'
                        : 'border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300'
                    }`}
                  >
                    {pageNum}
                  </button>
                );
              })}
            </div>
            <button
              onClick={() => setPage((p) => Math.min(pagination.pages, p + 1))}
              disabled={page === pagination.pages}
              className="h-8 w-8 inline-flex items-center justify-center rounded-md border border-slate-200 text-slate-700 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              aria-label="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* User Detail Modal */}
      {showUserModal && selectedUser && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          role="dialog"
          aria-modal="true"
        >
          <button
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm animate-in fade-in"
            onClick={() => setShowUserModal(false)}
            aria-label="Close"
          />
          <div className="relative bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-hidden flex flex-col animate-in fade-in zoom-in-95">
            <div className="sticky top-0 bg-white border-b border-slate-200 px-5 sm:px-6 py-4 flex items-center justify-between flex-shrink-0">
              <div>
                <h3 className="text-base sm:text-lg font-semibold text-slate-900 tracking-tight">
                  User details
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Complete user information and activity
                </p>
              </div>
              <button
                onClick={() => setShowUserModal(false)}
                className="p-1.5 hover:bg-slate-100 rounded-md transition-colors"
                aria-label="Close"
              >
                <X className="h-5 w-5 text-slate-500" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 sm:p-6 space-y-6">
              {/* Profile */}
              <div className="flex items-start gap-4">
                <div className="h-14 w-14 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 text-white flex items-center justify-center font-semibold text-xl flex-shrink-0 shadow-sm">
                  {formatFullName(selectedUser).charAt(0).toUpperCase()}
                </div>
                <div className="flex-1 min-w-0">
                  <h4 className="text-base font-semibold text-slate-900 truncate">
                    {formatFullName(selectedUser)}
                  </h4>
                  <p className="text-sm text-slate-600 truncate">{selectedUser.email}</p>
                  <div className="flex items-center gap-2 mt-2">
                    {(() => {
                      const k = getStatusKey(selectedUser);
                      const meta = statusMeta[k];
                      const I = meta.Icon;
                      return (
                        <span
                          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium border ${meta.class}`}
                        >
                          <I className="h-3 w-3" />
                          {meta.label}
                        </span>
                      );
                    })()}
                  </div>
                </div>
              </div>

              {/* Info grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  { label: 'User ID', value: selectedUser._id, mono: true },
                  { label: 'Joined', value: formatDate(selectedUser.createdAt) },
                  { label: 'First Name', value: selectedUser.firstName || '—' },
                  { label: 'Last Name', value: selectedUser.lastName || '—' },
                ].map((info) => (
                  <div
                    key={info.label}
                    className="bg-slate-50 border border-slate-100 rounded-lg p-3"
                  >
                    <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                      {info.label}
                    </p>
                    <p
                      className={`text-sm text-slate-900 mt-1 break-all ${
                        info.mono ? 'font-mono text-xs' : ''
                      }`}
                    >
                      {info.value}
                    </p>
                  </div>
                ))}
                <div className="bg-slate-50 border border-slate-100 rounded-lg p-3 sm:col-span-2">
                  <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Email Verified
                  </p>
                  <p className="text-sm text-slate-900 mt-1 inline-flex items-center gap-1.5">
                    {selectedUser.emailVerified ? (
                      <>
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" /> Yes
                      </>
                    ) : (
                      <>
                        <Clock className="h-3.5 w-3.5 text-amber-600" /> No
                      </>
                    )}
                  </p>
                </div>
              </div>

              {/* Actions */}
              <div className="border-t border-slate-100 pt-5">
                <h5 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">
                  Quick actions
                </h5>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  <button
                    onClick={() => handleResetPassword(selectedUser._id)}
                    disabled={passwordResetMutation.isPending}
                    className="flex items-center justify-center gap-2 h-10 px-4 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors disabled:opacity-60"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Reset password
                  </button>
                  <button
                    onClick={() => setShowRoleDialog(true)}
                    className="flex items-center justify-center gap-2 h-10 px-4 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors"
                  >
                    <UserCheck className="h-4 w-4" />
                    Change role
                  </button>
                  {getStatusKey(selectedUser) !== 'suspended' ? (
                    <button
                      onClick={() => {
                        handleSuspendUser(selectedUser._id);
                        setShowUserModal(false);
                      }}
                      className="flex items-center justify-center gap-2 h-10 px-4 rounded-lg border border-rose-200 bg-rose-50 text-sm font-medium text-rose-700 hover:bg-rose-100 transition-colors"
                    >
                      <ShieldBan className="h-4 w-4" />
                      Suspend
                    </button>
                  ) : (
                    <button
                      onClick={() => {
                        handleActivateUser(selectedUser._id);
                        setShowUserModal(false);
                      }}
                      className="flex items-center justify-center gap-2 h-10 px-4 rounded-lg border border-emerald-200 bg-emerald-50 text-sm font-medium text-emerald-700 hover:bg-emerald-100 transition-colors"
                    >
                      <UserCheck className="h-4 w-4" />
                      Reactivate
                    </button>
                  )}
                  <button
                    onClick={() => {
                      handleDeleteUser(selectedUser._id);
                      setShowUserModal(false);
                    }}
                    className="flex items-center justify-center gap-2 h-10 px-4 rounded-lg border border-rose-200 bg-rose-50 text-sm font-medium text-rose-700 hover:bg-rose-100 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </button>
                </div>
              </div>

              {/* Activity history */}
              <DetailSection
                title="Recent activity"
                loading={loadingDetails}
                empty={
                  !userDetails?.activityHistory || userDetails.activityHistory.length === 0
                }
                emptyText="No activity history available"
              >
                <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                  {userDetails?.activityHistory?.map((activity: any, idx: number) => (
                    <div
                      key={idx}
                      className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-sm"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="font-medium text-slate-900">{activity.action}</p>
                          {activity.description && (
                            <p className="text-slate-600 text-xs mt-0.5 line-clamp-2">
                              {activity.description}
                            </p>
                          )}
                        </div>
                        <span className="text-[11px] text-slate-500 whitespace-nowrap tabular-nums">
                          {activity.timestamp
                            ? new Date(activity.timestamp).toLocaleDateString()
                            : '—'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </DetailSection>

              <DetailSection
                title="Login history"
                loading={loadingDetails}
                empty={!userDetails?.loginHistory || userDetails.loginHistory.length === 0}
                emptyText="No login history available"
              >
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {userDetails?.loginHistory?.map((login: any, idx: number) => (
                    <div
                      key={idx}
                      className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-sm flex items-center justify-between gap-3"
                    >
                      <div className="min-w-0">
                        <p className="font-mono text-xs font-medium text-slate-900">
                          {login.ipAddress}
                        </p>
                        <p className="text-slate-600 text-[11px] mt-0.5 truncate max-w-xs">
                          {login.userAgent}
                        </p>
                      </div>
                      <span className="text-[11px] text-slate-500 whitespace-nowrap tabular-nums">
                        {login.timestamp
                          ? new Date(login.timestamp).toLocaleDateString()
                          : '—'}
                      </span>
                    </div>
                  ))}
                </div>
              </DetailSection>

              <DetailSection
                title="Quiz attempts"
                loading={loadingDetails}
                empty={!userDetails?.quizAttempts || userDetails.quizAttempts.length === 0}
                emptyText="No quiz attempts yet"
              >
                <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                  {userDetails?.quizAttempts?.map((quiz: any, idx: number) => (
                    <div
                      key={idx}
                      className="bg-slate-50 border border-slate-100 rounded-lg p-3 text-sm flex items-center justify-between gap-3"
                    >
                      <div>
                        <p className="font-medium text-slate-900">
                          Quiz {quiz.quizId?.slice(0, 8)}…
                        </p>
                        <p className="text-slate-600 text-xs mt-0.5">
                          Score: <span className="font-semibold tabular-nums">{quiz.score}%</span>
                        </p>
                      </div>
                      <span className="text-[11px] text-slate-500 whitespace-nowrap tabular-nums">
                        {quiz.completedAt
                          ? new Date(quiz.completedAt).toLocaleDateString()
                          : '—'}
                      </span>
                    </div>
                  ))}
                </div>
              </DetailSection>
            </div>

            <div className="sticky bottom-0 bg-slate-50 border-t border-slate-200 px-5 sm:px-6 py-3 flex justify-end flex-shrink-0">
              <button
                onClick={() => setShowUserModal(false)}
                className="h-9 px-4 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Role change dialog */}
      {showRoleDialog && selectedUser && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center p-4">
          <button
            className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm animate-in fade-in"
            onClick={() => setShowRoleDialog(false)}
            aria-label="Close"
          />
          <div className="relative bg-white rounded-2xl shadow-2xl max-w-md w-full p-5 sm:p-6 animate-in fade-in zoom-in-95">
            <h3 className="text-base font-semibold text-slate-900 tracking-tight mb-1">
              Change user role
            </h3>
            <p className="text-sm text-slate-600 mb-5">
              Change role for <strong className="font-semibold">{formatFullName(selectedUser)}</strong>
            </p>

            <div className="space-y-2 mb-5">
              {(['Student', 'Teacher'] as const).map((roleOption) => (
                <label
                  key={roleOption}
                  className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                    newRole === roleOption
                      ? 'border-indigo-400 bg-indigo-50 ring-1 ring-indigo-100'
                      : 'border-slate-200 hover:bg-slate-50 hover:border-slate-300'
                  }`}
                >
                  <input
                    type="radio"
                    name="role"
                    value={roleOption}
                    checked={newRole === roleOption}
                    onChange={(e) => setNewRole(e.target.value as 'Student' | 'Teacher')}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{roleOption}</p>
                    <p className="text-xs text-slate-500 mt-0.5">
                      {roleOption === 'Student'
                        ? 'Can take quizzes and view learning paths'
                        : 'Can create and manage quizzes'}
                    </p>
                  </div>
                </label>
              ))}
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => setShowRoleDialog(false)}
                className="flex-1 h-10 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleChangeRole}
                disabled={roleChangeMutation.isPending}
                className="flex-1 h-10 rounded-lg bg-slate-900 text-sm font-medium text-white hover:bg-slate-800 transition-colors disabled:opacity-60 inline-flex items-center justify-center gap-2"
              >
                {roleChangeMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                {roleChangeMutation.isPending ? 'Saving...' : 'Save changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const DetailSection: React.FC<{
  title: string;
  loading: boolean;
  empty: boolean;
  emptyText: string;
  children: React.ReactNode;
}> = ({ title, loading, empty, emptyText, children }) => (
  <div className="border-t border-slate-100 pt-5">
    <h5 className="text-xs font-semibold text-slate-700 uppercase tracking-wider mb-3">{title}</h5>
    {loading ? (
      <div className="bg-slate-50 border border-slate-100 rounded-lg p-4 text-center">
        <Loader2 className="h-5 w-5 animate-spin text-indigo-600 mx-auto" />
        <p className="text-xs text-slate-500 mt-2">Loading...</p>
      </div>
    ) : empty ? (
      <div className="bg-slate-50 border border-slate-100 rounded-lg p-4 text-center">
        <p className="text-xs text-slate-500">{emptyText}</p>
      </div>
    ) : (
      children
    )}
  </div>
);

export default UsersPage;
