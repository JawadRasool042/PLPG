/**
 * Roadmap-derived topic strings (phase topics + course picks) and canonical domain labels.
 * Domain chips on Quizzes use `LEARNING_DOMAIN_LABELS` (synced with backend `DOMAINS`).
 */

/** Canonical learning domains — keep in sync with `DOMAINS` in `backend-python/personalized_learning_path.py`. */
export const LEARNING_DOMAIN_LABELS: readonly string[] = [
  'Coding',
  'Web Development',
  'Game Development',
  'Cybersecurity',
  'Data Science',
  'Mobile Development',
  'Cloud Computing',
  'AI & Machine Learning',
  'Physical Games / Sports',
];

export function normalizeRoadmapDomain(value: string): string {
  const key = (value || '').trim().toLowerCase();
  const domainMap: Record<string, string> = {
    'ai/ml': 'AI & Machine Learning',
    'ai & machine learning': 'AI & Machine Learning',
    'artificial intelligence': 'AI & Machine Learning',
    'machine learning': 'AI & Machine Learning',
    'web dev': 'Web Development',
    'web development': 'Web Development',
    'cyber security': 'Cybersecurity',
    cybersecurity: 'Cybersecurity',
    'data science': 'Data Science',
    'mobile development': 'Mobile Development',
    'cloud computing': 'Cloud Computing',
    'game development': 'Game Development',
    'physical games / sports': 'Physical Games / Sports',
    sports: 'Physical Games / Sports',
    coding: 'Coding',
  };
  return domainMap[key] || value;
}

const PLACEHOLDER_SUBSTRINGS = [
  'connect to the learning api',
  'wait for the roadmap api',
];

function isPlaceholderTopic(text: string): boolean {
  const lower = text.toLowerCase();
  return PLACEHOLDER_SUBSTRINGS.some((p) => lower.includes(p));
}

function pushStringTopics(out: string[], raw: unknown): void {
  if (!Array.isArray(raw)) return;
  for (const item of raw) {
    if (typeof item !== 'string') continue;
    const t = item.trim();
    if (!t || isPlaceholderTopic(t)) continue;
    out.push(t);
  }
}

export const ROADMAP_PHASE_KEYS = ['basic', 'intermediate', 'advanced', 'expert'] as const;

export const ROADMAP_PHASE_LABELS: Record<(typeof ROADMAP_PHASE_KEYS)[number], string> = {
  basic: 'Basic',
  intermediate: 'Intermediate',
  advanced: 'Advanced',
  expert: 'Expert',
};

export function getRoadmapStageBlock(
  roadmap: Record<string, unknown>,
  key: (typeof ROADMAP_PHASE_KEYS)[number],
): Record<string, unknown> | undefined {
  const direct = roadmap[key];
  if (direct && typeof direct === 'object') return direct as Record<string, unknown>;
  if (key === 'basic') {
    const legacy = roadmap.beginner ?? roadmap.Beginner ?? roadmap.Basic;
    if (legacy && typeof legacy === 'object') return legacy as Record<string, unknown>;
  }
  return undefined;
}

export function collectQuizTopicsFromRoadmap(
  roadmap: Record<string, unknown> | null | undefined,
): string[] {
  if (!roadmap || typeof roadmap !== 'object') return [];

  const out: string[] = [];
  const phaseKeys = [
    ...ROADMAP_PHASE_KEYS,
    'beginner',
    'Beginner',
    'Intermediate',
    'Advanced',
    'Expert',
    'Basic',
  ] as const;

  for (const k of phaseKeys) {
    const block = roadmap[k];
    if (block && typeof block === 'object') {
      pushStringTopics(out, (block as { topics?: unknown }).topics);
      pushStringTopics(out, (block as { all_topics?: unknown }).all_topics);
    }
  }

  const resources = roadmap.resources;
  if (resources && typeof resources === 'object') {
    pushStringTopics(out, (resources as { courses?: unknown }).courses);
  }

  return out;
}

export function collectQuizTopicsFromSecondaryInsights(
  insights: Record<string, unknown> | null | undefined,
): string[] {
  if (!insights || typeof insights !== 'object') return [];
  const out: string[] = [];
  for (const value of Object.values(insights)) {
    if (!value || typeof value !== 'object') continue;
    const courses = (value as { recommended_courses?: unknown }).recommended_courses;
    pushStringTopics(out, courses);
  }
  return out;
}

export function mergeUniqueTopicStrings(...lists: string[][]): string[] {
  const seen = new Set<string>();
  const merged: string[] = [];
  for (const list of lists) {
    for (const raw of list) {
      const t = typeof raw === 'string' ? raw.trim() : '';
      if (!t || isPlaceholderTopic(t)) continue;
      const key = t.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      merged.push(t);
    }
  }
  return merged;
}
