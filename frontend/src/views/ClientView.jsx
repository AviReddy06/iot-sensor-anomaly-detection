import React, { useState, useEffect, useCallback, useRef } from "react";
import ClientStripChart from "../components/ClientStripChart";
import RoomMap from "../components/RoomMap";
import UnusualLog from "../components/UnusualLog";

export default function ClientView() {
  const [statusData, setStatusData] = useState(null);
  const [readings, setReadings] = useState([]);
  const [events, setEvents] = useState([]);
  const [activeRange, setActiveRange] = useState("1 h");
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);

  // Fetch initial client state from safe endpoints
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
    } catch (err) {
      setLoadError("Could not reach the sensor service. Showing the latest available data.");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Hydrate on mount and periodically poll status
  useEffect(() => {
    fetchClientData();
    const timer = setInterval(fetchClientData, 4000);
    return () => clearInterval(timer);
  }, [fetchClientData]);

  // Connect to live WebSocket for real-time trace acquisition
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

              // If an active event occurred, refresh events list
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

  // Format status values
  const currentTemp = statusData?.current_temperature ?? (readings.length ? readings[readings.length - 1].temperature : null);
  const currentHum = statusData?.current_humidity ?? (readings.length ? readings[readings.length - 1].humidity : null);
  const statusLabel = statusData?.status || (readings.length ? "Simulated" : "Offline");
  const lastTime = statusData?.last_reading_time || (readings.length ? readings[readings.length - 1].timestamp : null);

  const formattedTime = lastTime
    ? lastTime.length >= 19
      ? lastTime.slice(11, 19)
      : lastTime
    : "—";

  // Headline sentence composition
  let headline = "The room is normal.";
  if (statusData?.headline) {
    headline = statusData.headline;
  } else if (statusData?.active_unusual_reading) {
    headline = "Unusual reading detected.";
  }

  // Supporting reading line
  const currentLine =
    currentTemp !== null && currentHum !== null
      ? `Current reading: ${Number(currentTemp).toFixed(1)} °C, ${Number(currentHum).toFixed(1)}% RH at ${formattedTime}.`
      : readings.length === 0
      ? "No readings yet. Start the sensor or switch to the demo."
      : "Reading the sensor.";

  return (
    <div className="min-h-screen bg-[#EEF1EF] text-[#1C2A33] selection:bg-[#CBD5D0]">
      <div className="max-w-[1120px] mx-auto px-5 sm:px-8 py-8 sm:py-10">
        {/* 1. Header Bar: Title and Status Dot */}
        <header className="flex flex-wrap items-baseline justify-between gap-3 pb-6 border-b border-[#CBD5D0]">
          <div>
            <h1 className="text-[20px] sm:text-[22px] font-bold text-[#1C2A33] tracking-normal font-sans">
              AI-Based IoT Sensor Anomaly Detection
            </h1>
          </div>

          <div className="flex items-center gap-2.5 px-3 py-1 border border-[#CBD5D0] text-[13px] text-[#4F5F69] font-sans">
            <span className="relative flex h-2 w-2">
              {statusLabel === "Live" && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#28704A] opacity-75" />
              )}
              <span
                className={`relative inline-flex rounded-full h-2 w-2 ${
                  statusLabel === "Live"
                    ? "bg-[#28704A]"
                    : statusLabel === "Simulated"
                    ? "bg-[#7A4B00]"
                    : "bg-[#4F5F69]"
                }`}
              />
            </span>
            <span className="font-medium text-[#1C2A33]">{statusLabel}</span>
            <span className="text-[#CBD5D0]">|</span>
            <span className="text-[#4F5F69] num-tabular">{formattedTime}</span>
          </div>
        </header>

        {/* 2. Headline Sentence in Literata & Current Reading Line */}
        <section className="pt-6 pb-6">
          <h2 className="text-[28px] sm:text-[38px] font-normal leading-tight text-[#1C2A33] font-serif max-w-[840px]">
            {headline}
          </h2>
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2 text-[15px] sm:text-[16px] text-[#4F5F69] mt-3 font-sans leading-relaxed">
            <span>Current reading at <span className="text-[#1C2A33] font-medium num-tabular">{formattedTime}</span>:</span>
            {currentTemp !== null && currentHum !== null ? (
              <span className="inline-flex items-center gap-2">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 border border-[#CBD5D0] bg-[#EEF1EF] text-[#9B2C2C] font-semibold num-tabular">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#9B2C2C]" />
                  {Number(currentTemp).toFixed(1)} °C
                </span>
                <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 border border-[#CBD5D0] bg-[#EEF1EF] text-[#1D5C8C] font-semibold num-tabular">
                  <span className="w-1.5 h-1.5 rounded-full bg-[#1D5C8C]" />
                  {Number(currentHum).toFixed(1)}% RH
                </span>
              </span>
            ) : (
              <span>{currentLine}</span>
            )}
          </div>

          {loadError && (
            <div className="mt-3 p-3 bg-[#EEF1EF] border border-[#CBD5D0] text-[13px] text-[#7A4B00] font-sans">
              {loadError}
            </div>
          )}
        </section>

        {/* 3. Strip Chart (62%) and Room Map (34%) Layout */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start pt-2">
          {/* Dual-Trace Continuous Strip Chart */}
          <div className="lg:col-span-8 w-full">
            <ClientStripChart
              readings={readings}
              events={events}
              activeRange={activeRange}
              onRangeChange={setActiveRange}
              highlightedEvent={selectedEvent}
            />
          </div>

          {/* Room Map Phase Space */}
          <div className="lg:col-span-4 w-full">
            <RoomMap
              readings={readings}
              isUnusual={Boolean(statusData?.active_unusual_reading)}
            />
          </div>
        </section>

        {/* 4. Log of Unusual Readings */}
        <section>
          <UnusualLog
            events={events}
            onSelectEvent={(ev) => setSelectedEvent(ev)}
          />
        </section>

        {/* 5. Institutional Attribution Footer & Discrete Admin Link */}
        <footer className="mt-16 pt-6 border-t border-[#CBD5D0] flex flex-wrap items-center justify-between gap-4 text-[13px] text-[#4F5F69] font-sans">
          <div>
            Dungu Avinash Reddy | Roll RK3P25KZA09 | Reg. 12509090
          </div>
          <div>
            <a
              href="/admin"
              className="text-[#4F5F69] hover:text-[#1C2A33] transition-colors focus:outline-none focus:ring-2 focus:ring-[#1C2A33]"
            >
              Admin login
            </a>
          </div>
        </footer>
      </div>
    </div>
  );
}
