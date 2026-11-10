import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface ChapterItem {
  timestamp_seconds: number;
  timestamp_formatted: string;
  title: string;
  summary: string;
  source_segment_id: number;
}

export interface AssetDetail {
  id: number;
  asset_type: "blog" | "twitter_thread" | "linkedin_post" | "chapters";
  status: "pending" | "generating" | "completed" | "failed";
  content: any;
  validation_errors?: any;
  critique_score?: number;
  retry_count: number;
}

export interface BrandProfile {
  id: number;
  session_id: string;
  brand_name: string;
  tone_guidelines?: string;
  target_audience?: string;
  few_shot_examples?: Record<string, string>;
  created_at: string;
}

export interface PipelineResults {
  blog: string;
  twitter: string;
  linkedin: string;
  chapters?: ChapterItem[];
}

interface PipelineState {
  results: PipelineResults | null;
  videoUrl: string;
  activeJobId: number | null;
  isHistoryVisible: boolean;
  activeTab: "blog" | "twitter" | "linkedin" | "chapters";
  brandProfiles: BrandProfile[];
  selectedBrandProfileId: number | null;
  setResults: (results: PipelineResults | null) => void;
  setVideoUrl: (url: string) => void;
  setActiveJobId: (id: number | null) => void;
  setIsHistoryVisible: (isVisible: boolean) => void;
  setActiveTab: (tab: "blog" | "twitter" | "linkedin" | "chapters") => void;
  setBrandProfiles: (profiles: BrandProfile[]) => void;
  setSelectedBrandProfileId: (id: number | null) => void;
  clearState: () => void;
}

export const usePipelineStore = create<PipelineState>()(
  persist(
    (set) => ({
      results: null,
      videoUrl: "",
      activeJobId: null,
      isHistoryVisible: true,
      activeTab: "blog",
      brandProfiles: [],
      selectedBrandProfileId: null,
      setResults: (results) => set({ results }),
      setVideoUrl: (videoUrl) => set({ videoUrl }),
      setActiveJobId: (activeJobId) => set({ activeJobId }),
      setIsHistoryVisible: (isHistoryVisible) => set({ isHistoryVisible }),
      setActiveTab: (activeTab) => set({ activeTab }),
      setBrandProfiles: (brandProfiles) => set({ brandProfiles }),
      setSelectedBrandProfileId: (selectedBrandProfileId) => set({ selectedBrandProfileId }),
      clearState: () => set({ results: null, videoUrl: "", activeJobId: null }),
    }),
    {
      name: "pipeline-storage-v2",
    },
  ),
);
