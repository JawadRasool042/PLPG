import React, { useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useStore } from "../../store/useStore";
import { getEffectivePrimaryInterest } from "../../utils/interestDisplay";
import { LEARNING_DOMAIN_LABELS } from "../../utils/roadmapTopics";
import {
  startAIQuiz,
  requestNextAIQuestion,
  submitAIAnswer,
  finishAIQuiz,
  buildAIQuizAttemptSnapshot,
  deriveLevelRecommendation,
  AI_QUIZ_QUESTION_LIMIT,
  type AIQuizDifficulty,
  type AIQuizFeedback,
  type AIQuizLevelRecommendation,
  type AIQuizQuestion,
  type AIQuizSessionSummary,
} from "../../services/aiQuizService";
import { DEFAULT_PASSING_SCORE } from "../../services/remediationService";
import {
  findWrongOptionReason,
  normalizeChoice,
  optionBodyForLetter,
  buildMcqReviewNarratives,
} from "../../utils/quizReviewText";
import { Skeleton } from "../../components/ui/skeleton";

const DIFFICULTIES: AIQuizDifficulty[] = ["basic", "intermediate", "advanced", "expert"];
const ANSWER_LETTERS = ["A", "B", "C", "D"];

/** Backend returns 409 when /next is called but the session already has all MCQs. */
function isQuestionLimitReachedError(err: unknown): boolean {
  const e = err as {
    response?: { status?: number; data?: { code?: string; message?: string } };
    message?: string;
  };
  const d = e?.response?.data;
  if (e?.response?.status === 409 && d?.code === "QUESTION_LIMIT_REACHED") return true;
  const m = String(d?.message || e?.message || "");
  return m.includes("limited to") && m.includes("question");
}

