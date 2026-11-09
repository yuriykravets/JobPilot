"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Search,
  MapPin,
  Building2,
  DollarSign,
  Compass,
  ArrowRight,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

interface Job {
  id: string;
  title: string;
  company_name: string;
  location: string;
  region: "UA" | "EU" | "US" | "REMOTE";
  raw_description: string;
  required_skills: string[];
  preferred_skills: string[];
  min_experience_years: number;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  source_url: string | null;
  external_id: string | null;
  created_at: string;
}

export function JobDiscovery() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [region, setRegion] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [activeSkill, setActiveSkill] = useState<string | null>(null);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [seeding, setSeeding] = useState(false);
  const [syncingLive, setSyncingLive] = useState(false);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (region) params.append("region", region);
      if (search.trim()) params.append("search", search.trim());
      if (activeSkill) params.append("skill", activeSkill);
      params.append("limit", "20");

      const res = await fetch(`http://localhost:8000/api/v1/jobs?${params.toString()}`);
      if (!res.ok) throw new Error("Failed to fetch jobs");
      const data = await res.json();
      setJobs(data.items);
      setTotal(data.total);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [region, search, activeSkill]);

  useEffect(() => {
    let isCurrent = true;
    const params = new URLSearchParams();
    if (region) params.append("region", region);
    if (search.trim()) params.append("search", search.trim());
    if (activeSkill) params.append("skill", activeSkill);
    params.append("limit", "20");

    fetch(`http://localhost:8000/api/v1/jobs?${params.toString()}`)
      .then((res) => {
        if (!res.ok) throw new Error("Failed to fetch jobs");
        return res.json();
      })
      .then((data) => {
        if (isCurrent) {
          setJobs(data.items);
          setTotal(data.total);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isCurrent) {
          console.error(err);
          setLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [region, search, activeSkill]);

  const handleSeedJobs = async () => {
    setSeeding(true);
    try {
      await fetch("http://localhost:8000/api/v1/jobs/seed", { method: "POST" });
      await fetchJobs();
    } catch (err) {
      console.error("Seed error:", err);
    } finally {
      setSeeding(false);
    }
  };

  const handleSyncLiveFeeds = async () => {
    setSyncingLive(true);
    try {
      await fetch("http://localhost:8000/api/v1/jobs/sync-live-feeds", { method: "POST" });
      await fetchJobs();
    } catch (err) {
      console.error("Live sync error:", err);
    } finally {
      setSyncingLive(false);
    }
  };

  const getSourceBadge = (url: string | null) => {
    if (!url) return null;
    if (url.includes("dou.ua")) return { label: "🇺🇦 DOU.ua Live", isLive: true };
    if (url.includes("remotive.com")) return { label: "🌍 Remotive Live", isLive: true };
    return { label: "Direct Source", isLive: false };
  };

  const formatSalary = (min: number | null, max: number | null, currency: string) => {
    if (!min && !max) return "Competitive";
    const currSymbol = currency === "USD" ? "$" : currency === "EUR" ? "€" : "₴";
    const isYearly = (max || min || 0) > 30000;
    const period = isYearly ? "/yr" : "/mo";

    if (min && max) {
      return `${currSymbol}${min.toLocaleString()} – ${currSymbol}${max.toLocaleString()} ${period}`;
    }
    return `${currSymbol}${(min || max)?.toLocaleString()} ${period}`;
  };

  const popularSkills = ["Kotlin", "Jetpack Compose", "FastAPI", "Python", "pgvector", "LangChain"];

  return (
    <section className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
            2. Multi-Region Job Discovery
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--foreground-muted)" }}>
            Curated engineering vacancies across Ukraine 🇺🇦, Europe 🇪🇺, and the USA 🇺🇸.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleSyncLiveFeeds}
            disabled={syncingLive}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-medium text-white transition-all shadow-xs disabled:opacity-50 cursor-pointer"
            style={{ backgroundColor: "var(--primary)" }}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${syncingLive ? "animate-spin" : ""}`} />
            <span>{syncingLive ? "Syncing..." : "Sync Live Feeds (DOU & Global)"}</span>
          </button>

          <button
            onClick={handleSeedJobs}
            disabled={seeding}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg border font-medium transition-colors hover:bg-stone-50 cursor-pointer"
            style={{ borderColor: "var(--border)", color: "var(--foreground)" }}
          >
            <span>Reset Demo Seed</span>
          </button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        className="p-4 rounded-xl border space-y-3"
        style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
      >
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 absolute left-3 top-3" style={{ color: "var(--foreground-muted)" }} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by role, company, or tech stack..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border focus:outline-none focus:ring-1"
              style={{
                borderColor: "var(--border)",
                backgroundColor: "var(--background)",
                color: "var(--foreground)",
              }}
            />
          </div>

          {/* Region Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            {[
              { label: "All Regions", value: null },
              { label: "🇺🇦 Ukraine", value: "UA" },
              { label: "🇪🇺 Europe", value: "EU" },
              { label: "🇺🇸 USA", value: "US" },
              { label: "🌍 Remote", value: "REMOTE" },
            ].map((tab) => (
              <button
                key={tab.label}
                onClick={() => setRegion(tab.value)}
                className="text-xs px-3 py-2 rounded-lg font-medium transition-all shrink-0 cursor-pointer"
                style={{
                  backgroundColor: region === tab.value ? "var(--primary)" : "var(--surface-muted)",
                  color: region === tab.value ? "#FFFFFF" : "var(--foreground-muted)",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Quick Skill Filters */}
        <div className="flex items-center gap-2 flex-wrap pt-1 text-xs">
          <span style={{ color: "var(--foreground-muted)" }}>Quick Stack:</span>
          {popularSkills.map((sk) => (
            <button
              key={sk}
              onClick={() => setActiveSkill(activeSkill === sk ? null : sk)}
              className="px-2.5 py-1 rounded-md border text-[11px] font-medium transition-all cursor-pointer"
              style={{
                backgroundColor: activeSkill === sk ? "var(--accent-light)" : "var(--background)",
                borderColor: activeSkill === sk ? "var(--accent)" : "var(--border)",
                color: activeSkill === sk ? "var(--accent)" : "var(--foreground)",
              }}
            >
              {sk}
            </button>
          ))}
          {activeSkill && (
            <button
              onClick={() => setActiveSkill(null)}
              className="text-[11px] underline ml-1"
              style={{ color: "var(--foreground-muted)" }}
            >
              Clear skill
            </button>
          )}
        </div>
      </div>

      {/* Results Header */}
      <div className="flex items-center justify-between text-xs" style={{ color: "var(--foreground-muted)" }}>
        <span>Showing {jobs.length} of {total} vacancies</span>
        {region && <span>Filtered by: {region}</span>}
      </div>

      {/* Jobs Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              className="rounded-xl border p-5 space-y-3 animate-pulse"
              style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
            >
              <div className="h-5 bg-stone-200 rounded w-3/4"></div>
              <div className="h-4 bg-stone-100 rounded w-1/2"></div>
              <div className="h-16 bg-stone-50 rounded"></div>
            </div>
          ))}
        </div>
      ) : jobs.length === 0 ? (
        <div
          className="rounded-xl border border-dashed p-12 text-center flex flex-col items-center justify-center space-y-3"
          style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
        >
          <Compass className="w-8 h-8" style={{ color: "var(--foreground-muted)" }} />
          <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
            No vacancies match your criteria
          </p>
          <p className="text-xs max-w-sm" style={{ color: "var(--foreground-muted)" }}>
            Try adjusting your search query, selecting &quot;All Regions&quot;, or reload the seed catalog.
          </p>
          <button
            onClick={handleSeedJobs}
            className="text-xs px-3 py-2 rounded-lg text-white font-medium cursor-pointer"
            style={{ backgroundColor: "var(--primary)" }}
          >
            Load Seed Vacancies
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <div
              key={job.id}
              onClick={() => setSelectedJob(job)}
              className="rounded-xl border p-5 flex flex-col justify-between space-y-4 transition-all hover:shadow-xs hover:border-stone-400 cursor-pointer"
              style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
            >
              <div className="space-y-2">
                {/* Header: Company & Region */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-medium" style={{ color: "var(--foreground-muted)" }}>
                    <Building2 className="w-3.5 h-3.5" />
                    <span>{job.company_name}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    {getSourceBadge(job.source_url)?.isLive && (
                      <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-md bg-emerald-50 text-emerald-800 border border-emerald-200">
                        {getSourceBadge(job.source_url)?.label}
                      </span>
                    )}
                    <span
                      className="text-[10px] font-semibold px-2 py-0.5 rounded-full"
                      style={{
                        backgroundColor: job.region === "UA" ? "var(--primary-light)" : "var(--surface-muted)",
                        color: job.region === "UA" ? "var(--primary)" : "var(--foreground)",
                      }}
                    >
                      {job.region === "UA" ? "🇺🇦 UA" : job.region === "EU" ? "🇪🇺 EU" : job.region === "US" ? "🇺🇸 US" : "🌍 Remote"}
                    </span>
                  </div>
                </div>

                {/* Job Title */}
                <h3 className="font-semibold text-base leading-snug line-clamp-2" style={{ color: "var(--foreground)" }}>
                  {job.title}
                </h3>

                {/* Location & Compensation */}
                <div className="space-y-1 pt-1 text-xs" style={{ color: "var(--foreground-muted)" }}>
                  <div className="flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{job.location}</span>
                  </div>
                  <div className="flex items-center gap-1.5 font-medium" style={{ color: "var(--primary)" }}>
                    <DollarSign className="w-3.5 h-3.5 shrink-0" />
                    <span>{formatSalary(job.salary_min, job.salary_max, job.salary_currency)}</span>
                  </div>
                </div>
              </div>

              {/* Skills Tags */}
              <div className="space-y-3 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
                <div className="flex flex-wrap gap-1.5">
                  {job.required_skills.slice(0, 4).map((sk, idx) => (
                    <span
                      key={idx}
                      className="text-[10px] px-2 py-0.5 rounded font-medium"
                      style={{ backgroundColor: "var(--surface-muted)", color: "var(--foreground)" }}
                    >
                      {sk}
                    </span>
                  ))}
                  {job.required_skills.length > 4 && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded text-stone-500">
                      +{job.required_skills.length - 4}
                    </span>
                  )}
                </div>

                <div className="flex items-center justify-between text-xs font-medium" style={{ color: "var(--primary)" }}>
                  <span>View Details</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Selected Job Modal / Drawer */}
      {selectedJob && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-xs animate-in fade-in">
          <div
            className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl border p-6 space-y-5 shadow-lg"
            style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between border-b pb-4" style={{ borderColor: "var(--border)" }}>
              <div>
                <div className="flex items-center gap-2 text-xs font-medium" style={{ color: "var(--foreground-muted)" }}>
                  <span>{selectedJob.company_name}</span>
                  <span>•</span>
                  <span>{selectedJob.location}</span>
                </div>
                <h2 className="text-xl font-bold mt-1 tracking-tight" style={{ color: "var(--foreground)" }}>
                  {selectedJob.title}
                </h2>
                <p className="text-sm font-semibold mt-1" style={{ color: "var(--primary)" }}>
                  {formatSalary(selectedJob.salary_min, selectedJob.salary_max, selectedJob.salary_currency)}
                  <span className="font-normal text-xs ml-2 text-stone-500">
                    Min experience: {selectedJob.min_experience_years}y
                  </span>
                </p>
              </div>

              <button
                onClick={() => setSelectedJob(null)}
                className="text-stone-400 hover:text-stone-700 text-sm p-1 cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Required Skills */}
            <div className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-wider block" style={{ color: "var(--foreground)" }}>
                Required Skills
              </span>
              <div className="flex flex-wrap gap-2">
                {selectedJob.required_skills.map((sk, idx) => (
                  <span
                    key={idx}
                    className="text-xs px-2.5 py-1 rounded-md font-medium"
                    style={{ backgroundColor: "var(--primary-light)", color: "var(--primary)" }}
                  >
                    {sk}
                  </span>
                ))}
              </div>
            </div>

            {/* Preferred Skills */}
            {selectedJob.preferred_skills.length > 0 && (
              <div className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-wider block" style={{ color: "var(--foreground-muted)" }}>
                  Preferred / Nice to have
                </span>
                <div className="flex flex-wrap gap-2">
                  {selectedJob.preferred_skills.map((sk, idx) => (
                    <span
                      key={idx}
                      className="text-xs px-2.5 py-1 rounded-md"
                      style={{ backgroundColor: "var(--surface-muted)", color: "var(--foreground)" }}
                    >
                      {sk}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Description */}
            <div className="space-y-2 pt-2 border-t" style={{ borderColor: "var(--border)" }}>
              <span className="text-xs font-semibold uppercase tracking-wider block" style={{ color: "var(--foreground)" }}>
                Full Vacancy Description
              </span>
              <div className="text-xs leading-relaxed text-stone-700 whitespace-pre-line space-y-2">
                {selectedJob.raw_description}
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center justify-between pt-4 border-t" style={{ borderColor: "var(--border)" }}>
              {selectedJob.source_url ? (
                <a
                  href={selectedJob.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-xs px-4 py-2 rounded-lg font-medium text-white transition-all shadow-xs hover:opacity-95 cursor-pointer"
                  style={{ backgroundColor: "var(--primary)" }}
                >
                  <span>Apply on {selectedJob.source_url.includes("dou.ua") ? "DOU.ua" : "Original Job Board"}</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              ) : (
                <span className="text-xs text-stone-400">Internal catalog posting</span>
              )}

              <button
                onClick={() => setSelectedJob(null)}
                className="px-4 py-2 text-xs font-medium rounded-lg border hover:bg-stone-50 cursor-pointer"
                style={{ borderColor: "var(--border)", color: "var(--foreground)" }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
