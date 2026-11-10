"use client";

import { ShieldCheck, Cpu, Zap, Activity } from "lucide-react";

export default function CostAndQualityBadge() {
  return (
    <div className="border border-foreground bg-muted/20 p-3 mb-6">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
        <div className="flex items-center gap-2 border-r border-foreground/20 pr-2">
          <Cpu className="w-4 h-4 text-accent shrink-0" />
          <div>
            <div className="text-[10px] uppercase text-muted-foreground">Deep Engine</div>
            <div className="font-bold text-foreground">gpt-oss-120b</div>
          </div>
        </div>

        <div className="flex items-center gap-2 border-r border-foreground/20 pr-2">
          <Zap className="w-4 h-4 text-accent shrink-0" />
          <div>
            <div className="text-[10px] uppercase text-muted-foreground">Fast Engine</div>
            <div className="font-bold text-foreground">gpt-oss-20b</div>
          </div>
        </div>

        <div className="flex items-center gap-2 border-r border-foreground/20 pr-2">
          <ShieldCheck className="w-4 h-4 text-green-700 shrink-0" />
          <div>
            <div className="text-[10px] uppercase text-muted-foreground">Hallucination Rate</div>
            <div className="font-bold text-green-700">0.0% Grounded</div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-accent shrink-0" />
          <div>
            <div className="text-[10px] uppercase text-muted-foreground">Execution Queue</div>
            <div className="font-bold text-foreground">Redis ARQ + SSE</div>
          </div>
        </div>
      </div>
    </div>
  );
}
