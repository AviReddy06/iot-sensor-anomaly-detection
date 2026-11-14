// frontend/src/views/ClientView.jsx
// Client-facing digital thermohygrograph view
import React, { useState } from "react";
import { useClientData } from "../hooks/useClientData";
import ClientStripChart from "../components/ClientStripChart";
import RoomMap from "../components/RoomMap";
import UnusualLog from "../components/UnusualLog";

export default function ClientView() {
  const { statusData, readings, events, loadError } = useClientData();
  const [activeRange, setActiveRange] = useState("1 h");
  const [selectedEvent, setSelectedEvent] = useState(null);

  // Step 1: Format telemetry readings and timestamps
  const currentTemp = statusData?.current_temperature ?? (readings.length ? readings[readings.length - 1].temperature : null);
  const currentHum = statusData?.current_humidity ?? (readings.length ? readings[readings.length - 1].humidity : null);
  const statusLabel = statusData?.status || (readings.length ? "Simulated" : "Offline");
  const lastTime = statusData?.last_reading_time || (readings.length ? readings[readings.length - 1].timestamp : null);

  const formattedTime = lastTime
    ? lastTime.length >= 19
      ? lastTime.slice(11, 19)
      : lastTime
    : "—";

  // Step 2: Formulate headline sentence and supporting reading copy
  let headline = "The room is normal.";
  if (statusData?.headline) {
    headline = statusData.headline;
  } else if (statusData?.active_unusual_reading) {
    headline = "Unusual reading detected.";
  }

  return (
    <div className="min-h-screen bg-[#EEF1EF] text-[#1C2A33] selection:bg-[#CBD5D0]">
      <div className="max-w-[1120px] mx-auto px-5 sm:px-8 py-8 sm:py-10">
        {/* Step 3: Header Bar - Title and Status Dot */}
        <header className="flex flex-wrap items-baseline justify-between gap-3 pb-6 border-b border-[#CBD5D0]">
          <div>
            <h1 className="text-[20px] sm:text-[22px] font-bold text-[#1C2A33] tracking-normal font-sans">
              AI-Based IoT Sensor Anomaly Detection
            </h1>
          </div>

          <div className="flex items-center gap-2.5 text-[13px] text-[#4F5F69] font-sans">
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

        {/* Step 4: Headline in Literata 500 (40/1.2) & Supporting Sentence (20/1.4) */}
        <section className="pt-6 mb-[72px]">
          <h2 className="text-[28px] sm:text-[40px] font-medium leading-[1.2] text-[#1C2A33] font-serif text-balance max-w-[62ch]">
            {headline}
          </h2>
          <div className="text-[18px] sm:text-[20px] leading-[1.4] text-[#4F5F69] mt-6 font-sans text-pretty max-w-[62ch]">
            {currentTemp !== null && currentHum !== null ? (
              <span>
                Current reading at <span className="text-[#1C2A33] font-medium num-tabular">{formattedTime}</span>:{" "}
                <span className="text-[#9B2C2C] font-semibold num-tabular">
                  {Number(currentTemp).toFixed(1)}{"\u2009"}°C
                </span>
                {", "}
                <span className="text-[#1D5C8C] font-semibold num-tabular">
                  {Number(currentHum).toFixed(1)}{"\u2009"}% RH
                </span>
                {"."}
              </span>
            ) : readings.length === 0 ? (
              <span>No readings yet. Start the sensor or switch to the demo.</span>
            ) : (
              <span>Reading the sensor.</span>
            )}
          </div>

          {loadError && (
            <div className="mt-6 p-3 bg-[#EEF1EF] border border-[#CBD5D0] text-[13px] text-[#7A4B00] font-sans max-w-[62ch]">
              {loadError}
            </div>
          )}
        </section>

        {/* Step 5: Strip Chart (62%) and Room Map (34%) Layout */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          <div className="lg:col-span-8 w-full">
            <ClientStripChart
              readings={readings}
              events={events}
              activeRange={activeRange}
              onRangeChange={setActiveRange}
              highlightedEvent={selectedEvent}
            />
          </div>

          <div className="lg:col-span-4 w-full">
            <RoomMap
              readings={readings}
              isUnusual={Boolean(statusData?.active_unusual_reading)}
            />
          </div>
        </section>

        {/* Step 6: Log of Unusual Readings */}
        <section className="mt-[48px]">
          <UnusualLog
            events={events}
            onSelectEvent={(ev) => setSelectedEvent(ev)}
          />
        </section>

        {/* Step 7: Institutional Attribution Footer & Discrete Admin Link */}
        <footer className="mt-[48px] pt-6 border-t border-[#CBD5D0] flex flex-wrap items-center justify-between gap-4 text-[13px] text-[#4F5F69] font-sans">
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
