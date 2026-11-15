import React from "react";
import {
  Activity,
  BarChart3,
  Cpu,
  Layers,
  Radio,
  Sliders,
  Terminal,
  Zap,
} from "lucide-react";

export default function Sidebar({
  activeTab,
  setActiveTab,
  wsStatus,
  serialStatus,
}) {
  const navItems = [
    {
      id: "overview",
      label: "System Cockpit",
      sublabel: "Architecture & Metrics",
      icon: Layers,
    },
    {
      id: "live",
      label: "Live Telemetry",
      sublabel: "Dual Trace & State Space",
      icon: Activity,
    },
    {
      id: "analytics",
      label: "Dataset Evaluation",
      sublabel: "Confusion Matrix & Faults",
      icon: BarChart3,
    },
    {
      id: "settings",
      label: "Tuning & Alerts",
      sublabel: "Thresholds & Webhooks",
      icon: Sliders,
    },
  ];

  const isConnected = wsStatus === "connected";
  const isStreaming = Boolean(serialStatus?.is_streaming);
  const activePort = serialStatus?.current_port || serialStatus?.detected_esp32_port || "COM19";

  return (
    <aside className="w-64 flex-shrink-0 bg-paper-100 dark:bg-obsidian-900 border-r border-paper-200 dark:border-obsidian-800 flex flex-col justify-between select-none z-30 transition-colors duration-200">
      <div>
        {/* Brand Banner */}
        <div className="p-4 border-b border-paper-200 dark:border-obsidian-800/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-white dark:bg-obsidian-850 border border-paper-300 dark:border-obsidian-750 flex items-center justify-center text-cognac-600 dark:text-cognac-500 shadow-sm">
              <Cpu className="w-5 h-5 stroke-[2.2]" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-bold text-sm tracking-tight text-paper-900 dark:text-obsidian-100">
                  AetherSense
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cognac-500/10 text-cognac-700 dark:text-cognac-400 border border-cognac-500/20 font-semibold">
                  v2.0
                </span>
              </div>
              <p className="text-[11px] text-paper-500 dark:text-obsidian-400 font-mono truncate">
                ESP32 + DHT11 Anomaly Hub
              </p>
            </div>
          </div>
        </div>

        {/* Primary Navigation */}
        <nav className="p-3 space-y-1">
          <div className="px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider text-paper-500 dark:text-obsidian-500 font-semibold">
            Control Center
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full group text-left px-3 py-2.5 rounded-lg text-xs transition-all duration-150 flex items-center gap-3 border ${
                  isActive
                    ? "bg-white dark:bg-obsidian-800 text-paper-900 dark:text-obsidian-50 border-paper-300 dark:border-obsidian-700 shadow-sm"
                    : "text-paper-600 dark:text-obsidian-300 hover:text-paper-900 dark:hover:text-white hover:bg-paper-200/60 dark:hover:bg-obsidian-850 border-transparent"
                }`}
              >
                <div
                  className={`p-1.5 rounded-md transition-colors ${
                    isActive
                      ? "bg-cognac-600 text-white font-bold shadow-sm"
                      : "bg-paper-200/70 dark:bg-obsidian-850 text-paper-600 dark:text-obsidian-400 group-hover:text-paper-900 dark:group-hover:text-obsidian-200 border border-paper-300 dark:border-obsidian-750"
                  }`}
                >
                  <Icon className="w-4 h-4 stroke-[2]" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold tracking-tight">{item.label}</div>
                  <div className="text-[10px] text-paper-500 dark:text-obsidian-400 font-mono truncate">
                    {item.sublabel}
                  </div>
                </div>
                {isActive && (
                  <span className="w-1.5 h-1.5 rounded-full bg-cognac-600 dark:bg-cognac-400" />
                )}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Hardware Ticker & Author Attribution */}
      <div className="p-3 border-t border-paper-200 dark:border-obsidian-800/80 space-y-3">
        {/* Real-time Hardware Status Card */}
        <div className="p-2.5 rounded-lg bg-white dark:bg-obsidian-850 border border-paper-300 dark:border-obsidian-750 text-[11px] font-mono space-y-1.5 shadow-sm">
          <div className="flex items-center justify-between">
            <span className="text-paper-500 dark:text-obsidian-400 flex items-center gap-1.5">
              <Radio className="w-3 h-3 text-cognac-600 dark:text-cognac-400" />
              WS Socket
            </span>
            <span
              className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                isConnected
                  ? "bg-sage-500/15 text-sage-700 dark:text-sage-400 border border-sage-500/30"
                  : "bg-crimson-500/15 text-crimson-700 dark:text-crimson-400 border border-crimson-500/30"
              }`}
            >
              {isConnected ? "ONLINE" : "RECONNECTING"}
            </span>
          </div>

          <div className="flex items-center justify-between text-paper-700 dark:text-obsidian-300">
            <span className="text-paper-500 dark:text-obsidian-500 flex items-center gap-1">
              <Terminal className="w-3 h-3" />
              Node Port
            </span>
            <span className="text-paper-900 dark:text-obsidian-100 font-bold truncate max-w-[110px]" title={activePort}>
              {activePort}
            </span>
          </div>

          <div className="flex items-center justify-between text-paper-700 dark:text-obsidian-300">
            <span className="text-paper-500 dark:text-obsidian-500 flex items-center gap-1">
              <Zap className="w-3 h-3" />
              Stream State
            </span>
            <span
              className={`font-semibold ${
                isStreaming
                  ? "text-sage-600 dark:text-sage-400 flex items-center gap-1"
                  : "text-paper-500 dark:text-obsidian-400"
              }`}
            >
              {isStreaming ? (
                <>
                  <span className="w-1.5 h-1.5 rounded-full bg-sage-500 animate-ping inline-block" />
                  ACQUIRING
                </>
              ) : (
                "STANDBY"
              )}
            </span>
          </div>
        </div>

        {/* Academic Project Credits */}
        <div className="px-2 pt-1 text-center">
          <p className="text-[11px] font-semibold text-paper-800 dark:text-obsidian-200">
            Dungu Avinash Reddy
          </p>
          <p className="text-[10px] font-mono text-paper-500 dark:text-obsidian-400">
            Roll: 12509090 • Final Project
          </p>
        </div>
      </div>
    </aside>
  );
}
