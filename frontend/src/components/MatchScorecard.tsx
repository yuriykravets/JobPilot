"use client";

import { useState } from "react";
import {
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Cpu,
  BarChart3,
  Layers,
  Briefcase,
  Loader2,
} from "lucide-react";

interface MatchSkillEvidence {
  skill: string;
  evidence: string;
  is_required: boolean;
}

interface MissingSkillGap {
  skill: string;
  severity: string;
  suggestion?: string;
}

interface ExperienceAnalysis {
  candidate_years: number;
  required_years: number;
  meets_requirement: boolean;
  delta_years: number;
}

interface JobMatchScorecardData {
  overall_score: number;
  deterministic_score: number;
  semantic_score: number;
  llm_reasoning_score: number;
  weights: {
    deterministic: number;
    semantic: number;
    llm_reasoning: number;
  };
  matching_skills: MatchSkillEvidence[];
  missing_skills: MissingSkillGap[];
  experience_analysis: ExperienceAnalysis;
  recommendations: string;
  llm_provider?: string;
}

interface JobMatchResponse {
  id?: string;
  cv_profile_id: string;
  job_id: string;
  job_title?: string;
  company_name?: string;
  location?: string;
  region?: string;
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string;
  scorecard: JobMatchScorecardData;
}

export function MatchScorecard() {
  const [candidateEmail, setCandidateEmail] = useState("candidate@example.com");
  const provider = "gemini";
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<JobMatchResponse | null>(null);

  // Demo fallback state if backend database is offline or not yet seeded
  const runDemoMatch = () => {
    setLoading(true);
    setError(null);
    setTimeout(() => {
      setMatchResult({
        cv_profile_id: "demo-cv-id",
        job_id: "demo-job-id",
        job_title: "Senior Android & Cloud Architect",
        company_name: "Grammarly / Global Tech",
        location: "Kyiv, Ukraine (Hybrid)",
        region: "UA",
        salary_min: 5500,
        salary_max: 7500,
        salary_currency: "USD",
        scorecard: {
          overall_score: 88.5,
          deterministic_score: 91.2,
          semantic_score: 89.0,
          llm_reasoning_score: 85.0,
          weights: {
            deterministic: 0.35,
            semantic: 0.35,
            llm_reasoning: 0.30,
          },
          matching_skills: [
            {
              skill: "Kotlin",
              evidence: "5 years building high-throughput Android and KMP services",
              is_required: true,
            },
            {
              skill: "Jetpack Compose",
              evidence: "Architected modern design system UI in production apps",
              is_required: true,
            },
            {
              skill: "Coroutines",
              evidence: "Extensive reactive async concurrency optimization",
              is_required: true,
            },
            {
              skill: "PostgreSQL & pgvector",
              evidence: "Built hybrid vector similarity pipelines with HNSW indexing",
              is_required: false,
            },
          ],
          missing_skills: [
            {
              skill: "Terraform",
              severity: "preferred",
              suggestion: "Bonus Infrastructure as Code requirement. Highlight any Docker or CI/CD experience.",
            },
          ],
          experience_analysis: {
            candidate_years: 5.0,
            required_years: 4.0,
            meets_requirement: true,
            delta_years: 1.0,
          },
          recommendations:
            "Your Kotlin, Compose, and concurrency background strongly aligns with this position. For the technical interview, prepare concrete STAR examples highlighting how you manage memory and battery performance on mobile devices.",
          llm_provider: "gemini",
        },
      });
      setLoading(false);
    }, 600);
  };

  const handleFetchCandidateMatches = async () => {
    setLoading(true);
    setError(null);
    try {
      // 1. First get user's profile
      const profRes = await fetch(`http://localhost:8000/api/v1/cv/profile?email=${encodeURIComponent(candidateEmail)}`);
      if (!profRes.ok) {
        throw new Error("Could not find CV profile for this email. Please upload a CV first or click 'Run Interactive Simulation'.");
      }
      const profData = await profRes.json();

      // 2. Fetch ranked jobs
      const matchRes = await fetch(
        `http://localhost:8000/api/v1/matching/candidate/${profData.id}/jobs?limit=5&provider=${provider}`
      );
      if (!matchRes.ok) {
        throw new Error("Failed to calculate ranked matches.");
      }
      const matchData = await matchRes.json();
      if (matchData.matches && matchData.matches.length > 0) {
        setMatchResult(matchData.matches[0]);
      } else {
        setError("No active jobs found in catalog to match against. Please seed jobs first.");
      }
    } catch (err: unknown) {
      console.warn("Using demo simulation mode:", err);
      // If backend DB is not running, provide informative error with option to simulate
      setError(err instanceof Error ? err.message : "Backend unavailable");
    } finally {
      setLoading(false);
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return "var(--primary)";
    if (score >= 65) return "var(--warning)";
    return "var(--danger)";
  };

  const getScoreBadge = (score: number) => {
    if (score >= 85) return { label: "Exceptional Match", bg: "var(--primary-light)", text: "var(--primary)" };
    if (score >= 70) return { label: "Strong Candidate", bg: "var(--surface-muted)", text: "var(--foreground)" };
    if (score >= 50) return { label: "Partial Fit", bg: "var(--accent-light)", text: "var(--accent)" };
    return { label: "High Skill Gap", bg: "#FEE2E2", text: "#991B1B" };
  };

  const badge = matchResult ? getScoreBadge(matchResult.scorecard.overall_score) : null;

  return (
    <section className="space-y-6">
      {/* Header & Controls */}
      <div
        className="rounded-xl border p-6 shadow-xs space-y-5"
        style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
      >
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center"
              style={{ backgroundColor: "var(--accent-light)", color: "var(--accent)" }}
            >
              <BarChart3 className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
                3-Tier Hybrid Match Scoring
              </h2>
              <p className="text-xs" style={{ color: "var(--foreground-muted)" }}>
                Deterministic Hard Filters (35%) + Vector Cosine Semantic (35%) + LLM Reasoning Judge (30%)
              </p>
            </div>
          </div>

          {/* Provider Badge: Google Gemini */}
          <div className="flex items-center gap-2 bg-stone-100 px-3 py-1.5 rounded-lg border border-stone-200">
            <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
            <span className="text-xs font-medium text-emerald-800">LLM Judge: Google Gemini</span>
          </div>
        </div>

        {/* Input Bar */}
        <div className="flex flex-col sm:flex-row items-center gap-3 pt-2">
          <div className="relative flex-1 w-full">
            <input
              type="email"
              value={candidateEmail}
              onChange={(e) => setCandidateEmail(e.target.value)}
              placeholder="Candidate email address..."
              className="w-full text-sm rounded-lg border px-3.5 py-2.5 focus:outline-hidden transition-colors"
              style={{
                backgroundColor: "var(--surface)",
                borderColor: "var(--border)",
                color: "var(--foreground)",
              }}
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <button
              onClick={handleFetchCandidateMatches}
              disabled={loading}
              className="flex-1 sm:flex-initial flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-white shadow-xs transition-opacity hover:opacity-95 disabled:opacity-50"
              style={{ backgroundColor: "var(--primary)" }}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <BarChart3 className="w-4 h-4" />}
              <span>Score Matches</span>
            </button>

            <button
              onClick={runDemoMatch}
              className="flex-1 sm:flex-initial flex items-center justify-center gap-1.5 px-3.5 py-2.5 rounded-lg text-xs font-medium border hover:bg-stone-50 transition-colors"
              style={{ borderColor: "var(--border)", color: "var(--foreground-muted)" }}
              title="Test the 3-tier scoring UI without requiring a running database"
            >
              <Sparkles className="w-3.5 h-3.5 text-amber-600" />
              <span>Run Simulation</span>
            </button>
          </div>
        </div>

        {/* Error Notice */}
        {error && (
          <div className="p-3.5 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 shrink-0 text-amber-600" />
              <span>{error}</span>
            </div>
            <button
              onClick={runDemoMatch}
              className="font-semibold underline ml-3 shrink-0 hover:text-amber-950"
            >
              Run Interactive Demo
            </button>
          </div>
        )}
      </div>

      {/* Scorecard Results Display */}
      {matchResult && (
        <div className="space-y-6">
          {/* Top Level Summary Card */}
          <div
            className="rounded-xl border p-6 shadow-xs space-y-6"
            style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
          >
            {/* Header with Title and Overall Score */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 pb-6 border-b border-stone-200">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider" style={{ backgroundColor: badge?.bg, color: badge?.text }}>
                    {badge?.label}
                  </span>
                  <span className="text-xs text-stone-500">•</span>
                  <span className="text-xs font-medium text-stone-600">{matchResult.region} Region</span>
                </div>
                <h3 className="text-2xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
                  {matchResult.job_title}
                </h3>
                <p className="text-sm" style={{ color: "var(--foreground-muted)" }}>
                  {matchResult.company_name} • {matchResult.location}
                  {matchResult.salary_min && (
                    <span className="ml-2 font-medium text-stone-800">
                      • ${matchResult.salary_min.toLocaleString()} - ${matchResult.salary_max?.toLocaleString()} / mo
                    </span>
                  )}
                </p>
              </div>

              {/* Overall Gauge */}
              <div className="flex items-center gap-4 bg-stone-50 p-4 rounded-xl border border-stone-200 shrink-0">
                <div className="text-center">
                  <div
                    className="text-4xl font-bold tracking-tight font-mono"
                    style={{ color: getScoreColor(matchResult.scorecard.overall_score) }}
                  >
                    {matchResult.scorecard.overall_score.toFixed(1)}%
                  </div>
                  <span className="text-[11px] font-medium uppercase tracking-wider text-stone-500">
                    Overall Match
                  </span>
                </div>
              </div>
            </div>

            {/* 3-Tier Score Breakdown Bars */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-500">
                3-Tier Explainable Engine Breakdown
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Tier 1: Deterministic */}
                <div className="p-4 rounded-lg border bg-stone-50/70 border-stone-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-stone-600 flex items-center gap-1.5">
                      <Cpu className="w-3.5 h-3.5 text-stone-500" />
                      <span>Deterministic (35%)</span>
                    </span>
                    <span className="text-sm font-bold font-mono text-stone-800">
                      {matchResult.scorecard.deterministic_score.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-stone-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-2 rounded-full transition-all duration-500"
                      style={{
                        width: `${matchResult.scorecard.deterministic_score}%`,
                        backgroundColor: "var(--primary)",
                      }}
                    />
                  </div>
                  <p className="text-[11px] text-stone-500">
                    Exact required skills and years of experience check.
                  </p>
                </div>

                {/* Tier 2: Vector Cosine */}
                <div className="p-4 rounded-lg border bg-stone-50/70 border-stone-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-stone-600 flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-stone-500" />
                      <span>Vector Cosine (35%)</span>
                    </span>
                    <span className="text-sm font-bold font-mono text-stone-800">
                      {matchResult.scorecard.semantic_score.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-stone-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-2 rounded-full transition-all duration-500"
                      style={{
                        width: `${matchResult.scorecard.semantic_score}%`,
                        backgroundColor: "#2563EB",
                      }}
                    />
                  </div>
                  <p className="text-[11px] text-stone-500">
                    768-dim pgvector semantic embedding similarity.
                  </p>
                </div>

                {/* Tier 3: LLM Judge */}
                <div className="p-4 rounded-lg border bg-stone-50/70 border-stone-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-stone-600 flex items-center gap-1.5">
                      <Sparkles className="w-3.5 h-3.5 text-stone-500" />
                      <span>LLM Judge (30%)</span>
                    </span>
                    <span className="text-sm font-bold font-mono text-stone-800">
                      {matchResult.scorecard.llm_reasoning_score.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-stone-200 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-2 rounded-full transition-all duration-500"
                      style={{
                        width: `${matchResult.scorecard.llm_reasoning_score}%`,
                        backgroundColor: "var(--accent)",
                      }}
                    />
                  </div>
                  <p className="text-[11px] text-stone-500">
                    Evaluated by {matchResult.scorecard.llm_provider || "Google Gemini"}.
                  </p>
                </div>
              </div>
            </div>

            {/* Experience Threshold Analysis */}
            <div className="p-4 rounded-lg border bg-stone-50/50 border-stone-200 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
              <div className="flex items-center gap-2">
                <Briefcase className="w-4 h-4 text-stone-500" />
                <span className="font-medium text-stone-800">Experience Requirement:</span>
                <span className="text-stone-600">
                  Candidate has {matchResult.scorecard.experience_analysis.candidate_years} yrs (Job requires {matchResult.scorecard.experience_analysis.required_years} yrs)
                </span>
              </div>
              <span
                className={`px-2.5 py-0.5 rounded-full font-semibold ${
                  matchResult.scorecard.experience_analysis.meets_requirement
                    ? "bg-emerald-100 text-emerald-800"
                    : "bg-amber-100 text-amber-800"
                }`}
              >
                {matchResult.scorecard.experience_analysis.meets_requirement
                  ? `✓ Exceeds Requirement (+${matchResult.scorecard.experience_analysis.delta_years} yrs)`
                  : `⚠️ Experience Deficit (${matchResult.scorecard.experience_analysis.delta_years} yrs)`}
              </span>
            </div>

            {/* Skills Comparison: Matching vs Gaps */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5 pt-2">
              {/* Verified Matched Skills */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-emerald-800 flex items-center gap-1.5">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>Verified Candidate Skills ({matchResult.scorecard.matching_skills.length})</span>
                </h4>
                <div className="space-y-2">
                  {matchResult.scorecard.matching_skills.map((skill, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg border border-emerald-100 bg-emerald-50/40 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-emerald-950">{skill.skill}</span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 font-medium">
                          {skill.is_required ? "Must-Have" : "Preferred"}
                        </span>
                      </div>
                      <p className="text-[11px] text-stone-600 italic">
                        &quot;{skill.evidence}&quot;
                      </p>
                    </div>
                  ))}
                  {matchResult.scorecard.matching_skills.length === 0 && (
                    <p className="text-xs text-stone-400 italic">No direct skill matches found.</p>
                  )}
                </div>
              </div>

              {/* Missing Requirements / Skill Gaps */}
              <div className="space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-amber-800 flex items-center gap-1.5">
                  <AlertTriangle className="w-4 h-4 text-amber-600" />
                  <span>Missing Requirements & Gaps ({matchResult.scorecard.missing_skills.length})</span>
                </h4>
                <div className="space-y-2">
                  {matchResult.scorecard.missing_skills.map((gap, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg border border-amber-200 bg-amber-50/40 text-xs space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-amber-950">{gap.skill}</span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                            gap.severity === "required"
                              ? "bg-red-100 text-red-800"
                              : "bg-amber-100 text-amber-800"
                          }`}
                        >
                          {gap.severity === "required" ? "Critical Must-Have" : "Preferred Bonus"}
                        </span>
                      </div>
                      {gap.suggestion && (
                        <p className="text-[11px] text-stone-600">{gap.suggestion}</p>
                      )}
                    </div>
                  ))}
                  {matchResult.scorecard.missing_skills.length === 0 && (
                    <div className="p-4 rounded-lg bg-emerald-50 text-emerald-800 text-xs font-medium">
                      ✓ No missing skills detected! 100% skill coverage for this vacancy.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* AI Career Coach Recommendations */}
            <div className="p-5 rounded-xl border border-stone-200 bg-stone-50 space-y-2">
              <div className="flex items-center gap-2 text-stone-800 font-semibold text-sm">
                <Sparkles className="w-4 h-4 text-amber-600" />
                <span>Executive Recruiter Recommendations & Positioning Strategy</span>
              </div>
              <p className="text-xs text-stone-700 leading-relaxed">
                {matchResult.scorecard.recommendations}
              </p>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
