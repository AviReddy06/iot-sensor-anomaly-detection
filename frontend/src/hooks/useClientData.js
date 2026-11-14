// frontend/src/hooks/useClientData.js
// Dedicated hook for client data acquisition, REST polling, and WebSocket streaming
import { useState, useEffect, useCallback } from "react";

export function useClientData() {
  const [statusData, setStatusData] = useState(null);
  const [readings, setReadings] = useState([]);
  const [events, setEvents] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  // Step 1: Initial hydration & periodic REST polling fallback
  const fetchClientData = useCallback(async () => {
    try {
      const [statusRes, readingsRes, eventsRes] = await Promise.all([
        fetch("/api/client/status").then((r) => (r.ok ? r.json() : null)),
        fetch("/api/client/readings?limit=600").then((r) => (r.ok ? r.json() : [])),
        fetch("/api/client/events?limit=50").then((r) => (r.ok ? r.json() : [])),
      ]);

      if (statusRes) setStatusData(statusRes);
      if (readingsRes && readingsRes.length > 0) setReadings(readingsRes);
      if (eventsRes) setEvents(eventsRes);
      setLoadError(null);
    } catch {
      setLoadError("Could not reach the sensor service. Showing the latest available data.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchClientData();
    const timer = setInterval(fetchClientData, 4000);
    return () => clearInterval(timer);
  }, [fetchClientData]);

  // Step 2: Real-time WebSocket connection for live telemetry stream
  useEffect(() => {
    const wsProto = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsHost = window.location.host;
    const wsUrl = `${wsProto}//${wsHost}/ws/telemetry`;
    let ws = null;
    let reconnectTimeout = null;

    const connectWs = () => {
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

              setReadings((prev) => {
                const next = [...prev, newReading];
                return next.length > 1000 ? next.slice(next.length - 1000) : next;
              });

              setStatusData((prev) => {
                if (!prev) return prev;
                return {
                  ...prev,
                  current_temperature: newReading.temperature,
                  current_humidity: newReading.humidity,
                  last_reading_time: newReading.timestamp,
                  active_unusual_reading: Boolean(data.is_anomaly || data.hybrid_anomaly),
                  status: data.is_simulated ? "Simulated" : "Live",
                };
              });

              // Refresh event log on active anomaly signal
              if (data.is_anomaly || data.hybrid_anomaly) {
                fetch("/api/client/events?limit=50")
                  .then((r) => (r.ok ? r.json() : []))
                  .then((evs) => setEvents(evs))
                  .catch(() => {});
              }
            }
          } catch {
            // Ignore non-JSON broadcast frames
          }
        };
        ws.onclose = () => {
          reconnectTimeout = setTimeout(connectWs, 3000);
        };
      } catch {
        reconnectTimeout = setTimeout(connectWs, 3000);
      }
    };

    connectWs();
    return () => {
      if (ws) ws.close();
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
    };
  }, []);

  return { statusData, readings, events, isLoading, loadError };
}
