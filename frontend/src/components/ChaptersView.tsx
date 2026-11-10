"use client";

import { useState } from "react";
import { ChapterItem } from "@/store/usePipelineStore";
import { Copy, Check, ExternalLink, Video } from "lucide-react";

interface ChaptersViewProps {
  chapters: ChapterItem[];
  videoUrl: string;
}

export default function ChaptersView({ chapters, videoUrl }: ChaptersViewProps) {
  const [copied, setCopied] = useState(false);

  const getTimestampUrl = (seconds: number) => {
    if (!videoUrl) return "#";
    const separator = videoUrl.includes("?") ? "&" : "?";
    return `${videoUrl}${separator}t=${seconds}s`;
  };

  const handleCopyTimestamps = async () => {
    const formatted = chapters
      .map((ch) => `${ch.timestamp_formatted} ${ch.title}`)
      .join("\n");
    await navigator.clipboard.writeText(formatted);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!chapters || chapters.length === 0) {
    return (
      <div className="p-8 border border-foreground text-center font-body text-sm text-muted-foreground">
        No chapter markers available for this video.
      </div>
    );
  }

  return (
    <div className="border border-foreground bg-background hard-shadow-hover">
      <div className="flex items-center justify-between border-b border-foreground px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="border border-foreground h-10 w-10 flex items-center justify-center">
            <Video className="h-5 w-5" strokeWidth={1.5} />
          </div>
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground block">
              Format 04 — Indexing & Navigation
            </span>
            <h3 className="font-serif text-lg font-bold leading-tight">
              Timestamped Chapters & Source References
            </h3>
          </div>
        </div>

        <button
          onClick={handleCopyTimestamps}
          className="flex items-center gap-1.5 px-3 py-1.5 border border-foreground font-mono text-xs uppercase tracking-wider hover:bg-foreground hover:text-primary-foreground transition-colors"
        >
          {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
          {copied ? "Copied Format" : "Copy YouTube Timestamps"}
        </button>
      </div>

      <div className="p-4 md:p-6 divide-y divide-foreground/10">
        {chapters.map((ch, idx) => (
          <div key={idx} className="py-3 first:pt-0 last:pb-0 flex items-start gap-4">
            <a
              href={getTimestampUrl(ch.timestamp_seconds)}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1 border border-foreground font-mono text-xs font-bold hover:bg-foreground hover:text-primary-foreground transition-colors shrink-0"
              title="Jump to video timestamp"
            >
              <span>{ch.timestamp_formatted}</span>
              <ExternalLink className="w-3 h-3" />
            </a>

            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h4 className="font-serif font-bold text-sm text-foreground">{ch.title}</h4>
                <span className="font-mono text-[10px] text-muted-foreground border border-foreground/30 px-1">
                  Segment #{ch.source_segment_id}
                </span>
              </div>
              {ch.summary && (
                <p className="font-body text-xs text-muted-foreground mt-1 leading-relaxed">
                  {ch.summary}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
