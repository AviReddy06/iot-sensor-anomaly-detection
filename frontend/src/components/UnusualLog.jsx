import React, { useState } from "react";

export default function UnusualLog({ events = [], onSelectEvent }) {
  const [showDisclosure, setShowDisclosure] = useState(false);

  // Deduplicate events by start_time and end_time so simulation replays never stack duplicate rows
  const uniqueEvents = React.useMemo(() => {
    if (!events || events.length === 0) return [];
    const seen = new Set();
    const result = [];
    for (const ev of events) {
      const key = `${ev.start_time || ''}_${ev.end_time || ''}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push(ev);
      }
    }
    return result;
  }, [events]);

  return (
    <div className="w-full flex flex-col mt-8">
      {/* Table Title and Disclosure Toggle */}
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

      {/* Severity Disclosure Note */}
      {showDisclosure && (
        <div className="p-3 my-2 bg-[#EEF1EF] border border-[#CBD5D0] text-[13px] text-[#4F5F69] leading-relaxed font-sans">
          Severity reflects how far readings drifted from the room's usual baseline and how long the change lasted. Low indicates a brief or mild deviation that resolved quickly; Medium indicates a noticeable departure lasting more than 15 seconds; High indicates a steep spike, persistent shift, or rapid dual-metric change.
        </div>
      )}

      {/* Tabular Log */}
      {uniqueEvents && uniqueEvents.length > 0 ? (
        <div className="w-full overflow-x-auto mt-2">
          <table className="w-full min-w-[640px] border-collapse text-left text-[14px] font-sans">
            <thead>
              <tr className="border-b border-[#CBD5D0] text-[#4F5F69] text-[13px]">
                <th className="py-2.5 pr-4 font-normal">Event</th>
                <th className="py-2.5 pr-4 font-normal">Start</th>
                <th className="py-2.5 pr-4 font-normal">Duration</th>
                <th className="py-2.5 pr-4 font-normal">What changed</th>
                <th className="py-2.5 pr-4 font-normal">Peak temperature</th>
                <th className="py-2.5 pr-4 font-normal">Peak humidity</th>
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
                  ? `${Math.round(ev.duration_sec)} s`
                  : "—";
                const peakTempStr =
                  ev.peak_temp !== undefined && ev.peak_temp !== null
                    ? `${Number(ev.peak_temp).toFixed(1)} °C`
                    : "—";
                const peakHumStr =
                  ev.peak_hum !== undefined && ev.peak_hum !== null
                    ? `${Number(ev.peak_hum).toFixed(1)}% RH`
                    : "—";
                const whatChanged =
                  ev.what_changed ||
                  (ev.sentence ? ev.sentence : "Unusual reading detected");

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
                    <td className="py-2.5 pr-4 text-[#4F5F69] num-tabular">
                      {durStr}
                    </td>
                    <td className="py-2.5 pr-4 text-[#1C2A33]">
                      {whatChanged}
                    </td>
                    <td className="py-2.5 pr-4 text-[#9B2C2C] font-semibold num-tabular">
                      {peakTempStr}
                    </td>
                    <td className="py-2.5 pr-4 text-[#1D5C8C] font-semibold num-tabular">
                      {peakHumStr}
                    </td>
                    <td className="py-2.5">
                      <span
                        className={`inline-block px-2 py-0.5 text-[12px] font-medium border ${
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
      ) : (
        <div className="py-6 border-b border-[#CBD5D0] text-[14px] text-[#4F5F69] font-sans">
          No unusual readings recorded.
        </div>
      )}
    </div>
  );
}
