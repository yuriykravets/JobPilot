"use client";

import { useState } from "react";
import {
  MessageSquare,
  Send,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Award,
  Lightbulb,
  Loader2,
  Play,
  RotateCcw,
  GitBranch,
} from "lucide-react";

interface TurnRubricEvaluation {
  score: number;
  technical_accuracy: number;
  communication_clarity: number;
  stage: string;
  strengths: string[];
  improvements: string[];
  ideal_answer_hint: string;
}

interface InterviewMessage {
  id: string;
  role: "interviewer" | "candidate";
  content: string;
  step_number: number;
  feedback?: TurnRubricEvaluation | Record<string, unknown> | null;
}

interface InterviewSessionState {
  session_id: string;
  job_title: string;
  company_name: string;
  status: "IN_PROGRESS" | "COMPLETED";
  current_question_index: number;
  max_questions: number;
  current_stage: string;
  average_score: number | null;
  overall_feedback: string | null;
  messages: InterviewMessage[];
  latest_evaluation: TurnRubricEvaluation | null;
  llm_provider: string;
}

const STAGES = [
  { id: "WARMUP_EXPERIENCE", label: "1. CV Warmup" },
  { id: "CORE_TECHNICAL", label: "2. Core Technical" },
  { id: "SKILL_GAP_PROBE", label: "3. Gap Probe" },
  { id: "BEHAVIORAL_STAR", label: "4. Behavioral STAR" },
];

