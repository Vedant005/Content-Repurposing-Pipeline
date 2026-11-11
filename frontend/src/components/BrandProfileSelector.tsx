"use client";

import { useState } from "react";
import { Sparkles, Plus, X, Check, BookOpen } from "lucide-react";
import { BrandProfile, usePipelineStore } from "@/store/usePipelineStore";

interface BrandProfileSelectorProps {
  onProfileCreated?: () => void;
}

export default function BrandProfileSelector({ onProfileCreated }: BrandProfileSelectorProps) {
  const { brandProfiles, selectedBrandProfileId, setSelectedBrandProfileId, setBrandProfiles } =
    usePipelineStore();
  const [isOpen, setIsOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form state
  const [brandName, setBrandName] = useState("");
  const [toneGuidelines, setToneGuidelines] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [blogExample, setBlogExample] = useState("");
  const [twitterExample, setTwitterExample] = useState("");
  const [linkedinExample, setLinkedinExample] = useState("");
  const [error, setError] = useState<string | null>(null);

  const selectedProfile = brandProfiles.find((p) => p.id === selectedBrandProfileId);

  const handleCreateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!brandName.trim()) {
      setError("Please provide a brand or persona name.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const payload = {
        brand_name: brandName.trim(),
        tone_guidelines: toneGuidelines.trim() || undefined,
        target_audience: targetAudience.trim() || undefined,
        few_shot_examples: {
          blog: blogExample.trim() || undefined,
          twitter: twitterExample.trim() || undefined,
          linkedin: linkedinExample.trim() || undefined,
        },
      };

      const backendUrl =
        process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
      const res = await fetch(`${backendUrl}/api/v1/brand-profiles`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Failed to save brand profile");
      }

      const created: BrandProfile = await res.json();
      setBrandProfiles([created, ...brandProfiles]);
      setSelectedBrandProfileId(created.id);
      setIsOpen(false);

      // Reset form
      setBrandName("");
      setToneGuidelines("");
      setTargetAudience("");
      setBlogExample("");
      setTwitterExample("");
      setLinkedinExample("");

      if (onProfileCreated) onProfileCreated();
    } catch (err: any) {
      setError(err.message || "Failed to save profile.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mb-6">
      <div className="flex flex-wrap items-center justify-between gap-3 border border-foreground/20 p-3 bg-muted/20">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-accent" />
          <span className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
            Brand Persona:
          </span>
          <select
            value={selectedBrandProfileId || ""}
            onChange={(e) => {
              const val = e.target.value ? Number(e.target.value) : null;
              setSelectedBrandProfileId(val);
            }}
            className="font-mono text-xs uppercase tracking-wider bg-background border border-foreground px-2 py-1 focus:outline-none focus:ring-1 focus:ring-foreground"
          >
            <option value="">(Default Neutral Editorial)</option>
            {brandProfiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.brand_name}
              </option>
            ))}
          </select>
        </div>

        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="flex items-center gap-1 font-mono text-xs uppercase tracking-wider px-2 py-1 border border-foreground hover:bg-foreground hover:text-primary-foreground transition-colors"
        >
          <Plus className="w-3 h-3" />
          Add Brand Voice
        </button>
      </div>

      {selectedProfile && (
        <div className="mt-2 text-xs font-mono text-muted-foreground border-l-2 border-accent pl-3 py-0.5">
          <span>Active Guidelines: </span>
          <span className="text-foreground">{selectedProfile.tone_guidelines || "Custom tone rules"}</span>
        </div>
      )}

      {/* Modal Dialog */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-xl border-2 border-foreground bg-background p-6 shadow-[8px_8px_0px_0px_hsl(0_0%_7%)] max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b border-foreground pb-3 mb-4">
              <div className="flex items-center gap-2">
                <BookOpen className="w-5 h-5 text-accent" />
                <h3 className="font-serif text-xl font-bold">Add Custom Brand Voice</h3>
              </div>
              <button
                onClick={() => setIsOpen(false)}
                className="p-1 border border-foreground hover:bg-foreground hover:text-primary-foreground transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateProfile} className="space-y-4">
              {error && (
                <div className="p-2 border border-red-500 bg-red-50 text-red-600 font-mono text-xs">
                  {error}
                </div>
              )}

              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1">
                  Brand / Creator Name *
                </label>
                <input
                  type="text"
                  required
                  value={brandName}
                  onChange={(e) => setBrandName(e.target.value)}
                  placeholder="e.g. Acme Tech Insights"
                  className="w-full p-2 border border-foreground font-body text-sm bg-background focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1">
                  Tone Guidelines (Keywords & Rules)
                </label>
                <input
                  type="text"
                  value={toneGuidelines}
                  onChange={(e) => setToneGuidelines(e.target.value)}
                  placeholder="e.g. Data-first, no emojis, punchy sentences, authoritative"
                  className="w-full p-2 border border-foreground font-body text-sm bg-background focus:outline-none"
                />
              </div>

              <div>
                <label className="block font-mono text-xs uppercase tracking-wider text-muted-foreground mb-1">
                  Target Audience
                </label>
                <input
                  type="text"
                  value={targetAudience}
                  onChange={(e) => setTargetAudience(e.target.value)}
                  placeholder="e.g. Senior Software Engineers, Tech Founders"
                  className="w-full p-2 border border-foreground font-body text-sm bg-background focus:outline-none"
                />
              </div>

              <div className="border-t border-foreground/20 pt-3">
                <span className="block font-mono text-xs uppercase tracking-widest text-accent mb-2">
                  Few-Shot Writing Samples (Optional)
                </span>

                <div className="space-y-3">
                  <div>
                    <label className="block font-mono text-[11px] text-muted-foreground mb-0.5">
                      Sample Tweet Hook:
                    </label>
                    <input
                      type="text"
                      value={twitterExample}
                      onChange={(e) => setTwitterExample(e.target.value)}
                      placeholder="e.g. 1/ The biggest lie in distributed systems is..."
                      className="w-full p-1.5 border border-foreground/60 font-body text-xs bg-background focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block font-mono text-[11px] text-muted-foreground mb-0.5">
                      Sample Blog Intro:
                    </label>
                    <textarea
                      rows={2}
                      value={blogExample}
                      onChange={(e) => setBlogExample(e.target.value)}
                      placeholder="Paste 1-2 paragraphs of your typical blog voice..."
                      className="w-full p-1.5 border border-foreground/60 font-body text-xs bg-background focus:outline-none"
                    />
                  </div>

                  <div>
                    <label className="block font-mono text-[11px] text-muted-foreground mb-0.5">
                      Sample LinkedIn Opening:
                    </label>
                    <input
                      type="text"
                      value={linkedinExample}
                      onChange={(e) => setLinkedinExample(e.target.value)}
                      placeholder="e.g. Most CTOs look at metrics the wrong way."
                      className="w-full p-1.5 border border-foreground/60 font-body text-xs bg-background focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-foreground">
                <button
                  type="button"
                  onClick={() => setIsOpen(false)}
                  className="px-4 py-2 border border-foreground font-mono text-xs uppercase tracking-wider hover:bg-muted"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 border border-foreground bg-foreground text-primary-foreground font-mono text-xs uppercase tracking-wider hover:opacity-90 flex items-center gap-1.5 disabled:opacity-50"
                >
                  {isSubmitting ? (
                    "Saving..."
                  ) : (
                    <>
                      <Check className="w-3.5 h-3.5" /> Save Persona
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
