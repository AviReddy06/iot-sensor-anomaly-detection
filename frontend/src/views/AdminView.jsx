import React, { useState, useEffect, useCallback } from "react";

export default function AdminView() {
  const [token, setToken] = useState(() => sessionStorage.getItem("admin_token") || "");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");

  // Admin state data
  const [modelDetails, setModelDetails] = useState(null);
  const [evaluationMetrics, setEvaluationMetrics] = useState([]);
  const [serialStatus, setSerialStatus] = useState(null);
  const [ports, setPorts] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [sensitivitySetting, setSensitivitySetting] = useState("Medium");
  const [adminMessage, setAdminMessage] = useState(null);

  const tabs = [
    { id: "overview", label: "Overview" },
    { id: "live", label: "Live monitor" },
    { id: "evaluation", label: "Evaluation" },
    { id: "datasets", label: "Datasets" },
    { id: "alerts", label: "Alerts" },
    { id: "settings", label: "Settings" },
    { id: "audit", label: "Audit" },
  ];

  // Login handler
  const handleLogin = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setLoginError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });

      if (!res.ok) {
        if (res.status === 503) {
          throw new Error("Admin access is unavailable: ADMIN_PASSWORD environment variable is not set.");
        }
        if (res.status === 429) {
          throw new Error("Too many failed login attempts. Please wait 1 minute.");
        }
        if (res.status === 401) {
          throw new Error("Invalid admin password.");
        }
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || "Authentication failed.");
      }

      const data = await res.json();
      setToken(data.token);
      sessionStorage.setItem("admin_token", data.token);
      setPassword("");
    } catch (err) {
      setLoginError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleLogout = () => {
    setToken("");
    sessionStorage.removeItem("admin_token");
  };

  // Helper for authenticated admin fetch
  const fetchAdmin = useCallback(
    async (endpoint, options = {}) => {
      if (!token) return null;
      const res = await fetch(endpoint, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          ...(options.headers || {}),
        },
      });

      if (res.status === 401) {
        handleLogout();
        throw new Error("Session expired. Please log in again.");
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || `Request failed with status ${res.status}`);
      }
      return res.json();
    },
    [token]
  );

  // Load active tab data
  useEffect(() => {
    if (!token) return;

    if (activeTab === "overview" || activeTab === "settings") {
      fetchAdmin("/api/admin/model/details")
        .then((d) => {
          if (d) {
            setModelDetails(d);
            setSensitivitySetting(d.sensitivity || "Medium");
          }
        })
        .catch(console.warn);
    }

    if (activeTab === "live") {
      fetchAdmin("/api/admin/serial/status")
        .then((s) => s && setSerialStatus(s))
        .catch(console.warn);
      fetchAdmin("/api/admin/serial/ports")
        .then((p) => p && setPorts(p))
        .catch(console.warn);
    }

    if (activeTab === "evaluation") {
      fetchAdmin("/api/admin/evaluation")
        .then((m) => m && setEvaluationMetrics(m))
        .catch(console.warn);
    }

    if (activeTab === "audit") {
      fetchAdmin("/api/admin/audit")
        .then((a) => a && setAuditLogs(a))
        .catch(console.warn);
    }
  }, [token, activeTab, fetchAdmin]);

  // Actions
  const handleStartSerial = async (port, baud) => {
    try {
      await fetchAdmin("/api/admin/serial/start", {
        method: "POST",
        body: JSON.stringify({ port, baud: Number(baud) }),
      });
      setAdminMessage("Serial port opened successfully.");
      const s = await fetchAdmin("/api/admin/serial/status");
      if (s) setSerialStatus(s);
    } catch (err) {
      setAdminMessage(`Failed to open serial port: ${err.message}`);
    }
  };

  const handleStopSerial = async () => {
    try {
      await fetchAdmin("/api/admin/serial/stop", { method: "POST" });
      setAdminMessage("Serial stream stopped.");
      const s = await fetchAdmin("/api/admin/serial/status");
      if (s) setSerialStatus(s);
    } catch (err) {
      setAdminMessage(`Failed to stop serial stream: ${err.message}`);
    }
  };

  const handleStartSimulation = async (dataset, intervalSec) => {
    try {
      await fetchAdmin("/api/admin/simulation/start", {
        method: "POST",
        body: JSON.stringify({ dataset, interval_sec: Number(intervalSec) }),
      });
      setAdminMessage(`Simulation stream started (${dataset}).`);
      const s = await fetchAdmin("/api/admin/serial/status");
      if (s) setSerialStatus(s);
    } catch (err) {
      setAdminMessage(`Failed to start simulation: ${err.message}`);
    }
  };

  const handleStopSimulation = async () => {
    try {
      await fetchAdmin("/api/admin/simulation/stop", { method: "POST" });
      setAdminMessage("Simulation stream stopped.");
      const s = await fetchAdmin("/api/admin/serial/status");
      if (s) setSerialStatus(s);
    } catch (err) {
      setAdminMessage(`Failed to stop simulation: ${err.message}`);
    }
  };

  const handleSaveSensitivity = async (level) => {
    try {
      await fetchAdmin("/api/admin/settings/sensitivity", {
        method: "POST",
        body: JSON.stringify({ level }),
      });
      setSensitivitySetting(level);
      setAdminMessage(`Sensitivity updated to ${level}.`);
      const d = await fetchAdmin("/api/admin/model/details");
      if (d) setModelDetails(d);
    } catch (err) {
      setAdminMessage(`Failed to update sensitivity: ${err.message}`);
    }
  };

  // If not authenticated, render Login Form
  if (!token) {
    return (
      <div className="min-h-screen bg-[#EEF1EF] text-[#1C2A33] flex items-center justify-center p-6">
        <div className="w-full max-w-[420px] bg-[#EEF1EF] border border-[#CBD5D0] p-8">
          <div className="text-[13px] text-[#4F5F69] font-sans pb-1">
            System Administration
          </div>
          <h1 className="text-[22px] font-bold text-[#1C2A33] font-sans tracking-tight mb-4">
            AI-Based IoT Sensor Anomaly Detection
          </h1>
          <p className="text-[14px] text-[#4F5F69] font-sans mb-6">
            Enter the administrator password to access hardware configuration, model evaluation, and audit logs.
          </p>

          {loginError && (
            <div className="mb-4 p-3 bg-[#EEF1EF] border border-[#7A4B00] text-[13px] text-[#7A4B00] font-sans">
              {loginError}
            </div>
          )}

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label
                htmlFor="admin-password"
                className="block text-[13px] text-[#4F5F69] font-sans mb-1"
              >
                Password
              </label>
              <input
                id="admin-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="w-full px-3 py-2 bg-white border border-[#CBD5D0] text-[#1C2A33] text-[14px] font-sans focus:outline-none focus:ring-2 focus:ring-[#1C2A33]"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 bg-[#1C2A33] text-white text-[14px] font-medium font-sans hover:bg-[#2e404d] transition-colors focus:outline-none focus:ring-2 focus:ring-[#1C2A33]"
            >
              {isSubmitting ? "Authenticating..." : "Log in"}
            </button>
          </form>

          <div className="mt-8 pt-4 border-t border-[#CBD5D0] text-[13px] text-[#4F5F69] flex justify-between">
            <a href="/" className="hover:text-[#1C2A33] underline">
              Return to client page
            </a>
            <span>5 attempts per minute</span>
          </div>
        </div>
      </div>
    );
  }

  // Authenticated Admin Dashboard Layout
  return (
    <div className="min-h-screen bg-[#EEF1EF] text-[#1C2A33]">
      <div className="max-w-[1240px] mx-auto px-5 sm:px-8 py-6">
        {/* Top Header */}
        <header className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-[#CBD5D0]">
          <div>
            <div className="text-[12px] text-[#4F5F69] font-sans">
              Technical Administration
            </div>
            <h1 className="text-[18px] sm:text-[20px] font-bold text-[#1C2A33] font-sans">
              AI-Based IoT Sensor Anomaly Detection
            </h1>
          </div>
          <div className="flex items-center gap-4 text-[13px]">
            <a href="/" className="text-[#4F5F69] hover:text-[#1C2A33] underline">
              View client page
            </a>
            <button
              type="button"
              onClick={handleLogout}
              className="text-[#4F5F69] hover:text-[#1C2A33] underline"
            >
              Log out
            </button>
          </div>
        </header>

        {/* Status notification banner if set */}
        {adminMessage && (
          <div className="my-4 p-3 bg-[#EEF1EF] border border-[#CBD5D0] text-[13px] text-[#1C2A33] font-sans flex items-center justify-between">
            <span>{adminMessage}</span>
            <button
              type="button"
              onClick={() => setAdminMessage(null)}
              className="text-[12px] text-[#4F5F69] hover:text-[#1C2A33] underline ml-4"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Main Grid: Left Plain-Text Navigation (20%) + Right Content (80%) */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 pt-6">
          {/* Plain-text Left Navigation */}
          <nav className="md:col-span-3 space-y-1.5 border-r border-[#CBD5D0] pr-6">
            <div className="text-[12px] font-normal text-[#4F5F69] pb-2 border-b border-[#CBD5D0]/60 mb-2">
              Navigation
            </div>
            {tabs.map((t) => {
              const isActive = activeTab === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => {
                    setActiveTab(t.id);
                    setAdminMessage(null);
                  }}
                  className={`w-full text-left py-1.5 px-2 text-[14px] font-sans transition-colors focus:outline-none focus:ring-2 focus:ring-[#1C2A33] ${
                    isActive
                      ? "text-[#1C2A33] font-bold bg-[#CBD5D0]/40 border-l-2 border-[#1C2A33]"
                      : "text-[#4F5F69] hover:text-[#1C2A33] hover:bg-[#CBD5D0]/20"
                  }`}
                >
                  {t.label}
                </button>
              );
            })}
          </nav>

          {/* Right Content Area */}
          <main className="md:col-span-9">
            {/* 1. Overview */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                <h2 className="text-[18px] font-bold text-[#1C2A33] pb-2 border-b border-[#CBD5D0]">
                  System Overview
                </h2>
                <p className="text-[14px] text-[#4F5F69] leading-relaxed">
                  Full-stack environmental anomaly detection prototype for an edge ESP32 + DHT11 node streaming over USB serial at 115,200 baud. The system couples a rate-gated Adaptive Cauchy EWMA baseline with an in-sample calibrated Isolation Forest detector.
                </p>

                <div className="border border-[#CBD5D0] bg-[#EEF1EF] p-4 text-[13px] space-y-2">
                  <div className="font-bold text-[#1C2A33]">Detector Architecture & Invariance</div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-[#4F5F69]">
                    <div>
                      <span className="font-semibold text-[#1C2A33]">Version:</span> {modelDetails?.version || "v2.0-hybrid"}
                    </div>
                    <div>
                      <span className="font-semibold text-[#1C2A33]">Verified commit:</span> {modelDetails?.commit_hash || "10347c2"}
                    </div>
                    <div>
                      <span className="font-semibold text-[#1C2A33]">Feature dimensions:</span> 12 causal rate/residual features
                    </div>
                    <div>
                      <span className="font-semibold text-[#1C2A33]">Isolation Forest cutoff:</span> {modelDetails?.iforest_threshold || -0.21657}
                    </div>
                    <div>
                      <span className="font-semibold text-[#1C2A33]">Normal temperature mean:</span> {modelDetails?.normal_temp_mean ?? 25.67} °C (std: {modelDetails?.normal_temp_std ?? 0.83})
                    </div>
                    <div>
                      <span className="font-semibold text-[#1C2A33]">Normal humidity mean:</span> {modelDetails?.normal_hum_mean ?? 61.42}% (std: {modelDetails?.normal_hum_std ?? 4.40})
                    </div>
                  </div>
                </div>

                <div className="text-[13px] text-[#4F5F69]">
                  Single-node USB serial connection. Certified for prototype monitoring and research evaluation.
                </div>
              </div>
            )}

            {/* 2. Live Monitor */}
            {activeTab === "live" && (
              <div className="space-y-6">
                <h2 className="text-[18px] font-bold text-[#1C2A33] pb-2 border-b border-[#CBD5D0]">
                  Live Monitor & Hardware Control
                </h2>

                <div className="border border-[#CBD5D0] bg-[#EEF1EF] p-4 space-y-4">
                  <h3 className="text-[14px] font-bold text-[#1C2A33]">Hardware Serial Port</h3>
                  <div className="text-[13px] text-[#4F5F69]">
                    Current stream state:{" "}
                    <span className="font-bold text-[#1C2A33]">
                      {serialStatus?.is_streaming ? `Streaming (${serialStatus.stream_source})` : "Stopped"}
                    </span>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => handleStartSerial("COM19", 115200)}
                      disabled={serialStatus?.is_streaming}
                      className="px-4 py-2 bg-[#1C2A33] text-white text-[13px] hover:bg-[#2e404d] disabled:opacity-50"
                    >
                      Start serial
                    </button>
                    <button
                      type="button"
                      onClick={handleStopSerial}
                      disabled={!serialStatus?.is_streaming}
                      className="px-4 py-2 border border-[#CBD5D0] text-[#1C2A33] text-[13px] hover:bg-[#CBD5D0]/30 disabled:opacity-50"
                    >
                      Stop serial
                    </button>
                  </div>

                  <div className="pt-2 text-[12px] text-[#4F5F69]">
                    Ports detected (Bluetooth excluded): {ports.length ? ports.map((p) => p.port || p.device).join(", ") : "COM19 (fallback)"}
                  </div>
                </div>

                <div className="border border-[#CBD5D0] bg-[#EEF1EF] p-4 space-y-4">
                  <h3 className="text-[14px] font-bold text-[#1C2A33]">Simulation Stream Playback</h3>
                  <p className="text-[13px] text-[#4F5F69]">
                    Replay recorded datasets or synthetic fault injections with zero hardware attached.
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <button
                      type="button"
                      onClick={() => handleStartSimulation("eval_suite", 1.0)}
                      disabled={serialStatus?.is_streaming}
                      className="px-3.5 py-1.5 border border-[#1C2A33] text-[#1C2A33] text-[13px] hover:bg-[#CBD5D0]/40 disabled:opacity-50"
                    >
                      Replay multi-fault suite (1,947 rows)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleStartSimulation("pilot", 1.0)}
                      disabled={serialStatus?.is_streaming}
                      className="px-3.5 py-1.5 border border-[#1C2A33] text-[#1C2A33] text-[13px] hover:bg-[#CBD5D0]/40 disabled:opacity-50"
                    >
                      Replay physical pilot (3,084 rows)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleStartSimulation("test", 1.0)}
                      disabled={serialStatus?.is_streaming}
                      className="px-3.5 py-1.5 border border-[#1C2A33] text-[#1C2A33] text-[13px] hover:bg-[#CBD5D0]/40 disabled:opacity-50"
                    >
                      Replay thermal spike test (55 rows)
                    </button>
                    <button
                      type="button"
                      onClick={handleStopSimulation}
                      disabled={!serialStatus?.is_streaming}
                      className="px-3.5 py-1.5 bg-[#9B2C2C] text-white text-[13px] hover:bg-[#b03535] disabled:opacity-50"
                    >
                      Stop simulation
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* 3. Evaluation */}
            {activeTab === "evaluation" && (
              <div className="space-y-6">
                <h2 className="text-[18px] font-bold text-[#1C2A33] pb-2 border-b border-[#CBD5D0]">
                  Model Evaluation & Provenance
                </h2>
                <div className="p-3 bg-[#EEF1EF] border border-[#CBD5D0] text-[13px] text-[#4F5F69] space-y-1">
                  <div>
                    <strong className="text-[#1C2A33]">Tuning Note:</strong> The 0.25th-percentile cutoff (-0.21657) was calibrated on the synthetic evaluation suite.
                  </div>
                  <div>
                    <strong className="text-[#1C2A33]">Synthetic Provenance:</strong> All anomalies in the evaluation suite and external benchmarks (UCI Occupancy, IoTsec) are synthetic injections on normal traces.
                  </div>
                  <div>
                    <strong className="text-[#1C2A33]">Relabelled Pilot Note:</strong> Pilot event 1 was extended from 27 to 466 rows after inspecting initial detection curves, so pilot metrics represent development data.
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left text-[13px] font-sans">
                    <thead>
                      <tr className="border-b border-[#CBD5D0] text-[#4F5F69]">
                        <th className="py-2 font-normal">Dataset</th>
                        <th className="py-2 font-normal">Rows / Events</th>
                        <th className="py-2 font-normal">Provenance</th>
                        <th className="py-2 font-normal">Role</th>
                        <th className="py-2 font-normal">TP</th>
                        <th className="py-2 font-normal">FP</th>
                        <th className="py-2 font-normal">Precision</th>
                        <th className="py-2 font-normal">Recall</th>
                        <th className="py-2 font-normal">F1</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#CBD5D0]/60">
                      {/* Pilot Original Labels */}
                      <tr className="hover:bg-[#CBD5D0]/20">
                        <td className="py-2 font-semibold">Pilot (Original labels)</td>
                        <td className="py-2 num-tabular">3,084 rows / 46 pos</td>
                        <td className="py-2">Recorded</td>
                        <td className="py-2">Development (preliminary)</td>
                        <td className="py-2 num-tabular">46</td>
                        <td className="py-2 num-tabular">280</td>
                        <td className="py-2 num-tabular">0.141</td>
                        <td className="py-2 num-tabular">1.000</td>
                        <td className="py-2 font-bold num-tabular">0.247</td>
                      </tr>

                      {/* Pilot Revised Labels */}
                      <tr className="hover:bg-[#CBD5D0]/20">
                        <td className="py-2 font-semibold">Pilot (Revised labels)</td>
                        <td className="py-2 num-tabular">3,084 rows / 504 pos</td>
                        <td className="py-2">Recorded</td>
                        <td className="py-2">Development (post-hoc)</td>
                        <td className="py-2 num-tabular">470</td>
                        <td className="py-2 num-tabular">0</td>
                        <td className="py-2 num-tabular">1.000</td>
                        <td className="py-2 num-tabular">0.933</td>
                        <td className="py-2 font-bold num-tabular">0.965</td>
                      </tr>

                      {/* Synthetic Evaluation Suite */}
                      <tr className="hover:bg-[#CBD5D0]/20">
                        <td className="py-2 font-semibold">Synthetic Evaluation Suite</td>
                        <td className="py-2 num-tabular">1,947 rows / 143 pos</td>
                        <td className="py-2">Synthetic (injected)</td>
                        <td className="py-2">Held-out</td>
                        <td className="py-2 num-tabular">138</td>
                        <td className="py-2 num-tabular">4</td>
                        <td className="py-2 num-tabular">0.972</td>
                        <td className="py-2 num-tabular">0.965</td>
                        <td className="py-2 font-bold num-tabular">0.968</td>
                      </tr>

                      {/* IoTsec External Benchmark */}
                      <tr className="hover:bg-[#CBD5D0]/20">
                        <td className="py-2 font-semibold">IoTsec Room-Climate</td>
                        <td className="py-2 num-tabular">1,000 rows / 70 pos</td>
                        <td className="py-2">Synthetic injection</td>
                        <td className="py-2">Held-out</td>
                        <td className="py-2 num-tabular">69</td>
                        <td className="py-2 num-tabular text-[#9B2C2C] font-bold">470</td>
                        <td className="py-2 num-tabular text-[#9B2C2C] font-bold">0.509</td>
                        <td className="py-2 num-tabular">0.994</td>
                        <td className="py-2 font-bold num-tabular">0.673</td>
                      </tr>

                      {/* UCI Occupancy External Benchmark */}
                      <tr className="hover:bg-[#CBD5D0]/20">
                        <td className="py-2 font-semibold">UCI Occupancy #357</td>
                        <td className="py-2 num-tabular">2,665 rows / 473 pos</td>
                        <td className="py-2">Recorded (occupancy)</td>
                        <td className="py-2">Held-out</td>
                        <td className="py-2 num-tabular">281</td>
                        <td className="py-2 num-tabular">15</td>
                        <td className="py-2 num-tabular">0.948</td>
                        <td className="py-2 num-tabular">0.595</td>
                        <td className="py-2 font-bold num-tabular">0.731</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <p className="text-[12px] text-[#4F5F69]">
                  High false positive count on IoTsec (470 false alarms) demonstrates cross-domain sensitivity to baseline shifts, indicating that external transferability requires site calibration.
                </p>
              </div>
            )}

            {/* 4. Datasets */}
            {activeTab === "datasets" && (
              <div className="space-y-6">
                <h2 className="text-[18px] font-bold text-[#1C2A33] pb-2 border-b border-[#CBD5D0]">
                  Dataset Registry & Provenance
                </h2>

                <div className="p-3 bg-[#EEF1EF] border border-[#CBD5D0] text-[13px] text-[#4F5F69]">
                  <strong className="text-[#1C2A33]">Overlap Finding:</strong> <code>test.csv</code> and <code>pilot_data.csv</code> share 35 identical rows between 22:02:14 and 22:03:23 on 2026-10-27. The pilot has no rows for 22:03:25 to 22:04:05 where the test event is located.
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left text-[13px] font-sans">
                    <thead>
                      <tr className="border-b border-[#CBD5D0] text-[#4F5F69]">
                        <th className="py-2 font-normal">Dataset</th>
                        <th className="py-2 font-normal">Rows</th>
                        <th className="py-2 font-normal">Time Range</th>
                        <th className="py-2 font-normal">Provenance</th>
                        <th className="py-2 font-normal">Role</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#CBD5D0]/60">
                      <tr>
                        <td className="py-2 font-semibold">Training Baseline (Clean)</td>
                        <td className="py-2 num-tabular">34,374</td>
                        <td className="py-2">9 recorded sessions (&lt; Nov 1, 2026)</td>
                        <td className="py-2">Recorded (389 quarantined)</td>
                        <td className="py-2">Training</td>
                      </tr>
                      <tr>
                        <td className="py-2 font-semibold">Physical Pilot Data</td>
                        <td className="py-2 num-tabular">3,084</td>
                        <td className="py-2">2026-10-27 21:00:00 to 22:42:48</td>
                        <td className="py-2">Recorded (relabelled post-hoc)</td>
                        <td className="py-2">Development</td>
                      </tr>
                      <tr>
                        <td className="py-2 font-semibold">Legacy Test Set</td>
                        <td className="py-2 num-tabular">55</td>
                        <td className="py-2">2026-10-27 22:02:14 to 22:04:05</td>
                        <td className="py-2">Recorded (single thermal event)</td>
                        <td className="py-2">Development</td>
                      </tr>
                      <tr>
                        <td className="py-2 font-semibold">Evaluation Suite</td>
                        <td className="py-2 num-tabular">1,947</td>
                        <td className="py-2">6 injected fault sequences</td>
                        <td className="py-2">Synthetic injection (seed=42)</td>
                        <td className="py-2">Held-out</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="pt-4 border-t border-[#CBD5D0] flex flex-wrap gap-4">
                  <a
                    href="/api/admin/datasets/download/clean_baseline.csv"
                    download="clean_baseline.csv"
                    className="inline-block px-3 py-1.5 border border-[#1C2A33] text-[13px] text-[#1C2A33] hover:bg-[#1C2A33] hover:text-white transition-colors"
                  >
                    Download clean_baseline.csv
                  </a>
                  <a
                    href="/api/admin/datasets/download/test.csv"
                    download="test.csv"
                    className="inline-block px-3 py-1.5 border border-[#1C2A33] text-[13px] text-[#1C2A33] hover:bg-[#1C2A33] hover:text-white transition-colors"
                  >
                    Download test.csv
                  </a>
                </div>
              </div>
            )}

            {/* 5. Alerts */}
            {activeTab === "alerts" && (
              <div className="space-y-6">
                <h2 className="text-[18px] font-bold text-[#1C2A33] pb-2 border-b border-[#CBD5D0]">
                  Alert History & Export
                </h2>
                <p className="text-[13px] text-[#4F5F69]">
                  Export event detection ledger to standard CSV for offline inspection and verification.
                </p>
                <div>
                  <a
                    href="/api/admin/alerts/export"
                    download="alert_history.csv"
                    className="inline-block px-4 py-2 bg-[#1C2A33] text-white text-[13px] hover:bg-[#2e404d] transition-colors"
                  >
                    Export alerts CSV
                  </a>
                </div>
              </div>
            )}

            {/* 6. Settings */}
            {activeTab === "settings" && (
              <div className="space-y-6">
                <h2 className="text-[18px] font-bold text-[#1C2A33] pb-2 border-b border-[#CBD5D0]">
                  Detector Sensitivity & Threshold Calibration
                </h2>

                <p className="text-[13px] text-[#4F5F69] leading-relaxed">
                  Calibrate the Isolation Forest percentile contamination threshold. Higher sensitivity increases anomaly detection rate but increases the number of false alarms.
                </p>

                <div className="space-y-3 max-w-[500px]">
                  {[
                    {
                      id: "Low",
                      label: "Low (0.5th percentile)",
                      cutoff: "-0.205",
                      desc: "Conservative; catches large thermal excursions with minimal false alarms.",
                    },
                    {
                      id: "Medium",
                      label: "Medium (1.0th percentile, default)",
                      cutoff: "-0.21657",
                      desc: "Balanced; calibrated on clean training set.",
                    },
                    {
                      id: "High",
                      label: "High (5.0th percentile)",
                      cutoff: "-0.235",
                      desc: "Strict; detects subtle departures but triggers more frequent false alarms.",
                    },
                  ].map((preset) => {
                    const isSelected = sensitivitySetting === preset.id;
                    return (
                      <div
                        key={preset.id}
                        onClick={() => handleSaveSensitivity(preset.id)}
                        className={`p-3 border cursor-pointer transition-colors ${
                          isSelected
                            ? "border-[#1C2A33] bg-[#CBD5D0]/30"
                            : "border-[#CBD5D0] hover:bg-[#CBD5D0]/10"
                        }`}
                      >
                        <div className="flex justify-between items-center text-[14px]">
                          <span className="font-bold text-[#1C2A33]">{preset.label}</span>
                          <span className="text-[12px] num-tabular text-[#4F5F69]">
                            Cutoff: {preset.cutoff}
                          </span>
                        </div>
                        <div className="text-[12px] text-[#4F5F69] mt-1">{preset.desc}</div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* 7. Audit */}
            {activeTab === "audit" && (
              <div className="space-y-6">
                <h2 className="text-[18px] font-bold text-[#1C2A33] pb-2 border-b border-[#CBD5D0]">
                  System Action Audit Trail
                </h2>

                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left text-[13px] font-sans">
                    <thead>
                      <tr className="border-b border-[#CBD5D0] text-[#4F5F69]">
                        <th className="py-2 font-normal">Timestamp</th>
                        <th className="py-2 font-normal">Action</th>
                        <th className="py-2 font-normal">Actor</th>
                        <th className="py-2 font-normal">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#CBD5D0]/60">
                      {auditLogs && auditLogs.length > 0 ? (
                        auditLogs.map((log, idx) => (
                          <tr key={`aud-${log.id || idx}`}>
                            <td className="py-2 num-tabular text-[#4F5F69]">
                              {log.timestamp ? log.timestamp.slice(0, 19) : "—"}
                            </td>
                            <td className="py-2 font-semibold text-[#1C2A33]">{log.action}</td>
                            <td className="py-2 text-[#4F5F69]">{log.actor}</td>
                            <td className="py-2 text-[#1C2A33]">{log.details}</td>
                          </tr>
                        ))
                      ) : (
                        <tr>
                          <td colSpan="4" className="py-4 text-[#4F5F69]">
                            No administrative audit records logged yet.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </div>
  );
}
