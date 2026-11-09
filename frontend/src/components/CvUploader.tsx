"use client";

import { useState, useRef } from "react";
import {
  UploadCloud,
  FileCheck,
  AlertCircle,
  Briefcase,
  ShieldCheck,
  Sparkles,
  Quote,
  Loader2,
} from "lucide-react";

interface Skill {
  name: string;
  category: string;
  years_of_experience?: number;
  source_quote: string;
}

interface WorkExperience {
  company: string;
  role: string;
  start_date?: string;
  end_date?: string;
  responsibilities: string[];
  skills_used: string[];
  source_quote: string;
}

interface Education {
  institution: string;
  degree?: string;
  field_of_study?: string;
  graduation_year?: number;
}

interface CvProfile {
  id: string;
  user_id: string;
  target_role: string | null;
  years_of_experience: number | null;
  structured_data: {
    contact?: {
      email?: string;
      phone?: string;
      linkedin_url?: string;
      location?: string;
    };
    summary?: string;
    education?: Education[];
    page_count?: number;
  };
  work_experiences: WorkExperience[];
  skills: Skill[];
  verified_skills_count: number;
  discarded_hallucinations_count: number;
}

export function CvUploader() {
  const [file, setFile] = useState<File | null>(null);
  const [email, setEmail] = useState("candidate@example.com");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profile, setProfile] = useState<CvProfile | null>(null);
  const [activeQuote, setActiveQuote] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const selected = e.dataTransfer.files[0];
      if (selected.type === "application/pdf" || selected.name.endsWith(".pdf")) {
        setFile(selected);
        setError(null);
      } else {
        setError("Only PDF resume files (.pdf) are supported.");
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.type === "application/pdf" || selected.name.endsWith(".pdf")) {
        setFile(selected);
        setError(null);
      } else {
        setError("Only PDF resume files (.pdf) are supported.");
      }
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("user_email", email);

    try {
      const res = await fetch("http://localhost:8000/api/v1/cv/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to process CV");
      }

      setProfile(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Error connecting to backend");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
            1. CV Upload & Zero-Hallucination Extraction
          </h2>
          <p className="text-sm mt-1" style={{ color: "var(--foreground-muted)" }}>
            Upload your resume in PDF. Our engine parses the spatial layout and verifies every skill with verbatim citations.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Upload Column */}
        <div className="lg:col-span-5 space-y-4">
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleFileDrop}
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all hover:bg-stone-50/50 flex flex-col items-center justify-center space-y-3"
            style={{
              borderColor: file ? "var(--primary)" : "var(--border)",
              backgroundColor: "var(--surface)",
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,application/pdf"
              className="hidden"
              onChange={handleFileSelect}
            />

            <div
              className="w-12 h-12 rounded-full flex items-center justify-center shadow-xs"
              style={{ backgroundColor: file ? "var(--primary-light)" : "var(--surface-muted)" }}
            >
              {file ? (
                <FileCheck className="w-6 h-6" style={{ color: "var(--primary)" }} />
              ) : (
                <UploadCloud className="w-6 h-6" style={{ color: "var(--foreground-muted)" }} />
              )}
            </div>

            <div>
              <p className="font-medium text-sm" style={{ color: "var(--foreground)" }}>
                {file ? file.name : "Click to browse or drop your PDF here"}
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>
                {file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB • Ready to analyze` : "Digital PDF resume up to 10MB"}
              </p>
            </div>
          </div>

          {/* Email input & Action */}
          <div className="space-y-3 p-4 rounded-xl border" style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}>
            <label className="text-xs font-medium block" style={{ color: "var(--foreground-muted)" }}>
              Candidate Account Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 text-sm rounded-lg border focus:outline-none focus:ring-1"
              style={{
                borderColor: "var(--border)",
                backgroundColor: "var(--background)",
                color: "var(--foreground)",
              }}
              placeholder="candidate@example.com"
            />

            <button
              onClick={handleUpload}
              disabled={!file || loading}
              className="w-full py-2.5 px-4 rounded-lg font-medium text-sm text-white flex items-center justify-center gap-2 transition-all disabled:opacity-50 shadow-xs cursor-pointer"
              style={{ backgroundColor: "var(--primary)" }}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Analyzing layout with Gemini...</span>
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  <span>Extract & Verify Profile</span>
                </>
              )}
            </button>
          </div>

          {error && (
            <div className="p-3 rounded-lg border flex items-start gap-2 bg-red-50/70 border-red-200 text-red-800 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}
        </div>

        {/* Extracted Profile Review Column */}
        <div className="lg:col-span-7">
          {profile ? (
            <div
              className="rounded-xl border p-6 space-y-6 shadow-xs animate-in fade-in"
              style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
            >
              {/* Profile Header */}
              <div className="flex items-start justify-between border-b pb-4" style={{ borderColor: "var(--border)" }}>
                <div>
                  <h3 className="text-lg font-semibold tracking-tight" style={{ color: "var(--foreground)" }}>
                    {profile.target_role || "Extracted Candidate Profile"}
                  </h3>
                  <p className="text-xs mt-1" style={{ color: "var(--foreground-muted)" }}>
                    {profile.structured_data.contact?.location || "Location not specified"} • {profile.years_of_experience ?? "N/A"} years exp
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className="flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-full font-medium"
                    style={{ backgroundColor: "var(--primary-light)", color: "var(--primary)" }}
                  >
                    <ShieldCheck className="w-3.5 h-3.5" />
                    <span>{profile.verified_skills_count} verified skills</span>
                  </span>
                  {profile.discarded_hallucinations_count > 0 && (
                    <span
                      className="text-xs px-2 py-1 rounded-full font-medium"
                      style={{ backgroundColor: "var(--accent-light)", color: "var(--accent)" }}
                    >
                      {profile.discarded_hallucinations_count} unverified filtered
                    </span>
                  )}
                </div>
              </div>

              {/* Summary */}
              {profile.structured_data.summary && (
                <div className="space-y-1 text-xs leading-relaxed" style={{ color: "var(--foreground-muted)" }}>
                  <span className="font-semibold uppercase tracking-wider text-[10px]" style={{ color: "var(--foreground)" }}>
                    Summary
                  </span>
                  <p>{profile.structured_data.summary}</p>
                </div>
              )}

              {/* Skills with Verbatim Quotes */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--foreground)" }}>
                    Extracted Skills & Citations
                  </span>
                  <span className="text-[11px]" style={{ color: "var(--foreground-muted)" }}>
                    Click a skill to view the exact CV proof
                  </span>
                </div>

                <div className="flex flex-wrap gap-2">
                  {profile.skills.map((skill, idx) => (
                    <button
                      key={idx}
                      onClick={() => setActiveQuote(activeQuote === skill.source_quote ? null : skill.source_quote)}
                      className="text-xs px-2.5 py-1 rounded-md border flex items-center gap-1.5 transition-all hover:border-stone-400 cursor-pointer"
                      style={{
                        backgroundColor: activeQuote === skill.source_quote ? "var(--primary-light)" : "var(--surface-muted)",
                        borderColor: activeQuote === skill.source_quote ? "var(--primary)" : "var(--border)",
                        color: "var(--foreground)",
                      }}
                    >
                      <span>{skill.name}</span>
                      {skill.years_of_experience && (
                        <span className="text-[10px] font-medium opacity-60">
                          {skill.years_of_experience}y
                        </span>
                      )}
                    </button>
                  ))}
                </div>

                {/* Citation Proof Box */}
                {activeQuote && (
                  <div
                    className="p-3 rounded-lg border text-xs flex items-start gap-2.5 mt-2 animate-in fade-in"
                    style={{ backgroundColor: "var(--primary-light)", borderColor: "var(--primary)", color: "var(--primary)" }}
                  >
                    <Quote className="w-4 h-4 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-semibold text-[11px] uppercase tracking-wider">Verbatim Source Citation:</p>
                      <p className="italic mt-0.5">&quot;{activeQuote}&quot;</p>
                    </div>
                  </div>
                )}
              </div>

              {/* Work Experience */}
              <div className="space-y-3 pt-2">
                <span className="text-xs font-semibold uppercase tracking-wider block" style={{ color: "var(--foreground)" }}>
                  Work Experience
                </span>
                <div className="space-y-3">
                  {profile.work_experiences.map((exp, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg border text-xs space-y-1.5"
                      style={{ backgroundColor: "var(--background)", borderColor: "var(--border)" }}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-semibold" style={{ color: "var(--foreground)" }}>
                          {exp.role} • <span className="font-normal" style={{ color: "var(--foreground-muted)" }}>{exp.company}</span>
                        </span>
                        <span className="text-[11px]" style={{ color: "var(--foreground-muted)" }}>
                          {exp.start_date || "N/A"} — {exp.end_date || "Present"}
                        </span>
                      </div>
                      {exp.responsibilities.length > 0 && (
                        <ul className="list-disc list-inside space-y-1 text-stone-600 pl-1">
                          {exp.responsibilities.map((r, rIdx) => (
                            <li key={rIdx}>{r}</li>
                          ))}
                        </ul>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div
              className="rounded-xl border border-dashed p-12 text-center flex flex-col items-center justify-center space-y-2 h-full min-h-[320px]"
              style={{ backgroundColor: "var(--surface)", borderColor: "var(--border)" }}
            >
              <Briefcase className="w-8 h-8" style={{ color: "var(--foreground-muted)" }} />
              <p className="text-sm font-medium" style={{ color: "var(--foreground)" }}>
                No CV Analyzed Yet
              </p>
              <p className="text-xs max-w-sm" style={{ color: "var(--foreground-muted)" }}>
                Drop a resume on the left and click &quot;Extract &amp; Verify Profile&quot; to see the extracted structured skills and work chronology.
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
