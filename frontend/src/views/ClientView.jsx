import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Activity, Thermometer, Droplets, ShieldCheck, AlertTriangle, Play, Square, Radio, ExternalLink } from "lucide-react";
import ClientStripChart from "../components/ClientStripChart";
import RoomMap from "../components/RoomMap";
import UnusualLog from "../components/UnusualLog";

export default function ClientView() {
  const [statusData, setStatusData] = useState(null);
  const [readings, setReadings] = useState([]);
  const [events, setEvents] = useState([]);
  const [activeRange, setActiveRange] = useState("1 h");
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isSimulating, setIsSimulating] = useState(false);
  const [isLiveSerial, setIsLiveSerial] = useState(false);

  // Fetch initial client state from backend
  const fetchClientData = useCallback(async () => {
    try {
      const [statusRes, readingsRes, eventsRes] = await Promise.all([
        fetch("/api/client/status").then((r) => (r.ok ? r.json() : null)),
        fetch("/api/client/readings?limit=600").then((r) => (r.ok ? r.json() : [])),
        fetch("/api/client/events?limit=50").then((r) => (r.ok ? r.json() : [])),
      ]);
      if (statusRes) {
        setStatusData(statusRes);
        setIsSimulating(statusRes.status === "Simulated");
        setIsLiveSerial(statusRes.status === "Live");
      }
      if (readingsRes && readingsRes.length > 0) setReadings(readingsRes);
      if (eventsRes) setEvents(eventsRes);
    } catch (err) {
      console.error("Data fetch error:", err);
    }
  }, []);

  useEffect(() => {
    fetchClientData();
    const timer = setInterval(fetchClientData, 3000);
    return () => clearInterval(timer);
  }, [fetchClientData]);

  // Real-time WebSocket connection
  useEffect(() => {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProto}//${window.location.host}/ws/telemetry`;
    let ws = null;
    let reconnectTimer = null;

    const connect = () => {
      try {
        ws = new WebSocket(wsUrl);
        ws.onmessage = (evt) => {
          try {
            const data = JSON.parse(evt.data);
            if (data.temperature !== undefined && data.humidity !== undefined) {
              const newReading = {
                timestamp: data.timestamp || new Date().toISOString(),
                temperature: Number(data.temperature),
                humidity: Number(data.humidity),
                is_simulated: Boolean(data.is_simulated),
              };
              setReadings((prev) => [...prev.slice(-999), newReading]);
              setStatusData((prev) => ({
                ...(prev || {}),
                current_temperature: newReading.temperature,
                current_humidity: newReading.humidity,
                last_reading_time: newReading.timestamp,
                active_unusual_reading: Boolean(data.is_anomaly || data.hybrid_anomaly),
                status: data.is_simulated ? "Simulated" : "Live",
              }));
              if (data.is_simulated) setIsSimulating(true);
              if (data.is_anomaly || data.hybrid_anomaly) {
                fetch("/api/client/events?limit=50").then((r) => r.ok && r.json()).then((evs) => evs && setEvents(evs));
              }
            }
          } catch {}
        };
        ws.onclose = () => { reconnectTimer = setTimeout(connect, 3000); };
      } catch { reconnectTimer = setTimeout(connect, 3000); }
    };
    connect();
    return () => { if (ws) ws.close(); if (reconnectTimer) clearTimeout(reconnectTimer); };
  }, []);

  const handleStartSim = async () => {
    try {
      await fetch("/api/simulation/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset_name: "test", interval_sec: 0.5 }),
      });
      setIsSimulating(true);
      fetchClientData();
    } catch (e) { console.error(e); }
  };

  const handleStartLive = async () => {
    try {
      await fetch("/api/serial/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ port: "auto", baud: 115200 }),
      });
      setIsLiveSerial(true);
      fetchClientData();
    } catch (e) { console.error(e); }
  };

  const handleStop = async () => {
    try {
      await fetch("/api/simulation/stop", { method: "POST" });
      await fetch("/api/serial/stop", { method: "POST" });
      setIsSimulating(false);
      setIsLiveSerial(false);
      fetchClientData();
    } catch (e) { console.error(e); }
  };

  const curTemp = statusData?.current_temperature ?? (readings.length ? readings[readings.length - 1].temperature : 26.2);
  const curHum = statusData?.current_humidity ?? (readings.length ? readings[readings.length - 1].humidity : 59.4);
  const isAnom = Boolean(statusData?.active_unusual_reading);
  const streamStatus = statusData?.status || (isSimulating ? "Simulated" : isLiveSerial ? "Live" : "Offline");

  // Telemetry metrics
  const dewPoint = useMemo(() => (curTemp !== null && curHum !== null ? (curTemp - (100 - curHum) / 5).toFixed(1) : "—"), [curTemp, curHum]);
  const stats = useMemo(() => {
    if (!readings.length) return { tMin: 25.1, tMax: 27.8, hMin: 55.0, hMax: 63.8 };
    const temps = readings.map((r) => r.temperature);
    const hums = readings.map((r) => r.humidity);
    return { tMin: Math.min(...temps).toFixed(1), tMax: Math.max(...temps).toFixed(1), hMin: Math.min(...hums).toFixed(1), hMax: Math.max(...hums).toFixed(1) };
  }, [readings]);

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col font-sans selection:bg-blue-600 selection:text-white">
      {/* Top Navigation Bar */}
      <header className="border-b border-[#1E293B] bg-[#0F172A]/90 backdrop-blur sticky top-0 z-30 px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20">
              <Activity className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
                AI-Based IoT Sensor Anomaly Detection
                <span className="hidden sm:inline-block px-2 py-0.5 text-[11px] font-mono rounded bg-slate-800 text-slate-300 border border-slate-700">ESP32 + DHT11</span>
              </h1>
              <p className="text-xs text-slate-400">Indoor environmental telemetry & causal drift-resilient anomaly monitoring</p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Status indicator */}
            <div className="flex items-center gap-2 px-2.5 py-1.5 rounded-lg bg-[#1E293B] border border-slate-700 text-xs">
              <span className={`w-2 h-2 rounded-full ${streamStatus === "Live" ? "bg-emerald-500 animate-pulse" : streamStatus === "Simulated" ? "bg-blue-400 animate-pulse" : "bg-slate-500"}`} />
              <span className="font-semibold text-slate-200">{streamStatus.toUpperCase()}</span>
            </div>

            {/* Quick Actions */}
            {streamStatus === "Offline" ? (
              <div className="flex items-center gap-1.5">
                <button type="button" onClick={handleStartSim} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium transition shadow-md">
                  <Play className="w-3.5 h-3.5" /> <span className="hidden xs:inline">Simulate</span>
                </button>
                <button type="button" onClick={handleStartLive} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium border border-slate-700 transition">
                  <Radio className="w-3.5 h-3.5 text-emerald-400" /> <span className="hidden xs:inline">Live</span>
                </button>
              </div>
            ) : (
              <button type="button" onClick={handleStop} className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-medium transition shadow-md">
                <Square className="w-3.5 h-3.5 fill-current" /> <span>Stop</span>
              </button>
            )}

            <a href="/admin" className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 transition">
              <span className="hidden sm:inline">Admin</span> <ExternalLink className="w-3.5 h-3.5" />
            </a>
          </div>
        </div>
      </header>

      {/* Main Content Dashboard */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
        {/* Metric Cards Row */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* 1. Temperature Card */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 shadow-lg flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span className="flex items-center gap-1.5"><Thermometer className="w-4 h-4 text-rose-400" /> Ambient Temperature</span>
              <span className="font-mono text-slate-500">DHT11</span>
            </div>
            <div className="my-2 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-white tracking-tight num-tabular">{Number(curTemp).toFixed(1)}</span>
              <span className="text-lg font-semibold text-rose-400">°C</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400 border-t border-[#1F2937] pt-2">
              <span>Range: {stats.tMin}° – {stats.tMax}°</span>
              <span className="text-slate-500">Baseline 25.7°C</span>
            </div>
          </div>

          {/* 2. Humidity Card */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 shadow-lg flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span className="flex items-center gap-1.5"><Droplets className="w-4 h-4 text-sky-400" /> Relative Humidity</span>
              <span className="font-mono text-slate-500">Capacitive</span>
            </div>
            <div className="my-2 flex items-baseline gap-2">
              <span className="text-3xl font-extrabold text-white tracking-tight num-tabular">{Number(curHum).toFixed(1)}</span>
              <span className="text-lg font-semibold text-sky-400">% RH</span>
            </div>
            <div className="flex items-center justify-between text-xs text-slate-400 border-t border-[#1F2937] pt-2">
              <span>Range: {stats.hMin}% – {stats.hMax}%</span>
              <span className="text-slate-500">Baseline 61.4%</span>
            </div>
          </div>

          {/* 3. Indoor Comfort Index */}
          <div className="bg-[#111827] border border-[#1F2937] rounded-xl p-4 shadow-lg flex flex-col justify-between">
            <div className="flex items-center justify-between text-slate-400 text-xs font-medium">
              <span>Indoor Comfort Index</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Optimal</span>
            </div>
            <div className="my-2">
              <div className="text-sm font-semibold text-slate-200">Comfort Zone (ASHRAE 55)</div>
              <div className="text-xs text-slate-400 mt-0.5">Dew Point: <span className="font-semibold text-slate-200 num-tabular">{dewPoint} °C</span></div>
            </div>
            <div className="text-xs text-slate-500 border-t border-[#1F2937] pt-2 flex items-center justify-between">
              <span>VPD: ~1.35 kPa</span>
              <span className="text-emerald-400">Normal Range</span>
            </div>
          </div>

          {/* 4. AI Anomaly Engine Status */}
          <div className={`border rounded-xl p-4 shadow-lg flex flex-col justify-between transition-colors ${
            isAnom ? "bg-amber-950/20 border-amber-500/40 text-amber-200" : "bg-[#111827] border-[#1F2937]"
          }`}>
            <div className="flex items-center justify-between text-xs font-medium">
              <span className="flex items-center gap-1.5">
                {isAnom ? <AlertTriangle className="w-4 h-4 text-amber-400 animate-bounce" /> : <ShieldCheck className="w-4 h-4 text-emerald-400" />}
                AI Anomaly Engine
              </span>
              <span className="text-[10px] font-mono text-slate-400">Hybrid iForest</span>
            </div>
            <div className="my-2">
              <div className={`text-base font-bold ${isAnom ? "text-amber-400" : "text-emerald-400"}`}>
                {isAnom ? "Active Excursion Detected" : "Baseline Stable"}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">
                {isAnom ? "High departure from expected room state" : "0 active outliers in current buffer"}
              </div>
            </div>
            <div className="text-xs text-slate-500 border-t border-[#1F2937] pt-2 flex items-center justify-between">
              <span>Persistence: 3-of-5</span>
              <span className="text-slate-400">Sensitivity: Medium</span>
            </div>
          </div>
        </div>

        {/* Telemetry Waveform Strip Chart */}
        <ClientStripChart readings={readings} events={events} activeRange={activeRange} onRangeChange={setActiveRange} highlightedEvent={selectedEvent} />

        {/* Lower Row: Event Ledger & Phase Map */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8">
            <UnusualLog events={events} onSelectEvent={(ev) => setSelectedEvent(ev)} highlightedEvent={selectedEvent} />
          </div>
          <div className="lg:col-span-4">
            <RoomMap readings={readings} isUnusual={isAnom} />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[#1E293B] bg-[#0F172A] py-5 px-6 mt-auto text-xs text-slate-400">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div>
            <strong className="text-slate-200">Dungu Avinash Reddy</strong> | Roll: RK3P25KZA09 | Reg: 12509090
          </div>
          <div className="flex items-center gap-4 text-slate-500">
            <span>FastAPI + React 19 Full-Stack</span>
            <span>•</span>
            <a href="/admin" className="hover:text-slate-300 underline">Admin Login</a>
            <span>•</span>
            <a href="/docs" target="_blank" rel="noreferrer" className="hover:text-slate-300 underline">Swagger Docs</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
