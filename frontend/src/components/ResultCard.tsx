import { Copy, Check } from "lucide-react";
import { useState } from "react";

interface ResultCardProps {
  title: string;
  label: string;
  content: string;
  icon: React.ReactNode;
}

const ResultCard = ({ title, label, content, icon }: ResultCardProps) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-foreground bg-background hard-shadow-hover">
      {/* Card header */}
      <div className="flex items-center justify-between border-b border-foreground px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="border border-foreground h-10 w-10 flex items-center justify-center">
            {icon}
          </div>
          <div>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground block">
              {label}
            </span>
            <h3 className="font-serif text-lg font-bold leading-tight">
              {title}
            </h3>
          </div>
        </div>
        <button
          onClick={handleCopy}
          className="min-h-[44px] min-w-[44px] flex items-center justify-center border border-foreground hover:bg-foreground hover:text-primary-foreground transition-colors"
          aria-label="Copy content"
        >
          {copied ? (
            <Check className="h-4 w-4" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </button>
      </div>

      {/* Card content */}
      <div className="p-4 md:p-6 max-h-[400px] overflow-y-auto">
        <div className="font-body text-sm leading-relaxed whitespace-pre-wrap text-justify">
          {content}
        </div>
      </div>
    </div>
  );
};

export default ResultCard;
