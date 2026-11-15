import React from "react";
import {
  Activity,
  AlertTriangle,
  Radio,
  ShieldCheck,
} from "lucide-react";

export default function StatusBanner({ isAnomaly, latestFrame, isStreaming }) {
  if (!isStreaming && !latestFrame) {
    return (
      <div className="bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl p-4 shadow-card dark:shadow-card-dark flex flex-wrap items-center justify-between gap-4 transition-colors">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-lg bg-paper-100 dark:bg-obsidian-800 border border-paper-300 dark:border-obsidian-700 flex items-center justify-center text-paper-500 dark:text-obsidian-400">
            <Radio className="w-5 h-5 text-amber-600 dark:text-amber-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-sm font-bold text-paper-900 dark:text-obsidian-100">
                Hardware Node Standby — Awaiting Telemetry
              </h4>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-paper-100 dark:bg-obsidian-800 text-paper-600 dark:text-obsidian-300 border border-paper-200 dark:border-obsidian-700 font-semibold">
                IDLE
              </span>
            </div>
            <p className="text-xs text-paper-500 dark:text-obsidian-400 mt-0.5 font-mono">
              Click <strong className="text-cognac-600 dark:text-cognac-400">"Live ESP32"</strong> above to bind USB serial or <strong className="text-arctic-600 dark:text-arctic-400">"Simulate Replay"</strong> to evaluate against 6 synthetic fault suites.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono text-paper-500 dark:text-obsidian-400">
          <span className="w-2 h-2 rounded-full bg-paper-400 dark:bg-obsidian-600" />
          <span>Buffer: 0 frames</span>
        </div>
      </div>
    );
  }

  if (isAnomaly) {
    const trigger = latestFrame?.trigger || "Hybrid Ensemble Breach";
    const score = Number(latestFrame?.hybrid_score || 0).toFixed(2);
    const temp = Number(latestFrame?.temperature || 0).toFixed(1);
    const hum = Number(latestFrame?.humidity || 0).toFixed(1);

    return (
      <div className="bg-crimson-500/10 dark:bg-crimson-950/30 border-2 border-crimson-500 rounded-xl p-4 shadow-card dark:shadow-card-dark flex flex-wrap items-center justify-between gap-4 animate-pulse-subtle transition-colors">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-lg bg-crimson-500/20 border border-crimson-500/50 flex items-center justify-center text-crimson-600 dark:text-crimson-400">
            <AlertTriangle className="w-6 h-6 stroke-[2.2]" />
          </div>
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="text-sm font-bold text-crimson-800 dark:text-crimson-200 tracking-wide">
                TELEMETRY ANOMALY DETECTED IN INDOOR CLIMATE
              </h4>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-crimson-600 text-white uppercase tracking-wider">
                {trigger}
              </span>
            </div>
            <p className="text-xs text-crimson-700 dark:text-crimson-300 mt-1 font-mono">
              Live Reading: <strong className="text-crimson-900 dark:text-white font-bold">{temp} °C</strong> / <strong className="text-crimson-900 dark:text-white font-bold">{hum}% RH</strong> • Combined Severity Score: <strong className="text-crimson-900 dark:text-white font-bold">{score}</strong> (Exceeds safety envelope)
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-crimson-500 animate-ping" />
          <span className="text-xs font-mono font-bold text-crimson-700 dark:text-crimson-400 uppercase tracking-wider">
            Active Incident
          </span>
        </div>
      </div>
    );
  }

  // Nominal / Healthy State
  const ifScore = latestFrame?.iforest_score !== undefined
    ? Number(latestFrame.iforest_score).toFixed(4)
    : "-0.0564";
  const ewmaResidual = latestFrame?.temp_ewma_residual !== undefined
    ? Number(latestFrame.temp_ewma_residual).toFixed(2)
    : "0.04";

  return (
    <div className="bg-sage-500/10 dark:bg-sage-950/20 border border-sage-500/30 rounded-xl p-4 shadow-card dark:shadow-card-dark flex flex-wrap items-center justify-between gap-4 transition-colors">
      <div className="flex items-center gap-3.5">
        <div className="w-10 h-10 rounded-lg bg-sage-500/20 border border-sage-500/40 flex items-center justify-center text-sage-600 dark:text-sage-400">
          <ShieldCheck className="w-6 h-6 stroke-[2.2]" />
        </div>
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="text-sm font-bold text-sage-900 dark:text-sage-200">
              NOMINAL INDOOR CLIMATE ENVELOPE
            </h4>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-sage-500/20 text-sage-800 dark:text-sage-300 border border-sage-500/30 uppercase tracking-wider">
              SYSTEM HEALTHY
            </span>
          </div>
          <p className="text-xs text-sage-700 dark:text-sage-300 mt-1 font-mono">
            Cauchy EWMA adaptive baseline stable (Δ: {ewmaResidual} °C) • Isolation Forest score: {ifScore} (within -0.2166 threshold).
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs font-mono text-sage-700 dark:text-sage-400">
        <Activity className="w-4 h-4 animate-pulse text-sage-600 dark:text-sage-400" />
        <span>0.5 Hz Stream Active</span>
      </div>
    </div>
  );
}
