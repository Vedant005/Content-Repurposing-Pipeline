"use client";

import { useState, useEffect } from "react";
import {
  FileText,
  Twitter,
  Linkedin,
  Clock,
  ArrowRight,
  Loader2,
  ChevronDown,
  ChevronUp,
  AlertCircle,
} from "lucide-react";
import YouTubeInput from "@/components/YouTubeInput";
import ResultCard from "@/components/ResultCard";
import { usePipelineStore } from "@/store/usePipelineStore";

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
    isHistoryVisible,
    setIsHistoryVisible,
  } = usePipelineStore();

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/history?limit=5`,
        {
          credentials: "include",
        },
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

  const loadHistoryItem = async (jobId: number, url: string) => {
    setVideoUrl(url);
    setIsLoading(true);
    setResults(null);
    setError(null);

    try {
      const statusRes = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/status/${jobId}`,
        { credentials: "include" },
      );

      if (!statusRes.ok) throw new Error("Failed to fetch job details");

      const statusData = await statusRes.json();

      if (statusData.status === "completed") {
        let formattedTwitter = "";
        if (Array.isArray(statusData.tweets)) {
          formattedTwitter = statusData.tweets.join("\n\n");
        } else if (typeof statusData.tweets === "string") {
          try {
            const parsed = JSON.parse(statusData.tweets);
            formattedTwitter = Array.isArray(parsed)
              ? parsed.join("\n\n")
              : statusData.tweets;
          } catch (e) {
            formattedTwitter = statusData.tweets;
          }
        }

        setResults({
          blog: statusData.blog_content || "",
          twitter: formattedTwitter,
          linkedin: statusData.linkedin_post || "",
        });
      } else if (statusData.status === "failed") {
        setError(statusData.error_message || "This job failed to process.");
      } else {
        console.error("Job is not completed yet:", statusData.status);
      }
    } catch (err) {
      console.error("Error loading history item:", err);
      setError("Failed to load the details for this video.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmit = async (url: string) => {
    setVideoUrl(url);
    setIsLoading(true);
    setResults(null);
    setError(null);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/repurpose`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          credentials: "include",
          body: JSON.stringify({ url }),
        },
      );

      if (!response.ok) {
        throw new Error("Failed to start job");
      }

      const data = await response.json();
      const jobId = data.job_id;

      fetchHistory();
      setIsHistoryVisible(true);

      const pollInterval = setInterval(async () => {
        try {
          const statusRes = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/status/${jobId}`,
            {
              credentials: "include",
            },
          );
          if (!statusRes.ok) throw new Error("Failed to check status");

          const statusData = await statusRes.json();

          if (statusData.status === "completed") {
            clearInterval(pollInterval);

            let formattedTwitter = "";
            if (Array.isArray(statusData.tweets)) {
              formattedTwitter = statusData.tweets.join("\n\n");
            } else if (typeof statusData.tweets === "string") {
              try {
                const parsed = JSON.parse(statusData.tweets);
                formattedTwitter = Array.isArray(parsed)
                  ? parsed.join("\n\n")
                  : statusData.tweets;
              } catch (e) {
                formattedTwitter = statusData.tweets;
              }
            }

            setResults({
              blog: statusData.blog_content || "",
              twitter: formattedTwitter,
              linkedin: statusData.linkedin_post || "",
            });

            setIsLoading(false);
            fetchHistory();
          } else if (
            statusData.status === "failed" ||
            statusData.error_message
          ) {
            clearInterval(pollInterval);
            const errMsg = statusData.error_message || "";
            console.error("Job failed:", errMsg);

            if (
              errMsg.includes("413") ||
              errMsg.includes("too large") ||
              errMsg.includes("rate_limit_exceeded") ||
              errMsg.includes("tokens")
            ) {
              setError(
                "The transcript for this video is too long. Our AI context limit currently restricts processing to videos around 25-30 minutes. We'll be extending this capacity soon!",
              );
            } else {
              setError(
                errMsg ||
                  "An error occurred while extracting content from this video.",
              );
            }

            setIsLoading(false);
            fetchHistory();
          }
        } catch (pollErr) {
          clearInterval(pollInterval);
          console.error("Polling error:", pollErr);
          setError("Lost connection to the server while checking status.");
          setIsLoading(false);
        }
      }, 3000);
    } catch (err) {
      console.error("Submission error:", err);
      setError(
        "Failed to communicate with the server. Please check your connection.",
      );
      setIsLoading(false);
    }
  };

  return (
    <div>
      <section className="border-b border-foreground">
        <div className="container py-12 md:py-16">
          <span className="font-mono text-xs uppercase tracking-widest text-accent font-semibold">
            ● The Pipeline
          </span>
          <h2 className="font-serif text-4xl sm:text-5xl lg:text-7xl font-black tracking-tighter leading-[0.9] mt-3">
            Content Repurposing Pipeline
          </h2>
          <p className="font-body text-muted-foreground mt-4 max-w-lg">
            Paste a YouTube URL below. We'll extract the content and generate
            three optimized formats for you.
          </p>
        </div>
      </section>

      <section className="border-b border-foreground">
        <div className="container py-8 md:py-10">
          <div>
            <div className="mb-6 border-l-2 border-accent pl-4 py-1">
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1">
                Notice
              </p>
              <p className="font-body text-sm text-foreground/80">
                Please avoid videos with more than{" "}
                <strong>25-30 minutes</strong> of runtime. Longer videos
                currently exceed our context limits. This capacity will be
                extended in the near future.
              </p>
            </div>

            <YouTubeInput onSubmit={handleSubmit} isLoading={isLoading} />

            {error && (
              <div className="mt-6 p-4 border border-red-500/20 bg-red-500/10 text-red-500 dark:text-red-400 font-body text-sm flex items-start gap-3 animate-in fade-in slide-in-from-top-2">
                <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
                <p className="leading-relaxed">{error}</p>
              </div>
            )}
          </div>
        </div>
      </section>

      {!isLoadingHistory && history.length > 0 && (
        <section className="border-b border-foreground bg-muted/20">
          <div className="container py-3">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="w-4 h-4" />
                <span className="font-mono text-xs uppercase tracking-widest">
                  Recent Jobs
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
                      if (
                        item.status === "completed" ||
                        item.status === "failed"
                      ) {
                        loadHistoryItem(item.id, item.youtube_url);
                      }
                    }}
                    className={`flex items-center justify-between p-3 border border-foreground/10 bg-background transition-colors ${
                      item.status === "completed" || item.status === "failed"
                        ? "hover:border-foreground/30 cursor-pointer"
                        : "opacity-80 cursor-default"
                    }`}
                  >
                    <div className="truncate pr-4 flex-1">
                      <p className="font-mono text-sm truncate">
                        {item.youtube_url}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span
                        className={`font-mono text-xs uppercase tracking-wider ${
                          item.status === "completed"
                            ? "text-green-600 dark:text-green-400"
                            : item.status === "failed"
                              ? "text-red-600 dark:text-red-400"
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

      {isLoading && (
        <section className="border-b border-foreground">
          <div className="container py-16 text-center">
            <div className="inline-block border-4 border-foreground p-8">
              <div className="flex items-center gap-3 mb-4">
                <div className="h-3 w-3 bg-accent animate-pulse" />
                <span className="font-mono text-xs uppercase tracking-widest">
                  Processing
                </span>
              </div>
              <p className="font-serif text-2xl font-bold">
                Extracting & generating content...
              </p>
              <p className="font-body text-sm text-muted-foreground mt-2">
                This typically takes 15-30 seconds
              </p>
            </div>
          </div>
        </section>
      )}

      {results && !isLoading && (
        <section>
          <div className="container py-8 md:py-12">
            <div className="flex items-center gap-3 mb-8">
              <span className="font-mono text-xs uppercase tracking-widest text-accent font-semibold">
                ● Results
              </span>
            </div>

            <div className="grid grid-cols-1 gap-6">
              <ResultCard
                title="SEO Blog Post"
                label="Format 01 — Long Form"
                content={results.blog}
                icon={<FileText className="h-5 w-5" strokeWidth={1.5} />}
              />
              <ResultCard
                title="Twitter Thread"
                label="Format 02 — Social"
                content={results.twitter}
                icon={<Twitter className="h-5 w-5" strokeWidth={1.5} />}
              />
              <ResultCard
                title="LinkedIn Summary"
                label="Format 03 — Professional"
                content={results.linkedin}
                icon={<Linkedin className="h-5 w-5" strokeWidth={1.5} />}
              />
            </div>
          </div>
        </section>
      )}

      {!results && !isLoading && !error && (
        <section>
          <div className="container py-16 md:py-24 text-center">
            <div className="max-w-md mx-auto">
              <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
                ✧ ✧ ✧
              </span>
              <p className="font-serif text-2xl font-bold mt-4 mb-2">
                No content yet
              </p>
              <p className="font-body text-sm text-muted-foreground">
                Paste a YouTube URL above to generate your repurposed content.
              </p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
};

export default Pipeline;
