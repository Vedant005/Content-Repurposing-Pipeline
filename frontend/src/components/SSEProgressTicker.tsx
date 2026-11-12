"use client";

import { useEffect, useRef, useState } from "react";
import { Terminal, CheckCircle2, AlertTriangle, Loader2 } from "lucide-react";

interface SSEProgressTickerProps {
  jobId: number;
  onCompleted: () => void;
  onFailed: (errorMsg: string) => void;
}

interface EventLog {
  id: string;
  stage: string;
  message: string;
  time: string;
}

const KNOWN_EVENTS = [
  "job_created",
  "job_started",
  "fetching_transcript",
  "transcript_ready",
  "chunking_transcript",
  "transcript_chunked",
  "generating_chapters",
  "chapters_generated",
  "generating_blog",
  "blog_generated",
  "generating_tweets",
  "tweets_generated",
  "generating_linkedin",
  "linkedin_generated",
  "critiquing_assets",
  "critique_completed",
  "job_completed",
  "job_failed",
  "asset_retry_queued",
];

const STAGE_LABELS: Record<string, string> = {
  job_created: "Job Queued",
  job_started: "Worker Started",
  fetching_transcript: "Extracting YouTube Transcript",
  transcript_ready: "Transcript Extracted",
  chunking_transcript: "Semantic Chunking",
  transcript_chunked: "Semantic Chunks Ready",
  generating_chapters: "Generating Timestamped Chapters",
  chapters_generated: "Chapters Generated",
  generating_blog: "Generating SEO Blog Post",
  blog_generated: "Blog Post Generated",
  generating_tweets: "Generating Twitter Thread",
  tweets_generated: "Twitter Thread Generated",
  generating_linkedin: "Generating LinkedIn Thought Leadership",
  linkedin_generated: "LinkedIn Post Generated",
  critiquing_assets: "Critiquing & Verifying Outputs",
  critique_completed: "Critique Completed",
  job_completed: "Completed — Finalizing Assets",
  job_failed: "Pipeline Failed",
};

