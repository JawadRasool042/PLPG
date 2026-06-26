const MCQ_LETTERS = ['A', 'B', 'C', 'D'] as const;

/** Letter key for an option string (e.g. "A) foo" → "A"). */
export function extractOptionKey(option: string, index: number): string {
  const text = String(option ?? '').trim();
  const directPrefix = text.match(/^([A-D])[\)\].:\-\s]/i);
  if (directPrefix) return directPrefix[1].toUpperCase();

  const optionWordPrefix = text.match(/^option\s+([A-D])\b/i);
  if (optionWordPrefix) return optionWordPrefix[1].toUpperCase();

  return MCQ_LETTERS[index] ?? 'A';
}

/** Normalize user/correct answer to a single letter A–D when possible. */
export function normalizeChoice(value: string | undefined | null): string {
  const raw = String(value ?? '').trim().toUpperCase();
  const direct = raw.match(/^([A-D])(?:[\)\].:\-\s]|$)/);
  if (direct) return direct[1];
  const optionWord = raw.match(/^OPTION\s+([A-D])\b/);
  if (optionWord) return optionWord[1];
  return raw;
}

/** Strip leading "A) " / "Option A:" for shorter inline display. */
export function stripOptionLetterPrefix(text: string): string {
  const t = String(text ?? '').trim();
  const stripped = t.replace(/^option\s+[A-D][\)\].:\-\s]*/i, '').replace(/^[A-D][\)\].:\-\s]+/i, '').trim();
  return stripped || t;
}

export function optionBodyForLetter(options: string[], letter: string): string | null {
  const L = normalizeChoice(letter);
  for (let i = 0; i < options.length; i++) {
    if (extractOptionKey(options[i], i) === L) {
      return stripOptionLetterPrefix(options[i]);
    }
  }
  return null;
}

/**
 * Human-readable blocks for post-quiz review (classic + mixed quizzes).
 */
export function buildMcqReviewNarratives(args: {
  options: string[];
  userAnswer: string;
  correctAnswer: string;
  isCorrect: boolean;
  explanation: string;
}): { whyCorrect: string; whyIncorrect: string | null } {
  const { options, userAnswer, correctAnswer, isCorrect, explanation } = args;
  const correctLetter = normalizeChoice(correctAnswer);
  const userLetter = normalizeChoice(userAnswer);
  const correctBody = optionBodyForLetter(options, correctLetter);
  const userBody = optionBodyForLetter(options, userLetter);
  const exp = (explanation || '').trim();

  const correctLabel = correctBody
    ? `Option ${correctLetter} (${correctBody})`
    : `Option ${correctLetter}`;

  const whyCorrectParts = [
    `${correctLabel} is the correct answer.`,
    correctBody
      ? `That choice matches what the question asks (for example the code output or definition in the prompt).`
      : null,
    exp ? exp : null,
  ].filter(Boolean);
  const whyCorrect = whyCorrectParts.join(' ');

  if (isCorrect) {
    return { whyCorrect, whyIncorrect: null };
  }

  const youLabel = userBody
    ? `You selected option ${userLetter} (${userBody}).`
    : `You selected option ${userLetter}.`;

  const whyIncorrectParts = [
    youLabel,
    `That option does not match the correct outcome or reasoning for this question.`,
    correctBody
      ? `${correctLabel} is correct because it aligns with the facts or output implied by the prompt.`
      : `${correctLabel} reflects the right conclusion.`,
    exp ? `Key idea to review: ${exp}` : null,
  ].filter(Boolean);

  return {
    whyCorrect,
    whyIncorrect: whyIncorrectParts.join(' '),
  };
}

export type AIQuizReasoningShape = {
  why_correct?: string;
  wrong_options?: Array<{ option?: string; reason?: string }>;
};

export function findWrongOptionReason(
  reasoning: AIQuizReasoningShape | undefined,
  userLetter: string
): string | null {
  if (!reasoning?.wrong_options?.length) return null;
  const u = normalizeChoice(userLetter);
  for (const wo of reasoning.wrong_options) {
    const o = normalizeChoice(wo.option ?? '');
    if (o === u && (wo.reason || '').trim()) {
      return (wo.reason || '').trim();
    }
  }
  return null;
}
