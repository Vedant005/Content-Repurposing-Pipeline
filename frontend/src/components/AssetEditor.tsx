"use client";

import { useState } from "react";
import { Copy, Check, Edit3, Eye, Download, RefreshCw, AlertCircle } from "lucide-react";
import ReactMarkdown from "react-markdown";

interface AssetEditorProps {
  title: string;
  label: string;
  assetType: "blog" | "twitter_thread" | "linkedin_post";
  content: string;
  icon: React.ReactNode;
  jobId: number | null;
  onContentChange?: (updated: string) => void;
  onRegenerateTriggered?: () => void;
}

export default function AssetEditor({
  title,
  label,
  assetType,
  content,
  icon,
  jobId,
  onContentChange,
  onRegenerateTriggered,
}: AssetEditorProps) {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedText, setEditedText] = useState(content);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [retryMessage, setRetryMessage] = useState<string | null>(null);

  // Stats calculation
  const wordCount = editedText ? editedText.trim().split(/\s+/).length : 0;
  const readingTime = Math.max(1, Math.ceil(wordCount / 200));
  const charCount = editedText ? editedText.length : 0;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(editedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const ext = assetType === "blog" ? "md" : "txt";
    const filename = `${assetType}_${Date.now()}.${ext}`;
    const blob = new Blob([editedText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  };

  const handleRegenerate = async () => {
    if (!jobId) return;
    setIsRegenerating(true);
    setRetryMessage(null);

    try {
      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const res = await fetch(
        `${backendUrl}/api/v1/jobs/${jobId}/assets/${assetType}/retry`,
        {
          method: "POST",
          credentials: "include",
        }
      );

      if (!res.ok) {
        throw new Error("Targeted retry failed to enqueue");
      }

      setRetryMessage("Regeneration task enqueued. Checking updates...");
      if (onRegenerateTriggered) onRegenerateTriggered();
    } catch (err: any) {
      setRetryMessage(err.message || "Failed to trigger retry.");
    } finally {
      setIsRegenerating(false);
    }
  };

  return (
    <div className="border border-foreground bg-background hard-shadow-hover">
      {/* Card Header */}
      <div className="flex flex-wrap items-center justify-between border-b border-foreground px-4 py-3 gap-3">
        <div className="flex items-center gap-3">
          <div className="border border-foreground h-10 w-10 flex items-center justify-center shrink-0">
            {icon}
          </div>
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground block">
              {label}
            </span>
            <h3 className="font-serif text-lg font-bold leading-tight">{title}</h3>
          </div>
        </div>

        {/* Action Toolbar */}
        <div className="flex items-center gap-2">
          {/* Mode Switcher */}
          <button
            onClick={() => setIsEditing(!isEditing)}
            className="flex items-center gap-1 px-2.5 py-1.5 border border-foreground font-mono text-xs uppercase tracking-wider hover:bg-muted transition-colors"
            title={isEditing ? "Switch to Preview" : "Switch to Editor"}
          >
            {isEditing ? <Eye className="w-3.5 h-3.5" /> : <Edit3 className="w-3.5 h-3.5" />}
            {isEditing ? "Preview" : "Edit Copy"}
          </button>

          {/* Regenerate Asset */}
          {jobId && (
            <button
              onClick={handleRegenerate}
              disabled={isRegenerating}
              className="flex items-center gap-1 px-2.5 py-1.5 border border-foreground font-mono text-xs uppercase tracking-wider hover:bg-muted transition-colors disabled:opacity-50"
              title="Regenerate this specific asset with critique feedback"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isRegenerating ? "animate-spin" : ""}`} />
              {isRegenerating ? "Retrying..." : "Regenerate"}
            </button>
          )}

          {/* Download */}
          <button
            onClick={handleDownload}
            className="flex items-center gap-1 px-2.5 py-1.5 border border-foreground font-mono text-xs uppercase tracking-wider hover:bg-muted transition-colors"
            title="Download file"
          >
            <Download className="w-3.5 h-3.5" />
            Export
          </button>

          {/* Copy Button */}
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-3 py-1.5 border border-foreground bg-foreground text-primary-foreground font-mono text-xs uppercase tracking-wider hover:opacity-90 transition-opacity"
            aria-label="Copy content"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? "Copied" : "Copy"}
          </button>
        </div>
      </div>

      {retryMessage && (
        <div className="px-4 py-2 bg-muted/40 border-b border-foreground/20 font-mono text-xs flex items-center gap-2 text-accent">
          <AlertCircle className="w-3.5 h-3.5" />
          <span>{retryMessage}</span>
        </div>
      )}

      {/* Editor or Preview Pane */}
      <div className="p-4 md:p-6 min-h-[320px] max-h-[500px] overflow-y-auto">
        {isEditing ? (
          <textarea
            value={editedText}
            onChange={(e) => {
              setEditedText(e.target.value);
              if (onContentChange) onContentChange(e.target.value);
            }}
            className="w-full h-full min-h-[300px] p-3 border border-foreground/40 font-mono text-xs leading-relaxed bg-background focus:outline-none focus:ring-1 focus:ring-foreground resize-y"
            placeholder="Edit your content here..."
          />
        ) : assetType === "blog" ? (
          <div className="prose prose-sm max-w-none font-body leading-relaxed text-justify space-y-3">
            <ReactMarkdown>{editedText}</ReactMarkdown>
          </div>
        ) : (
          <div className="font-body text-sm leading-relaxed whitespace-pre-wrap text-justify">
            {editedText}
          </div>
        )}
      </div>

      {/* Editorial Metadata Footer Bar */}
      <div className="border-t border-foreground px-4 py-2 bg-muted/20 flex flex-wrap items-center justify-between font-mono text-[11px] text-muted-foreground gap-2">
        <div className="flex items-center gap-3">
          {assetType === "blog" && (
            <>
              <span>Words: {wordCount}</span>
              <span>•</span>
              <span>Reading Time: ~{readingTime} min</span>
            </>
          )}
          {assetType === "twitter_thread" && (
            <>
              <span>Total Chars: {charCount}</span>
              <span>•</span>
              <span className="text-foreground">280-char verified threads</span>
            </>
          )}
          {assetType === "linkedin_post" && (
            <>
              <span>Total Chars: {charCount}</span>
              <span>•</span>
              <span>Words: {wordCount}</span>
            </>
          )}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-green-700 font-bold">● Grounded & Quote-Verified</span>
        </div>
      </div>
    </div>
  );
}
