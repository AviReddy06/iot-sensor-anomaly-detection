import React from "react";
import {
  Moon,
  Play,
  RefreshCw,
  Square,
  Sun,
  Volume2,
  VolumeX,
} from "lucide-react";

export default function Header({
  activeTab,
  onStartSerial,
  onStartSimulation,
  onStopStream,
  isStreaming,
  onRefresh,
  theme,
  onToggleTheme,
  audioAlerts,
  onToggleAudio,
  isRefreshing,
}) {
  const titles = {
    overview: {
      heading: "System Cockpit",
      subheading: "Unsupervised Drift-Resilient Anomaly Detection for Indoor Climate",
    },
    live: {
      heading: "Real-Time Telemetry Monitor",
      subheading: "Continuous Dual-Trace Oscilloscope & Anomaly State Space",
    },
    analytics: {
      heading: "Dataset Evaluation & Diagnostics",
      subheading: "Cross-Fault Confusion Matrices, Recall Breakdown & CSV Feature Extraction",
    },
    settings: {
      heading: "Parameter Tuning & Alert Dispatch",
      subheading: "Isolation Forest Cutoffs, EWMA Gating & Multi-Channel Notifications",
    },
  };

  const currentMeta = titles[activeTab] || {
    heading: "IoT Climate Hub",
    subheading: "ESP32 + DHT11 Sensor Telemetry",
  };

  return (
    <header className="h-16 border-b border-paper-200 dark:border-obsidian-800 bg-white/90 dark:bg-obsidian-900/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-20 transition-colors duration-200">
      {/* Title & Context */}
      <div className="flex items-center gap-4 min-w-0">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-sm font-bold text-paper-900 dark:text-obsidian-100 tracking-tight">
              {currentMeta.heading}
            </h1>
            <span className="hidden sm:inline-flex text-[10px] font-mono px-2 py-0.5 rounded bg-paper-200/80 dark:bg-obsidian-800 text-paper-600 dark:text-obsidian-300 border border-paper-300 dark:border-obsidian-700">
              0.5 Hz Cadence
            </span>
          </div>
          <p className="text-[11px] text-paper-500 dark:text-obsidian-400 font-mono truncate hidden md:block">
            {currentMeta.subheading}
          </p>
        </div>
      </div>

      {/* Stream Controls & Utilities */}
      <div className="flex items-center gap-2">
        {/* Stream Actions */}
        {isStreaming ? (
          <button
            onClick={onStopStream}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold bg-crimson-600 hover:bg-crimson-700 text-white transition-all shadow-sm btn-action"
            title="Terminate active telemetry acquisition"
          >
            <Square className="w-3.5 h-3.5 fill-current" />
            <span>Halt Stream</span>
          </button>
        ) : (
          <div className="flex items-center gap-2">
            <button
              onClick={onStartSerial}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold bg-cognac-600 hover:bg-cognac-700 text-white transition-all shadow-sm btn-action"
              title="Stream live readings directly from connected ESP32 node"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Live ESP32</span>
            </button>

            <button
              onClick={onStartSimulation}
              className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-paper-100 dark:bg-obsidian-800 hover:bg-paper-200 dark:hover:bg-obsidian-750 text-paper-700 dark:text-obsidian-200 border border-paper-300 dark:border-obsidian-700 transition shadow-sm btn-action"
              title="Replay 6-fault evaluation test suite"
            >
              <span>Simulate Replay</span>
            </button>
          </div>
        )}

        {/* Audio Alert Chime Toggle */}
        <button
          onClick={onToggleAudio}
          className={`p-2 rounded-lg border transition ${
            audioAlerts
              ? "bg-cognac-500/15 border-cognac-500/30 text-cognac-700 dark:text-cognac-400"
              : "bg-paper-100 dark:bg-obsidian-850 border-paper-300 dark:border-obsidian-750 text-paper-400 dark:text-obsidian-400 hover:text-paper-700 dark:hover:text-obsidian-200"
          }`}
          title={audioAlerts ? "Audio alarm tone enabled" : "Audio alarm tone muted"}
        >
          {audioAlerts ? (
            <Volume2 className="w-4 h-4 stroke-[2]" />
          ) : (
            <VolumeX className="w-4 h-4 stroke-[2]" />
          )}
        </button>

        {/* Theme Toggle (Dark / Light) */}
        <button
          onClick={onToggleTheme}
          className="p-2 rounded-lg bg-paper-100 dark:bg-obsidian-850 border border-paper-300 dark:border-obsidian-750 text-paper-600 dark:text-obsidian-300 hover:text-paper-900 dark:hover:text-obsidian-100 transition shadow-sm"
          title={theme === "dark" ? "Switch to Light Mode (Warm Alabaster)" : "Switch to Dark Mode (Obsidian Basalt)"}
        >
          {theme === "dark" ? (
            <Sun className="w-4 h-4 text-cognac-400 stroke-[2]" />
          ) : (
            <Moon className="w-4 h-4 text-obsidian-700 stroke-[2]" />
          )}
        </button>

        {/* Refresh System State Button */}
        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="p-2 rounded-lg bg-paper-100 dark:bg-obsidian-850 border border-paper-300 dark:border-obsidian-750 text-paper-600 dark:text-obsidian-300 hover:text-paper-900 dark:hover:text-obsidian-100 transition disabled:opacity-50 shadow-sm"
          title="Refresh server state & buffers"
        >
          <RefreshCw
            className={`w-4 h-4 ${isRefreshing ? "animate-spin text-cognac-600 dark:text-cognac-400" : ""}`}
          />
        </button>
      </div>
    </header>
  );
}
