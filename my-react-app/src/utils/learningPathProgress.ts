/** Live path progress from quiz performance (cached roadmaps stay static). */

import type { UserPerformance } from '../services/quizService';
import { normalizeRoadmapDomain } from './roadmapTopics';

export interface DomainPerfSnapshot {
  avg: number;
  attempts: number;
  recent: number[];
}

export function getDomainPerfSnapshot(
  performance: UserPerformance | null | undefined,
  domain: string,
): DomainPerfSnapshot {
  if (!performance) return { avg: 0, recent: [], attempts: 0 };
  const target = normalizeRoadmapDomain(domain).toLowerCase();
  let topicStats: UserPerformance['byInterest'][string] | undefined = performance.byInterest?.[domain];
  if (!topicStats && performance.byInterest) {
    const match = Object.entries(performance.byInterest).find(
      ([key]) => normalizeRoadmapDomain(key).toLowerCase() === target,
    );
    topicStats = match?.[1];
  }
  const avg = topicStats?.averageScore ?? performance.overallStats?.averageScore ?? 0;
  const attempts = topicStats?.totalQuizzes ?? performance.overallStats?.totalQuizzes ?? 0;
  const recent = (performance.recentScores || [])
    .filter((r) => !r.interest || normalizeRoadmapDomain(r.interest).toLowerCase() === target)
    .map((r) => r.score)
    .slice(0, 5);
  return { avg, recent, attempts };
}

export function resolveCurrentPhase(
  totalPhases: number,
  perf: DomainPerfSnapshot,
  adaptiveState?: Record<string, number | string>,
): number {
  const phases = Math.max(1, totalPhases);
  const { avg, attempts } = perf;

  if (attempts > 0 || avg > 0) {
    if (attempts >= 4 && avg >= 82) return Math.min(phases, 4);
    if (attempts >= 3 && avg >= 72) return Math.min(phases, 3);
    if (attempts >= 2 && avg >= 52) return Math.min(phases, 2);
    return 1;
  }

  const stage = String(adaptiveState?.current_stage || '').toLowerCase();
  if (stage === 'expert') return phases;
  if (stage === 'advanced') return Math.min(phases, 3);
  if (stage === 'intermediate') return Math.min(phases, 2);
  if (stage === 'basic' || stage === 'beginner') return 1;

  const progression = Number(adaptiveState?.progression_completeness ?? 0);
  if (progression > 0) {
    return Math.max(1, Math.min(phases, Math.ceil(progression * phases)));
  }

  return 1;
}

export function computePathProgression(
  totalPhases: number,
  currentPhase: number,
  perf: DomainPerfSnapshot,
): number {
  const phases = Math.max(1, totalPhases);
  const phase = Math.max(1, Math.min(phases, currentPhase));
  const completedPhases = Math.max(0, phase - 1);
  const stageBase = completedPhases / phases;

  if (perf.attempts <= 0 && perf.avg <= 0) {
    return stageBase;
  }

  const attemptFactor = Math.min(1, perf.attempts / 3);
  const scoreFactor = Math.min(1, Math.max(0, perf.avg) / 100);
  const withinStage = attemptFactor * scoreFactor;

  return Math.min(1, stageBase + withinStage / phases);
}
