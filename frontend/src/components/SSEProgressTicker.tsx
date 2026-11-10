"use client";

import { useEffect, useState } from "react";
import { Terminal, CheckCircle2, AlertTriangle } from "lucide-react";

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

export default function SSEProgressTicker({ jobId, onCompleted, onFailed }: SSEProgressTickerProps) {
  const [logs, setLogs] = useState<EventLog[]>([]);
  const [currentStage, setCurrentStage] = useState("Initializing...");
  const [lastEventId, setLastEventId] = useState<string | null>(null);

  useEffect(() => {
    let eventSource: EventSource | null = null;
    let isTerminated = false;

    const connectSSE = () => {
      const url = new URL(`${process.env.NEXT_PUBLIC_BACKEND_URL}/api/v1/jobs/${jobId}/events`);
      if (lastEventId) {
        url.searchParams.set("last_event_id", lastEventId);
      }

      eventSource = new EventSource(url.toString(), { withCredentials: true });

      eventSource.onmessage = (event) => {
        if (isTerminated) return;

        try {
          if (event.lastEventId) {
            setLastEventId(event.lastEventId);
          }

          const parsed = JSON.parse(event.data);
          const stage = parsed.stage || "progress";
          const msg =
            parsed.message ||
            (parsed.payload?.message ? parsed.payload.message : JSON.stringify(parsed.payload || ""));

          const timeStr = new Date().toLocaleTimeString();

          setCurrentStage(msg || stage);
          setLogs((prev) => [
            ...prev,
            {
              id: `${Date.now()}-${Math.random()}`,
              stage,
              message: msg,
              time: timeStr,
            },
          ]);

          if (stage === "job_completed" || stage === "completed") {
            isTerminated = true;
            eventSource?.close();
            onCompleted();
          } else if (stage === "job_failed" || stage === "failed") {
            isTerminated = true;
            eventSource?.close();
            onFailed(parsed.payload?.error || msg || "Job failed during processing.");
          }
        } catch (e) {
          console.error("Failed to parse SSE event payload", e);
        }
      };

      eventSource.onerror = (err) => {
        console.warn("SSE connection interrupted or pending close", err);
        // Will auto reconnect unless closed
      };
    };

    connectSSE();

    return () => {
      isTerminated = true;
      if (eventSource) {
        eventSource.close();
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
          <div className="h-2.5 w-2.5 bg-accent animate-pulse" />
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Job #{jobId}
          </span>
        </div>
      </div>

      <div className="bg-muted/30 border border-foreground/30 p-3 mb-4 font-mono text-xs">
        <div className="flex items-center gap-2 text-foreground font-semibold">
          <span>Status:</span>
          <span className="text-accent">{currentStage}</span>
        </div>
      </div>

      {/* Scrolling Stage Log */}
      <div className="space-y-1.5 max-h-48 overflow-y-auto font-mono text-xs">
        {logs.length === 0 ? (
          <div className="text-muted-foreground italic">Connecting to Redis ARQ worker event stream...</div>
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
