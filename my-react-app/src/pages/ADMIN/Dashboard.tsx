import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchDashboardAnalytics } from '../../services/admin/analytics';
import { adminRealtimeQueryOptions } from '../../services/admin/realtime';
import StatCard from '../../components/Admin/StatCard';
import ChartCard from '../../components/Admin/ChartCard';
import {
  Activity,
  Users,
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ArrowUpRight,
  Loader2,
} from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

const Dashboard: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: fetchDashboardAnalytics,
    ...adminRealtimeQueryOptions,
  });

  const growth = Array.isArray(data?.charts?.userGrowth) ? data.charts.userGrowth : [];
  const hasGrowthData = growth.some((d: any) => Number(d.count || 0) > 0);

  const chartData = {
    labels: growth.map((d: any) => d._id),
    datasets: [
      {
        label: 'New Users',
        data: growth.map((d: any) => Number(d.count || 0)),
        fill: true,
        borderColor: '#4f46e5',
        backgroundColor: 'rgba(79, 70, 229, 0.08)',
        tension: 0.35,
        pointRadius: 3,
        pointBackgroundColor: '#4f46e5',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        borderWidth: 2,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0f172a',
        padding: 12,
        cornerRadius: 8,
        titleFont: { weight: 600, size: 12 },
        bodyFont: { size: 12 },
      },
    },
    scales: {
      y: {
        beginAtZero: true,
        min: hasGrowthData ? 0 : -0.5,
        suggestedMax: hasGrowthData ? undefined : 2,
        ticks: { precision: 0, color: '#94a3b8', font: { size: 11 } },
        grid: { color: 'rgba(15, 23, 42, 0.05)' },
        border: { display: false },
      },
      x: {
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 11 } },
        border: { display: false },
      },
    },
  };

  const successRate = data?.metrics?.activity
    ? ((data.metrics.activity.totalLogins - data.metrics.activity.failedLogins) /
        Math.max(data.metrics.activity.totalLogins || 1, 1)) *
      100
    : 0;

  return (
    <div className="space-y-6">
      {/* Page intro */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <p className="text-sm text-slate-500">
            Welcome back{admin_first_name(data) ? `, ${admin_first_name(data)}` : ''}.
          </p>
          <h2 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight mt-1">
            Platform overview
          </h2>
          <p className="text-sm text-slate-600 mt-1.5 max-w-xl">
            Real-time analytics, security posture, and recent administrative activity.
          </p>
        </div>
        <div className="inline-flex items-center gap-2 px-3 h-9 rounded-lg border border-emerald-200 bg-emerald-50">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          <span className="text-xs font-semibold text-emerald-700">All systems operational</span>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Total Users"
          value={data?.metrics.users.total ?? '—'}
          trend={`${data?.metrics.users.verified ?? 0} verified accounts`}
          icon={<Users className="h-5 w-5" />}
          accent="indigo"
        />
        <StatCard
          label="New This Month"
          value={data?.metrics.users.newThisMonth ?? '—'}
          trend={`${data?.metrics.users.newThisWeek ?? 0} this week`}
          trendDirection="up"
          icon={<TrendingUp className="h-5 w-5" />}
          accent="emerald"
        />
        <StatCard
          label="Login Success Rate"
          value={`${successRate.toFixed(1)}%`}
          trend={`${data?.metrics.activity.failedLogins ?? 0} failed attempts`}
          icon={<CheckCircle2 className="h-5 w-5" />}
          accent="amber"
        />
        <StatCard
          label="Admin Actions (7d)"
          value={data?.metrics.activity.adminActionsThisWeek ?? '—'}
          trend="Audited & logged"
          icon={<ShieldCheck className="h-5 w-5" />}
          accent="rose"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
        <ChartCard
          title="User Growth"
          description="Daily sign-ups over the last 30 days"
          className="lg:col-span-2"
        >
          <div className="h-64 sm:h-72">
            {isLoading ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <Loader2 className="h-6 w-6 text-indigo-600 animate-spin mx-auto mb-2" />
                  <p className="text-sm text-slate-500">Loading chart...</p>
                </div>
              </div>
            ) : isError ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <AlertTriangle className="h-7 w-7 text-rose-600 mx-auto mb-2" />
                  <p className="text-sm font-medium text-rose-700">Failed to load analytics</p>
                </div>
              </div>
            ) : !hasGrowthData ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <p className="text-sm font-medium text-slate-700">
                    No new sign-ups in the last 30 days
                  </p>
                  <p className="text-xs text-slate-500 mt-1">Auto-refreshes every 20 seconds</p>
                </div>
              </div>
            ) : (
              <Line data={chartData} options={chartOptions as any} />
            )}
          </div>
        </ChartCard>

        <ChartCard title="Security Posture" description="Authentication & audit health">
          <div className="space-y-5">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Login Success Rate</span>
                <span className="text-base font-semibold text-emerald-600 tabular-nums">
                  {successRate.toFixed(1)}%
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-emerald-600 rounded-full transition-all"
                  style={{ width: `${successRate}%` }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Failed Logins</span>
                <span className="text-base font-semibold text-amber-600 tabular-nums">
                  {data?.metrics.activity.failedLogins ?? '—'}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-xs text-slate-500">
                <Clock className="h-3.5 w-3.5" />
                Last 24 hours
              </div>
            </div>

            <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
              <span className="text-sm font-medium text-slate-700">Audit Entries (7d)</span>
              <span className="text-base font-semibold text-indigo-600 tabular-nums">
                {data?.metrics.activity.adminActionsThisWeek ?? '—'}
              </span>
            </div>
          </div>
        </ChartCard>
      </div>

      {/* Recent Activity */}
      <div className="rounded-xl border border-slate-200 bg-white shadow-xs overflow-hidden">
        <div className="px-5 sm:px-6 py-4 border-b border-slate-100 flex items-start justify-between gap-3">
          <div>
            <h3 className="text-[15px] font-semibold text-slate-900 tracking-tight">
              Recent administrative activity
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Latest audited actions across the platform
            </p>
          </div>
          <a
            href="/admin/logs"
            className="hidden sm:inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-700 transition-colors"
          >
            View all
            <ArrowUpRight className="h-3.5 w-3.5" />
          </a>
        </div>

        <div className="divide-y divide-slate-100">
          {isLoading ? (
            <div className="px-6 py-10 text-center">
              <Loader2 className="h-5 w-5 text-indigo-600 animate-spin mx-auto mb-2" />
              <p className="text-sm text-slate-500">Loading activity...</p>
            </div>
          ) : !data?.recentActivities || data.recentActivities.length === 0 ? (
            <div className="px-6 py-10 text-center">
              <Activity className="h-7 w-7 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No recent activity</p>
            </div>
          ) : (
            data.recentActivities.slice(0, 6).map((log: any, idx: number) => (
              <div
                key={log.id || log._id || `recent-${idx}`}
                className="px-5 sm:px-6 py-3.5 hover:bg-slate-50/70 transition-colors"
              >
                <div className="flex items-start gap-3 sm:gap-4">
                  <div className="h-9 w-9 rounded-full bg-gradient-to-br from-slate-200 to-slate-300 text-slate-700 flex items-center justify-center text-sm font-semibold flex-shrink-0">
                    {log.admin?.name?.[0]?.toUpperCase() ?? 'A'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-baseline justify-between gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-slate-900">{log.action}</p>
                      <span className="text-[11px] text-slate-500 whitespace-nowrap tabular-nums">
                        {new Date(log.createdAt).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    {log.description && (
                      <p className="text-xs text-slate-600 mt-0.5 line-clamp-1">
                        {log.description}
                      </p>
                    )}
                    <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                      <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-medium">
                        {log.admin?.name ?? 'Unknown'}
                      </span>
                      {log.ipAddress && (
                        <span className="text-[11px] text-slate-500 font-mono">
                          {log.ipAddress}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* System Health Footer */}
      <div className="rounded-xl border border-slate-200 bg-gradient-to-br from-white to-slate-50 p-5 sm:p-6">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 min-w-0">
            <div className="h-11 w-11 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center flex-shrink-0">
              <CheckCircle2 className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h3 className="text-[15px] font-semibold text-slate-900">System health</h3>
              <p className="text-xs sm:text-sm text-slate-600 mt-0.5 truncate">
                All systems are operating normally
              </p>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <p className="text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              Uptime
            </p>
            <p className="text-xl sm:text-2xl font-semibold text-emerald-600 tabular-nums">99.9%</p>
          </div>
        </div>
      </div>
    </div>
  );
};

const admin_first_name = (data: any): string | null => {
  // Reserved for future personalization; keep null for stability
  void data;
  return null;
};

export default Dashboard;
