import React, { useState } from 'react';
import { fetchReport } from '../../services/admin/analytics';
import { exportUsersCsv } from '../../services/admin/users';
import { exportLogsCsv } from '../../services/admin/logs';
import {
  FileText,
  Download,
  RefreshCw,
  Users,
  Activity,
  BarChart3,
  BookOpen,
  CheckCircle2,
  Loader2,
  Sparkles,
} from 'lucide-react';

interface GeneratedReport {
  id: string;
  type: string;
  title: string;
  generatedAt: string;
  status: 'ready' | 'generating';
  summary: Record<string, any>;
}

const REPORT_TYPES = [
  {
    id: 'user_overview',
    label: 'User Overview',
    icon: Users,
    description: 'Complete user list, registration stats, and verification status',
    accent: 'bg-indigo-50 text-indigo-600 ring-1 ring-indigo-100',
  },
  {
    id: 'performance',
    label: 'User Performance',
    icon: BarChart3,
    description: 'Quiz scores, completion rates, and learning progress',
    accent: 'bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100',
  },
  {
    id: 'engagement',
    label: 'Engagement',
    icon: Activity,
    description: 'Login activity, session data, and platform usage',
    accent: 'bg-amber-50 text-amber-600 ring-1 ring-amber-100',
  },
  {
    id: 'content_usage',
    label: 'Content Usage',
    icon: BookOpen,
    description: 'Most accessed content and learning path adoption',
    accent: 'bg-rose-50 text-rose-600 ring-1 ring-rose-100',
  },
];

const Reports: React.FC = () => {
  const [reports, setReports] = useState<GeneratedReport[]>([]);
  const [generating, setGenerating] = useState<string | null>(null);
  const [exportingCsv, setExportingCsv] = useState(false);

  const handleGenerate = async (type: typeof REPORT_TYPES[number]) => {
    setGenerating(type.id);
    try {
      const liveReport = await fetchReport({ reportType: type.id });
      const summary = liveReport?.summary || {};
      const report: GeneratedReport = {
        id: `${type.id}_${Date.now()}`,
        type: type.id,
        title: type.label,
        generatedAt: new Date(liveReport?.generatedAt || Date.now()).toLocaleString(),
        status: 'ready',
        summary,
      };
      setReports((prev) => [report, ...prev]);
    } finally {
      setGenerating(null);
    }
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
    <div className="space-y-6">
      {/* Page intro */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h2 className="text-2xl sm:text-3xl font-semibold text-slate-900 tracking-tight">
            Reports
          </h2>
          <p className="text-sm text-slate-600 mt-1.5 max-w-xl">
            Generate detailed reports on content usage, user performance, and platform engagement.
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={handleExportUsers}
            disabled={exportingCsv}
            className="inline-flex items-center gap-2 h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-60 transition-colors"
          >
            {exportingCsv ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">Users CSV</span>
          </button>
          <button
            onClick={handleExportLogs}
            disabled={exportingCsv}
            className="inline-flex items-center gap-2 h-9 px-3 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 disabled:opacity-60 transition-colors"
          >
            {exportingCsv ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            <span className="hidden sm:inline">Logs CSV</span>
          </button>
        </div>
      </div>

      {/* Generate Reports */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Sparkles className="h-4 w-4 text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
            Generate report
          </h3>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          {REPORT_TYPES.map((type) => {
            const Icon = type.icon;
            const isGenerating = generating === type.id;
            return (
              <div
                key={type.id}
                className="group rounded-xl border border-slate-200 bg-white p-4 sm:p-5 flex items-start gap-4 hover:shadow-md hover:border-slate-300 transition-all"
              >
                <div
                  className={`h-10 w-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-transform group-hover:scale-105 ${type.accent}`}
                >
                  <Icon className="h-5 w-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-900">{type.label}</p>
                  <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">
                    {type.description}
                  </p>
                </div>
                <button
                  onClick={() => handleGenerate(type)}
                  disabled={!!generating}
                  className="flex-shrink-0 inline-flex items-center gap-1.5 h-8 px-3 rounded-md bg-slate-900 text-white text-xs font-medium hover:bg-slate-800 disabled:opacity-50 transition-colors"
                >
                  {isGenerating ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <RefreshCw className="h-3.5 w-3.5" />
                  )}
                  {isGenerating ? 'Generating' : 'Generate'}
                </button>
              </div>
            );
          })}
        </div>
      </section>

      {/* Generated Reports */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-slate-900 uppercase tracking-wider">
            Generated reports
          </h3>
          {reports.length > 0 && (
            <span className="text-xs text-slate-500 tabular-nums">
              {reports.length} {reports.length === 1 ? 'report' : 'reports'}
            </span>
          )}
        </div>

        {reports.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50/50 p-10 sm:p-12 text-center">
            <div className="h-12 w-12 rounded-xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto mb-3">
              <FileText className="h-6 w-6" />
            </div>
            <p className="text-sm font-medium text-slate-700">No reports generated yet</p>
            <p className="text-xs text-slate-500 mt-1">
              Click "Generate" on any report type above
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {reports.map((report) => (
              <div
                key={report.id}
                className="rounded-xl border border-slate-200 bg-white p-4 sm:p-5"
              >
                <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="h-9 w-9 rounded-lg bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100 flex items-center justify-center flex-shrink-0">
                      <CheckCircle2 className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-slate-900 truncate">
                        {report.title}
                      </p>
                      <p className="text-[11px] text-slate-500 mt-0.5 tabular-nums">
                        Generated {report.generatedAt}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDownloadReport(report)}
                    className="inline-flex items-center gap-1.5 h-8 px-3 rounded-md border border-slate-200 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-colors"
                  >
                    <Download className="h-3.5 w-3.5" />
                    Download
                  </button>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
                  {Object.entries(report.summary).map(([key, value]) => (
                    <div
                      key={key}
                      className="bg-slate-50 border border-slate-100 rounded-lg p-3"
                    >
                      <p className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold truncate">
                        {key}
                      </p>
                      <p className="text-base sm:text-lg font-semibold text-slate-900 mt-1 tabular-nums">
                        {String(value)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
};

export default Reports;
