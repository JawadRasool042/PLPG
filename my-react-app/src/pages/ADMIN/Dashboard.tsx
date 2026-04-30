import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchDashboardAnalytics } from '../../services/admin/analytics';
import StatCard from '../../components/Admin/StatCard';
import ChartCard from '../../components/Admin/ChartCard';
import { Activity, Users, ShieldCheck, TrendingUp, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

const Dashboard: React.FC = () => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: fetchDashboardAnalytics,
  });

  const growth = data?.charts?.userGrowth ?? [];

  const chartData = {
    labels: Array.isArray(growth) ? growth.map((d: any) => d._id) : [],
    datasets: [
      {
        label: 'New Users',
        data: Array.isArray(growth) ? growth.map((d: any) => d.count) : [],
        fill: true,
        borderColor: '#6366f1',
        backgroundColor: 'rgba(99, 102, 241, 0.15)',
        tension: 0.35,
        pointRadius: 4,
        pointBackgroundColor: '#6366f1',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: { display: false },
      filler: { propagate: true },
    },
    scales: {
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(0, 0, 0, 0.05)' },
      },
      x: {
        grid: { display: false },
      },
    },
  };

  const successRate = data?.metrics?.activity
    ? ((data.metrics.activity.totalLogins - data.metrics.activity.failedLogins) /
        Math.max(data.metrics.activity.totalLogins || 1, 1)) *
      100
    : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Welcome back</p>
          <h1 className="text-4xl font-bold text-slate-900 mt-1">Dashboard</h1>
          <p className="text-slate-600 mt-2">Real-time platform analytics and system health</p>
        </div>
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-emerald-50 border border-emerald-200">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></div>
          <span className="text-sm font-semibold text-emerald-700">All systems operational</span>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Total Users"
          value={data?.metrics.users.total ?? '—'}
          trend={`${data?.metrics.users.verified ?? 0} verified`}
          icon={<Users className="h-6 w-6" />}
          accent="indigo"
        />
        <StatCard
          label="New This Month"
          value={data?.metrics.users.newThisMonth ?? '—'}
          trend={`${data?.metrics.users.newThisWeek ?? 0} this week`}
          icon={<TrendingUp className="h-6 w-6" />}
          accent="emerald"
        />
        <StatCard
          label="Login Success Rate"
          value={`${successRate.toFixed(1)}%`}
          trend={`${data?.metrics.activity.failedLogins ?? 0} failed attempts`}
          icon={<CheckCircle2 className="h-6 w-6" />}
          accent="amber"
        />
        <StatCard
          label="Admin Actions (7d)"
          value={data?.metrics.activity.adminActionsThisWeek ?? '—'}
          trend="Audit logged"
          icon={<ShieldCheck className="h-6 w-6" />}
          accent="rose"
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* User Growth Chart */}
        <ChartCard title="User Growth" description="Daily sign-ups (last 30 days)" className="lg:col-span-2">
          {isLoading ? (
            <div className="h-64 flex items-center justify-center">
              <div className="text-center">
                <div className="h-8 w-8 rounded-full border-4 border-indigo-200 border-t-indigo-600 animate-spin mx-auto mb-2"></div>
                <p className="text-sm text-slate-500">Loading chart...</p>
              </div>
            </div>
          ) : isError ? (
            <div className="h-64 flex items-center justify-center">
              <div className="text-center">
                <AlertTriangle className="h-8 w-8 text-rose-600 mx-auto mb-2" />
                <p className="text-sm text-rose-600">Failed to load analytics</p>
              </div>
            </div>
          ) : (
            <Line data={chartData} options={chartOptions as any} />
          )}
        </ChartCard>

        {/* Security Posture */}
        <ChartCard title="Security Posture" description="Auth events & system health">
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Login Success Rate</span>
                <span className="text-lg font-bold text-emerald-600">{successRate.toFixed(1)}%</span>
              </div>
              <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-500 to-emerald-600 transition-all"
                  style={{ width: `${successRate}%` }}
                ></div>
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Failed Logins</span>
                <span className="text-lg font-bold text-amber-600">{data?.metrics.activity.failedLogins ?? '—'}</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Clock className="h-3.5 w-3.5" />
                Last 24 hours
              </div>
            </div>

            <div className="pt-2 border-t border-slate-100">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Audit Entries (7d)</span>
                <span className="text-lg font-bold text-indigo-600">{data?.metrics.activity.adminActionsThisWeek ?? '—'}</span>
              </div>
            </div>
          </div>
        </ChartCard>
      </div>

      {/* Recent Activity */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-slate-100">
          <h3 className="text-lg font-semibold text-slate-900">Recent Admin Activity</h3>
          <p className="text-sm text-slate-600 mt-1">Latest audited actions from administrators</p>
        </div>

        <div className="divide-y divide-slate-100">
          {isLoading ? (
            <div className="px-6 py-8 text-center">
              <div className="h-6 w-6 rounded-full border-3 border-indigo-200 border-t-indigo-600 animate-spin mx-auto mb-2"></div>
              <p className="text-sm text-slate-500">Loading activity...</p>
            </div>
          ) : data?.recentActivities?.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <Activity className="h-8 w-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">No recent activity</p>
            </div>
          ) : (
            data?.recentActivities?.slice(0, 8).map((log: any) => (
              <div key={log._id} className="px-6 py-4 hover:bg-slate-50 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="h-10 w-10 rounded-full bg-gradient-to-br from-indigo-500 to-indigo-600 text-white flex items-center justify-center text-sm font-semibold flex-shrink-0">
                    {log.admin?.name?.[0] ?? 'A'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-slate-900">{log.action}</p>
                      <span className="text-xs text-slate-500 whitespace-nowrap">
                        {new Date(log.createdAt).toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm text-slate-600 mt-1">{log.description}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-xs px-2 py-1 rounded-full bg-slate-100 text-slate-700">
                        {log.admin?.name ?? 'Unknown'}
                      </span>
                      <span className="text-xs text-slate-500">{log.ipAddress ?? 'N/A'}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {data && data.recentActivities && data.recentActivities.length > 8 && (
          <div className="px-6 py-4 bg-slate-50 border-t border-slate-100 text-center">
            <button className="text-sm font-semibold text-indigo-600 hover:text-indigo-700">
              View all activity →
            </button>
          </div>
        )}
      </div>

      {/* System Health Footer */}
      <div className="rounded-2xl border border-slate-200 bg-gradient-to-r from-slate-50 to-slate-100 p-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-slate-900">System Health</h3>
            <p className="text-sm text-slate-600 mt-1">All systems are operating normally</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-xs text-slate-600">Uptime</p>
              <p className="text-lg font-bold text-emerald-600">99.9%</p>
            </div>
            <div className="h-12 w-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center">
              <CheckCircle2 className="h-6 w-6" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
