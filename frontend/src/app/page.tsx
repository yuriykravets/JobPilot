"use client";

import { useEffect, useState } from "react";
import {
  FileText,
  Compass,
  CheckCircle2,
  MessageSquare,
  Activity,
  Layers,
  Database,
  Server,
  Zap,
} from "lucide-react";
import { CvUploader } from "@/components/CvUploader";
import { JobDiscovery } from "@/components/JobDiscovery";
import { MatchScorecard } from "@/components/MatchScorecard";
import { InterviewCoach } from "@/components/InterviewCoach";

interface HealthStatus {
  status: string;
  environment: string;
  services: {
    database: {
      status: string;
      latency_ms?: number;
      pgvector_installed?: boolean;
      pgvector_version?: string;
    };
    redis: {
      status: string;
      latency_ms?: number;
    };
  };
}

export default function Home() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiError, setApiError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setApiError(null);
    try {
      const res = await fetch("http://localhost:8000/health");
      const data = await res.json();
      setHealth(data);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Failed to connect to backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    fetch("http://localhost:8000/health")
      .then((res) => res.json())
      .then((data) => {
        if (isMounted) {
          setHealth(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setApiError(err instanceof Error ? err.message : "Failed to connect to backend");
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <div className="min-h-screen" style={{ backgroundColor: "var(--background)" }}>
      {/* Top Navigation */}
      <header className="border-b" style={{ borderColor: "var(--border)", backgroundColor: "var(--surface)" }}>
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-lg flex items-center justify-center font-bold text-white shadow-sm"
              style={{ backgroundColor: "var(--primary)" }}
            >
              JP
            </div>
            <div>
              <span className="font-semibold text-lg tracking-tight" style={{ color: "var(--foreground)" }}>
                JobPilot
              </span>
              <span className="ml-2 text-xs px-2 py-0.5 rounded-full font-medium" style={{ backgroundColor: "var(--accent-light)", color: "var(--accent)" }}>
                MVP Dev
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-sm">
            <button
              onClick={fetchHealth}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md border transition-colors hover:bg-stone-50"
              style={{ borderColor: "var(--border)", color: "var(--foreground-muted)" }}
            >
              <Activity className="w-4 h-4" />
              <span>Refresh Status</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-6xl mx-auto px-6 py-10 space-y-10">
        {/* Hero Section */}
        <div className="space-y-3">
          <h1 className="text-3xl sm:text-4xl font-serif font-medium tracking-tight" style={{ color: "var(--foreground)" }}>
            Welcome to JobPilot
          </h1>
          <p className="text-base sm:text-lg max-w-2xl" style={{ color: "var(--foreground-muted)" }}>
            A modular AI-powered job search and interview coach platform. Engineered with clean architecture, explainable matching scores, and zero-hallucination verification.
          </p>
        </div>

        {/* System Health / Status Card */}
        <section
          className="rounded-xl border p-6 shadow-xs"
          style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Server className="w-5 h-5" style={{ color: "var(--primary)" }} />
              <h2 className="font-semibold text-base" style={{ color: "var(--foreground)" }}>
                System Architecture Health
              </h2>
            </div>
            {loading ? (
              <span className="text-xs px-2.5 py-1 rounded-full animate-pulse" style={{ backgroundColor: "var(--surface-muted)", color: "var(--foreground-muted)" }}>
                Checking connections...
              </span>
            ) : apiError ? (
              <span className="text-xs px-2.5 py-1 rounded-full font-medium bg-red-100 text-red-800">
                Backend Offline (FastAPI not responding)
              </span>
            ) : (
              <span
                className="text-xs px-2.5 py-1 rounded-full font-medium"
                style={{
                  backgroundColor: health?.status === "healthy" ? "var(--primary-light)" : "var(--accent-light)",
                  color: health?.status === "healthy" ? "var(--primary)" : "var(--accent)",
                }}
              >
                ● {health?.status === "healthy" ? "All Systems Operational" : "Degraded Service"}
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            {/* FastAPI Box */}
            <div className="p-4 rounded-lg border" style={{ backgroundColor: "var(--surface-muted)", borderColor: "var(--border)" }}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--foreground-muted)" }}>
                  Backend API
                </span>
                <Zap className="w-4 h-4" style={{ color: "var(--primary)" }} />
              </div>
              <p className="font-semibold mt-1" style={{ color: "var(--foreground)" }}>FastAPI (AsyncIO)</p>
              <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>
                {apiError ? "Not running on :8000" : "Port 8000 • OpenAPI Docs enabled"}
              </p>
            </div>

            {/* PostgreSQL Box */}
            <div className="p-4 rounded-lg border" style={{ backgroundColor: "var(--surface-muted)", borderColor: "var(--border)" }}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--foreground-muted)" }}>
                  Database & Vectors
                </span>
                <Database className="w-4 h-4" style={{ color: "var(--primary)" }} />
              </div>
              <p className="font-semibold mt-1" style={{ color: "var(--foreground)" }}>PostgreSQL 16 + pgvector</p>
              <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>
                {health?.services?.database?.status === "healthy"
                  ? `Connected • Latency: ${health.services.database.latency_ms}ms • pgvector: ${health.services.database.pgvector_version}`
                  : "Awaiting Docker postgres start"}
              </p>
            </div>

            {/* Redis Box */}
            <div className="p-4 rounded-lg border" style={{ backgroundColor: "var(--surface-muted)", borderColor: "var(--border)" }}>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--foreground-muted)" }}>
                  Cache & Tasks
                </span>
                <Layers className="w-4 h-4" style={{ color: "var(--primary)" }} />
              </div>
              <p className="font-semibold mt-1" style={{ color: "var(--foreground)" }}>Redis 7 + Celery</p>
              <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>
                {health?.services?.redis?.status === "healthy"
                  ? `Connected • Latency: ${health.services.redis.latency_ms}ms`
                  : "Awaiting Docker redis start"}
              </p>
            </div>
          </div>
        </section>

        {/* Feature 1: CV Uploader & Profile Extractor */}
        <CvUploader />

        {/* Feature 2: Multi-Region Job Discovery */}
        <JobDiscovery />

        {/* Feature 3: 3-Tier Hybrid Match Scoring */}
        <MatchScorecard />

        {/* Feature 4: Stateful Multi-Turn AI Interview Coach */}
        <InterviewCoach />

        {/* Roadmap / Features Grid */}
        <section className="space-y-4">
          <h2 className="font-semibold text-lg" style={{ color: "var(--foreground)" }}>
            JobPilot MVP Pipeline
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* Feature 1 */}
            <div className="p-5 rounded-xl border space-y-3" style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: "var(--primary-light)", color: "var(--primary)" }}>
                <FileText className="w-5 h-5" />
              </div>
              <h3 className="font-medium text-base" style={{ color: "var(--foreground)" }}>1. Structured CV Parsing</h3>
              <p className="text-xs leading-relaxed" style={{ color: "var(--foreground-muted)" }}>
                Layout-aware PDF parsing with strict Pydantic schema validation and verbatim source verification to avoid hallucinated skills.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="p-5 rounded-xl border space-y-3" style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: "var(--surface-muted)", color: "var(--foreground)" }}>
                <Compass className="w-5 h-5" />
              </div>
              <h3 className="font-medium text-base" style={{ color: "var(--foreground)" }}>2. Multi-Region Jobs</h3>
              <p className="text-xs leading-relaxed" style={{ color: "var(--foreground-muted)" }}>
                Targeted job discovery for Ukraine, Europe, and the USA with normalized skills and compensation ranges.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="p-5 rounded-xl border space-y-3" style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: "var(--accent-light)", color: "var(--accent)" }}>
                <CheckCircle2 className="w-5 h-5" />
              </div>
              <h3 className="font-medium text-base" style={{ color: "var(--foreground)" }}>3. Hybrid Match Scoring</h3>
              <p className="text-xs leading-relaxed" style={{ color: "var(--foreground-muted)" }}>
                Three-tier explainable match engine: Deterministic hard filters + Cosine vector similarity + LLM reasoning judge.
              </p>
            </div>

            {/* Feature 4 */}
            <div className="p-5 rounded-xl border space-y-3" style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}>
              <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: "var(--primary-light)", color: "var(--primary)" }}>
                <MessageSquare className="w-5 h-5" />
              </div>
              <h3 className="font-medium text-base" style={{ color: "var(--foreground)" }}>4. LangGraph Interview Coach</h3>
              <p className="text-xs leading-relaxed" style={{ color: "var(--foreground-muted)" }}>
                Stateful multi-turn mock interview with STAR criteria evaluation, real-time SSE streaming, and actionable feedback.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
