import React from 'react';
import { BookOpen, Check, Clock, Route } from 'lucide-react';
import { cn } from '../../lib/utils';
import type { UserPerformance } from '../../services/quizService';
import {
  computePathProgression,
  getDomainPerfSnapshot,
  resolveCurrentPhase,
} from '../../utils/learningPathProgress';
import type { RoadmapPhaseItem } from '../../utils/roadmapTopics';

type LearningPathRoadmapPreviewProps = {
  primary: string;
  phases: RoadmapPhaseItem[];
  performance: UserPerformance | null;
  adaptiveState?: Record<string, number | string>;
  loading?: boolean;
  onOpenPath?: () => void;
};

const LearningPathRoadmapPreview: React.FC<LearningPathRoadmapPreviewProps> = ({
  primary,
  phases,
  performance,
  adaptiveState,
  loading = false,
  onOpenPath,
}) => {
  const totalPhases = Math.max(phases.length, 1);
  const domainPerf = getDomainPerfSnapshot(performance, primary);
  const currentPhase = resolveCurrentPhase(totalPhases, domainPerf, adaptiveState);
  const progression = computePathProgression(totalPhases, currentPhase, domainPerf);
  const progressionPct = Math.round(progression * 100);

  if (loading) {
    return (
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8 mb-8">
        <div className="h-6 w-48 bg-slate-200 rounded animate-pulse mb-6" />
        <div className="h-3 w-full bg-slate-100 rounded-full animate-pulse mb-8" />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-24 bg-slate-100 rounded-xl animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  if (!phases.length) return null;

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 sm:p-8 mb-8">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
          <Route className="h-5 w-5 text-violet-600" aria-hidden />
          Learning path
        </h2>
        {onOpenPath && (
          <button
            type="button"
            onClick={onOpenPath}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition-colors shrink-0"
          >
            Open full path
          </button>
        )}
      </div>

      <div className="grid lg:grid-cols-[minmax(220px,280px)_minmax(0,1fr)] gap-6 lg:gap-8 items-start">
        <aside className="rounded-2xl border border-slate-200/90 bg-gradient-to-br from-violet-50/80 to-indigo-50/50 p-4 sm:p-5">
          <p className="text-sm text-slate-700 leading-relaxed">
            <span className="font-semibold text-slate-900">{primary}</span>
            <span className="text-slate-600"> — milestones from basic to expert.</span>
          </p>
          <div className="mt-4 rounded-xl border border-slate-200/90 bg-white/90 p-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-4">
              <span className="shrink-0 text-xs font-medium tabular-nums text-slate-600 sm:text-sm">
                Path progress{' '}
                <span className="font-semibold text-slate-900">{progressionPct}%</span>
              </span>
              <div className="h-2 min-h-[8px] w-full flex-1 overflow-hidden rounded-full bg-slate-200/90 shadow-inner">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-violet-600 via-violet-500 to-indigo-600 transition-[width] duration-700 ease-out"
                  style={{ width: `${Math.min(100, Math.max(0, progressionPct))}%` }}
                  role="progressbar"
                  aria-valuenow={progressionPct}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="Roadmap completion"
                />
              </div>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              {currentPhase} of {totalPhases} stages active
            </p>
          </div>
        </aside>

        <ol className="min-w-0 space-y-3 sm:space-y-4">
          {phases.map((phase, i) => {
            const isDone = i < currentPhase - 1;
            const isCurrent = i === currentPhase - 1;
            return (
              <li key={`${phase.phase}-${i}`} className="list-none">
                <article
                  className={cn(
                    'relative flex gap-3 rounded-xl border bg-white p-4 shadow-sm transition-all sm:gap-4 sm:p-5',
                    isCurrent && 'border-violet-300/80 ring-1 ring-violet-500/10 shadow-md',
                    isDone && 'border-slate-200/90',
                    !isCurrent && !isDone && 'border-slate-200/70 opacity-90',
                  )}
                >
                  <div className="relative flex shrink-0 flex-col items-center">
                    <div
                      className={cn(
                        'flex h-10 w-10 items-center justify-center rounded-full text-sm font-bold text-white shadow-md',
                        isDone && 'bg-gradient-to-br from-emerald-600 to-teal-600',
                        isCurrent && !isDone && 'bg-gradient-to-br from-violet-600 to-indigo-600',
                        !isCurrent && !isDone && 'bg-gradient-to-br from-slate-400 to-slate-500',
                      )}
                      aria-hidden
                    >
                      {isDone ? <Check className="h-5 w-5" strokeWidth={2.5} /> : i + 1}
                    </div>
                    {i < phases.length - 1 && (
                      <div
                        className={cn(
                          'mt-2 w-px min-h-[1.5rem] bg-gradient-to-b',
                          isDone ? 'from-emerald-200 via-slate-200 to-slate-200' : 'from-violet-300/80 via-violet-100 to-slate-200/90',
                        )}
                        aria-hidden
                      />
                    )}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="mb-2 flex flex-wrap items-baseline gap-x-2 gap-y-1">
                      <h3 className="text-base font-bold text-slate-900 sm:text-lg">{phase.phase}</h3>
                      {isCurrent && (
                        <span className="rounded-md border border-violet-200/80 bg-violet-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-violet-900">
                          Current focus
                        </span>
                      )}
                      {isDone && (
                        <span className="rounded-md border border-emerald-200/80 bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-emerald-900">
                          Complete
                        </span>
                      )}
                    </div>
                    <p className="mb-3 flex items-start gap-2 text-sm text-slate-600">
                      <Clock className="mt-0.5 h-4 w-4 shrink-0 text-slate-400" aria-hidden />
                      <span>{phase.duration}</span>
                    </p>
                    <div className="mb-1 flex items-center gap-2">
                      <BookOpen className="h-3.5 w-3.5 text-violet-600/90" aria-hidden />
                      <p className="text-[11px] font-bold uppercase tracking-[0.12em] text-slate-600">Topics</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {phase.topics.slice(0, 4).map((topic, j) => (
                        <span
                          key={j}
                          className="inline-flex max-w-full rounded-lg border border-violet-200/70 bg-violet-50/90 px-2.5 py-1 text-xs font-medium text-violet-950"
                        >
                          <span className="truncate">{topic}</span>
                        </span>
                      ))}
                      {phase.topics.length > 4 && (
                        <span className="text-xs text-slate-500 self-center">
                          +{phase.topics.length - 4} more
                        </span>
                      )}
                    </div>
                  </div>
                </article>
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
};

export default LearningPathRoadmapPreview;
