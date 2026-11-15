import React from "react";
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  Cpu,
  Database,
  GitBranch,
  Layers,
  Radio,
  Shield,
  ShieldCheck,
  Sliders,
} from "lucide-react";
import MetricCard from "../components/MetricCard";

export default function OverviewView({
  benchmarks,
  serialStatus,
  onNavigate,
  onStartSimulation,
}) {
  const evalMetrics =
    benchmarks?.datasets?.eval_suite?.["Hybrid (IF + EWMA-Z)"] || {};
  const pilotMetrics =
    benchmarks?.datasets?.pilot?.["Hybrid (IF + EWMA-Z)"] || {};

  const activePort =
    serialStatus?.current_port || serialStatus?.detected_esp32_port || "COM19";

  return (
    <div className="space-y-6">
      {/* Editorial System Header Banner */}
      <div className="bg-white dark:bg-obsidian-900 border border-paper-200 dark:border-obsidian-800 rounded-2xl p-6 sm:p-7 shadow-card dark:shadow-card-dark relative overflow-hidden transition-colors">
        <div className="relative z-10 max-w-4xl">
          <div className="inline-flex items-center gap-2 px-2.5 py-1 rounded-full bg-cognac-500/10 dark:bg-cognac-500/15 border border-cognac-500/25 text-cognac-700 dark:text-cognac-400 text-xs font-mono font-semibold mb-3">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Unsupervised Environmental Anomaly Intelligence</span>
          </div>

          <h2 className="text-2xl sm:text-3xl font-extrabold text-paper-900 dark:text-white tracking-tight">
            AI-Driven Indoor Climate Telemetry & Anomaly Detection
          </h2>

          <p className="text-sm text-paper-600 dark:text-obsidian-300 mt-2.5 leading-relaxed">
            Full-stack continuous environmental monitoring for edge{" "}
            <strong className="text-paper-900 dark:text-white font-semibold">ESP32 + DHT11</strong> sensor nodes over USB serial.
            Combines causal rate-gated Cauchy EWMA baselining with an in-sample calibrated Isolation Forest ensemble to achieve multi-day drift resilience with zero false alarms.
          </p>

          <div className="flex flex-wrap items-center gap-3 mt-5">
            <button
              onClick={() => onNavigate("live")}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold bg-cognac-600 hover:bg-cognac-700 text-white transition shadow-sm btn-action"
            >
              <Activity className="w-4 h-4 stroke-[2.2]" />
              <span>Launch Live Monitor</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={() => onNavigate("analytics")}
              className="flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold bg-paper-100 dark:bg-obsidian-800 hover:bg-paper-200 dark:hover:bg-obsidian-750 text-paper-700 dark:text-obsidian-200 border border-paper-300 dark:border-obsidian-700 transition shadow-sm btn-action"
            >
              <Database className="w-4 h-4 text-arctic-600 dark:text-arctic-400" />
              <span>Inspect Evaluation Datasets</span>
            </button>

            <button
              onClick={() => onNavigate("settings")}
              className="flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium text-paper-500 dark:text-obsidian-400 hover:text-paper-900 dark:hover:text-obsidian-200 transition"
            >
              <Sliders className="w-4 h-4" />
              <span>Calibrate Thresholds</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Core KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Hardware Node"
          value={activePort}
          subtitle="ESP32 @ 115,200 baud, 0.5 Hz"
          icon={Cpu}
          color="cognac"
          trend="DTR/RTS Safe"
        />
        <MetricCard
          title="Clean Baseline"
          value="34,374"
          subtitle="9 sessions (< Nov 1, 2026)"
          icon={Layers}
          color="arctic"
          trend="12 Features"
        />
        <MetricCard
          title="Physical Pilot F1"
          value={pilotMetrics.f1 ? `${(pilotMetrics.f1 * 100).toFixed(1)}%` : "93.2%"}
          subtitle="0 false alarms on 2,581 normal rows"
          icon={CheckCircle2}
          color="sage"
          trend="0 FP"
        />
        <MetricCard
          title="Eval Suite F1"
          value={evalMetrics.f1 ? `${(evalMetrics.f1 * 100).toFixed(1)}%` : "96.8%"}
          subtitle="6/6 synthetic fault categories caught"
          icon={Activity}
          color="amber"
          trend="0/57 Live FP"
        />
      </div>

      {/* Detection Pipeline & Division of Labor */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Core Ensemble Architecture (2 cols) */}
        <div className="lg:col-span-2 bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl p-5 shadow-card dark:shadow-card-dark space-y-4 transition-colors">
          <div className="flex items-center justify-between border-b border-paper-200 dark:border-obsidian-800 pb-3">
            <div className="flex items-center gap-2">
              <GitBranch className="w-4 h-4 text-cognac-600 dark:text-cognac-400" />
              <h3 className="text-sm font-bold text-paper-900 dark:text-obsidian-100 font-mono uppercase tracking-wider">
                Dual-Detector Ensemble Architecture
              </h3>
            </div>
            <span className="text-[10px] font-mono text-paper-500 dark:text-obsidian-400 bg-paper-100 dark:bg-obsidian-800 px-2 py-0.5 rounded border border-paper-200 dark:border-obsidian-700">
              Division of Labor
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Component 1: Isolation Forest */}
            <div className="p-4 rounded-xl bg-paper-50 dark:bg-obsidian-900 border border-paper-200 dark:border-obsidian-800 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-cognac-700 dark:text-cognac-400 font-mono">
                  Gated Isolation Forest
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cognac-500/15 text-cognac-700 dark:text-cognac-400 font-semibold">
                  200 iTrees
                </span>
              </div>
              <p className="text-xs text-paper-600 dark:text-obsidian-300 leading-relaxed">
                Calibrated on 34,374 clean training samples. Specializes in steep thermal transients, high-frequency sensor spikes, and chatter noise. Employs a 3-of-5 persistence filter to suppress single-point ADC jitter.
              </p>
              <div className="pt-2 border-t border-paper-200 dark:border-obsidian-800 text-[11px] font-mono flex items-center justify-between text-paper-500 dark:text-obsidian-400">
                <span>Chatter Noise Recall:</span>
                <strong className="text-sage-600 dark:text-sage-400 font-bold">100.0%</strong>
              </div>
            </div>

            {/* Component 2: Cauchy EWMA */}
            <div className="p-4 rounded-xl bg-paper-50 dark:bg-obsidian-900 border border-paper-200 dark:border-obsidian-800 space-y-2.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-arctic-700 dark:text-arctic-400 font-mono">
                  Adaptive Cauchy EWMA-Z
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-arctic-500/15 text-arctic-700 dark:text-arctic-400 font-semibold">
                  3.5σ Cutoff
                </span>
              </div>
              <p className="text-xs text-paper-600 dark:text-obsidian-300 leading-relaxed">
                Maintains a 2,400s half-life baseline with rate gating (|dT/dt| &lt; 0.05°C/s). Bridges tree detector blind spots on zero-derivative steady state plateaus, offsets, and persistent drift.
              </p>
              <div className="pt-2 border-t border-paper-200 dark:border-obsidian-800 text-[11px] font-mono flex items-center justify-between text-paper-500 dark:text-obsidian-400">
                <span>Offset Plateau Recall:</span>
                <strong className="text-sage-600 dark:text-sage-400 font-bold">100.0%</strong>
              </div>
            </div>
          </div>

          {/* Logical Union Callout */}
          <div className="p-4 rounded-xl bg-paper-50 dark:bg-obsidian-900/90 border border-cognac-500/25 flex flex-wrap items-center justify-between gap-3">
            <div className="space-y-0.5 min-w-0">
              <h4 className="text-xs font-bold text-paper-900 dark:text-white font-mono uppercase tracking-wide flex items-center gap-2">
                <Shield className="w-3.5 h-3.5 text-cognac-600 dark:text-cognac-400" />
                Hybrid Logical Union (IF | Adaptive EWMA-Z)
              </h4>
              <p className="text-xs text-paper-600 dark:text-obsidian-400">
                Maintains 0 false alarms on warm ambient baseline drift days (28.2–29.7 °C) where static Z-Score suffers 100% false alarm rate.
              </p>
            </div>
            <div className="text-right">
              <span className="text-sm font-bold font-mono text-sage-700 dark:text-sage-400 bg-white dark:bg-obsidian-850 px-2.5 py-1 rounded border border-paper-200 dark:border-obsidian-700">
                Ensemble F1: 0.968
              </span>
            </div>
          </div>
        </div>

        {/* Evaluation Stream Replay Launcher (1 col) */}
        <div className="bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl p-5 shadow-card dark:shadow-card-dark space-y-4 flex flex-col justify-between transition-colors">
          <div>
            <div className="flex items-center gap-2 mb-2 border-b border-paper-200 dark:border-obsidian-800 pb-3">
              <Radio className="w-4 h-4 text-arctic-600 dark:text-arctic-400" />
              <h3 className="text-sm font-bold text-paper-900 dark:text-obsidian-100 font-mono uppercase tracking-wider">
                Evaluation Stream Replay
              </h3>
            </div>
            <p className="text-xs text-paper-500 dark:text-obsidian-400 leading-relaxed">
              Test detection algorithms against real historical recordings and synthetic fault injection sets with zero hardware connected.
            </p>
          </div>

          <div className="space-y-2.5">
            <button
              onClick={() => {
                onNavigate("live");
                onStartSimulation("eval_suite");
              }}
              className="w-full flex items-center justify-between p-3 rounded-lg bg-paper-50 dark:bg-obsidian-900 hover:bg-paper-100 dark:hover:bg-obsidian-800 text-paper-900 dark:text-white border border-paper-200 dark:border-obsidian-750 transition text-xs font-medium group"
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-cognac-600 group-hover:animate-ping" />
                <span className="font-semibold">Replay 6-Fault Evaluation Suite</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-paper-400 dark:text-obsidian-400 group-hover:translate-x-1 transition" />
            </button>

            <button
              onClick={() => {
                onNavigate("live");
                onStartSimulation("pilot");
              }}
              className="w-full flex items-center justify-between p-3 rounded-lg bg-paper-50 dark:bg-obsidian-900 hover:bg-paper-100 dark:hover:bg-obsidian-800 text-paper-900 dark:text-white border border-paper-200 dark:border-obsidian-750 transition text-xs font-medium group"
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-arctic-500 group-hover:animate-ping" />
                <span className="font-semibold">Replay Physical Pilot (3k rows)</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-paper-400 dark:text-obsidian-400 group-hover:translate-x-1 transition" />
            </button>

            <button
              onClick={() => {
                onNavigate("live");
                onStartSimulation("test");
              }}
              className="w-full flex items-center justify-between p-3 rounded-lg bg-paper-50 dark:bg-obsidian-900 hover:bg-paper-100 dark:hover:bg-obsidian-800 text-paper-900 dark:text-white border border-paper-200 dark:border-obsidian-750 transition text-xs font-medium group"
            >
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-sage-500 group-hover:animate-ping" />
                <span className="font-semibold">Replay Thermal Spike Test Set</span>
              </div>
              <ArrowRight className="w-3.5 h-3.5 text-paper-400 dark:text-obsidian-400 group-hover:translate-x-1 transition" />
            </button>
          </div>

          {/* Hardware Pinout Specs */}
          <div className="p-3 rounded-lg bg-paper-50 dark:bg-obsidian-900/60 border border-paper-200 dark:border-obsidian-800 text-[11px] font-mono space-y-1.5 text-paper-500 dark:text-obsidian-400">
            <div className="flex justify-between">
              <span>Hardware Link:</span>
              <span className="text-paper-900 dark:text-white font-semibold">ESP32-WROOM-32</span>
            </div>
            <div className="flex justify-between">
              <span>Sensor Interface:</span>
              <span className="text-arctic-600 dark:text-arctic-400">GPIO 4 (DHT11 Data)</span>
            </div>
            <div className="flex justify-between">
              <span>UART Sampling:</span>
              <span className="text-cognac-600 dark:text-cognac-400">115,200 baud • 0.5 Hz</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
