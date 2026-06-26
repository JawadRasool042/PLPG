import type { UserPerformance } from '../services/quizService';
import type { UserInterests } from '../store/useStore';
import { getEffectivePrimaryInterest } from './interestDisplay';
import { normalizeRoadmapDomain } from './roadmapTopics';

/** Step 1: interest assessment saved with a primary domain. */
export function hasCompletedInterestCheck(
  hasCompletedOnboarding: boolean,
  userInterests: UserInterests | null | undefined,
): boolean {
  return hasCompletedOnboarding && Boolean(getEffectivePrimaryInterest(userInterests ?? null));
}

/** Step 2: at least one completed quiz attempt (any domain). */
export function hasCompletedAnyQuiz(
  performance: UserPerformance | null | undefined,
): boolean {
  return (performance?.overallStats?.totalQuizzes ?? 0) > 0;
}

/** Quiz attempts on the student's primary interest domain. */
export function getDomainQuizCount(
  performance: UserPerformance | null | undefined,
  domain: string,
): number {
  if (!performance?.byInterest) return 0;
  const target = normalizeRoadmapDomain(domain).toLowerCase();
  let total = 0;
  for (const [key, stats] of Object.entries(performance.byInterest)) {
    if (normalizeRoadmapDomain(key).toLowerCase() === target) {
      total += stats.totalQuizzes || 0;
    }
  }
  return total;
}

/** Learning path unlocks after interest check + at least one quiz. */
export function hasCompletedDomainQuiz(
  performance: UserPerformance | null | undefined,
  domain: string,
  options?: { justCompletedDomain?: string | null },
): boolean {
  if (options?.justCompletedDomain) return true;
  if (getDomainQuizCount(performance, domain) > 0) return true;
  return hasCompletedAnyQuiz(performance);
}

/** Full gate: interest assessment → quiz → learning path. */
export function canAccessLearningPath(
  hasCompletedOnboarding: boolean,
  userInterests: UserInterests | null | undefined,
  performance: UserPerformance | null | undefined,
  options?: { justCompletedDomain?: string | null },
): boolean {
  if (!hasCompletedInterestCheck(hasCompletedOnboarding, userInterests)) return false;
  const primary = getEffectivePrimaryInterest(userInterests ?? null);
  if (!primary) return false;
  return hasCompletedDomainQuiz(performance, primary, options);
}
