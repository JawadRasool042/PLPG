import type { AnalysisResponse } from '../services/interestService';
import type { UserInterests } from '../store/useStore';

/**
 * Slider 0–10 → display percent 0–100. Same formula everywhere: (value / 10) * 100.
 */
/**
 * Collect unique tags from assessment free-text (comma / newline separated) for profile + search.
 */
export function collectAssessmentTags(known: string, want: string, goals: string): string[] {
  const blob = [known, want, goals].join(',');
  const parts = blob
    .split(/[,;\n]+/)
    .map((s) => s.trim())
    .filter(Boolean)
    .map((s) => s.slice(0, 64));
  return [...new Set(parts.map((p) => p.toLowerCase()))].slice(0, 48);
}

export function getPercentage(value: number | string | undefined): number {
  const v = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(v)) return 0;
  return Math.round(Math.max(0, Math.min(100, (v / 10) * 100)));
}

/** 0–10 slider → 0..1 (stored `confidence` unit in profile). */
export function sliderIntensityUnit(sliderValue: number | string | undefined): number {
  return getPercentage(sliderValue) / 100;
}

/**
 * Build profile `allInterests`: each domain `confidence` = slider/10 (0–1).
 * Falls back to API share only when that domain has no slider value in this assessment.
 */
export function buildAllInterestsFromSlidersAndRanked(
  ranked: AnalysisResponse['ranked_interests'] | undefined,
  scores: Record<string, number>,
): { domain: string; confidence: number }[] {
  const parsed = (ranked || []).map((item) => {
    const name = item.name;
    const w = Math.max(0, Number(scores[name] ?? 0));
    let confidence: number;
    if (w > 0) {
      confidence = Math.min(1, Math.max(0, w / 10));
    } else {
      const raw = parseFloat(String(item.percentage || '0').replace('%', ''));
      confidence = Number.isFinite(raw) ? Math.min(1, Math.max(0, raw / 100)) : 0;
    }
    return { domain: name, confidence };
  });
  const unique = parsed.filter(
    (entry, idx, arr) =>
      entry.domain &&
      arr.findIndex((x) => x.domain.toLowerCase() === entry.domain.toLowerCase()) === idx,
  );
  return unique.sort((a, b) => b.confidence - a.confidence);
}

/** Primary row `confidence` in profile: matches slider height (e.g. 7 → 0.7), not model share. */
export function primaryStrengthFromSliders(primary: string, scores: Record<string, number>): number {
  return sliderIntensityUnit(Number(scores[primary] ?? 0));
}

/** Normalize legacy API titles so Coding never shows the generic "Software Engineer" card label. */
export function sanitizeCareerPathTitle(primaryInterest: string, title: string | undefined | null): string {
  const raw = (title ?? '').trim();
  if (!raw || primaryInterest !== 'Coding') return raw;
  if (raw.toLowerCase() === 'software engineer') {
    return 'Programming & Application Developer';
  }
  return raw;
}

/** Domains the user rated above zero, sorted by rating (highest first). */
export function ratedDomainsFromScores(
  domainScores: Record<string, number> | undefined | null,
): { domain: string; score: number }[] {
  if (!domainScores || typeof domainScores !== 'object') return [];
  const rows = Object.entries(domainScores)
    .map(([domain, raw]) => ({
      domain,
      score: typeof raw === 'number' ? raw : Number(raw),
    }))
    .filter((r) => Number.isFinite(r.score) && r.score > 0)
    .sort((a, b) => b.score - a.score);
  return rows;
}

/** Primary domain from slider ratings when available; otherwise saved ML primary. */
export function getEffectivePrimaryInterest(interests: UserInterests | null): string {
  if (!interests) return '';
  const rated = ratedDomainsFromScores(interests.domainScores);
  if (rated.length > 0) return rated[0].domain;
  return interests.primaryInterest || '';
}

export interface InterestAssessmentDisplay {
  primary: string;
  confidenceRatio: number;
  confidencePct: number;
  tagDomains: string[];
}

/**
 * Labels for dashboard / quizzes: derived from stored slider scores when present,
 * so they match what the user actually selected instead of a mismatched ML pick.
 */
export function getInterestAssessmentDisplay(interests: UserInterests | null): InterestAssessmentDisplay {
  if (!interests) {
    return { primary: '', confidenceRatio: 0, confidencePct: 0, tagDomains: [] };
  }

  const rated = ratedDomainsFromScores(interests.domainScores);
  if (rated.length > 0) {
    const top = rated[0];
    const ratio = sliderIntensityUnit(top.score);
    const tagDomains = rated.slice(0, 3).map((r) => r.domain);
    return {
      primary: top.domain,
      confidenceRatio: ratio,
      confidencePct: getPercentage(top.score),
      tagDomains,
    };
  }

  const tagDomains = (interests.allInterests || [])
    .slice(0, 3)
    .map((i) => i.domain)
    .filter(Boolean);

  return {
    primary: interests.primaryInterest || '',
    confidenceRatio: interests.confidence ?? 0,
    confidencePct: Math.round((interests.confidence ?? 0) * 100),
    tagDomains,
  };
}

/** Emoji per interest domain (shared across Home, assessment, learning path). */
export const INTEREST_DOMAIN_ICONS: Record<string, string> = {
  Coding: '💻',
  'Web Development': '🌐',
  'Game Development': '🎮',
  Cybersecurity: '🔐',
  'Data Science': '📊',
  'Mobile Development': '📱',
  'Cloud Computing': '☁️',
  'AI & Machine Learning': '🤖',
  'Physical Games / Sports': '⚽',
};

export function getInterestDomainIcon(domain: string): string {
  const normalized = (domain || '').trim().toLowerCase();
  const match = Object.keys(INTEREST_DOMAIN_ICONS).find((k) => k.toLowerCase() === normalized);
  return match ? INTEREST_DOMAIN_ICONS[match] : '📌';
}

/** Canonical backend `DOMAINS` keys — `/generate-roadmap` expects these in `scores`. */
export const ROADMAP_DOMAIN_KEYS = [
  'Coding',
  'Web Development',
  'Game Development',
  'Cybersecurity',
  'Data Science',
  'Mobile Development',
  'Cloud Computing',
  'AI & Machine Learning',
  'Physical Games / Sports',
] as const;

/**
 * Map persisted assessment sliders → `scores` payload for roadmap/resume generation.
 * Unknown domains are skipped; backend fills missing keys with its default (5).
 */
export function buildRoadmapScoresPayload(
  domainScores: Record<string, number> | undefined | null,
): Record<string, number> | undefined {
  if (!domainScores || typeof domainScores !== 'object') return undefined;
  const byLower = new Map<string, number>();
  for (const [k, raw] of Object.entries(domainScores)) {
    const n = typeof raw === 'number' ? raw : Number(raw);
    if (!Number.isFinite(n)) continue;
    byLower.set(String(k).trim().toLowerCase(), n);
  }
  const out: Record<string, number> = {};
  for (const canonical of ROADMAP_DOMAIN_KEYS) {
    const direct = domainScores[canonical];
    const resolved =
      typeof direct === 'number' && Number.isFinite(direct) ? direct : byLower.get(canonical.toLowerCase());
    if (typeof resolved === 'number' && Number.isFinite(resolved)) {
      out[canonical] = Math.max(0, Math.min(10, resolved));
    }
  }
  return Object.keys(out).length ? out : undefined;
}
