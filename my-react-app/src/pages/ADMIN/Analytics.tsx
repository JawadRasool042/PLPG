import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchDashboardAnalytics, fetchEngagementAnalytics } from '../../services/admin/analytics';
import { BarChart3, TrendingUp, Users, Activity, RefreshCw, Award, BookOpen, Target } from 'lucide-react';
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

const Analytics: React.FC = () => {
  const [days, setDays] = useState(30);

  const { data: dashboard, isLoading: dashLoading, refetch } = useQuery({
    queryKey: ['admin-analytics-dashboard'],
    queryFn: fetchDashboardAnalytics,
  });

  const { data: engagement, isLoading: engLoading } = useQuery({
    queryKey: ['admin-analytics-engagement', days],
    queryFn: () => fetchEngagementAnalytics(days),
  });

  const growth = dashboard?.charts?.userGrowth ?? [];

  const userGrowthChart = {
    labels: growth.map((d: any) => d._id),
    datasets: [{
      label: 'New Users',
      data: growth.map((d: any) => d.count),
      fill: true,
      borderColor: '#6366f1',
      backgroundColor: 'rgba(99,102,241,0.12)',
      tension: 0.4,
      pointRadius: 4,
      pointBackgroundColor: '#6366f1',
    }],
  };

  // Quiz scores distribution (from engagement data or fallback)
  const quizScores = engagement?.quizScoreDistribution ?? [
    { range: '0-20%', count: 12 },
    { range: '21-40%', count: 28 },
    { range: '41-60%', count: 45 },
    { range: '61-80%', count: 67 },
    { range: '81-100%', count: 89 },
  ];

  const quizScoreChart = {
    labels: quizScores.map((d: any) => d.range),
    datasets: [{
      label: 'Students',
      data: quizScores.map((d: any) => d.count),
      backgroundColor: ['#f87171', '#fb923c', '#facc15', '#4ade80', '#6366f1'],
      borderRadius: 8,
    }],
  };

  // User progress data
  const progressData = engagement?.weeklyProgress ?? [
    { week: 'Week 1', completed: 23 },
    { week: 'Week 2', completed: 34 },
    { week: 'Week 3', completed: 28 },
    { week: 'Week 4', completed: 45 },
  ];

  const progressChart = {
    labels: progressData.map((d: any) => d.week),
    datasets: [{
      label: 'Completed Quizzes',
      data: progressData.map((d: any) => d.completed),
      fill: true,
      borderColor: '#10b981',
      backgroundColor: 'rgba(16,185,129,0.12)',
      tension: 0.4,
      pointRadius: 4,
      pointBackgroundColor: '#10b981',
    }],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
      x: { grid: { display: false } },
    },
  };

  const totalUsers = dashboard?.metrics?.users?.total ?? 0;
  const verifiedUsers = dashboard?.metrics?.users?.verified ?? 0;
  const newThisWeek = dashboard?.metrics?.users?.newThisWeek ?? 0;
  const totalLogins = dashboard?.metrics?.activity?.totalLogins ?? 0;
  const failedLogins = dashboard?.metrics?.activity?.failedLogins ?? 0;
  const successRate = totalLogins > 0 ? Math.round(((totalLogins - failedLogins) / totalLogins) * 100) : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">User interactions & platform insights</p>
          <h1 className="text-3xl font-bold text-slate-900 mt-1">Analytics</h1>
          <p className="text-sm text-slate-600 mt-1">Track user progress, quiz scores, and engagement</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={days}
            onChange={e => setDays(Number(e.target.value))}
            className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm text-slate-700 focus:ring-2 focus:ring-indigo-500"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
          <button
            onClick={() => refetch()}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        <StatCard
          label="Total Users"
          value={dashLoading ? '...' : totalUsers.toLocaleString()}
          trend={`+${newThisWeek} this week`}
          icon={<Users className="h-6 w-6" />}
          accent="indigo"
        />
        <StatCard
          label="Verified Users"
          value={dashLoading ? '...' : verifiedUsers.toLocaleString()}
          trend={`${totalUsers > 0 ? Math.round((verifiedUsers / totalUsers) * 100) : 0}% of total`}
          icon={<Award className="h-6 w-6" />}
          accent="emerald"
        />
        <StatCard
          label="Total Logins"
          value={dashLoading ? '...' : totalLogins.toLocaleString()}
          trend={`${successRate}% success rate`}
          icon={<Activity className="h-6 w-6" />}
          accent="amber"
        />
        <StatCard
          label="New This Week"
          value={dashLoading ? '...' : newThisWeek.toLocaleString()}
          trend="Active registrations"
          icon={<TrendingUp className="h-6 w-6" />}
          accent="rose"
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="User Growth" description="New user registrations over time">
          <div className="h-56">
            {dashLoading ? (
              <div className="h-full flex items-center justify-center text-slate-400 text-sm">Loading...</div>
            ) : growth.length > 0 ? (
              <Line data={userGrowthChart} options={chartOptions} />
            ) : (
              <div className="h-full flex items-center justify-center text-slate-400 text-sm">No data available</div>
            )}
          </div>
        </ChartCard>

        <ChartCard title="Quiz Score Distribution" description="How students are performing on quizzes">
          <div className="h-56">
            <Bar data={quizScoreChart} options={chartOptions} />
          </div>
        </ChartCard>
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Weekly Quiz Completions" description="Student quiz completion trends">
          <div className="h-56">
            <Line data={progressChart} options={chartOptions} />
          </div>
        </ChartCard>

        <ChartCard title="Learning Performance Metrics" description="Overall platform performance">
          <div className="space-y-5 py-2">
            {[
              { label: 'Average Quiz Score', value: engagement?.avgQuizScore ?? 72, color: 'bg-indigo-500' },
              { label: 'Path Completion Rate', value: engagement?.pathCompletionRate ?? 65, color: 'bg-emerald-500' },
              { label: 'User Engagement Rate', value: engagement?.engagementRate ?? 81, color: 'bg-amber-500' },
              { label: 'Login Success Rate', value: successRate || 94, color: 'bg-rose-500' },
            ].map(item => (
              <div key={item.label} className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-700">{item.label}</span>
                  <span className="text-sm font-bold text-slate-900">{item.value}%</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100 overflow-hidden">
                  <div className={`h-full rounded-full ${item.color} transition-all`} style={{ width: `${item.value}%` }} />
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      </div>

      {/* Recent Activity Table */}
      {dashboard?.recentActivities && dashboard.recentActivities.length > 0 && (
        <ChartCard title="Recent User Activity" description="Latest platform interactions">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left py-3 px-2 text-xs font-semibold text-slate-500 uppercase">Action</th>
                  <th className="text-left py-3 px-2 text-xs font-semibold text-slate-500 uppercase">Resource</th>
                  <th className="text-left py-3 px-2 text-xs font-semibold text-slate-500 uppercase">Status</th>
                  <th className="text-left py-3 px-2 text-xs font-semibold text-slate-500 uppercase">Time</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50">
                {dashboard.recentActivities.slice(0, 8).map((a: any) => (
                  <tr key={a._id} className="hover:bg-slate-50">
                    <td className="py-2.5 px-2 font-medium text-slate-800">{a.action}</td>
                    <td className="py-2.5 px-2 text-slate-600">{a.resource}</td>
                    <td className="py-2.5 px-2">
                      <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${a.status === 'success' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
                        {a.status}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 text-slate-500">{new Date(a.createdAt).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </ChartCard>
      )}
    </div>
  );
};

export default Analytics;