const AIQuiz: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, user, userInterests, hasCompletedOnboarding } =
    useStore();

  const defaultTopic = getEffectivePrimaryInterest(userInterests) || "";
  const navState = (location.state || {}) as {
    topic?: string;
    difficulty?: AIQuizDifficulty;
  };

  const [topic, setTopic] = useState<string>(navState.topic || defaultTopic);
  const [difficulty, setDifficulty] = useState<AIQuizDifficulty>(
    navState.difficulty || "basic"
  );
  // AI quizzes are hard-capped to AI_QUIZ_QUESTION_LIMIT (10) MCQs per session.
  const targetCount = AI_QUIZ_QUESTION_LIMIT;

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questionIndex, setQuestionIndex] = useState<number>(0);
  const [question, setQuestion] = useState<AIQuizQuestion | null>(null);
  const [selectedAnswer, setSelectedAnswer] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<AIQuizFeedback | null>(null);

  const [stats, setStats] = useState<{ correct: number; total: number }>({
    correct: 0,
    total: 0,
  });
  const [summary, setSummary] = useState<AIQuizSessionSummary | null>(null);

  const [loadingState, setLoadingState] = useState<
    "idle" | "starting" | "answering" | "next" | "finishing"
  >("idle");
  const [error, setError] = useState<string | null>(null);
  const [autoStartAttempted, setAutoStartAttempted] = useState(false);

  const questionStartedAt = useRef<number>(Date.now());
  const finishingRef = useRef(false);

  useEffect(() => {
    if (defaultTopic && !topic) {
      setTopic(defaultTopic);
    }
  }, [defaultTopic, topic]);

  useEffect(() => {
    questionStartedAt.current = Date.now();
  }, [questionIndex, sessionId]);

  useEffect(() => {
    if (
      !isAuthenticated ||
      !user ||
      sessionId ||
      summary ||
      loadingState !== "idle" ||
      autoStartAttempted
    ) {
      return;
    }

    const hasPrefilledStart = !!(navState.topic && navState.difficulty);
    if (!hasPrefilledStart) return;

    setAutoStartAttempted(true);
    void handleStart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    isAuthenticated,
    user?.id,
    sessionId,
    summary,
    loadingState,
    autoStartAttempted,
    navState.topic,
    navState.difficulty,
  ]);

  const resetSessionState = () => {
    setSessionId(null);
    setQuestion(null);
    setQuestionIndex(0);
    setSelectedAnswer(null);
    setFeedback(null);
    setStats({ correct: 0, total: 0 });
    setSummary(null);
    finishingRef.current = false;
  };

  const handleStart = async (override?: { difficulty?: AIQuizDifficulty }) => {
    if (!topic.trim()) {
      setError("Please pick a topic first.");
      return;
    }
    const effectiveDifficulty = override?.difficulty ?? difficulty;
    try {
      setError(null);
      setLoadingState("starting");
      resetSessionState();
      const data = await startAIQuiz({
        topic: topic.trim(),
        difficulty: effectiveDifficulty,
        questionCount: targetCount,
      });
      if (DIFFICULTIES.includes((data.difficulty as AIQuizDifficulty) || "basic")) {
        setDifficulty(data.difficulty as AIQuizDifficulty);
      }
      setSessionId(data.session_id);
      setQuestionIndex(data.question_index);
      setQuestion(data.question);
    } catch (err: any) {
      setError(err.message || "Failed to start AI quiz");
    } finally {
      setLoadingState("idle");
    }
  };

  const handleAnswerSelect = async (letter: string) => {
    if (!sessionId || !question || loadingState === "answering" || selectedAnswer) return;
    setSelectedAnswer(letter);
    setError(null);
    try {
      setLoadingState("answering");
      const elapsed = Date.now() - questionStartedAt.current;
      const data = await submitAIAnswer({
        sessionId,
        questionIndex,
        answer: letter,
        timeSpentMs: elapsed,
      });
      if (typeof data.question_index === "number") {
        setQuestionIndex(data.question_index);
      }
      // Keep answers hidden during the active session; reveal in end-of-quiz summary.
      setFeedback(null);
      setStats((prev) => ({
        correct: prev.correct + (data.feedback.is_correct ? 1 : 0),
        total: prev.total + 1,
      }));

      const totalAnswered = data.total_answered ?? stats.total + 1;
      const atLimit =
        Boolean(data.limit_reached) || totalAnswered >= targetCount;

      if (atLimit) {
        await handleFinish();
      }
    } catch (err: any) {
      setError(err.message || "Failed to submit answer");
      setSelectedAnswer(null);
    } finally {
      setLoadingState("idle");
    }
  };

  const handleNext = async () => {
    if (!sessionId || loadingState === "answering" || loadingState === "next") return;
    if (stats.total >= targetCount) {
      void handleFinish();
      return;
    }
    try {
      setError(null);
      setLoadingState("next");
      const data = await requestNextAIQuestion({ sessionId });
      setQuestion(data.question);
      setQuestionIndex(data.question_index);
      setSelectedAnswer(null);
      setFeedback(null);
    } catch (err: any) {
      if (isQuestionLimitReachedError(err)) {
        setError(null);
        await handleFinish();
        return;
      }
      setError(err.message || "Failed to fetch next question");
    } finally {
      setLoadingState("idle");
    }
  };

  const handleFinish = async () => {
    if (!sessionId || finishingRef.current) return;
    finishingRef.current = true;
    setError(null);
    const activeSessionId = sessionId;
    try {
      setLoadingState("finishing");
      const data = await finishAIQuiz(activeSessionId);
      setSessionId(null);
      setQuestion(null);
      setSelectedAnswer(null);
      setFeedback(null);
      const domain = data.topic || topic;
      if (data.attemptId) {
        navigate(`/quiz/results/${data.attemptId}`, {
          state: {
            attemptSnapshot: buildAIQuizAttemptSnapshot(data, data.attemptId),
            mixedAttempt: {
              domain,
              score: data.score,
            },
            remediation: data.remediation,
          },
        });
        return;
      }
      setSummary({ ...data, topic: domain });
    } catch (err: any) {
      finishingRef.current = false;
      setError(err.message || "Failed to finish AI quiz");
    } finally {
      setLoadingState("idle");
    }
  };

  const reachedTarget = sessionId
    ? stats.total >= targetCount
    : false;

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  if (!hasCompletedOnboarding) {
    return (
      <Navigate
        to="/quizzes/interest-check"
        replace
        state={{ message: 'Complete the interest assessment before taking a quiz.' }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 pt-24 pb-12">
      <div className="max-w-5xl mx-auto px-4">
        {/* Setup card (pre-session OR after summary) */}
        {!sessionId && !summary && !autoStartAttempted && (
          <SetupCard
            topic={topic}
            setTopic={setTopic}
            difficulty={difficulty}
            setDifficulty={setDifficulty}
            targetCount={targetCount}
            onStart={handleStart}
            loading={loadingState === "starting"}
            primaryInterest={defaultTopic}
            hasCompletedOnboarding={hasCompletedOnboarding}
          />
        )}

        {/* Active session */}
        {sessionId && question && !summary && (
          <ActiveSession
            question={question}
            questionIndex={questionIndex}
            targetCount={targetCount}
            selectedAnswer={selectedAnswer}
            feedback={feedback}
            onAnswerSelect={handleAnswerSelect}
            onNext={handleNext}
            onFinish={handleFinish}
            loadingNext={loadingState === "next"}
            loadingAnswer={loadingState === "answering"}
            loadingFinish={loadingState === "finishing"}
            reachedTarget={reachedTarget}
          />
        )}

        {/* Auto-start / first question: keep visible until session + question load (do not tie to weak-concept fetch). */}
        {!sessionId && !summary && autoStartAttempted && loadingState === "starting" && (
          <div className="space-y-6" aria-busy="true" aria-label="Loading quiz">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="space-y-2 flex-1">
                  <Skeleton className="h-3 w-32 bg-slate-200" />
                  <Skeleton className="h-5 w-48 bg-slate-200" />
                </div>
                <Skeleton className="h-6 w-16 rounded-full bg-slate-200" />
              </div>
              <Skeleton className="h-2 w-full rounded-full bg-slate-200" />
            </div>
            <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 space-y-4">
              <Skeleton className="h-5 w-full bg-slate-200" />
              <Skeleton className="h-5 w-[90%] bg-slate-200" />
              <Skeleton className="h-5 w-[70%] bg-slate-200" />
              <div className="space-y-3 pt-4">
                <Skeleton className="h-14 w-full rounded-xl bg-slate-200" />
                <Skeleton className="h-14 w-full rounded-xl bg-slate-200" />
                <Skeleton className="h-14 w-full rounded-xl bg-slate-200" />
                <Skeleton className="h-14 w-full rounded-xl bg-slate-200" />
              </div>
              <p className="text-sm text-slate-500 pt-2">
                Generating your first question — this usually takes a few seconds.
              </p>
            </div>
          </div>
        )}

        {/* Finished summary */}
        {summary && (
          <SummaryCard
            summary={summary}
            onRestart={() => {
              setSummary(null);
              resetSessionState();
            }}
            onBack={() => navigate("/quizzes")}
            onGoToLearningPath={() =>
              navigate("/learning-path", {
                state: {
                  mixedAttempt: {
                    domain: summary.topic,
                    score: summary.score,
                  },
                },
              })
            }
            onStartAtLevel={(nextLevel) => {
              setDifficulty(nextLevel);
              setSummary(null);
              resetSessionState();
              setAutoStartAttempted(true);
              void handleStart({ difficulty: nextLevel });
            }}
          />
        )}

        {error && (
          <div className="mt-6 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Setup card
// ---------------------------------------------------------------------------
const SetupCard: React.FC<{
  topic: string;
  setTopic: (v: string) => void;
  difficulty: AIQuizDifficulty;
  setDifficulty: (d: AIQuizDifficulty) => void;
  targetCount: number;
  onStart: () => void;
  loading: boolean;
  primaryInterest: string;
  hasCompletedOnboarding: boolean;
}> = ({
  topic,
  setTopic,
  difficulty,
  setDifficulty,
  targetCount,
  onStart,
  loading,
  primaryInterest,
  hasCompletedOnboarding,
}) => {
  const domainSuggestions = useMemo(() => {
    const labels = [...LEARNING_DOMAIN_LABELS];
    const norm = (primaryInterest || "").trim();
    if (
      norm &&
      !labels.some((l) => l.toLowerCase() === norm.toLowerCase())
    ) {
      labels.unshift(norm);
    }
    return labels;
  }, [primaryInterest]);

  return (
    <div className="bg-gradient-to-br from-indigo-600 to-purple-600 rounded-2xl shadow-lg p-6 mb-6 text-white">
      <p className="text-xs uppercase tracking-wide text-indigo-200">PLPG</p>
      <h2 className="text-2xl font-bold mt-1">PLPG Generated quiz</h2>
      <p className="text-sm text-indigo-100 mt-2 max-w-2xl">
        {hasCompletedOnboarding
          ? `Questions are built on demand from your profile (including ${primaryInterest}), weak concepts when available, and the difficulty you choose—not from a fixed question bank.`
          : "Pick a topic or domain chip below — questions are generated on demand by your PLPG backend, not from a fixed bank."}
      </p>
      {topic.trim() ? (
        <div className="flex flex-wrap gap-2 mt-3">
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-white/20 text-white border border-white/30">
            Topic: {topic.trim()}
          </span>
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-white/15 text-white/95 border border-white/25 capitalize">
            {difficulty}
          </span>
        </div>
      ) : null}

      <label className="block text-sm font-semibold text-indigo-100 mb-2 mt-5">
        Topic
      </label>
      <input
        value={topic}
        onChange={(e) => setTopic(e.target.value)}
        placeholder="e.g. Python Decorators, React Hooks, or pick a chip"
        className="w-full rounded-xl border-2 border-white/40 bg-white/10 px-4 py-3 mb-3 text-white placeholder:text-indigo-200/80 focus:outline-none focus:ring-2 focus:ring-white/40"
      />
      <p className="text-xs font-semibold uppercase tracking-wide text-indigo-200 mb-2">
        Quick picks
      </p>
      <div className="flex flex-wrap gap-2 mb-6">
        {domainSuggestions.map((s) => {
          const active = topic.trim().toLowerCase() === s.toLowerCase();
          return (
            <button
              key={s}
              type="button"
              onClick={() => setTopic(s)}
              className={`px-3 py-1.5 text-sm font-semibold rounded-full border-2 capitalize transition-colors ${
                active
                  ? "border-white bg-white text-indigo-700"
                  : "border-white/40 bg-transparent text-white hover:bg-white/10"
              }`}
            >
              {s}
            </button>
          );
        })}
      </div>

      <p className="text-sm font-semibold mb-3 text-indigo-100">Difficulty</p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {DIFFICULTIES.map((d) => (
          <button
            key={d}
            type="button"
            onClick={() => setDifficulty(d)}
            className={`px-4 py-3 rounded-xl border-2 font-semibold capitalize transition-colors ${
              difficulty === d
                ? "bg-white text-indigo-700 border-white"
                : "bg-transparent text-white border-white/40 hover:bg-white/10"
            }`}
          >
            {d}
          </button>
        ))}
      </div>

      <div className="mb-6 rounded-xl border border-white/20 bg-white/10 px-4 py-3">
        <p className="text-sm font-semibold text-indigo-100">
          Quiz length: {targetCount} questions
        </p>
        <p className="text-xs text-indigo-200 mt-1">
          AI quiz automatically finishes after {AI_QUIZ_QUESTION_LIMIT} questions.
        </p>
      </div>

      <button
        onClick={onStart}
        disabled={loading || !topic.trim()}
        className="w-full sm:w-auto px-6 py-3 bg-white text-indigo-700 rounded-xl font-semibold hover:bg-indigo-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? "Starting…" : "Start Quiz"}
      </button>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Active session — question + instant feedback
// ---------------------------------------------------------------------------
const ActiveSession: React.FC<{
  question: AIQuizQuestion;
  questionIndex: number;
  targetCount: number;
  selectedAnswer: string | null;
  feedback: AIQuizFeedback | null;
  onAnswerSelect: (letter: string) => void;
  onNext: () => void;
  onFinish: () => void;
  loadingNext: boolean;
  loadingAnswer: boolean;
  loadingFinish: boolean;
  reachedTarget: boolean;
}> = ({
  question,
  questionIndex,
  targetCount,
  selectedAnswer,
  feedback,
  onAnswerSelect,
  onNext,
  onFinish,
  loadingNext,
  loadingAnswer,
  loadingFinish,
  reachedTarget,
}) => {
  const progress = Math.min(
    100,
    Math.round(((questionIndex + 1) / Math.max(1, targetCount)) * 100)
  );

  const optionLetter = (_option: string, idx: number): string =>
    ANSWER_LETTERS[idx] ?? "A";

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-xs uppercase text-slate-500">
              {question.topic} • {question.difficulty}
            </p>
            <h2 className="text-lg font-semibold text-slate-900 mt-1">
              Question {questionIndex + 1}
            </h2>
          </div>
          <span className="text-xs font-medium text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full">
            {questionIndex + 1} / {targetCount}
          </span>
        </div>
        <div className="w-full bg-slate-200 rounded-full h-2">
          <div
            className="bg-indigo-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <p className="text-lg text-slate-900 mb-6 whitespace-pre-wrap">
          {question.question}
        </p>

        <div className="space-y-3">
          {question.options.map((option, idx) => {
            const letter = optionLetter(option, idx);
            const isSelected = selectedAnswer === letter;

            const base =
              "w-full text-left p-4 rounded-xl border-2 transition-all";
            let style = "border-slate-200 hover:border-indigo-300 bg-white";

            if (isSelected) {
              style = "border-indigo-600 bg-indigo-50";
            }

            return (
              <button
                key={letter}
                onClick={() => onAnswerSelect(letter)}
                disabled={!!selectedAnswer || loadingAnswer}
                className={`${base} ${style} disabled:cursor-default`}
              >
                <div className="flex items-center gap-3">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                      isSelected
                        ? "bg-indigo-600 text-white"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {letter}
                  </div>
                  <span className="text-base text-slate-800">{option}</span>
                  {isSelected && (
                    <span className="ml-auto text-indigo-700 text-sm font-semibold">
                      Selected
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {loadingAnswer && (
          <p className="mt-4 text-sm text-slate-500">Checking your answer...</p>
        )}
      </div>

      {feedback && <FeedbackPanel feedback={feedback} />}

      <div className="flex flex-col sm:flex-row gap-3 justify-end">
        <button
          onClick={onFinish}
          disabled={loadingFinish || loadingAnswer}
          className="px-6 py-3 border-2 border-slate-300 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors disabled:opacity-50"
        >
          {loadingFinish ? "Wrapping up..." : "Finish session"}
        </button>
        {selectedAnswer && !reachedTarget && (
          <button
            onClick={onNext}
            disabled={loadingNext || loadingAnswer}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50"
          >
            {loadingNext
              ? "Generating next question..."
              : "Next question"}
          </button>
        )}
        {selectedAnswer && reachedTarget && (
          <button
            onClick={onFinish}
            disabled={loadingFinish}
            className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors disabled:opacity-50"
          >
            {loadingFinish ? "Wrapping up..." : "Complete quiz"}
          </button>
        )}
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Feedback panel
// ---------------------------------------------------------------------------
const FeedbackPanel: React.FC<{ feedback: AIQuizFeedback }> = ({ feedback }) => {
  const wrongMap = useMemo(() => {
    const map: Record<string, string> = {};
    const byLetter = feedback.why_wrong || {};
    Object.entries(byLetter).forEach(([letter, reason]) => {
      map[String(letter).toUpperCase()] = String(reason || "");
    });
    (feedback.reasoning?.wrong_options || []).forEach((entry) => {
      if (entry?.option) {
        map[entry.option.toUpperCase()] = entry.reason || "";
      }
    });
    return map;
  }, [feedback.reasoning]);

  return (
    <div
      className={`rounded-2xl shadow-sm border p-6 space-y-4 ${
        feedback.is_correct
          ? "bg-green-50 border-green-200"
          : "bg-rose-50 border-rose-200"
      }`}
    >
      <div className="flex items-center gap-3">
        <div
          className={`w-10 h-10 rounded-full flex items-center justify-center text-white font-bold ${
            feedback.is_correct ? "bg-green-600" : "bg-rose-600"
          }`}
        >
          {feedback.is_correct ? "✓" : "✗"}
        </div>
        <div>
          <p
            className={`text-base font-semibold ${
              feedback.is_correct ? "text-green-800" : "text-rose-800"
            }`}
          >
            {feedback.is_correct
              ? "Correct! Well done."
              : "Not quite — let's break it down."}
          </p>
          <p className="text-xs text-slate-600">
            Correct answer: {feedback.correct_answer}
          </p>
        </div>
      </div>

      {(feedback.why_correct || feedback.reasoning?.why_correct) && (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs uppercase font-semibold text-slate-500 mb-1">
            Why {feedback.correct_answer} is correct
          </p>
          <p className="text-sm text-slate-800">
            {feedback.why_correct || feedback.reasoning.why_correct}
          </p>
        </div>
      )}

      {Object.keys(wrongMap).length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs uppercase font-semibold text-slate-500 mb-2">
            Why the other options miss
          </p>
          <ul className="space-y-2 text-sm text-slate-800">
            {Object.entries(wrongMap).map(([letter, reason]) => (
              <li key={letter} className="flex gap-3">
                <span className="font-semibold text-rose-700 w-6">
                  {letter}
                </span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {feedback.concept_summary && (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <p className="text-xs uppercase font-semibold text-slate-500 mb-1">
            Concept summary
          </p>
          <p className="text-sm text-slate-800">{feedback.concept_summary}</p>
        </div>
      )}

      {feedback.memory_tip && (
        <div className="bg-indigo-50 rounded-xl border border-indigo-200 p-4">
          <p className="text-xs uppercase font-semibold text-indigo-700 mb-1">
            Memory tip
          </p>
          <p className="text-sm text-indigo-900">{feedback.memory_tip}</p>
        </div>
      )}

      {!feedback.is_correct && feedback.concept_summary && (
        <p className="text-xs text-rose-700">
          We'll retrain you on this concept in upcoming questions.
        </p>
      )}
    </div>
  );
};

// ---------------------------------------------------------------------------
// Recommendation card — surfaces the AI's level suggestion based on the score
// ---------------------------------------------------------------------------
const CHANGE_META: Record<
  string,
  { icon: string; label: string; tone: string; cta: string }
> = {
  promote: {
    icon: "⬆️",
    label: "Step up",
    tone: "from-emerald-500 to-teal-600",
    cta: "Start at",
  },
  jump: {
    icon: "🚀",
    label: "Jump ahead",
    tone: "from-indigo-500 to-purple-600",
    cta: "Take the leap to",
  },
  repeat: {
    icon: "🔁",
    label: "Repeat",
    tone: "from-sky-500 to-blue-600",
    cta: "Practice again at",
  },
  demote: {
    icon: "⬇️",
    label: "Step back",
    tone: "from-amber-500 to-orange-600",
    cta: "Go back to",
  },
};

// Render markdown-ish **bold** without bringing in a library.
const renderEmphasis = (text: string): React.ReactNode => {
  const parts = text.split(/\*\*([^*]+?)\*\*/g);
  return parts.map((part, idx) =>
    idx % 2 === 1 ? (
      <strong key={idx} className="font-semibold">
        {part}
      </strong>
    ) : (
      <React.Fragment key={idx}>{part}</React.Fragment>
    )
  );
};

const RecommendationCard: React.FC<{
  recommendation: AIQuizLevelRecommendation;
  topic: string;
  onStart: (level: AIQuizDifficulty) => void;
}> = ({ recommendation, topic, onStart }) => {
  const meta =
    CHANGE_META[recommendation.change] || CHANGE_META.repeat;
  const recommendedLevel =
    (recommendation.recommended || "basic").toLowerCase() as AIQuizDifficulty;

  return (
    <div className="rounded-2xl shadow-sm border border-slate-200 bg-white overflow-hidden">
      <div
        className={`bg-gradient-to-br ${meta.tone} text-white px-6 py-5 flex items-center gap-4`}
      >
        <span className="text-4xl" aria-hidden>
          {meta.icon}
        </span>
        <div className="flex-1 min-w-0">
          <p className="uppercase text-xs tracking-wide opacity-90">
            AI recommendation • {meta.label}
          </p>
          <h3 className="text-xl font-bold mt-0.5">
            Next quiz at{" "}
            <span className="capitalize underline decoration-white/40 underline-offset-4">
              {recommendation.recommended}
            </span>
          </h3>
          <p className="text-sm text-white/85 mt-0.5">
            Based on your score of{" "}
            <strong>{Math.round(recommendation.score)}%</strong> on{" "}
            <span className="capitalize">{recommendation.from}</span>
          </p>
        </div>
      </div>

      <div className="px-6 py-5 space-y-4">
        <p className="text-sm text-slate-700 leading-relaxed">
          {renderEmphasis(recommendation.reason)}
        </p>

        {/* Level ladder visualisation */}
        <div className="flex items-center gap-1 sm:gap-2 text-xs">
          {(
            ["basic", "intermediate", "advanced", "expert"] as AIQuizDifficulty[]
          ).map((lvl, idx, arr) => {
            const isFrom = lvl === recommendation.from;
            const isTo = lvl === recommendedLevel;
            return (
              <React.Fragment key={lvl}>
                <div
                  className={`flex-1 px-2 py-1.5 rounded-md text-center font-medium border transition-colors ${
                    isTo
                      ? "bg-indigo-600 text-white border-indigo-600 shadow-sm"
                      : isFrom
                      ? "bg-slate-100 text-slate-600 border-slate-200"
                      : "bg-white text-slate-400 border-slate-200"
                  }`}
                >
                  <span className="capitalize">{lvl}</span>
                  {isFrom && (
                    <span className="block text-[10px] mt-0.5 opacity-70">
                      You played
                    </span>
                  )}
                  {isTo && !isFrom && (
                    <span className="block text-[10px] mt-0.5 opacity-90">
                      Recommended
                    </span>
                  )}
                </div>
                {idx < arr.length - 1 && (
                  <span className="text-slate-300" aria-hidden>
                    →
                  </span>
                )}
              </React.Fragment>
            );
          })}
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pt-2">
          <p className="text-xs text-slate-500">
            Topic: <span className="font-medium text-slate-700">{topic}</span>
          </p>
          <button
            type="button"
            onClick={() => onStart(recommendedLevel)}
            className={`inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-gradient-to-br ${meta.tone} hover:opacity-95 shadow-sm`}
          >
            {meta.cta}{" "}
            <span className="capitalize">{recommendation.recommended}</span>
            <span aria-hidden>→</span>
          </button>
        </div>
      </div>
    </div>
  );
};

// ---------------------------------------------------------------------------
// Summary view
// ---------------------------------------------------------------------------
const SummaryCard: React.FC<{
  summary: AIQuizSessionSummary;
  onRestart: () => void;
  onBack: () => void;
  onGoToLearningPath: () => void;
  onStartAtLevel: (level: AIQuizDifficulty) => void;
}> = ({ summary, onRestart, onBack, onGoToLearningPath, onStartAtLevel }) => {
  const accuracy = summary.score;
  const passedQuiz = accuracy >= DEFAULT_PASSING_SCORE;
  const tone =
    accuracy >= 80
      ? "from-green-600 to-emerald-600"
      : accuracy >= 60
      ? "from-amber-500 to-orange-500"
      : "from-rose-600 to-pink-600";

  const recommendation =
    summary.recommendation ??
    deriveLevelRecommendation(summary.score, summary.difficulty);

  const sessionScoreFeedback = useMemo(() => {
    if (accuracy >= 95) {
      return "Excellent mastery. Move to harder questions and timed problem-solving next.";
    }
    if (accuracy >= 85) {
      return "Great performance. Increase difficulty and focus only on remaining weak concepts.";
    }
    if (accuracy >= 75) {
      return "Strong result. One more practice round at this level, then level up.";
    }
    if (accuracy >= 65) {
      return "Good progress. Review incorrect answers and practice targeted subtopics before the next quiz.";
    }
    if (accuracy >= 50) {
      return "Developing performance. Stay at this level and strengthen core concepts first.";
    }
    if (accuracy >= 35) {
      return "Low score signal. Step down one difficulty level and do focused revision.";
    }
    return "Very low score signal. Restart with fundamentals and guided examples before retesting.";
  }, [accuracy]);

  const answerMap = useMemo(() => {
    const map = new Map<number, { isCorrect: boolean; userAnswer?: string }>();
    (summary.answers || []).forEach((a) => {
      map.set(Number(a.questionIndex), {
        isCorrect: Boolean(a.isCorrect),
        userAnswer: a.userAnswer,
      });
    });
    return map;
  }, [summary.answers]);

  const progressSeries = useMemo(() => {
    let runningCorrect = 0;
    const answeredRows = (summary.answers || [])
      .map((a) => ({
        index: Number(a.questionIndex),
        isCorrect: Boolean(a.isCorrect),
      }))
      .filter((a) => Number.isFinite(a.index) && a.index >= 0)
      .sort((a, b) => a.index - b.index);

    return answeredRows.map((row, i) => {
      if (row.isCorrect) runningCorrect += 1;
      const attempted = i + 1;
      const pct = attempted > 0 ? Math.round((runningCorrect / attempted) * 100) : 0;
      return {
        q: row.index + 1,
        isCorrect: row.isCorrect,
        pct,
      };
    });
  }, [summary.answers]);

  return (
    <div className="space-y-6">
      <div
        className={`rounded-2xl shadow-sm bg-gradient-to-br ${tone} p-8 text-white text-center`}
      >
        <p className="uppercase text-sm tracking-wide opacity-80">
          Session complete
        </p>
        <p className="text-5xl font-bold mt-2">{accuracy}%</p>
        <p className="mt-2 text-white/90 capitalize">
          {summary.topic} · {summary.difficulty}
        </p>

        <div className="mt-6 rounded-xl bg-white/15 border border-white/25 px-5 py-4 text-left backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-white/90">
            AI suggestion
          </p>
          <p className="text-lg font-bold mt-1">
            Next quiz:{" "}
            <span className="capitalize underline decoration-white/40">
              {recommendation.recommended}
            </span>{" "}
            <span className="text-sm font-normal text-white/85">
              (you played{" "}
              <span className="capitalize font-medium">{recommendation.from}</span>
              )
            </span>
          </p>
          <p className="text-sm text-white/95 mt-2 leading-relaxed">
            {renderEmphasis(recommendation.reason)}
          </p>
        </div>
        <div className="mt-4 rounded-xl bg-white/15 border border-white/25 px-5 py-4 text-left backdrop-blur-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-white/90">
            Score feedback
          </p>
          <p className="text-sm text-white/95 mt-2 leading-relaxed">
            You scored <span className="font-semibold">{accuracy}%</span>. {sessionScoreFeedback}
          </p>
        </div>
      </div>

      <RecommendationCard
        recommendation={recommendation}
        topic={summary.topic}
        onStart={onStartAtLevel}
      />

      <div className={`rounded-2xl border p-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 ${
        passedQuiz
          ? 'border-indigo-200 bg-gradient-to-r from-indigo-50 to-violet-50'
          : 'border-amber-200 bg-gradient-to-r from-amber-50 to-orange-50'
      }`}>
        <div>
          <p className={`text-xs font-semibold uppercase tracking-wide ${
            passedQuiz ? 'text-indigo-700' : 'text-amber-700'
          }`}>
            {passedQuiz ? 'Personalized path unlocked' : 'Remediation required'}
          </p>
          <p className="text-sm text-slate-700 mt-1">
            {passedQuiz ? (
              <>
                View your OpenAI-generated Roadmap, Courses, Careers, and Resume for{" "}
                <span className="font-semibold text-slate-900">{summary.topic}</span>.
              </>
            ) : (
              <>
                You scored below {DEFAULT_PASSING_SCORE}%. Retake this quiz after studying a
                personalized lesson built from your answers.
              </>
            )}
          </p>
        </div>
        {passedQuiz ? (
          <button
            type="button"
            onClick={onGoToLearningPath}
            className="shrink-0 px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors shadow-sm shadow-indigo-600/20"
          >
            Go to Learning Path →
          </button>
        ) : (
          <button
            type="button"
            onClick={onRestart}
            className="shrink-0 px-6 py-3 bg-amber-600 text-white rounded-xl font-semibold hover:bg-amber-700 transition-colors"
          >
            Retake quiz
          </button>
        )}
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6">
        <h3 className="font-semibold text-slate-900 mb-4">Results Graph</h3>
        <div className="rounded-xl border border-slate-200 p-4 bg-slate-50 mb-5">
          <p className="text-xs uppercase font-semibold text-slate-500">Performance</p>
          <div className="mt-3 h-3 rounded-full bg-rose-100 overflow-hidden">
            <div
              className="h-full bg-emerald-500"
              style={{
                width: `${summary.totalAnswered > 0 ? (summary.correctCount / summary.totalAnswered) * 100 : 0}%`,
              }}
            />
          </div>
          <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
            <div>
              <p className="text-slate-500">Answered</p>
              <p className="font-semibold text-slate-800">{summary.totalAnswered}</p>
            </div>
            <div>
              <p className="text-slate-500">Correct</p>
              <p className="font-semibold text-emerald-700">{summary.correctCount}</p>
            </div>
            <div>
              <p className="text-slate-500">Incorrect</p>
              <p className="font-semibold text-rose-700">
                {Math.max(0, summary.totalAnswered - summary.correctCount)}
              </p>
            </div>
          </div>
        </div>
        <div>
          <p className="text-xs uppercase font-semibold text-slate-500 mb-3">Per-question performance</p>
          <div className="grid grid-cols-5 sm:grid-cols-8 lg:grid-cols-10 gap-2">
            {progressSeries.map((pt) => (
              <div
                key={pt.q}
                className={`rounded-lg border px-2 py-2 text-center ${
                  pt.isCorrect
                    ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                    : "bg-rose-50 border-rose-200 text-rose-700"
                }`}
                title={`Q${pt.q}: ${pt.isCorrect ? "Correct" : "Incorrect"} | Running accuracy ${pt.pct}%`}
              >
                <p className="text-[10px] font-semibold">Q{pt.q}</p>
                <p className="text-[11px] font-bold">{pt.isCorrect ? "✓" : "✗"}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 space-y-4">
        <h3 className="font-semibold text-slate-900">Question review</h3>
        {summary.questions.map((q, idx) => {
          const answered = answerMap.get(idx);
          const options = q.options ?? [];
          const correctLetter = normalizeChoice(q.correct_answer ?? "");
          const userLetter = answered?.userAnswer
            ? normalizeChoice(answered.userAnswer)
            : "";
          const modelWhyCorrect = (q.reasoning as { why_correct?: string } | undefined)?.why_correct?.trim();
          const wrongSpecific = userLetter
            ? findWrongOptionReason(q.reasoning, userLetter)
            : null;
          const concept = (q.concept_summary ?? "").trim();
          const fallbackExp = modelWhyCorrect || concept || (q.memory_tip ?? "").trim();

          const built =
            options.length && answered
              ? buildMcqReviewNarratives({
                  options,
                  userAnswer: answered.userAnswer ?? "",
                  correctAnswer: q.correct_answer ?? "",
                  isCorrect: Boolean(answered.isCorrect),
                  explanation: fallbackExp || "Review the question and the reference answer above.",
                })
              : null;

          const correctBody = correctLetter ? optionBodyForLetter(options, correctLetter) : null;
          const whyCorrectText =
            modelWhyCorrect && correctLetter
              ? `Option ${correctLetter}${correctBody ? ` (${correctBody})` : ""} is correct. ${modelWhyCorrect}`
              : built?.whyCorrect ||
                (concept ? `Correct because: ${concept}` : fallbackExp) ||
                "See the correct answer above.";

          const whyIncorrectText =
            answered?.isCorrect === false
              ? wrongSpecific ||
                built?.whyIncorrect ||
                (userLetter
                  ? `Option ${userLetter} does not match the expected result for this question. Compare it with option ${correctLetter}.`
                  : null)
              : null;

          return (
            <div
              key={idx}
              className="border border-slate-200 rounded-xl p-4 bg-slate-50 space-y-3"
            >
              <p className="text-sm font-semibold text-slate-700 mb-1">
                Q{idx + 1}
              </p>
              <p className="text-sm text-slate-900 mb-2">{q.question}</p>
              <p className="text-xs text-slate-600">
                Correct answer: {q.correct_answer}
                {correctBody ? ` — ${correctBody}` : ""}
              </p>
              {answered && (
                <p
                  className={`text-xs mt-1 ${answered.isCorrect ? "text-emerald-700" : "text-rose-700"}`}
                >
                  Your answer: {answered.userAnswer || "-"} (
                  {answered.isCorrect ? "correct" : "incorrect"})
                </p>
              )}

              <div className="rounded-lg border border-emerald-200 bg-emerald-50/80 p-3">
                <p className="text-xs font-semibold text-emerald-900 uppercase tracking-wide mb-1">
                  Why the correct answer is right
                </p>
                <p className="text-sm text-emerald-950 leading-relaxed">{whyCorrectText}</p>
              </div>

              {whyIncorrectText && (
                <div className="rounded-lg border border-rose-200 bg-rose-50/80 p-3">
                  <p className="text-xs font-semibold text-rose-900 uppercase tracking-wide mb-1">
                    Why your answer was incorrect
                  </p>
                  <p className="text-sm text-rose-950 leading-relaxed">{whyIncorrectText}</p>
                </div>
              )}

              {q.memory_tip && !answered?.isCorrect && (
                <p className="text-xs text-slate-600">
                  <span className="font-semibold text-slate-700">Memory tip: </span>
                  {q.memory_tip}
                </p>
              )}
            </div>
          );
        })}
      </div>

      <div className="flex flex-col sm:flex-row gap-3 justify-end">
        <button
          onClick={onBack}
          className="px-6 py-3 border-2 border-slate-300 text-slate-700 rounded-xl font-semibold hover:bg-slate-50 transition-colors"
        >
          Back to quizzes
        </button>
        <button
          onClick={onRestart}
          className="px-6 py-3 border-2 border-indigo-200 text-indigo-700 rounded-xl font-semibold hover:bg-indigo-50 transition-colors"
        >
          Start a new AI session
        </button>
        <button
          type="button"
          onClick={onGoToLearningPath}
          className="px-6 py-3 bg-indigo-600 text-white rounded-xl font-semibold hover:bg-indigo-700 transition-colors"
        >
          Go to Learning Path
        </button>
      </div>
    </div>
  );
};

export default AIQuiz;
