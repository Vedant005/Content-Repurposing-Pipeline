import { create } from "zustand";
import { persist } from "zustand/middleware";

interface Results {
  blog: string;
  twitter: string;
  linkedin: string;
}

interface PipelineState {
  results: Results | null;
  videoUrl: string;
  isHistoryVisible: boolean;
  setResults: (results: Results | null) => void;
  setVideoUrl: (url: string) => void;
  setIsHistoryVisible: (isVisible: boolean) => void;
  clearState: () => void;
}

export const usePipelineStore = create<PipelineState>()(
  persist(
    (set) => ({
      results: null,
      videoUrl: "",
      isHistoryVisible: true,
      setResults: (results) => set({ results }),
      setVideoUrl: (videoUrl) => set({ videoUrl }),
      setIsHistoryVisible: (isHistoryVisible) => set({ isHistoryVisible }),
      clearState: () => set({ results: null, videoUrl: "" }),
    }),
    {
      name: "pipeline-storage",
    },
  ),
);
