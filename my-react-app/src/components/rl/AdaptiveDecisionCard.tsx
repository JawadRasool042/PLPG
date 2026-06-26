import React, { useEffect, useState } from 'react';
import type { RLDecision } from '../../services/rlService';
import { formatActionLabel } from '../../services/rlService';

interface AdaptiveDecisionCardProps {
  decision: RLDecision | null;
  loading?: boolean;
  compact?: boolean;
  /** When compact, still show the four metric tiles (e.g. quiz screen). */
  showMetrics?: boolean;
  onRequestNext?: () => void;
  /** When the decision was last fetched (for live UI). */
  updatedAt?: Date | null;
}

const ACTION_BADGE_STYLES: Record<string, string> = {
  increase_difficulty: 'bg-orange-100 text-orange-700 border-orange-200',
  decrease_difficulty: 'bg-blue-100 text-blue-700 border-blue-200',
  keep_difficulty: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  change_topic: 'bg-purple-100 text-purple-700 border-purple-200',
  give_hint: 'bg-amber-100 text-amber-700 border-amber-200',
  shorten_quiz: 'bg-slate-100 text-slate-700 border-slate-200',
  extend_quiz: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  recommend_revision: 'bg-rose-100 text-rose-700 border-rose-200',
  recommend_project: 'bg-teal-100 text-teal-700 border-teal-200',
  recommend_resource: 'bg-sky-100 text-sky-700 border-sky-200',
};

const formatRelativeTime = (d: Date): string => {
  const sec = Math.round((Date.now() - d.getTime()) / 1000);
  if (sec < 5) return 'just now';
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  return `${Math.floor(min / 60)}h ago`;
};

const AdaptiveDecisionCard: React.FC<AdaptiveDecisionCardProps> = ({
  decision,
  loading,
  compact,
  showMetrics,
  onRequestNext,
  updatedAt,
}) => {
  const [, setRelativeTick] = useState(0);
  useEffect(() => {
    if (!updatedAt) return;
    const id = window.setInterval(() => setRelativeTick((n) => n + 1), 2000);
    return () => window.clearInterval(id);
  }, [updatedAt]);

  const showStatRow = !compact || !!showMetrics;

  if (loading) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <span className="inline-block h-2 w-2 animate-ping rounded-full bg-indigo-500" />
          Adaptive engine is thinking…
        </div>
      </div>
    );
  }

  if (!decision) {
    return null;
  }

  const badgeClass =
    ACTION_BADGE_STYLES[decision.action] ?? 'bg-slate-100 text-slate-700 border-slate-200';

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Adaptive Recommendation
          </p>
          <h3 className="mt-1 text-lg font-bold text-slate-900">
            {formatActionLabel(decision.action)}
          </h3>
          <p className={`mt-2 ${compact ? 'text-xs' : 'text-sm'} text-slate-600`}>{decision.reason}</p>
        </div>
        <span
          className={`inline-flex items-center rounded-full border px-3 py-1 text-xs font-semibold ${badgeClass}`}
        >
          Next: {decision.next_difficulty}
        </span>
      </div>

      {showStatRow && (
        <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Accuracy" value={`${Math.round(decision.state.accuracy * 100)}%`} />
          <Stat label="Streak" value={`${decision.state.streak}`} />
          <Stat label="Engagement" value={`${Math.round(decision.state.engagement_score * 100)}%`} />
          <Stat
            label="Dropout risk"
            value={`${Math.round(decision.state.dropout_risk * 100)}%`}
            warn={decision.state.dropout_risk > 0.5}
          />
        </dl>
      )}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="inline-flex items-center gap-1 font-medium text-emerald-700">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
            </span>
            Live
          </span>
          {updatedAt ? <span>· updated {formatRelativeTime(updatedAt)}</span> : null}
          <span>
            · Policy v{decision.policy_version}
            {decision.exploration ? ' · exploring' : ' · exploiting'}
            {' · '}
            ε={decision.metadata.epsilon}
          </span>
        </span>
        {onRequestNext && (
          <button
            type="button"
            onClick={onRequestNext}
            className="rounded-lg border border-indigo-200 px-3 py-1 font-medium text-indigo-600 hover:bg-indigo-50"
          >
            Refresh now
          </button>
        )}
      </div>
    </div>
  );
};

const Stat: React.FC<{ label: string; value: string; warn?: boolean }> = ({ label, value, warn }) => (
  <div
    className={`rounded-xl border px-3 py-2 ${
      warn ? 'border-rose-200 bg-rose-50' : 'border-slate-200 bg-slate-50'
    }`}
  >
    <p className="text-[11px] font-medium uppercase tracking-wide text-slate-500">{label}</p>
    <p className={`text-base font-semibold ${warn ? 'text-rose-700' : 'text-slate-800'}`}>{value}</p>
  </div>
);

export default AdaptiveDecisionCard;
