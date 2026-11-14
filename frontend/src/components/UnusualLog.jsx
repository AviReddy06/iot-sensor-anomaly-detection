// frontend/src/components/UnusualLog.jsx
// Structured log of unusual readings with standardized typography and right-aligned numeric data
import React, { useState } from "react";

// Helper: format string with initial capital letter
function capitalizeInitial(str) {
  if (!str || str.length === 0) return str;
  const code = str.charCodeAt(0);
  if (code >= 97 && code <= 122) {
    return String.fromCharCode(code - 32) + str.slice(1);
  }
  return str;
}

export default function UnusualLog({ events = [], onSelectEvent }) {
  const [showDisclosure, setShowDisclosure] = useState(false);

  // Step 1: Deduplicate events by start_time and end_time
  const uniqueEvents = React.useMemo(() => {
    if (!events || events.length === 0) return [];
    const seen = new Set();
    const result = [];
    for (const ev of events) {
      const key = `${ev.start_time || ""}_${ev.end_time || ""}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push(ev);
      }
    }
    return result;
  }, [events]);

  return (
    <div className="w-full flex flex-col">
      {/* Step 2: Table Title Bar and Disclosure Toggle */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-2 border-b border-[#CBD5D0]">
        <div className="text-[15px] font-bold text-[#1C2A33] font-sans">
          Log of unusual readings
        </div>
        <button
          type="button"
          onClick={() => setShowDisclosure((prev) => !prev)}
          className="text-[13px] text-[#4F5F69] hover:text-[#1C2A33] underline transition-colors focus:outline-none focus:ring-2 focus:ring-[#1C2A33]"
        >
          {showDisclosure ? "Hide how severity is decided" : "How severity is decided"}
        </button>
      </div>

      {/* Step 3: Severity Disclosure Note (constrained to <62ch measure) */}
      {showDisclosure && (
        <div className="p-3 my-2 bg-[#EEF1EF] border border-[#CBD5D0] text-[13px] text-[#4F5F69] leading-relaxed font-sans text-pretty max-w-[62ch]">
          Severity reflects how far readings drifted from the room's usual baseline and how long the change lasted. Low indicates a brief or mild deviation that resolved quickly; Medium indicates a noticeable departure lasting more than 15 seconds; High indicates a steep spike, persistent shift, or rapid dual-metric change.
        </div>
      )}

      {/* Step 4: Event Log - Mobile 2-Line Cards and Desktop Table */}
      {uniqueEvents && uniqueEvents.length > 0 ? (
        <>
          {/* Step 4a: Mobile 2-Line Event Cards (sm:hidden) */}
          <div className="sm:hidden mt-6 divide-y divide-[#CBD5D0]/60">
            {uniqueEvents.map((ev, idx) => {
              const eventNum = idx + 1;
              const startTimeStr =
                ev.start_time && ev.start_time.length >= 16
                  ? ev.start_time.slice(11, 16)
                  : ev.start_time || "—";
              const durStr = ev.duration_sec
                ? `${Math.round(ev.duration_sec)}\u2009s`
                : "—";
              const rawWhat =
                ev.what_changed ||
                (ev.sentence ? ev.sentence : "Unusual reading detected");
              const whatChanged = capitalizeInitial(rawWhat);

              return (
                <div
                  key={`card-${eventNum}-${idx}`}
                  onClick={() => onSelectEvent?.(ev)}
                  className="py-3 flex flex-col gap-1 cursor-pointer hover:bg-[#CBD5D0]/20 transition-colors"
                >
                  <div className="flex items-center justify-between text-[13px] font-sans">
                    <div className="flex items-center gap-3">
                      <span className="font-bold text-[#1C2A33]">#{eventNum}</span>
                      <span className="text-[#4F5F69] num-tabular">{startTimeStr}</span>
                      <span className="text-[#4F5F69] num-tabular">{durStr}</span>
                    </div>
                    <span
                      className={`inline-block px-2 py-0.5 text-[13px] font-medium border ${
                        ev.severity === "High"
                          ? "border-[#7A4B00] text-[#7A4B00] bg-[rgba(232,176,74,0.25)]"
                          : ev.severity === "Medium"
                          ? "border-[#7A4B00] text-[#7A4B00]"
                          : "border-[#4F5F69] text-[#4F5F69]"
                      }`}
                    >
                      {ev.severity || "Unusual"}
                    </span>
                  </div>
                  <div className="text-[14px] text-[#1C2A33] font-sans">
                    {whatChanged}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Step 4b: Desktop Tabular Event Log (hidden sm:block) */}
          <div className="hidden sm:block w-full overflow-x-auto mt-6">
            <table className="w-full border-collapse text-left text-[15px] font-sans">
              <thead>
                <tr className="border-b border-[#CBD5D0] text-[#4F5F69] text-[13px]">
                  <th className="py-2.5 pr-4 font-normal">Event</th>
                  <th className="py-2.5 pr-4 font-normal">Start</th>
                  <th className="py-2.5 pr-4 font-normal text-right">Duration</th>
                  <th className="py-2.5 pr-4 font-normal">What changed</th>
                  <th className="py-2.5 pr-4 font-normal text-right">Peak temperature</th>
                  <th className="py-2.5 pr-4 font-normal text-right">Peak humidity</th>
                  <th className="py-2.5 font-normal">Severity</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#CBD5D0]/60">
                {uniqueEvents.map((ev, idx) => {
                  const eventNum = idx + 1;
                  const startTimeStr =
                    ev.start_time && ev.start_time.length >= 19
                      ? ev.start_time.slice(11, 19)
                      : ev.start_time || "—";
                  const durStr = ev.duration_sec
                    ? `${Math.round(ev.duration_sec)}\u2009s`
                    : "—";
                  const peakTempStr =
                    ev.peak_temp !== undefined && ev.peak_temp !== null
                      ? `${Number(ev.peak_temp).toFixed(1)}\u2009°C`
                      : "—";
                  const peakHumStr =
                    ev.peak_hum !== undefined && ev.peak_hum !== null
                      ? `${Number(ev.peak_hum).toFixed(1)}\u2009% RH`
                      : "—";
                  const rawWhat =
                    ev.what_changed ||
                    (ev.sentence ? ev.sentence : "Unusual reading detected");
                  const whatChanged = capitalizeInitial(rawWhat);

                  return (
                    <tr
                      key={`log-${eventNum}-${idx}`}
                      onClick={() => onSelectEvent?.(ev)}
                      className="hover:bg-[#CBD5D0]/30 cursor-pointer transition-colors"
                    >
                      <td className="py-2.5 pr-4 font-bold text-[#1C2A33]">
                        {eventNum}
                      </td>
                      <td className="py-2.5 pr-4 text-[#4F5F69] num-tabular">
                        {startTimeStr}
                      </td>
                      <td className="py-2.5 pr-4 text-[#4F5F69] num-tabular text-right">
                        {durStr}
                      </td>
                      <td className="py-2.5 pr-4 text-[#1C2A33]">
                        {whatChanged}
                      </td>
                      <td className="py-2.5 pr-4 text-[#9B2C2C] font-semibold num-tabular text-right">
                        {peakTempStr}
                      </td>
                      <td className="py-2.5 pr-4 text-[#1D5C8C] font-semibold num-tabular text-right">
                        {peakHumStr}
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`inline-block px-2 py-0.5 text-[13px] font-medium border ${
                            ev.severity === "High"
                              ? "border-[#7A4B00] text-[#7A4B00] bg-[rgba(232,176,74,0.25)]"
                              : ev.severity === "Medium"
                              ? "border-[#7A4B00] text-[#7A4B00]"
                              : "border-[#4F5F69] text-[#4F5F69]"
                          }`}
                        >
                          {ev.severity || "Unusual"}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="py-6 border-b border-[#CBD5D0] text-[15px] text-[#4F5F69] font-sans">
          No unusual readings recorded.
        </div>
      )}
    </div>
  );
}
