import React, { useState, useEffect } from "react";
import {
  Activity,
  Droplets,
  Flame,
  Layers,
  Play,
  RefreshCw,
  Sliders,
  Square,
  Zap,
} from "lucide-react";
import MetricCard from "../components/MetricCard";
import StatusBanner from "../components/StatusBanner";
import LiveChart from "../components/LiveChart";
import IncidentLog from "../components/IncidentLog";
import RoomMap from "../components/RoomMap";

export default function LiveMonitorView({
  serialStatus,
  ports = [],
  onRefreshPorts,
  onStartSerial,
  onStartSimulation,
  onStopStream,
  isStreaming,
  liveFrames = [],
  incidents = [],
  latestFrame,
  theme = "dark",
}) {
  const [selectedPort, setSelectedPort] = useState(
    () => serialStatus?.current_port || serialStatus?.detected_esp32_port || "COM19"
  );
  const [selectedBaud, setSelectedBaud] = useState(115200);
  const [simDataset, setSimDataset] = useState("eval_suite");
  const [simSpeed, setSimSpeed] = useState(1.0);

  useEffect(() => {
    if (serialStatus?.detected_esp32_port && !serialStatus?.current_port) {
      setSelectedPort((prev) => (prev === "COM19" ? serialStatus.detected_esp32_port : prev));
    }
  }, [serialStatus?.detected_esp32_port, serialStatus?.current_port]);

  const isAnomaly = Boolean(latestFrame?.is_anomaly || latestFrame?.hybrid_anomaly);

  return (
    <div className="space-y-6">
      {/* Stream Control Console */}
      <div className="bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl p-4 shadow-card dark:shadow-card-dark flex flex-wrap items-center justify-between gap-4 transition-colors">
        {/* Hardware Serial Options */}
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-paper-500 dark:text-obsidian-400">COM Port:</span>
            <select
              disabled={isStreaming}
              value={selectedPort}
              onChange={(e) => setSelectedPort(e.target.value)}
              className="bg-paper-50 dark:bg-obsidian-900 border border-paper-300 dark:border-obsidian-700 text-paper-900 dark:text-white text-xs rounded-lg px-2.5 py-1.5 font-mono focus:border-cognac-500 focus:outline-none disabled:opacity-50"
            >
              {ports.map((p) => (
                <option key={p.port} value={p.port}>
                  {p.port} {p.is_esp32 ? "(ESP32 Detected)" : `(${p.description})`}
                </option>
              ))}
              {ports.length === 0 && <option value="COM19">COM19 (Default Node)</option>}
            </select>
            <button
              onClick={onRefreshPorts}
              disabled={isStreaming}
              className="p-1.5 rounded-lg text-paper-500 dark:text-obsidian-400 hover:text-paper-900 dark:hover:text-white hover:bg-paper-100 dark:hover:bg-obsidian-800 transition disabled:opacity-50"
              title="Rescan serial COM ports"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-paper-500 dark:text-obsidian-400">Baud:</span>
            <select
              disabled={isStreaming}
              value={selectedBaud}
              onChange={(e) => setSelectedBaud(Number(e.target.value))}
              className="bg-paper-50 dark:bg-obsidian-900 border border-paper-300 dark:border-obsidian-700 text-paper-900 dark:text-white text-xs rounded-lg px-2.5 py-1.5 font-mono focus:border-cognac-500 focus:outline-none disabled:opacity-50"
            >
              <option value={115200}>115,200 baud</option>
              <option value={9600}>9,600 baud</option>
              <option value={57600}>57,600 baud</option>
            </select>
          </div>

          {isStreaming ? (
            <button
              onClick={onStopStream}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-bold bg-crimson-600 hover:bg-crimson-700 text-white transition shadow-sm btn-action"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>Halt Stream</span>
            </button>
          ) : (
            <button
              onClick={() => onStartSerial(selectedPort, selectedBaud)}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-bold bg-cognac-600 hover:bg-cognac-700 text-white transition shadow-sm btn-action"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Connect ESP32</span>
            </button>
          )}
        </div>

        {/* Evaluation Replay Controls */}
        <div className="flex items-center gap-2 pt-2 sm:pt-0 border-t sm:border-t-0 border-paper-200 dark:border-obsidian-800 w-full sm:w-auto justify-end">
          <span className="text-xs font-mono text-paper-500 dark:text-obsidian-400 flex items-center gap-1">
            <Zap className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" />
            Simulate Replay:
          </span>
          <select
            disabled={isStreaming}
            value={simDataset}
            onChange={(e) => setSimDataset(e.target.value)}
            className="bg-paper-50 dark:bg-obsidian-900 border border-paper-300 dark:border-obsidian-700 text-paper-900 dark:text-white text-xs rounded-lg px-2.5 py-1 font-mono disabled:opacity-50 focus:border-cognac-500 focus:outline-none"
          >
            <option value="eval_suite">Eval Suite (6 Faults)</option>
            <option value="pilot">Physical Pilot (3k rows)</option>
            <option value="test">Thermal Spike Holdout</option>
          </select>
          <select
            disabled={isStreaming}
            value={simSpeed}
            onChange={(e) => setSimSpeed(Number(e.target.value))}
            className="bg-paper-50 dark:bg-obsidian-900 border border-paper-300 dark:border-obsidian-700 text-paper-900 dark:text-white text-xs rounded-lg px-2.5 py-1 font-mono disabled:opacity-50 focus:border-cognac-500 focus:outline-none"
          >
            <option value={1.0}>1.0s (1 Hz)</option>
            <option value={0.5}>0.5s (2 Hz)</option>
            <option value={2.0}>2.0s (0.5 Hz)</option>
          </select>
          {!isStreaming && (
            <button
              onClick={() => onStartSimulation(simDataset, simSpeed)}
              className="px-3 py-1 rounded-lg text-xs font-semibold bg-paper-100 dark:bg-obsidian-800 hover:bg-paper-200 dark:hover:bg-obsidian-750 text-amber-700 dark:text-amber-400 border border-paper-300 dark:border-obsidian-700 transition shadow-sm btn-action"
            >
              Replay
            </button>
          )}
        </div>
      </div>

      {/* Prominent Telemetry Annunciator Banner */}
      <StatusBanner
        isAnomaly={isAnomaly}
        latestFrame={latestFrame}
        isStreaming={isStreaming}
      />

      {/* 4 Live Telemetry Gauges */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Current Temperature"
          value={latestFrame ? `${Number(latestFrame.temperature).toFixed(1)} °C` : "--"}
          subtitle={
            latestFrame
              ? `Rate: ${Number(latestFrame.temp_rate || 0).toFixed(2)} °C/s • Baseline Δ: ${Number(
                  latestFrame.temp_ewma_residual || 0
                ).toFixed(2)} °C`
              : "Waiting for stream"
          }
          icon={Flame}
          color={isAnomaly ? "crimson" : "cognac"}
          trend={latestFrame ? `${Number(latestFrame.temperature) > 28 ? "Warm" : "Nominal"}` : null}
        />
        <MetricCard
          title="Current Humidity"
          value={latestFrame ? `${Number(latestFrame.humidity).toFixed(1)} %` : "--"}
          subtitle={
            latestFrame
              ? `Rate: ${Number(latestFrame.hum_rate || 0).toFixed(2)} %/s • Baseline Δ: ${Number(
                  latestFrame.hum_ewma_residual || 0
                ).toFixed(2)} %`
              : "Waiting for stream"
          }
          icon={Droplets}
          color={isAnomaly ? "crimson" : "arctic"}
          trend={latestFrame ? `${Number(latestFrame.humidity) > 70 ? "High RH" : "Normal"}` : null}
        />
        <MetricCard
          title="Isolation Forest Score"
          value={latestFrame ? Number(latestFrame.iforest_score || 0).toFixed(4) : "--"}
          subtitle="Operating Cutoff: -0.2166 (0.25th %ile)"
          icon={Layers}
          color={latestFrame?.iforest_anomaly ? "crimson" : "cognac"}
          trend={latestFrame?.iforest_anomaly ? "TRIGGER" : "NORMAL"}
        />
        <MetricCard
          title="Cauchy EWMA-Z Score"
          value={
            latestFrame
              ? `${Number(latestFrame.ewma_z_score || 0).toFixed(2)} σ`
              : "--"
          }
          subtitle="Plateau Outlier Cutoff: 3.50 σ"
          icon={Sliders}
          color={latestFrame?.ewma_z_anomaly ? "crimson" : "sage"}
          trend={latestFrame?.ewma_z_anomaly ? "TRIGGER" : "NORMAL"}
        />
      </div>

      {/* Main Oscilloscope & Phase Space Portrait Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Oscilloscope Stream (2 cols) */}
        <div className="lg:col-span-2 bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl p-5 shadow-card dark:shadow-card-dark space-y-3 transition-colors">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-paper-200 dark:border-obsidian-800 pb-3">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 text-cognac-600 dark:text-cognac-400" />
              <h3 className="text-sm font-bold text-paper-900 dark:text-obsidian-100 font-mono uppercase tracking-wider">
                Continuous Telemetry Strip Chart
              </h3>
            </div>
            <span className="text-[10px] font-mono text-paper-500 dark:text-obsidian-400 bg-paper-100 dark:bg-obsidian-900 px-2 py-0.5 rounded border border-paper-200 dark:border-obsidian-800">
              Buffer: {liveFrames.length} points • Diamonds = Anomaly Points
            </span>
          </div>

          <div className="pt-2">
            <LiveChart data={liveFrames} height={300} theme={theme} />
          </div>
        </div>

        {/* Phase State Portrait (1 col) */}
        <div className="lg:col-span-1">
          <RoomMap readings={liveFrames} theme={theme} />
        </div>
      </div>

      {/* Incident Ledger */}
      <IncidentLog incidents={incidents} />
    </div>
  );
}
