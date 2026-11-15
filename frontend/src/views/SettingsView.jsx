import React, { useState, useEffect } from "react";
import {
  Bell,
  CheckCircle2,
  Send,
  Sliders,
  Smartphone,
  Webhook,
} from "lucide-react";
import { api } from "../services/api";

export default function SettingsView({ modelInfo, onRefresh }) {
  const [thresholds, setThresholds] = useState({
    if_threshold: -0.21657,
    ewma_threshold: 3.5,
    zscore_threshold: 3.0,
    sensitivity_label: "Medium (0.25th %ile)",
  });

  const [alertsConfig, setAlertsConfig] = useState({
    enabled: false,
    building_zone: "Building A - Sensor Chamber",
    min_severity: "Medium",
    cooldown_sec: 180,
    recovery_sec: 30,
    ntfy_enabled: true,
    ntfy_topic: "aethersense-alerts",
    webhook_enabled: false,
    webhook_url: "",
    email_enabled: false,
    email_from: "",
    email_to: [],
  });

  const [testResult, setTestResult] = useState(null);
  const [saveStatus, setSaveStatus] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (modelInfo?.thresholds) {
      setThresholds((prev) => ({
        ...prev,
        if_threshold: modelInfo.thresholds.iforest_threshold || -0.21657,
        ewma_threshold: modelInfo.thresholds.ewma_zscore_threshold || 3.5,
        zscore_threshold: modelInfo.thresholds.zscore_threshold || 3.0,
        sensitivity_label:
          modelInfo.thresholds.active_sensitivity || "Medium (0.25th %ile)",
      }));
    }

    // Load alert settings
    api
      .getAlertsConfig()
      .then((cfg) => {
        setAlertsConfig((prev) => ({
          ...prev,
          ...cfg,
          ntfy_topic: cfg.ntfy?.topic || "aethersense-alerts",
          webhook_url: cfg.webhook?.configured ? "Configured in backend .env" : "",
          email_from: cfg.email?.from || "",
        }));
      })
      .catch(console.warn);
  }, [modelInfo]);

  const handleSensitivitySelect = async (label, value) => {
    const updated = {
      ...thresholds,
      if_threshold: value,
      sensitivity_label: label,
    };
    setThresholds(updated);
    setIsSaving(true);
    try {
      await api.updateThresholds(updated);
      setSaveStatus("Sensitivity preset applied successfully!");
      setTimeout(() => setSaveStatus(null), 3000);
      onRefresh?.();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleThresholdSave = async () => {
    setIsSaving(true);
    try {
      await api.updateThresholds(thresholds);
      setSaveStatus("Threshold parameters synchronized to inference engine!");
      setTimeout(() => setSaveStatus(null), 3000);
      onRefresh?.();
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAlertConfigSave = async () => {
    setIsSaving(true);
    try {
      await api.updateAlertsConfig(alertsConfig);
      setSaveStatus("Alert configuration saved!");
      setTimeout(() => setSaveStatus(null), 3000);
    } catch (err) {
      console.error(err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleTestAlert = async () => {
    setTestResult({ status: "dispatching" });
    try {
      const res = await api.testAlert();
      setTestResult(res);
      setTimeout(() => setTestResult(null), 4000);
    } catch (err) {
      setTestResult({ status: "error", error: err.message });
      setTimeout(() => setTestResult(null), 4000);
    }
  };

  const presets = [
    {
      label: "Conservative (0.10th %ile)",
      value: -0.225,
      desc: "Ultra-low false alarm tolerance; only catches severe anomalies",
    },
    {
      label: "Medium (0.25th %ile)",
      value: -0.21657,
      desc: "Recommended default; 0 FP on 2,581 pilot rows, 96.8% eval F1",
    },
    {
      label: "Sensitive (0.50th %ile)",
      value: -0.205,
      desc: "Higher detection sensitivity for critical cleanroom monitoring",
    },
  ];

  return (
    <div className="space-y-6">
      {saveStatus && (
        <div className="p-3.5 rounded-xl bg-sage-500/15 border border-sage-500/40 text-sage-800 dark:text-sage-300 text-xs font-mono flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-sage-600 dark:text-sage-400" />
            <span>{saveStatus}</span>
          </div>
          <span className="text-[10px] text-sage-700 dark:text-sage-400 uppercase font-bold">Synchronized</span>
        </div>
      )}

      {/* Grid: 2 Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: Model Sensitivity Calibration */}
        <div className="bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl p-5 shadow-card dark:shadow-card-dark space-y-5 transition-colors">
          <div className="flex items-center justify-between border-b border-paper-200 dark:border-obsidian-800 pb-3">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cognac-600 dark:text-cognac-400" />
              <h3 className="text-sm font-bold text-paper-900 dark:text-obsidian-100 font-mono uppercase tracking-wider">
                Detection Sensitivity & Cutoffs
              </h3>
            </div>
            <span className="text-[10px] font-mono text-paper-500 dark:text-obsidian-400 bg-paper-100 dark:bg-obsidian-900 px-2 py-0.5 rounded border border-paper-200 dark:border-obsidian-800">
              Runtime Tunable
            </span>
          </div>

          {/* Quick Preset Selector */}
          <div className="space-y-2">
            <label className="text-xs font-mono uppercase tracking-wider text-paper-500 dark:text-obsidian-400 block font-semibold">
              Isolation Forest Contamination Presets
            </label>
            <div className="grid grid-cols-1 gap-2">
              {presets.map((p) => {
                const isSelected =
                  thresholds.sensitivity_label === p.label ||
                  Math.abs(thresholds.if_threshold - p.value) < 0.001;
                return (
                  <button
                    key={p.label}
                    onClick={() => handleSensitivitySelect(p.label, p.value)}
                    className={`p-3 rounded-lg border text-left transition flex items-start justify-between gap-3 ${
                      isSelected
                        ? "bg-paper-50 dark:bg-obsidian-900 border-cognac-500/50 shadow-sm"
                        : "bg-paper-50/60 dark:bg-obsidian-900/60 border-paper-200 dark:border-obsidian-800 hover:border-paper-300 dark:hover:border-obsidian-700"
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className={`w-2 h-2 rounded-full ${
                            isSelected ? "bg-cognac-600 dark:bg-cognac-400" : "bg-paper-300 dark:bg-obsidian-600"
                          }`}
                        />
                        <span className="text-xs font-bold font-mono text-paper-900 dark:text-white">
                          {p.label}
                        </span>
                      </div>
                      <p className="text-[11px] text-paper-500 dark:text-obsidian-400 mt-1 font-sans">
                        {p.desc}
                      </p>
                    </div>
                    <span className="text-xs font-mono font-bold text-cognac-600 dark:text-cognac-400">
                      {p.value}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Precise Parameter Sliders */}
          <div className="space-y-4 pt-2 border-t border-paper-200 dark:border-obsidian-800 font-mono text-xs">
            {/* IF Cutoff */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-paper-700 dark:text-obsidian-300">
                <span>Isolation Forest Threshold:</span>
                <span className="font-bold text-cognac-600 dark:text-cognac-400 text-sm">
                  {thresholds.if_threshold}
                </span>
              </div>
              <input
                type="range"
                min="-0.260"
                max="-0.180"
                step="0.001"
                value={thresholds.if_threshold}
                onChange={(e) =>
                  setThresholds({
                    ...thresholds,
                    if_threshold: parseFloat(e.target.value),
                    sensitivity_label: "Custom Calibration",
                  })
                }
                className="w-full h-1.5 bg-paper-200 dark:bg-obsidian-800 rounded-lg appearance-none cursor-pointer accent-cognac-600"
              />
              <div className="flex justify-between text-[10px] text-paper-400 dark:text-obsidian-500">
                <span>-0.260 (More Conservative)</span>
                <span>-0.180 (More Sensitive)</span>
              </div>
            </div>

            {/* Cauchy EWMA Cutoff */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-paper-700 dark:text-obsidian-300">
                <span>Cauchy EWMA-Z Cutoff (σ):</span>
                <span className="font-bold text-arctic-600 dark:text-arctic-400 text-sm">
                  {thresholds.ewma_threshold} σ
                </span>
              </div>
              <input
                type="range"
                min="2.0"
                max="5.0"
                step="0.1"
                value={thresholds.ewma_threshold}
                onChange={(e) =>
                  setThresholds({
                    ...thresholds,
                    ewma_threshold: parseFloat(e.target.value),
                  })
                }
                className="w-full h-1.5 bg-paper-200 dark:bg-obsidian-800 rounded-lg appearance-none cursor-pointer accent-arctic-600"
              />
              <div className="flex justify-between text-[10px] text-paper-400 dark:text-obsidian-500">
                <span>2.0 σ (Strict Plateau Alert)</span>
                <span>5.0 σ (Permissive)</span>
              </div>
            </div>

            {/* Static Z-Score Fallback */}
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-paper-700 dark:text-obsidian-300">
                <span>Static Z-Score Fallback:</span>
                <span className="font-bold text-sage-600 dark:text-sage-400 text-sm">
                  {thresholds.zscore_threshold} σ
                </span>
              </div>
              <input
                type="range"
                min="2.0"
                max="4.5"
                step="0.1"
                value={thresholds.zscore_threshold}
                onChange={(e) =>
                  setThresholds({
                    ...thresholds,
                    zscore_threshold: parseFloat(e.target.value),
                  })
                }
                className="w-full h-1.5 bg-paper-200 dark:bg-obsidian-800 rounded-lg appearance-none cursor-pointer accent-sage-600"
              />
            </div>
          </div>

          <button
            onClick={handleThresholdSave}
            disabled={isSaving}
            className="w-full py-2.5 rounded-lg text-xs font-bold bg-cognac-600 hover:bg-cognac-700 text-white transition shadow-sm btn-action font-sans"
          >
            Apply & Save Parameters
          </button>
        </div>

        {/* Right Column: Multi-Channel Alerting Hub */}
        <div className="bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl p-5 shadow-card dark:shadow-card-dark space-y-5 transition-colors">
          <div className="flex items-center justify-between border-b border-paper-200 dark:border-obsidian-800 pb-3">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-arctic-600 dark:text-arctic-400" />
              <h3 className="text-sm font-bold text-paper-900 dark:text-obsidian-100 font-mono uppercase tracking-wider">
                Alert Dispatch & Webhooks
              </h3>
            </div>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <span className="text-[11px] font-mono text-paper-500 dark:text-obsidian-400">Dispatch:</span>
              <input
                type="checkbox"
                checked={alertsConfig.enabled}
                onChange={(e) =>
                  setAlertsConfig({ ...alertsConfig, enabled: e.target.checked })
                }
                className="w-4 h-4 rounded bg-paper-100 dark:bg-obsidian-900 border-paper-300 dark:border-obsidian-700 text-cognac-600 focus:ring-0 accent-cognac-600"
              />
            </label>
          </div>

          {/* Alert Options Form */}
          <div className="space-y-3.5 text-xs font-mono">
            {/* Zone Tag */}
            <div className="space-y-1">
              <label className="text-paper-500 dark:text-obsidian-400 text-[11px]">Facility Chamber Tag:</label>
              <input
                type="text"
                value={alertsConfig.building_zone}
                onChange={(e) =>
                  setAlertsConfig({ ...alertsConfig, building_zone: e.target.value })
                }
                className="w-full bg-paper-50 dark:bg-obsidian-900 border border-paper-300 dark:border-obsidian-750 rounded-lg px-3 py-2 text-paper-900 dark:text-white font-mono focus:border-arctic-500 focus:outline-none"
              />
            </div>

            {/* Severity Threshold */}
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label className="text-paper-500 dark:text-obsidian-400 text-[11px]">Minimum Severity:</label>
                <select
                  value={alertsConfig.min_severity}
                  onChange={(e) =>
                    setAlertsConfig({ ...alertsConfig, min_severity: e.target.value })
                  }
                  className="w-full bg-paper-50 dark:bg-obsidian-900 border border-paper-300 dark:border-obsidian-750 rounded-lg px-3 py-2 text-paper-900 dark:text-white font-mono focus:border-arctic-500 focus:outline-none"
                >
                  <option value="Low">Low (Score &gt; 2.5)</option>
                  <option value="Medium">Medium (Score &gt; 4.5)</option>
                  <option value="High">High (Score &gt; 8.0)</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-paper-500 dark:text-obsidian-400 text-[11px]">Cooldown (Sec):</label>
                <input
                  type="number"
                  value={alertsConfig.cooldown_sec}
                  onChange={(e) =>
                    setAlertsConfig({
                      ...alertsConfig,
                      cooldown_sec: parseInt(e.target.value) || 60,
                    })
                  }
                  className="w-full bg-paper-50 dark:bg-obsidian-900 border border-paper-300 dark:border-obsidian-750 rounded-lg px-3 py-2 text-paper-900 dark:text-white font-mono focus:border-arctic-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Ntfy Mobile Push */}
            <div className="p-3.5 rounded-lg bg-paper-50 dark:bg-obsidian-900 border border-paper-200 dark:border-obsidian-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Smartphone className="w-4 h-4 text-amber-600 dark:text-amber-400" />
                  <span className="text-xs font-bold text-paper-900 dark:text-white font-mono">
                    Ntfy.sh Mobile Push
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={alertsConfig.ntfy_enabled}
                  onChange={(e) =>
                    setAlertsConfig({
                      ...alertsConfig,
                      ntfy_enabled: e.target.checked,
                    })
                  }
                  className="w-4 h-4 rounded bg-paper-100 dark:bg-obsidian-800 text-amber-600 accent-amber-600"
                />
              </div>
              <input
                type="text"
                placeholder="Topic name (e.g. aethersense-alerts)"
                value={alertsConfig.ntfy_topic}
                onChange={(e) =>
                  setAlertsConfig({ ...alertsConfig, ntfy_topic: e.target.value })
                }
                className="w-full bg-white dark:bg-obsidian-850 border border-paper-300 dark:border-obsidian-750 rounded-lg px-3 py-1.5 text-paper-900 dark:text-white font-mono text-xs focus:border-amber-500 focus:outline-none"
              />
              <p className="text-[10px] text-paper-500 dark:text-obsidian-500 font-sans">
                Subscribe on mobile via the free Ntfy app (iOS/Android) at: ntfy.sh/{alertsConfig.ntfy_topic || "topic"}
              </p>
            </div>

            {/* Webhook Endpoint */}
            <div className="p-3.5 rounded-lg bg-paper-50 dark:bg-obsidian-900 border border-paper-200 dark:border-obsidian-800 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Webhook className="w-4 h-4 text-arctic-600 dark:text-arctic-400" />
                  <span className="text-xs font-bold text-paper-900 dark:text-white font-mono">
                    Custom Webhook (Slack / Discord)
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={alertsConfig.webhook_enabled}
                  onChange={(e) =>
                    setAlertsConfig({
                      ...alertsConfig,
                      webhook_enabled: e.target.checked,
                    })
                  }
                  className="w-4 h-4 rounded bg-paper-100 dark:bg-obsidian-800 text-arctic-600 accent-arctic-600"
                />
              </div>
              <input
                type="text"
                placeholder="https://hooks.slack.com/services/..."
                value={alertsConfig.webhook_url}
                onChange={(e) =>
                  setAlertsConfig({ ...alertsConfig, webhook_url: e.target.value })
                }
                className="w-full bg-white dark:bg-obsidian-850 border border-paper-300 dark:border-obsidian-750 rounded-lg px-3 py-1.5 text-paper-900 dark:text-white font-mono text-xs focus:border-arctic-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={handleAlertConfigSave}
              className="flex-1 py-2.5 rounded-lg text-xs font-bold bg-paper-100 dark:bg-obsidian-800 hover:bg-paper-200 dark:hover:bg-obsidian-750 text-paper-900 dark:text-white border border-paper-300 dark:border-obsidian-700 transition shadow-sm btn-action font-sans"
            >
              Save Alert Rules
            </button>

            <button
              onClick={handleTestAlert}
              className="flex items-center gap-1.5 px-4 py-2.5 rounded-lg text-xs font-bold bg-arctic-600 hover:bg-arctic-700 text-white transition shadow-sm btn-action font-sans"
              title="Dispatch instantaneous test ping"
            >
              <Send className="w-3.5 h-3.5" />
              <span>Test Ping</span>
            </button>
          </div>

          {testResult && (
            <div
              className={`p-3 rounded-lg text-xs font-mono border ${
                testResult.status === "dispatched"
                  ? "bg-sage-500/10 border-sage-500/40 text-sage-800 dark:text-sage-300"
                  : "bg-crimson-500/10 border-crimson-500/40 text-crimson-800 dark:text-crimson-300"
              }`}
            >
              {testResult.status === "dispatching" && "Dispatching test message..."}
              {testResult.status === "dispatched" &&
                `✓ Test alert dispatched through: ${testResult.channels?.join(", ") || "Active channels"}`}
              {testResult.status === "failed_or_no_channels" &&
                "⚠ No active channels configured. Enable Ntfy or Webhook above."}
              {testResult.status === "error" && `Error: ${testResult.error}`}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
