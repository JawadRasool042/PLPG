import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchUsers, fetchUserDetails, changeUserRole, resetUserPassword, suspendUser, activateUser, deleteUser, exportUsersCsv } from '../../services/admin/users';
import type { UserRow } from '../../services/admin/types';
import { Search, ShieldBan, Loader2, Download, Filter, X, Eye, Trash2, RefreshCw, UserCheck } from 'lucide-react';

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

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ['admin-users', page, search, sortBy, sortOrder, filterStatus],
    queryFn: () => fetchUsers({ 
      page, 
      limit: 10, 
      search,
      status: filterStatus !== 'all' ? filterStatus : undefined,
      sortBy,
      sortOrder
    }),
    refetchInterval: 30000, // Auto-refresh every 30 seconds
  });

  // Mutation for suspending users
  const suspendMutation = useMutation({
    mutationFn: (userId: string) => suspendUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  // Mutation for activating users
  const activateMutation = useMutation({
    mutationFn: (userId: string) => activateUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  // Mutation for deleting users
  const deleteMutation = useMutation({
    mutationFn: (userId: string) => deleteUser(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
    },
  });

  // Mutation for changing role
  const roleChangeMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) => changeUserRole(userId, role),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setShowRoleDialog(false);
    },
  });

  // Mutation for password reset
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
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export users');
    }
  };

  const handleSuspendUser = async (userId: string) => {
    if (confirm('Are you sure you want to suspend this user?')) {
      try {
        await suspendMutation.mutateAsync(userId);
        alert('User suspended successfully');
      } catch (error) {
        console.error('Suspend failed:', error);
        alert('Failed to suspend user');
      }
    }
  };

  const handleActivateUser = async (userId: string) => {
    if (confirm('Are you sure you want to activate this user?')) {
      try {
        await activateMutation.mutateAsync(userId);
        alert('User activated successfully');
      } catch (error) {
        console.error('Activate failed:', error);
        alert('Failed to activate user');
      }
    }
  };

  const handleDeleteUser = async (userId: string) => {
    if (confirm('Are you sure you want to delete this user? This action cannot be undone.')) {
      try {
        await deleteMutation.mutateAsync(userId);
        alert('User deleted successfully');
      } catch (error) {
        console.error('Delete failed:', error);
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
    } catch (error) {
      console.error('Failed to fetch user details:', error);
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
    } catch (error) {
      console.error('Role change failed:', error);
      alert('Failed to change role');
    }
  };

  const handleResetPassword = async (userId: string) => {
    if (confirm('Send password reset email to this user?')) {
      try {
        const result = await passwordResetMutation.mutateAsync(userId);
        alert(`Password reset email sent! Reset link: ${result.resetLink}`);
      } catch (error) {
        console.error('Password reset failed:', error);
        alert('Failed to send password reset email');
      }
    }
  };

  const rows = data?.data || [];
  const pagination = data?.pagination;

  // Filter and sort data (server-side filtering is now handled by backend)
  const filteredAndSortedRows = useMemo(() => {
    if (!Array.isArray(rows)) {
      return [];
    }
    return [...rows];
  }, [rows]);

  const getStatusBadge = (user: UserRow) => {
    const status = user.status || (user.suspended ? 'suspended' : user.emailVerified ? 'verified' : 'pending');
    
    if (status === 'suspended') {
      return {
        label: 'Suspended',
        color: 'bg-rose-50 border-rose-200 text-rose-700',
        icon: '🚫',
      };
    }
    if (status === 'verified') {
      return {
        label: 'Verified',
        color: 'bg-emerald-50 border-emerald-200 text-emerald-700',
        icon: '✓',
      };
    }
    return {
      label: 'Pending',
      color: 'bg-amber-50 border-amber-200 text-amber-700',
      icon: '⏳',
    };
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
    // Use the name field from backend, or construct from firstName/lastName
    if (user.name && user.name !== 'N/A') {
      return user.name;
    }
    const firstName = user.firstName || '';
    const lastName = user.lastName || '';
    const fullName = `${firstName} ${lastName}`.trim();
    return fullName || 'N/A';
  };

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white p-6">
        <div className="flex items-start gap-4">
          <div className="flex-shrink-0 h-12 w-12 rounded-xl bg-indigo-600 text-white flex items-center justify-center">
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-bold text-slate-900">Welcome, Admin</h3>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              This panel shows all users stored in MongoDB with real-time updates (auto-refresh every 30s). 
              Search, filter, and paginate to quickly find users by name, email, or ID. 
              Click <strong>View</strong> to see details, activity, and enrollment history. 
              Suspend/activate accounts, reset passwords, and manage roles with a single action. 
              All actions are logged for audit and compliance. Protected by JWT + RBAC.
            </p>
            <div className="flex items-center gap-4 mt-3 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                Real-time updates
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-indigo-500"></span>
                JWT + RBAC Protected
              </span>
              <span className="flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-amber-500"></span>
                Audit Logged
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Manage platform users</p>
          <h2 className="text-3xl font-bold text-slate-900 mt-1">Users</h2>
          <p className="text-sm text-slate-600 mt-1">
            {pagination?.total || 0} total users • {filteredAndSortedRows.length} displayed
            {isLoading && ' (loading...)'}
            {isError && ' (error loading)'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
            title="Refresh data"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
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
          <button 
            onClick={handleExportCSV}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
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

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Status Filter */}
            <div>
              <label className="text-xs font-semibold text-slate-700 uppercase tracking-wide">Status</label>
              <select
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value as any)}
                className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="all">All Users</option>
                <option value="verified">Verified Only</option>
                <option value="pending">Pending Verification</option>
                <option value="suspended">Suspended</option>
              </select>
            </div>

            {/* Sort By */}
            <div>
              <label className="text-xs font-semibold text-slate-700 uppercase tracking-wide">Sort By</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="name">Name</option>
                <option value="email">Email</option>
                <option value="created">Created Date</option>
              </select>
            </div>

            {/* Sort Order */}
            <div>
              <label className="text-xs font-semibold text-slate-700 uppercase tracking-wide">Order</label>
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as any)}
                className="mt-2 w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm text-slate-900 focus:ring-2 focus:ring-indigo-500"
              >
                <option value="asc">Ascending</option>
                <option value="desc">Descending</option>
              </select>
            </div>

            {/* Reset Filters */}
            <div className="flex items-end">
              <button
                onClick={() => {
                  setFilterStatus('all');
                  setSortBy('created');
                  setSortOrder('desc');
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
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 flex items-start gap-3">
          <div className="text-rose-600 mt-0.5">⚠️</div>
          <div>
            <p className="font-semibold text-rose-900">Failed to load users</p>
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
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Name</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Email</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-700 uppercase tracking-wider">Joined</th>
                <th className="px-6 py-4 text-right text-xs font-semibold text-slate-700 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {isLoading && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <div className="flex items-center justify-center gap-2">
                      <Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
                      <span className="text-slate-600">Loading users...</span>
                    </div>
                  </td>
                </tr>
              )}
              {!isLoading && filteredAndSortedRows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center">
                    <div className="space-y-2">
                      <p className="text-slate-600 font-medium">No users found</p>
                      <p className="text-sm text-slate-500">Try adjusting your search or filters</p>
                    </div>
                  </td>
                </tr>
              )}
              {filteredAndSortedRows.map((user: UserRow) => {
                const status = getStatusBadge(user);
                return (
                  <tr key={user._id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 text-white flex items-center justify-center font-semibold text-sm">
                          {formatFullName(user).charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <p className="font-semibold text-slate-900">{formatFullName(user)}</p>
                          <p className="text-xs text-slate-500">ID: {user._id.slice(0, 8)}...</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <p className="text-slate-900 font-medium">{user.email}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        {(user as any).isEmailVerified ? '✓ Verified' : '⏳ Pending'}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${status.color}`}>
                        <span>{status.icon}</span>
                        {status.label}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-slate-900 font-medium">{formatDate(user.createdAt)}</p>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {user.createdAt ? `${Math.floor((Date.now() - new Date(user.createdAt).getTime()) / (1000 * 60 * 60 * 24))} days ago` : '—'}
                        </p>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="inline-flex items-center gap-2">
                        <button 
                          onClick={() => handleViewUser(user)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 transition-colors"
                          title="View details"
                        >
                          <Eye className="h-4 w-4" />
                          View
                        </button>
                        {user.status !== 'suspended' ? (
                          <button 
                            onClick={() => handleSuspendUser(user._id)}
                            disabled={suspendMutation.isPending}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 transition-colors disabled:opacity-50"
                            title="Suspend user"
                          >
                            <ShieldBan className="h-4 w-4" />
                            Suspend
                          </button>
                        ) : (
                          <button 
                            onClick={() => handleActivateUser(user._id)}
                            disabled={activateMutation.isPending}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-emerald-200 text-emerald-700 hover:bg-emerald-50 transition-colors disabled:opacity-50"
                            title="Reactivate user"
                          >
                            <UserCheck className="h-4 w-4" />
                            Activate
                          </button>
                        )}
                        <button 
                          onClick={() => handleDeleteUser(user._id)}
                          disabled={deleteMutation.isPending}
                          className="p-2 rounded-lg hover:bg-rose-50 text-rose-600 transition-colors disabled:opacity-50"
                          title="Delete user"
                        >
                          <Trash2 className="h-4 w-4" />
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
        <div className="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4">
          <div className="text-sm text-slate-600">
            Page <span className="font-semibold text-slate-900">{pagination.page}</span> of{' '}
            <span className="font-semibold text-slate-900">{pagination.pages}</span> •{' '}
            <span className="font-semibold text-slate-900">{pagination.total}</span> total users
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              ← Previous
            </button>
            <div className="flex items-center gap-1">
              {Array.from({ length: Math.min(5, pagination.pages) }, (_, i) => {
                const pageNum = i + 1;
                return (
                  <button
                    key={pageNum}
                    onClick={() => setPage(pageNum)}
                    className={`h-10 w-10 rounded-lg text-sm font-medium transition-colors ${
                      page === pageNum
                        ? 'bg-indigo-600 text-white'
                        : 'border border-slate-200 text-slate-700 hover:bg-slate-50'
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
              className="px-4 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Next →
            </button>
          </div>
        </div>
      )}

      {/* User Detail Modal */}
      {showUserModal && selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-slate-900">User Details</h3>
                <p className="text-sm text-slate-500 mt-1">Complete user information and activity</p>
              </div>
              <button
                onClick={() => setShowUserModal(false)}
                className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
              >
                <X className="h-5 w-5 text-slate-500" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-6">
              {/* User Profile Section */}
              <div className="flex items-start gap-4">
                <div className="h-16 w-16 rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 text-white flex items-center justify-center font-bold text-2xl flex-shrink-0">
                  {formatFullName(selectedUser).charAt(0).toUpperCase()}
                </div>
                <div className="flex-1">
                  <h4 className="text-lg font-bold text-slate-900">{formatFullName(selectedUser)}</h4>
                  <p className="text-sm text-slate-600">{selectedUser.email}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold border ${getStatusBadge(selectedUser).color}`}>
                      <span>{getStatusBadge(selectedUser).icon}</span>
                      {getStatusBadge(selectedUser).label}
                    </span>
                  </div>
                </div>
              </div>

              {/* User Information Grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">User ID</p>
                  <p className="text-sm font-mono text-slate-900 mt-1">{selectedUser._id}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Joined</p>
                  <p className="text-sm text-slate-900 mt-1">{formatDate(selectedUser.createdAt)}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">First Name</p>
                  <p className="text-sm text-slate-900 mt-1">{selectedUser.firstName || 'N/A'}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Last Name</p>
                  <p className="text-sm text-slate-900 mt-1">{selectedUser.lastName || 'N/A'}</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4 col-span-2">
                  <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Email Verified</p>
                  <p className="text-sm text-slate-900 mt-1">
                    {selectedUser.emailVerified ? '✓ Yes' : '✗ No'}
                  </p>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="border-t border-slate-200 pt-6">
                <h5 className="text-sm font-semibold text-slate-900 mb-3">Quick Actions</h5>
                <div className="grid grid-cols-2 gap-3">
                  <button 
                    onClick={() => handleResetPassword(selectedUser._id)}
                    disabled={passwordResetMutation.isPending}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors disabled:opacity-50"
                  >
                    <RefreshCw className="h-4 w-4" />
                    Reset Password
                  </button>
                  <button 
                    onClick={() => setShowRoleDialog(true)}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    <UserCheck className="h-4 w-4" />
                    Change Role
                  </button>
                  {selectedUser.status !== 'suspended' ? (
                    <button 
                      onClick={() => {
                        handleSuspendUser(selectedUser._id);
                        setShowUserModal(false);
                      }}
                      className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-rose-200 bg-rose-50 text-sm font-medium text-rose-700 hover:bg-rose-100 transition-colors"
                    >
                      <ShieldBan className="h-4 w-4" />
                      Suspend Account
                    </button>
                  ) : (
                    <button 
                      onClick={() => {
                        handleActivateUser(selectedUser._id);
                        setShowUserModal(false);
                      }}
                      className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-emerald-200 bg-emerald-50 text-sm font-medium text-emerald-700 hover:bg-emerald-100 transition-colors"
                    >
                      <UserCheck className="h-4 w-4" />
                      Reactivate Account
                    </button>
                  )}
                  <button 
                    onClick={() => {
                      handleDeleteUser(selectedUser._id);
                      setShowUserModal(false);
                    }}
                    className="flex items-center justify-center gap-2 px-4 py-3 rounded-lg border border-rose-200 bg-rose-50 text-sm font-medium text-rose-700 hover:bg-rose-100 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete User
                  </button>
                </div>
              </div>

              {/* Activity History */}
              <div className="border-t border-slate-200 pt-6">
                <h5 className="text-sm font-semibold text-slate-900 mb-3">Recent Activity</h5>
                {loadingDetails ? (
                  <div className="bg-slate-50 rounded-lg p-4 text-center">
                    <Loader2 className="h-5 w-5 animate-spin text-indigo-600 mx-auto" />
                    <p className="text-sm text-slate-500 mt-2">Loading activity...</p>
                  </div>
                ) : userDetails?.activityHistory && userDetails.activityHistory.length > 0 ? (
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {userDetails.activityHistory.map((activity: any, idx: number) => (
                      <div key={idx} className="bg-slate-50 rounded-lg p-3 text-sm">
                        <div className="flex items-start justify-between">
                          <div>
                            <p className="font-medium text-slate-900">{activity.action}</p>
                            <p className="text-slate-600 text-xs mt-1">{activity.description}</p>
                          </div>
                          <span className="text-xs text-slate-500">
                            {activity.timestamp ? new Date(activity.timestamp).toLocaleDateString() : 'N/A'}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-slate-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-slate-500">No activity history available</p>
                  </div>
                )}
              </div>

              {/* Login History */}
              <div className="border-t border-slate-200 pt-6">
                <h5 className="text-sm font-semibold text-slate-900 mb-3">Login History</h5>
                {loadingDetails ? (
                  <div className="bg-slate-50 rounded-lg p-4 text-center">
                    <Loader2 className="h-5 w-5 animate-spin text-indigo-600 mx-auto" />
                    <p className="text-sm text-slate-500 mt-2">Loading logins...</p>
                  </div>
                ) : userDetails?.loginHistory && userDetails.loginHistory.length > 0 ? (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {userDetails.loginHistory.map((login: any, idx: number) => (
                      <div key={idx} className="bg-slate-50 rounded-lg p-3 text-sm flex items-center justify-between">
                        <div>
                          <p className="font-medium text-slate-900">{login.ipAddress}</p>
                          <p className="text-slate-600 text-xs mt-1 truncate max-w-xs">{login.userAgent}</p>
                        </div>
                        <span className="text-xs text-slate-500">
                          {login.timestamp ? new Date(login.timestamp).toLocaleDateString() : 'N/A'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-slate-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-slate-500">No login history available</p>
                  </div>
                )}
              </div>

              {/* Quiz Attempts */}
              <div className="border-t border-slate-200 pt-6">
                <h5 className="text-sm font-semibold text-slate-900 mb-3">Quiz Attempts</h5>
                {loadingDetails ? (
                  <div className="bg-slate-50 rounded-lg p-4 text-center">
                    <Loader2 className="h-5 w-5 animate-spin text-indigo-600 mx-auto" />
                    <p className="text-sm text-slate-500 mt-2">Loading quizzes...</p>
                  </div>
                ) : userDetails?.quizAttempts && userDetails.quizAttempts.length > 0 ? (
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {userDetails.quizAttempts.map((quiz: any, idx: number) => (
                      <div key={idx} className="bg-slate-50 rounded-lg p-3 text-sm flex items-center justify-between">
                        <div>
                          <p className="font-medium text-slate-900">Quiz {quiz.quizId.slice(0, 8)}...</p>
                          <p className="text-slate-600 text-xs mt-1">Score: {quiz.score}%</p>
                        </div>
                        <span className="text-xs text-slate-500">
                          {quiz.completedAt ? new Date(quiz.completedAt).toLocaleDateString() : 'N/A'}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="bg-slate-50 rounded-lg p-4 text-center">
                    <p className="text-sm text-slate-500">No quiz attempts yet</p>
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="sticky bottom-0 bg-slate-50 border-t border-slate-200 px-6 py-4 flex justify-end gap-3">
              <button
                onClick={() => setShowUserModal(false)}
                className="px-4 py-2 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Role Change Dialog */}
      {showRoleDialog && selectedUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
            <h3 className="text-lg font-bold text-slate-900 mb-4">Change User Role</h3>
            <p className="text-sm text-slate-600 mb-4">
              Change role for <strong>{formatFullName(selectedUser)}</strong>
            </p>
            
            <div className="space-y-3 mb-6">
              <label className="flex items-center gap-3 p-3 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
                <input
                  type="radio"
                  name="role"
                  value="Student"
                  checked={newRole === 'Student'}
                  onChange={(e) => setNewRole(e.target.value as 'Student' | 'Teacher')}
                  className="h-4 w-4 text-indigo-600"
                />
                <div>
                  <p className="font-medium text-slate-900">Student</p>
                  <p className="text-xs text-slate-500">Can take quizzes and view learning paths</p>
                </div>
              </label>
              
              <label className="flex items-center gap-3 p-3 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50 transition-colors">
                <input
                  type="radio"
                  name="role"
                  value="Teacher"
                  checked={newRole === 'Teacher'}
                  onChange={(e) => setNewRole(e.target.value as 'Student' | 'Teacher')}
                  className="h-4 w-4 text-indigo-600"
                />
                <div>
                  <p className="font-medium text-slate-900">Teacher</p>
                  <p className="text-xs text-slate-500">Can create and manage quizzes</p>
                </div>
              </label>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowRoleDialog(false)}
                className="flex-1 px-4 py-2 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleChangeRole}
                disabled={roleChangeMutation.isPending}
                className="flex-1 px-4 py-2 rounded-lg bg-indigo-600 text-sm font-medium text-white hover:bg-indigo-700 transition-colors disabled:opacity-50"
              >
                {roleChangeMutation.isPending ? 'Changing...' : 'Change Role'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersPage;
