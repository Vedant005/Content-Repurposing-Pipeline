import { useState } from "react";
import { ArrowRight, Loader2 } from "lucide-react";

interface YouTubeInputProps {
  onSubmit: (url: string) => void;
  isLoading: boolean;
}

const YouTubeInput = ({ onSubmit, isLoading }: YouTubeInputProps) => {
  const [url, setUrl] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) onSubmit(url.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="border-4 border-foreground p-6 md:p-8 bg-background newsprint-texture">
        <label className="font-sans text-xs uppercase tracking-widest font-semibold mb-4 block">
          Paste YouTube URL
        </label>
        <div className="flex flex-col md:flex-row gap-3">
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://youtube.com/watch?v=..."
            className="flex-1 border-b-2 border-foreground bg-transparent px-3 py-3 font-mono text-sm focus-visible:bg-secondary focus-visible:outline-none transition-colors"
            required
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="min-h-[44px] px-8 py-3 bg-foreground text-primary-foreground font-sans text-xs uppercase tracking-widest font-semibold border border-transparent hover:bg-background hover:text-foreground hover:border-foreground transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Processing
              </>
            ) : (
              <>
                Repurpose
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
};

export default YouTubeInput;
