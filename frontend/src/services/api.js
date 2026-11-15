/**
 * frontend/src/services/api.js
 * Centralized API client for communicating with the FastAPI backend.
 */

const getApiBase = () => {
  if (typeof window !== "undefined") {
    // If running in Vite dev server (port 5173 or 3000), point to FastAPI backend
    if (window.location.port === "5173" || window.location.port === "3000") {
      return "http://localhost:8000/api";
    }
    // If running on Render static site, use the backend URL from env or detect
    if (window.location.hostname.includes(".onrender.com")) {
      // Frontend is on *.onrender.com, backend is on iot-anomaly-backend.onrender.com
      return "https://iot-anomaly-backend.onrender.com/api";
    }
    // When served directly by FastAPI (e.g. port 8000), use relative /api
    return "/api";
  }
  return "http://localhost:8000/api";
};

export async function fetchApi(endpoint, options = {}) {
  const url = `${getApiBase()}${endpoint}`;
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    let errorDetail = "API request failed";
    try {
      const err = await response.json();
      errorDetail = err.detail || JSON.stringify(err);
    } catch {
      errorDetail = await response.text();
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

export const api = {
  // System Status
  getStatus: () => fetchApi("/status"),

  // Models & Metrics
  getModelInfo: () => fetchApi("/models/info"),
  getBenchmarks: () => fetchApi("/models/benchmarks"),
  updateThresholds: (data) =>
    fetchApi("/thresholds/update", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Serial & Simulation
  getSerialPorts: () => fetchApi("/serial/ports"),
  startSerialStream: (port, baud = 115200) =>
    fetchApi("/serial/start", {
      method: "POST",
      body: JSON.stringify({ port, baud }),
    }),
  stopStream: () =>
    fetchApi("/serial/stop", {
      method: "POST",
    }),
  startSimulation: (dataset_name = "eval_suite", interval_sec = 1.0) =>
    fetchApi("/simulation/start", {
      method: "POST",
      body: JSON.stringify({ dataset_name, interval_sec }),
    }),
  stopSimulation: () =>
    fetchApi("/simulation/stop", {
      method: "POST",
    }),

  // Telemetry & Incidents
  getRecentTelemetry: () => fetchApi("/telemetry/recent"),
  getRecentIncidents: () => fetchApi("/incidents"),

  // Datasets & Upload
  getDatasets: () => fetchApi("/datasets"),
  getDatasetAnalysis: (name) => fetchApi(`/datasets/${name}`),
  uploadDataset: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await fetch(`${getApiBase()}/datasets/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || "Upload failed");
    }
    return response.json();
  },

  // Alerts
  getAlertsConfig: () => fetchApi("/alerts/config"),
  updateAlertsConfig: (config) =>
    fetchApi("/alerts/config", {
      method: "POST",
      body: JSON.stringify(config),
    }),
  testAlert: () =>
    fetchApi("/alerts/test", {
      method: "POST",
    }),
};