export default function SSEProgressTicker({ jobId, onCompleted, onFailed }: SSEProgressTickerProps) {
  const [logs, setLogs] = useState<EventLog[]>([]);
  const [currentStage, setCurrentStage] = useState("Initializing Engine...");
  const [isCompleted, setIsCompleted] = useState(false);
  const isTerminatedRef = useRef(false);

  useEffect(() => {
    isTerminatedRef.current = false;
    let eventSource: EventSource | null = null;
    let pollInterval: NodeJS.Timeout | null = null;

    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

    const triggerComplete = () => {
      if (isTerminatedRef.current) return;
      isTerminatedRef.current = true;
      setIsCompleted(true);
      setCurrentStage("All assets generated successfully!");
      if (eventSource) {
        eventSource.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
      // Small delay to let user see "Completed" before unmounting
      setTimeout(() => {
        onCompleted();
      }, 300);
    };

    const triggerFail = (errMsg: string) => {
      if (isTerminatedRef.current) return;
      isTerminatedRef.current = true;
      if (eventSource) {
        eventSource.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
      onFailed(errMsg);
    };

    const handleMessage = (event: MessageEvent) => {
      if (isTerminatedRef.current) return;

      try {
        let parsed: any = {};
        if (event.data) {
          try {
            parsed = JSON.parse(event.data);
          } catch {
            parsed = { message: event.data };
          }
        }

        const rawType = event.type && event.type !== "message" ? event.type : null;
        const stage = rawType || parsed.stage || parsed.event || parsed.event_type || "progress";
        const displayLabel = STAGE_LABELS[stage] || stage;
        const msg =
          parsed.message ||
          (parsed.payload?.message ? parsed.payload.message : "") ||
          displayLabel;

        const timeStr = new Date().toLocaleTimeString();

        setCurrentStage(msg || displayLabel);
        setLogs((prev) => [
          ...prev,
          {
            id: `${Date.now()}-${Math.random()}`,
            stage: displayLabel,
            message: msg,
            time: timeStr,
          },
        ]);

        // Check for terminal conditions
        if (
          stage === "job_completed" ||
          stage === "completed" ||
          parsed.status === "completed" ||
          parsed.status === "partial_success"
        ) {
          triggerComplete();
        } else if (
          stage === "job_failed" ||
          stage === "failed" ||
          parsed.status === "failed"
        ) {
          triggerFail(parsed.payload?.error || parsed.error || msg || "Job failed during processing.");
        }
      } catch (e) {
        console.error("Failed to parse SSE event", e);
      }
    };

    const connectSSE = () => {
      const url = new URL(`${backendUrl}/api/v1/jobs/${jobId}/events`);
      eventSource = new EventSource(url.toString(), { withCredentials: true });

      eventSource.onmessage = handleMessage;

      // Register all known named events
      KNOWN_EVENTS.forEach((evtName) => {
        eventSource?.addEventListener(evtName, handleMessage);
      });

      eventSource.onerror = (err) => {
        console.warn("SSE connection interrupted or pending close", err);
      };
    };

    connectSSE();

    // Resilient fallback status poller: checks every 2 seconds in case SSE is buffered or closed
    pollInterval = setInterval(async () => {
      if (isTerminatedRef.current) return;

      try {
        const res = await fetch(`${backendUrl}/api/v1/status/${jobId}`, {
          credentials: "include",
        });
        if (res.ok) {
          const data = await res.json();
          if (data.status === "completed" || data.status === "partial_success") {
            triggerComplete();
          } else if (data.status === "failed") {
            triggerFail(data.error_message || "Job execution failed.");
          }
        }
      } catch (err) {
        // Soft fail on polling check
      }
    }, 1500);

    return () => {
      isTerminatedRef.current = true;
      if (eventSource) {
        eventSource.close();
      }
      if (pollInterval) {
        clearInterval(pollInterval);
      }
    };
  }, [jobId]);

  return (
    <div className="border-2 border-foreground bg-background p-6 shadow-[6px_6px_0px_0px_hsl(0_0%_7%)] mb-8">
      <div className="flex items-center justify-between border-b border-foreground pb-3 mb-4">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-accent" />
          <h3 className="font-serif text-lg font-bold">Live Repurposing Engine Ticker</h3>
        </div>
        <div className="flex items-center gap-2">
          {isCompleted ? (
            <CheckCircle2 className="w-4 h-4 text-green-600" />
          ) : (
            <div className="h-2.5 w-2.5 bg-accent animate-pulse" />
          )}
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Job #{jobId} {isCompleted ? "● COMPLETED" : "● ACTIVE"}
          </span>
        </div>
      </div>

      <div className="bg-muted/30 border border-foreground/30 p-3 mb-4 font-mono text-xs">
        <div className="flex items-center gap-2 text-foreground font-semibold">
          <span>Status:</span>
          {isCompleted ? (
            <span className="text-green-600 font-bold flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {currentStage}
            </span>
          ) : (
            <span className="text-accent flex items-center gap-1.5">
              <Loader2 className="w-3 h-3 animate-spin" />
              {currentStage}
            </span>
          )}
        </div>
      </div>

      {/* Scrolling Stage Log */}
      <div className="space-y-1.5 max-h-48 overflow-y-auto font-mono text-xs">
        {logs.length === 0 ? (
          <div className="text-muted-foreground italic flex items-center gap-2">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Connecting to Redis ARQ worker event stream...
          </div>
        ) : (
          logs.map((log) => (
            <div key={log.id} className="flex items-start gap-2 border-l border-foreground/30 pl-2 py-0.5">
              <span className="text-muted-foreground text-[10px]">[{log.time}]</span>
              <span className="text-accent uppercase text-[10px] font-bold">[{log.stage}]</span>
              <span className="text-foreground/90 flex-1">{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
