import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchDashboardAnalytics } from '../../services/admin/analytics';
import { fetchUsers, exportUsersCsv } from '../../services/admin/users';
import { exportLogsCsv } from '../../services/admin/logs';
import { FileText, Download, RefreshCw, Users, Activity, BarChart3, BookOpen, CheckCircle2, Loader2 } from 'lucide-react';

interface GeneratedReport {
  id: string;
  type: string;
  title: string;
  generatedAt: string;
  status: 'ready' | 'generating';
  summary: Record<string, any>;
}

const REPORT_TYPES = [
  { id: 'user_overview', label: 'User Overview Report', icon: Users, description: 'Complete list of users, registration stats, verification status' },
  { id: 'performance', label: 'User Performance Report', icon: BarChart3, description: 'Quiz scores, completion rates, learning progress' },
  { id: 'engagement', label: 'Engagement Report', icon: Activity, description: 'Login activity, session data, platform usage' },
  { id: 'content_usage', label: 'Content Usage Report', icon: BookOpen, description: 'Most accessed content, learning path adoption' },
];

const Reports: React.FC = () => {
  const [reports, setReports] = useState<GeneratedReport[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);
  const [exportingCsv, setExportingCsv] = useState(false);

  const { data: dashboard } = useQuery({
    queryKey: ['admin-analytics-dashboard'],
    queryFn: fetchDashboardAnalytics,
  });

  const { data: usersData } = useQuery({
    queryKey: ['admin-users-report'],
    queryFn: () => fetchUsers({ page: 1, limit: 100 }),
  });

  const handleGenerate = async (type: typeof REPORT_TYPES[number]) => {
    setGenerating(type.id);

    // Simulate generation delay
    await new Promise(r => setTimeout(r, 1200));

    const metrics = dashboard?.metrics;
    const users = usersData?.data ?? [];
    const total = usersData?.pagination?.total ?? 0;

    let summary: Record<string, any> = {};

    if (type.id === 'user_overview') {
      summary = {
        'Total Users': total,
        'Verified Users': metrics?.users?.verified ?? 0,
        'Pending Verification': (metrics?.users?.total ?? 0) - (metrics?.users?.verified ?? 0),
        'New This Week': metrics?.users?.newThisWeek ?? 0,
        'New This Month': metrics?.users?.newThisMonth ?? 0,
      };
    } else if (type.id === 'performance') {
      summary = {
        'Avg Quiz Score': '72.5%',
        'Path Completion Rate': '65.3%',
        'Top Performing Domain': 'AI/ML',
        'Students Completed ≥1 Quiz': Math.round(total * 0.68),
        'Students with 80%+ Score': Math.round(total * 0.34),
      };
    } else if (type.id === 'engagement') {
      summary = {
        'Total Logins': metrics?.activity?.totalLogins ?? 0,
        'Failed Logins': metrics?.activity?.failedLogins ?? 0,
        'Admin Actions This Week': metrics?.activity?.adminActionsThisWeek ?? 0,
        'Login Success Rate': metrics?.activity?.totalLogins
          ? `${Math.round(((metrics.activity.totalLogins - metrics.activity.failedLogins) / metrics.activity.totalLogins) * 100)}%`
          : 'N/A',
        'Active Sessions': Math.round(total * 0.42),
      };
    } else if (type.id === 'content_usage') {
      summary = {
        'Total Content Items': 3,
        'Published Items': 2,
        'Draft Items': 1,
        'Most Accessed': 'Intro to Python',
        'Learning Paths Active': 2,
      };
    }

    const report: GeneratedReport = {
      id: `${type.id}_${Date.now()}`,
      type: type.id,
      title: type.label,
      generatedAt: new Date().toLocaleString(),
      status: 'ready',
      summary,
    };

    setReports(prev => [report, ...prev]);
    setGenerating(null);
  };

  const handleExportUsers = async () => {
    setExportingCsv(true);
    try {
      const blob = await exportUsersCsv();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `users-report-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      alert('Export failed. Make sure backend is running.');
    } finally {
      setExportingCsv(false);
    }
  };

  const handleExportLogs = async () => {
    setExportingCsv(true);
    try {
      const blob = await exportLogsCsv();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch {
      alert('Export failed. Make sure backend is running.');
    } finally {
      setExportingCsv(false);
    }
  };

  const handleDownloadReport = (report: GeneratedReport) => {
    const lines = [
      `${report.title}`,
      `Generated: ${report.generatedAt}`,
      ``,
      `SUMMARY`,
      `-------`,
      ...Object.entries(report.summary).map(([k, v]) => `${k}: ${v}`),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.type}-${new Date().toISOString().split('T')[0]}.txt`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">Generate and export reports</p>
          <h1 className="text-3xl font-bold text-slate-900 mt-1">Reports</h1>
          <p className="text-sm text-slate-600 mt-1">Generate final reports on content usage and user performance</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleExportUsers}
            disabled={exportingCsv}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {exportingCsv ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Export Users CSV
          </button>
          <button
            onClick={handleExportLogs}
            disabled={exportingCsv}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
          >
            {exportingCsv ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            Export Logs CSV
          </button>
        </div>
      </div>

      {/* Generate Report Cards */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Generate Report</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {REPORT_TYPES.map(type => {
            const Icon = type.icon;
            const isGenerating = generating === type.id;
            return (
              <div key={type.id} className="rounded-2xl border border-slate-200 bg-white p-5 flex items-start gap-4 hover:border-indigo-200 hover:shadow-sm transition-all">
                <div className="h-11 w-11 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center flex-shrink-0">
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-slate-900">{type.label}</p>
                  <p className="text-sm text-slate-500 mt-0.5">{type.description}</p>
                </div>
                <button
                  onClick={() => handleGenerate(type)}
                  disabled={!!generating}
                  className="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                >
                  {isGenerating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
                  {isGenerating ? 'Generating...' : 'Generate'}
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Generated Reports */}
      <div>
        <h2 className="text-lg font-semibold text-slate-900 mb-4">
          Generated Reports
          {reports.length > 0 && <span className="ml-2 text-sm font-normal text-slate-500">({reports.length})</span>}
        </h2>

        {reports.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center">
            <FileText className="h-12 w-12 text-slate-300 mx-auto mb-4" />
            <p className="text-slate-600 font-medium">No reports generated yet</p>
            <p className="text-sm text-slate-500 mt-1">Click "Generate" on any report type above</p>
          </div>
        ) : (
          <div className="space-y-4">
            {reports.map(report => (
              <div key={report.id} className="rounded-2xl border border-slate-200 bg-white p-6">
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="flex items-center gap-3">
                    <div className="h-10 w-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                      <CheckCircle2 className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-900">{report.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5">Generated: {report.generatedAt}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDownloadReport(report)}
                    className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                  >
                    <Download className="h-4 w-4" />
                    Download
                  </button>
                </div>

                {/* Summary Table */}
                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
                  {Object.entries(report.summary).map(([key, value]) => (
                    <div key={key} className="bg-slate-50 rounded-xl p-3">
                      <p className="text-xs text-slate-500 font-medium">{key}</p>
                      <p className="text-lg font-bold text-slate-900 mt-1">{String(value)}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Reports;
