import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchDashboardAnalytics, fetchEngagementAnalytics } from '../../services/admin/analytics';
import { adminRealtimeQueryOptions } from '../../services/admin/realtime';
import { TrendingUp, Users, Activity, RefreshCw, Award, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import StatCard from '../../components/Admin/StatCard';
import ChartCard from '../../components/Admin/ChartCard';
import { Line, Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Tooltip, Legend, Filler);

const tooltipStyle = {
  backgroundColor: '#0f172a',
  padding: 12,
  cornerRadius: 8,
  titleFont: { weight: 600, size: 12 },
  bodyFont: { size: 12 },
};

const Analytics: React.FC = () => {
  const [days, setDays] = useState(30);

  const { data: dashboard, isLoading: dashLoading, refetch, isFetching } = useQuery({
    queryKey: ['admin-analytics-dashboard'],
    queryFn: fetchDashboardAnalytics,
    ...adminRealtimeQueryOptions,
  });

  const { data: engagement } = useQuery({
    queryKey: ['admin-analytics-engagement', days],
    queryFn: () => fetchEngagementAnalytics(days),
    ...adminRealtimeQueryOptions,
  });

  const growth = Array.isArray(dashboard?.charts?.userGrowth) ? dashboard.charts.userGrowth : [];
  const hasGrowthData = growth.some((d: any) => Number(d.count || 0) > 0);

  const userGrowthChart = {
    labels: growth.map((d: any) => d._id),
    datasets: [
      {
        label: 'New Users',
        data: growth.map((d: any) => Number(d.count || 0)),
        fill: true,
        borderColor: '#4f46e5',
        backgroundColor: 'rgba(79,70,229,0.08)',
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#4f46e5',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        borderWidth: 2,
      },
    ],
  };

  const emptyDistribution = [
    { range: '0-20%', count: 0 },
    { range: '21-40%', count: 0 },
    { range: '41-60%', count: 0 },
    { range: '61-80%', count: 0 },
    { range: '81-100%', count: 0 },
  ];
  const quizScores =
    Array.isArray(engagement?.quizScoreDistribution) && engagement.quizScoreDistribution.length > 0
      ? engagement.quizScoreDistribution
      : emptyDistribution;

  const quizScoreChart = {
    labels: quizScores.map((d: any) => d.range),
    datasets: [
      {
        label: 'Students',
        data: quizScores.map((d: any) => d.count),
        backgroundColor: ['#fb7185', '#fb923c', '#facc15', '#4ade80', '#6366f1'],
        borderRadius: 6,
        barThickness: 28,
      },
    ],
  };

  const emptyWeeklyProgress = [
    { week: 'Week 1', completed: 0 },
    { week: 'Week 2', completed: 0 },
    { week: 'Week 3', completed: 0 },
    { week: 'Week 4', completed: 0 },
  ];
  const progressData =
    Array.isArray(engagement?.weeklyProgress) && engagement.weeklyProgress.length > 0
      ? engagement.weeklyProgress
      : emptyWeeklyProgress;

  const progressChart = {
    labels: progressData.map((d: any) => d.week),
    datasets: [
      {
        label: 'Completed Quizzes',
        data: progressData.map((d: any) => d.completed),
        fill: true,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16,185,129,0.08)',
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#10b981',
        pointBorderColor: '#fff',
        pointBorderWidth: 2,
        borderWidth: 2,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false }, tooltip: tooltipStyle },
    scales: {
      y: {
        beginAtZero: true,
        min: hasGrowthData ? 0 : -0.5,
        suggestedMax: hasGrowthData ? undefined : 2,
        ticks: { precision: 0, color: '#94a3b8', font: { size: 11 } },
        grid: { color: 'rgba(15,23,42,0.05)' },
        border: { display: false },
      },
      x: {
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 11 } },
        border: { display: false },
      },
    },
  };

  const totalUsers = dashboard?.metrics?.users?.total ?? 0;
  const verifiedUsers = dashboard?.metrics?.users?.verified ?? 0;
  const newThisWeek = dashboard?.metrics?.users?.newThisWeek ?? 0;
  const totalLogins = dashboard?.metrics?.activity?.totalLogins ?? 0;
  const failedLogins = dashboard?.metrics?.activity?.failedLogins ?? 0;
  const successRate = totalLogins > 0 ? Math.round(((totalLogins - failedLogins) / totalLogins) * 100) : 0;

  return (
    <div className="space-y-6">
      {/* Page intro */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">
            Analytics
          </h2>
          <p className="text-sm text-slate-600 mt-1.5 max-w-xl">
            Track user progress, quiz performance, and platform engagement over time.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm font-medium text-slate-700 focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 outline-none transition"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="inline-flex items-center gap-2 h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-60 transition-colors"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Total Users"
          value={dashLoading ? '—' : totalUsers.toLocaleString()}
          trend={`+${newThisWeek} this week`}
          trendDirection="up"
          icon={<Users className="h-5 w-5" />}
          accent="indigo"
        />
        <StatCard
          label="Verified Users"
          value={dashLoading ? '—' : verifiedUsers.toLocaleString()}
          trend={`${totalUsers > 0 ? Math.round((verifiedUsers / totalUsers) * 100) : 0}% of total`}
          icon={<Award className="h-5 w-5" />}
          accent="emerald"
        />
        <StatCard
          label="Total Logins"
          value={dashLoading ? '—' : totalLogins.toLocaleString()}
          trend={`${successRate}% success rate`}
          icon={<Activity className="h-5 w-5" />}
          accent="amber"
        />
        <StatCard
          label="New This Week"
          value={dashLoading ? '—' : newThisWeek.toLocaleString()}
          trend="Active registrations"
          trendDirection="up"
          icon={<TrendingUp className="h-5 w-5" />}
          accent="rose"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        <ChartCard title="User growth" description="New user registrations over time">
          <div className="h-60 sm:h-64">
            {dashLoading ? (
              <div className="h-full flex items-center justify-center">
                <Loader2 className="h-5 w-5 text-indigo-600 animate-spin" />
              </div>
            ) : growth.length > 0 && hasGrowthData ? (
              <Line data={userGrowthChart} options={chartOptions as any} />
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center">
                <p className="text-sm font-medium text-slate-700">No new sign-ups in the last {days} days</p>
                <p className="text-xs text-slate-500 mt-1">Auto-refreshes every 20 seconds</p>
              </div>
            )}
          </div>
        </ChartCard>

        <ChartCard
          title="Quiz score distribution"
          description="How students are performing on quizzes"
        >
          <div className="h-60 sm:h-64">
            <Bar data={quizScoreChart} options={chartOptions as any} />
          </div>
        </ChartCard>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        <ChartCard title="Weekly quiz completions" description="Student quiz completion trends">
          <div className="h-60 sm:h-64">
            <Line data={progressChart} options={chartOptions as any} />
          </div>
        </ChartCard>

        <ChartCard title="Performance metrics" description="Overall platform performance">
          <div className="space-y-5 py-1">
            {[
              {
                label: 'Average Quiz Score',
                value: Number(engagement?.avgQuizScore ?? 0),
                color: 'from-indigo-500 to-indigo-600',
              },
              {
                label: 'Path Completion Rate',
                value: Number(engagement?.pathCompletionRate ?? 0),
                color: 'from-emerald-500 to-emerald-600',
              },
              {
                label: 'User Engagement Rate',
                value: Number(engagement?.engagementRate ?? 0),
                color: 'from-amber-500 to-amber-600',
              },
              {
                label: 'Login Success Rate',
                value: Number(successRate ?? 0),
                color: 'from-rose-500 to-rose-600',
              },
            ].map((item) => (
              <div key={item.label} className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-700">{item.label}</span>
                  <span className="text-sm font-semibold text-slate-900 tabular-nums">
                    {item.value}%
                  </span>
                </div>
                <div className="h-1.5 rounded-full bg-slate-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full bg-gradient-to-r ${item.color} transition-all`}
                    style={{ width: `${Math.min(100, Math.max(0, item.value))}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>

      {/* Recent Activity Table */}
      {dashboard?.recentActivities && dashboard.recentActivities.length > 0 && (
        <ChartCard title="Recent user activity" description="Latest platform interactions" contentClassName="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50/60">
                <tr className="border-b border-slate-100">
                  <th className="text-left py-3 px-5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Action
                  </th>
                  <th className="text-left py-3 px-5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Resource
                  </th>
                  <th className="text-left py-3 px-5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="text-left py-3 px-5 text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                    Time
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {dashboard.recentActivities.slice(0, 8).map((a: any, idx: number) => {
                  const ok = a.status === 'success';
                  return (
                    <tr
                      key={a.id || a._id || `activity-${idx}`}
                      className="hover:bg-slate-50/60 transition-colors"
                    >
                      <td className="py-3 px-5 font-medium text-slate-800">{a.action}</td>
                      <td className="py-3 px-5 text-slate-600">{a.resource}</td>
                      <td className="py-3 px-5">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium border ${
                            ok
                              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                              : 'bg-rose-50 text-rose-700 border-rose-200'
                          }`}
                        >
                          {ok ? (
                            <CheckCircle2 className="h-3 w-3" />
                          ) : (
                            <XCircle className="h-3 w-3" />
                          )}
                          {a.status}
                        </span>
                      </td>
                      <td className="py-3 px-5 text-slate-500 tabular-nums">
                        {new Date(a.createdAt).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </ChartCard>
      )}
    </div>
  );
};

export default Analytics;