export function InterviewCoach() {
  const [candidateEmail, setCandidateEmail] = useState("candidate@example.com");
  const provider = "gemini";
  const [session, setSession] = useState<InterviewSessionState | null>(null);
  const [answerInput, setAnswerInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDemoMode, setIsDemoMode] = useState(false);

  const startLiveInterview = async () => {
    setLoading(true);
    setError(null);
    setIsDemoMode(false);
    try {
      const cvRes = await fetch(
        `http://localhost:8000/api/v1/cv/profile?email=${encodeURIComponent(candidateEmail)}`
      );
      if (!cvRes.ok) {
        throw new Error(
          "No CV Profile found for this email. Upload a CV above first, or click 'Interactive Demo Session'."
        );
      }
      const cvData = await cvRes.json();

      const jobsRes = await fetch("http://localhost:8000/api/v1/jobs?limit=5");
      if (!jobsRes.ok) {
        throw new Error("Could not fetch jobs from backend.");
      }
      const jobsData = await jobsRes.json();
      const jobsList = jobsData.items || jobsData || [];
      if (!jobsList.length) {
        throw new Error("No jobs seeded in database yet. Seed jobs above or use Demo Mode.");
      }

      const startRes = await fetch("http://localhost:8000/api/v1/interviews/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cv_profile_id: cvData.id,
          job_id: jobsList[0].id,
          max_questions: 4,
          provider,
        }),
      });

      if (!startRes.ok) {
        const errBody = await startRes.json().catch(() => ({}));
        throw new Error(errBody.detail || "Failed to start interview session.");
      }

      const sessionData: InterviewSessionState = await startRes.json();
      setSession(sessionData);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Could not start live interview.");
    } finally {
      setLoading(false);
    }
  };

  const startDemoInterview = () => {
    setError(null);
    setIsDemoMode(true);
    setSession({
      session_id: "demo-session-1",
      job_title: "Senior AI & Backend Engineer",
      company_name: "Grammarly / Enterprise AI",
      status: "IN_PROGRESS",
      current_question_index: 1,
      max_questions: 4,
      current_stage: "WARMUP_EXPERIENCE",
      average_score: null,
      overall_feedback: null,
      llm_provider: provider,
      latest_evaluation: null,
      messages: [
        {
          id: "m-1",
          role: "interviewer",
          step_number: 1,
          content:
            "Welcome! I've reviewed your CV profile and matched it against our Senior AI & Backend Engineer role.\n\n**Question 1 (WARMUP_EXPERIENCE):** You listed experience building FastAPI services and vector search with PostgreSQL/pgvector. Walk me through a production bottleneck you encountered in your retrieval or matching pipeline and how you resolved it.",
        },
      ],
    });
  };

  const submitAnswer = async () => {
    if (!session || !answerInput.trim() || loading) return;
    const trimmed = answerInput.trim();
    setLoading(true);
    setError(null);

    if (isDemoMode) {
      setTimeout(() => {
        const qIdx = session.current_question_index;
        const nextQIdx = qIdx + 1;
        const isDone = qIdx >= session.max_questions;
        const stageMap: Record<number, string> = {
          1: "WARMUP_EXPERIENCE",
          2: "CORE_TECHNICAL",
          3: "SKILL_GAP_PROBE",
          4: "BEHAVIORAL_STAR",
        };
        const nextStage = isDone ? "COMPLETED" : stageMap[nextQIdx] || "BEHAVIORAL_STAR";

        const demoEval: TurnRubricEvaluation = {
          score: 8.8,
          technical_accuracy: 9.0,
          communication_clarity: 8.5,
          stage: stageMap[qIdx] || "CORE_TECHNICAL",
          strengths: [
            "Clear explanation of architectural trade-offs and system mechanics",
            "Good grounding in production constraints and observability",
          ],
          improvements: [
            "Quantify p95/p99 latency improvements and throughput (RPS) explicitly",
            "Briefly contrast your chosen approach with at least one rejected alternative",
          ],
          ideal_answer_hint:
            "Anchor with STAR: state baseline latency/cost, explain HNSW index tuning (m=16, ef_construction=64) or async connection pooling, and state the final measurable delta.",
        };

        const demoQuestions: Record<number, string> = {
          2: "**Question 2 (CORE_TECHNICAL):** How do you design an LLM integration layer with Google Gemini that guarantees strict JSON schema compliance and handles transient rate limits gracefully?",
          3: "**Question 3 (SKILL_GAP_PROBE):** Suppose we need to optimize vector embeddings in PostgreSQL pgvector for high-recall semantic search. How would you leverage 768-dimensional Matryoshka embeddings and HNSW indexing here?",
          4: "**Question 4 (BEHAVIORAL_STAR):** Tell me about a time when an AI feature you built produced unexpected hallucinations or degraded accuracy in production. How did you detect it, add guardrails, and communicate with stakeholders?",
        };

        const newMessages: InterviewMessage[] = [
          ...session.messages,
          {
            id: `cand-${qIdx}`,
            role: "candidate",
            content: trimmed,
            step_number: session.messages.length + 1,
            feedback: demoEval,
          },
          {
            id: `int-${nextQIdx}`,
            role: "interviewer",
            content: isDone
              ? "Thank you for completing all 4 stages of the technical & behavioral mock interview! Review your executive hiring scorecard below."
              : demoQuestions[nextQIdx],
            step_number: session.messages.length + 2,
          },
        ];

        setSession({
          ...session,
          status: isDone ? "COMPLETED" : "IN_PROGRESS",
          current_question_index: isDone ? session.max_questions : nextQIdx,
          current_stage: nextStage,
          average_score: 8.8,
          latest_evaluation: demoEval,
          messages: newMessages,
          overall_feedback: isDone
            ? "### Hiring Signal: STRONG_HIRE (Average Score: 8.8/10)\n\nCandidate demonstrated strong end-to-end ownership across FastAPI async architecture, pgvector HNSW indexing, Gemini structured output validation, and deterministic anti-hallucination guardrails.\n\n**Key Strengths Demonstrated:**\n- Deep understanding of hybrid deterministic + semantic + LLM-as-a-Judge pipelines\n- Production awareness of rate-limiting and strict Pydantic schema validation\n\n**Action Plan for Your Real Interview:**\n- Prepare 2 concrete latency/cost numbers from your JobPilot benchmarks\n- Practice walking through your anti-hallucination verbatim quote verifier step by step"
            : null,
        });
        setAnswerInput("");
        setLoading(false);
      }, 600);
      return;
    }

    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/interviews/${session.session_id}/answer`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            answer: trimmed,
            provider,
          }),
        }
      );

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.detail || "Failed to evaluate answer.");
      }

      const updated: InterviewSessionState = await res.json();
      setSession(updated);
      setAnswerInput("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit answer.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section
      className="rounded-xl border p-6 space-y-6 shadow-xs"
      style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b pb-5" style={{ borderColor: "var(--border)" }}>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5" style={{ color: "var(--primary)" }} />
            <h2 className="font-semibold text-lg" style={{ color: "var(--foreground)" }}>
              4. Stateful AI Mock Interview Coach (StateGraph Engine)
            </h2>
          </div>
          <p className="text-sm" style={{ color: "var(--foreground-muted)" }}>
            Multi-turn technical & STAR behavioral interview tailored to your CV and target job gaps, with real-time rubric scoring.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div
            className="text-xs px-3 py-2 rounded-lg border font-medium flex items-center gap-1.5"
            style={{ backgroundColor: "var(--surface-muted)", borderColor: "var(--border)", color: "var(--foreground)" }}
          >
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            <span>Engine: Google Gemini</span>
          </div>

          <button
            onClick={startDemoInterview}
            className="flex items-center gap-1.5 text-xs px-3 py-2 rounded-lg border font-medium transition-colors hover:opacity-90"
            style={{ backgroundColor: "var(--accent-light)", borderColor: "var(--border)", color: "var(--accent)" }}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Interactive Demo Session</span>
          </button>
        </div>
      </div>

      {/* Stage Progression Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {STAGES.map((st, idx) => {
          const isCurrent = session?.current_stage === st.id && session?.status !== "COMPLETED";
          const isPassed =
            session?.status === "COMPLETED" ||
            (session && session.current_question_index > idx + 1);
          return (
            <div
              key={st.id}
              className="p-3 rounded-lg border flex items-center justify-between text-xs font-medium transition-all"
              style={{
                backgroundColor: isCurrent
                  ? "var(--primary-light)"
                  : isPassed
                  ? "var(--surface-muted)"
                  : "var(--background)",
                borderColor: isCurrent ? "var(--primary)" : "var(--border)",
                color: isCurrent ? "var(--primary)" : "var(--foreground)",
              }}
            >
              <span className=" flex items-center gap-1.5">
                <GitBranch className="w-3.5 h-3.5" />
                {st.label}
              </span>
              {isPassed && <CheckCircle2 className="w-4 h-4" style={{ color: "var(--primary)" }} />}
            </div>
          );
        })}
      </div>

      {/* Controls to Start Session if not active */}
      {!session && (
        <div
          className="p-5 rounded-xl border flex flex-col sm:flex-row items-center justify-between gap-4"
          style={{ backgroundColor: "var(--surface-muted)", borderColor: "var(--border)" }}
        >
          <div className="flex-1 w-full sm:w-auto space-y-1">
            <label className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--foreground-muted)" }}>
              Candidate CV Email
            </label>
            <input
              type="email"
              value={candidateEmail}
              onChange={(e) => setCandidateEmail(e.target.value)}
              placeholder="candidate@example.com"
              className="w-full px-3 py-2 rounded-lg border text-sm"
              style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)", color: "var(--foreground)" }}
            />
          </div>

          <div className="flex items-center gap-3 w-full sm:w-auto pt-2 sm:pt-5">
            <button
              onClick={startLiveInterview}
              disabled={loading}
              className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-white shadow-xs transition-opacity hover:opacity-95 disabled:opacity-50"
              style={{ backgroundColor: "var(--primary)" }}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              <span>Start Live Interview</span>
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg border bg-red-50 border-red-200 text-red-800 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Active Session Workspace */}
      {session && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2 Columns: Conversation Transcript & Answer Input */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center justify-between text-xs px-1" style={{ color: "var(--foreground-muted)" }}>
              <span>
                Target Role: <strong style={{ color: "var(--foreground)" }}>{session.job_title}</strong> at{" "}
                <strong style={{ color: "var(--foreground)" }}>{session.company_name}</strong>
              </span>
              <button
                onClick={() => setSession(null)}
                className="flex items-center gap-1 underline hover:opacity-80"
              >
                <RotateCcw className="w-3 h-3" /> Reset Session
              </button>
            </div>

            {/* Messages Box */}
            <div
              className="rounded-xl border p-4 space-y-4 max-h-96 overflow-y-auto"
              style={{ backgroundColor: "var(--background)", borderColor: "var(--border)" }}
            >
              {session.messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`p-4 rounded-xl border text-sm leading-relaxed whitespace-pre-line ${
                    msg.role === "interviewer" ? "mr-6" : "ml-6"
                  }`}
                  style={{
                    backgroundColor: msg.role === "interviewer" ? "var(--surface)" : "var(--primary-light)",
                    borderColor: msg.role === "interviewer" ? "var(--border)" : "var(--primary)",
                    color: "var(--foreground)",
                  }}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--primary)" }}>
                      {msg.role === "interviewer" ? "AI Staff Interviewer" : "Your Answer"}
                    </span>
                    {msg.role === "candidate" &&
                      msg.feedback &&
                      typeof (msg.feedback as TurnRubricEvaluation).score === "number" && (
                        <span
                          className="text-xs px-2 py-0.5 rounded-full font-semibold"
                          style={{ backgroundColor: "var(--surface)", color: "var(--primary)" }}
                        >
                          Score: {(msg.feedback as TurnRubricEvaluation).score}/10
                        </span>
                      )}
                  </div>
                  {msg.content}
                </div>
              ))}
            </div>

            {/* Answer Input Box */}
            {session.status !== "COMPLETED" ? (
              <div className="space-y-2">
                <textarea
                  rows={4}
                  value={answerInput}
                  onChange={(e) => setAnswerInput(e.target.value)}
                  placeholder="Structure your answer using STAR (Situation, Task, Action, Result) and include concrete technical trade-offs or metrics..."
                  className="w-full p-3.5 rounded-xl border text-sm focus:outline-none"
                  style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)", color: "var(--foreground)" }}
                />
                <div className="flex items-center justify-between">
                  <span className="text-xs" style={{ color: "var(--foreground-muted)" }}>
                    Question {session.current_question_index} of {session.max_questions} • Stage:{" "}
                    <strong>{session.current_stage}</strong>
                  </span>
                  <button
                    onClick={submitAnswer}
                    disabled={loading || !answerInput.trim()}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white transition-opacity hover:opacity-95 disabled:opacity-50"
                    style={{ backgroundColor: "var(--primary)" }}
                  >
                    {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    <span>Submit Answer & Evaluate</span>
                  </button>
                </div>
              </div>
            ) : (
              /* Executive Final Report */
              <div
                className="p-5 rounded-xl border space-y-3"
                style={{ backgroundColor: "var(--primary-light)", borderColor: "var(--primary)" }}
              >
                <div className="flex items-center gap-2">
                  <Award className="w-5 h-5" style={{ color: "var(--primary)" }} />
                  <h3 className="font-semibold text-base" style={{ color: "var(--foreground)" }}>
                    Executive Hiring Committee Report
                  </h3>
                </div>
                <div className="text-sm whitespace-pre-line leading-relaxed" style={{ color: "var(--foreground)" }}>
                  {session.overall_feedback}
                </div>
              </div>
            )}
          </div>

          {/* Right Column: Live Turn Rubric Evaluation */}
          <div
            className="rounded-xl border p-5 space-y-4 h-fit"
            style={{ backgroundColor: "var(--surface-muted)", borderColor: "var(--border)" }}
          >
            <div className="flex items-center justify-between border-b pb-3" style={{ borderColor: "var(--border)" }}>
              <span className="font-semibold text-sm" style={{ color: "var(--foreground)" }}>
                Real-Time Turn Rubric
              </span>
              {session.average_score !== null && (
                <span
                  className="text-xs px-2.5 py-1 rounded-full font-bold"
                  style={{ backgroundColor: "var(--primary-light)", color: "var(--primary)" }}
                >
                  Avg: {session.average_score}/10
                </span>
              )}
            </div>

            {session.latest_evaluation ? (
              <div className="space-y-4 text-xs">
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 rounded-lg border" style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}>
                    <span className="block text-[11px]" style={{ color: "var(--foreground-muted)" }}>
                      Technical Depth
                    </span>
                    <span className="text-base font-bold" style={{ color: "var(--primary)" }}>
                      {session.latest_evaluation.technical_accuracy}/10
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg border" style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}>
                    <span className="block text-[11px]" style={{ color: "var(--foreground-muted)" }}>
                      STAR & Clarity
                    </span>
                    <span className="text-base font-bold" style={{ color: "var(--primary)" }}>
                      {session.latest_evaluation.communication_clarity}/10
                    </span>
                  </div>
                </div>

                {session.latest_evaluation.strengths.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-semibold block" style={{ color: "var(--foreground)" }}>
                      ✓ Demonstrated Strengths
                    </span>
                    <ul className="space-y-1 pl-4 list-disc" style={{ color: "var(--foreground-muted)" }}>
                      {session.latest_evaluation.strengths.map((s, i) => (
                        <li key={i}>{s}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {session.latest_evaluation.improvements.length > 0 && (
                  <div className="space-y-1.5">
                    <span className="font-semibold block" style={{ color: "var(--accent)" }}>
                      ↑ How to Level Up
                    </span>
                    <ul className="space-y-1 pl-4 list-disc" style={{ color: "var(--foreground-muted)" }}>
                      {session.latest_evaluation.improvements.map((imp, i) => (
                        <li key={i}>{imp}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {session.latest_evaluation.ideal_answer_hint && (
                  <div
                    className="p-3 rounded-lg border space-y-1"
                    style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
                  >
                    <div className="flex items-center gap-1.5 font-semibold" style={{ color: "var(--primary)" }}>
                      <Lightbulb className="w-3.5 h-3.5" />
                      <span>10/10 Senior Answer Blueprint</span>
                    </div>
                    <p className="leading-relaxed" style={{ color: "var(--foreground-muted)" }}>
                      {session.latest_evaluation.ideal_answer_hint}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs leading-relaxed" style={{ color: "var(--foreground-muted)" }}>
                Submit your response to Question #1 to receive an instant breakdown of your technical depth, STAR communication clarity, and senior-level answer hints.
              </p>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
