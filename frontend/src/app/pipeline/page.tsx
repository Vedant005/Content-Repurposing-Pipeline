"use client";

import { useState, useEffect } from "react";
import {
  FileText,
  Twitter,
  Linkedin,
  Clock,
  Loader2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  Download,
  Video,
} from "lucide-react";
import YouTubeInput from "@/components/YouTubeInput";
import AssetEditor from "@/components/AssetEditor";
import ChaptersView from "@/components/ChaptersView";
import BrandProfileSelector from "@/components/BrandProfileSelector";
import CostAndQualityBadge from "@/components/CostAndQualityBadge";
import SSEProgressTicker from "@/components/SSEProgressTicker";
import { ChapterItem, usePipelineStore } from "@/store/usePipelineStore";

interface HistoryItem {
  id: number;
  youtube_url: string;
  status: string;
  created_at: string;
}

const Pipeline = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const {
    results,
    setResults,
    videoUrl,
    setVideoUrl,
    activeJobId,
    setActiveJobId,
    isHistoryVisible,
    setIsHistoryVisible,
    activeTab,
    setActiveTab,
    selectedBrandProfileId,
    setBrandProfiles,
  } = usePipelineStore();

  useEffect(() => {
    fetchHistory();
    fetchBrandProfiles();
  }, []);

  const fetchBrandProfiles = async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/brand-profiles`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data = await res.json();
        setBrandProfiles(data);
      }
    } catch (e) {
      console.warn("Could not load brand profiles:", e);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/history?limit=10`,
        { credentials: "include" }
      );
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch (error) {
      console.error("Failed to fetch history:", error);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  const parseTweets = (tweets: unknown): string => {
    if (Array.isArray(tweets)) {
      return tweets
        .map((t) => (typeof t === "object" && t !== null && "content" in t ? (t as any).content : String(t)))
        .join("\n\n---\n\n");
    }
    if (typeof tweets === "string") {
      try {
        const parsed = JSON.parse(tweets);
        if (Array.isArray(parsed)) {
          return parsed
            .map((t) => (typeof t === "object" && t !== null && "content" in t ? (t as any).content : String(t)))
            .join("\n\n---\n\n");
        }
        return tweets;
      } catch {
        return tweets;
      }
    }
    return "";
  };

  const loadJobAssets = async (jobId: number) => {
    try {
      const [statusRes, assetsRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/status/${jobId}`, {
          credentials: "include",
        }),
        fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/jobs/${jobId}/assets`, {
          credentials: "include",
        }),
      ]);

      if (!statusRes.ok) throw new Error("Failed to fetch job details");
      const statusData = await statusRes.json();

      let chaptersList: ChapterItem[] = [];
      if (assetsRes.ok) {
        const assetsData = await assetsRes.json();
        const chaptersAsset = assetsData.find((a: any) => a.asset_type === "chapters");
        if (chaptersAsset?.content?.chapters) {
          chaptersList = chaptersAsset.content.chapters;
        }
      }

      setResults({
        blog: statusData.blog_content || "",
        twitter: parseTweets(statusData.tweets),
        linkedin: statusData.linkedin_post || "",
        chapters: chaptersList,
      });
      setIsLoading(false);
      fetchHistory();
    } catch (err: any) {
      console.error("Error loading job assets:", err);
      setError(err.message || "Failed to load generated content.");
      setIsLoading(false);
    }
  };

  const loadHistoryItem = async (jobId: number, url: string) => {
    setVideoUrl(url);
    setActiveJobId(jobId);
    setIsLoading(true);
    setResults(null);
    setError(null);
    await loadJobAssets(jobId);
  };

  const handleSubmit = async (url: string) => {
    setVideoUrl(url);
    setIsLoading(true);
    setResults(null);
    setError(null);

    try {
      const payload: { url: string; brand_profile_id?: number } = { url };
      if (selectedBrandProfileId) {
        payload.brand_profile_id = selectedBrandProfileId;
      }

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/repurpose`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          credentials: "include",
          body: JSON.stringify(payload),
        }
      );

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || "Failed to submit video for repurposing.");
      }

      const data = await response.json();
      setActiveJobId(data.job_id);
      fetchHistory();
      setIsHistoryVisible(true);
    } catch (err: any) {
      console.error("Submission error:", err);
      setError(err.message || "Failed to communicate with the server.");
      setIsLoading(false);
    }
  };

  const handleExportAll = () => {
    if (!results) return;
    const bundleText = `================================================================================
CONTENT REPURPOSING STUDIO v2.0 - PUBLICATION BUNDLE
Source Video: ${videoUrl}
Generated at: ${new Date().toISOString()}
================================================================================

--------------------------------------------------------------------------------
FORMAT 01: SEO BLOG POST
--------------------------------------------------------------------------------
${results.blog}


--------------------------------------------------------------------------------
FORMAT 02: TWITTER / X THREAD
--------------------------------------------------------------------------------
${results.twitter}


--------------------------------------------------------------------------------
FORMAT 03: LINKEDIN POST
--------------------------------------------------------------------------------
${results.linkedin}


--------------------------------------------------------------------------------
FORMAT 04: TIMESTAMPED CHAPTERS
--------------------------------------------------------------------------------
${
  results.chapters && results.chapters.length > 0
    ? results.chapters
        .map((ch) => `${ch.timestamp_formatted} - ${ch.title}\n${ch.summary}\n`)
        .join("\n")
    : "No chapters available."
}
================================================================================
`;
    const blob = new Blob([bundleText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `repurposed_content_bundle_${Date.now()}.txt`;
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div>
      {/* Header Banner */}
      <section className="border-b border-foreground">
        <div className="container py-12 md:py-16">
          <span className="font-mono text-xs uppercase tracking-widest text-accent font-semibold">
            ● The Pipeline
          </span>
          <h2 className="font-serif text-4xl sm:text-5xl lg:text-7xl font-black tracking-tighter leading-[0.9] mt-3">
            Content Repurposing Studio
          </h2>
          <p className="font-body text-muted-foreground mt-4 max-w-xl">
            Transform YouTube videos into SEO blog posts, Twitter threads, LinkedIn thought-leadership posts, and timestamped chapters with deterministic quote grounding.
          </p>
        </div>
      </section>

      {/* Input & Persona Section */}
      <section className="border-b border-foreground">
        <div className="container py-8 md:py-10">
          <CostAndQualityBadge />

          {/* Brand Profile Voice Selector */}
          <BrandProfileSelector onProfileCreated={fetchBrandProfiles} />

          {/* YouTube Input Box */}
          <YouTubeInput onSubmit={handleSubmit} isLoading={isLoading} />
        </div>
      </section>

      {/* Live SSE Progress Ticker (When Job is Active) */}
      {isLoading && activeJobId && (
        <section className="border-b border-foreground bg-muted/10">
          <div className="container py-8">
            <SSEProgressTicker
              jobId={activeJobId}
              onCompleted={() => loadJobAssets(activeJobId)}
              onFailed={(msg) => {
                setError(msg);
                setIsLoading(false);
                fetchHistory();
              }}
            />
          </div>
        </section>
      )}

      {/* Recent History Drawer */}
      {!isLoadingHistory && history.length > 0 && (
        <section className="border-b border-foreground bg-muted/20">
          <div className="container py-3">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="w-4 h-4" />
                <span className="font-mono text-xs uppercase tracking-widest">
                  Recent Jobs ({history.length})
                </span>
              </div>
              <button
                onClick={() => setIsHistoryVisible(!isHistoryVisible)}
                className="flex items-center gap-1 font-mono text-xs uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors"
              >
                {isHistoryVisible ? (
                  <>
                    Hide <ChevronUp className="w-3 h-3" />
                  </>
                ) : (
                  <>
                    Show <ChevronDown className="w-3 h-3" />
                  </>
                )}
              </button>
            </div>

            {isHistoryVisible && (
              <div className="flex flex-col gap-2">
                {history.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => {
                      if (item.status === "completed" || item.status === "partial_success") {
                        loadHistoryItem(item.id, item.youtube_url);
                      }
                    }}
                    className={`flex items-center justify-between p-3 border border-foreground/10 bg-background transition-colors ${
                      item.status === "completed" || item.status === "partial_success"
                        ? "hover:border-foreground/40 cursor-pointer"
                        : "opacity-80 cursor-default"
                    } ${activeJobId === item.id ? "border-foreground bg-muted/30" : ""}`}
                  >
                    <div className="truncate pr-4 flex-1">
                      <p className="font-mono text-sm truncate">{item.youtube_url}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span
                        className={`font-mono text-xs uppercase tracking-wider ${
                          item.status === "completed"
                            ? "text-green-700 font-bold"
                            : item.status === "partial_success"
                            ? "text-amber-700 font-bold"
                            : item.status === "failed"
                            ? "text-red-600 font-bold"
                            : "text-accent animate-pulse"
                        }`}
                      >
                        [{item.status}]
                      </span>
                      {item.status === "processing" && (
                        <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}

      {/* Error Banner */}
      {error && (
        <div className="container mt-6">
          <div className="p-4 border border-red-500/40 bg-red-500/10 text-red-600 font-body text-sm flex items-start gap-3">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <p className="leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* Results Workbench */}
      {results && !isLoading && (
        <section>
          <div className="container py-8 md:py-12">
            <div className="flex flex-wrap items-center justify-between border-b border-foreground pb-4 mb-8 gap-4">
              <div>
                <span className="font-mono text-xs uppercase tracking-widest text-accent font-semibold block">
                  ● Publication Workbench
                </span>
                <h3 className="font-serif text-2xl font-bold mt-1">Repurposed Content Assets</h3>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                {/* Format Filter Tabs */}
                <div className="flex border border-foreground font-mono text-xs uppercase tracking-wider">
                  <button
                    onClick={() => setActiveTab("blog")}
                    className={`px-3 py-1.5 transition-colors ${
                      activeTab === "blog" ? "bg-foreground text-primary-foreground font-bold" : "hover:bg-muted"
                    }`}
                  >
                    Blog
                  </button>
                  <button
                    onClick={() => setActiveTab("twitter")}
                    className={`px-3 py-1.5 border-l border-foreground transition-colors ${
                      activeTab === "twitter" ? "bg-foreground text-primary-foreground font-bold" : "hover:bg-muted"
                    }`}
                  >
                    X Thread
                  </button>
                  <button
                    onClick={() => setActiveTab("linkedin")}
                    className={`px-3 py-1.5 border-l border-foreground transition-colors ${
                      activeTab === "linkedin" ? "bg-foreground text-primary-foreground font-bold" : "hover:bg-muted"
                    }`}
                  >
                    LinkedIn
                  </button>
                  <button
                    onClick={() => setActiveTab("chapters")}
                    className={`px-3 py-1.5 border-l border-foreground transition-colors ${
                      activeTab === "chapters" ? "bg-foreground text-primary-foreground font-bold" : "hover:bg-muted"
                    }`}
                  >
                    Chapters ({results.chapters?.length || 0})
                  </button>
                </div>

                {/* Export All Bundle */}
                <button
                  onClick={handleExportAll}
                  className="flex items-center gap-1.5 px-4 py-1.5 border border-foreground bg-accent text-accent-foreground font-mono text-xs uppercase tracking-wider font-bold hover:opacity-90 transition-opacity"
                >
                  <Download className="w-3.5 h-3.5" />
                  Export Bundle (.txt)
                </button>
              </div>
            </div>

            {/* Tabbed / Active Asset View */}
            <div className="space-y-6">
              {activeTab === "blog" && (
                <AssetEditor
                  title="SEO Optimized Blog Post"
                  label="Format 01 — Long Form Analysis"
                  assetType="blog"
                  content={results.blog}
                  icon={<FileText className="h-5 w-5" strokeWidth={1.5} />}
                  jobId={activeJobId}
                  onContentChange={(val) => setResults({ ...results, blog: val })}
                  onRegenerateTriggered={() => activeJobId && loadJobAssets(activeJobId)}
                />
              )}

              {activeTab === "twitter" && (
                <AssetEditor
                  title="Viral Twitter / X Thread"
                  label="Format 02 — High Engagement Social"
                  assetType="twitter_thread"
                  content={results.twitter}
                  icon={<Twitter className="h-5 w-5" strokeWidth={1.5} />}
                  jobId={activeJobId}
                  onContentChange={(val) => setResults({ ...results, twitter: val })}
                  onRegenerateTriggered={() => activeJobId && loadJobAssets(activeJobId)}
                />
              )}

              {activeTab === "linkedin" && (
                <AssetEditor
                  title="LinkedIn Thought-Leadership Post"
                  label="Format 03 — Professional Editorial"
                  assetType="linkedin_post"
                  content={results.linkedin}
                  icon={<Linkedin className="h-5 w-5" strokeWidth={1.5} />}
                  jobId={activeJobId}
                  onContentChange={(val) => setResults({ ...results, linkedin: val })}
                  onRegenerateTriggered={() => activeJobId && loadJobAssets(activeJobId)}
                />
              )}

              {activeTab === "chapters" && (
                <ChaptersView
                  chapters={results.chapters || []}
                  videoUrl={videoUrl}
                />
              )}
            </div>
          </div>
        </section>
      )}

      {/* Empty State */}
      {!results && !isLoading && !error && (
        <section>
          <div className="container py-16 md:py-24 text-center">
            <div className="max-w-md mx-auto">
              <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                ✧ ✧ ✧
              </span>
              <p className="font-serif text-2xl font-bold mt-4 mb-2">Ready to Repurpose</p>
              <p className="font-body text-sm text-muted-foreground">
                Paste any YouTube URL above to produce SEO blogs, threads, thought leadership posts, and timestamped chapter bookmarks.
              </p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default Pipeline;
