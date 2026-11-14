import React, { useState } from "react";
import { AlertTriangle, Info, ChevronDown, ChevronUp } from "lucide-react";

export default function UnusualLog({ events = [], onSelectEvent, highlightedEvent = null }) {
  const [showDisclosure, setShowDisclosure] = useState(false);

  return (
    <div className="w-full bg-[#111827] border border-[#1F2937] rounded-xl p-5 shadow-lg flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#1F2937]">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
            <AlertTriangle className="w-4 h-4" />
          </div>
          <h3 className="text-base font-semibold text-slate-100">Anomaly Incident Ledger</h3>
          <span className="px-2 py-0.5 text-xs font-mono font-medium rounded-full bg-slate-800 text-slate-300 border border-slate-700">
            {events.length} {events.length === 1 ? "Event" : "Events"}
          </span>
        </div>

        <button
          type="button"
          onClick={() => setShowDisclosure((prev) => !prev)}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
        >
          <Info className="w-3.5 h-3.5" />
          <span>Severity criteria</span>
          {showDisclosure ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
      </div>

      {showDisclosure && (
        <div className="mt-3 p-3.5 bg-[#0B0F19] rounded-lg border border-slate-800 text-xs text-slate-300 leading-relaxed">
          <strong className="text-slate-100">Detection Methodology:</strong> Incidents are flagged when sensor telemetry departs significantly from the Cauchy EWMA room baseline or triggers the Isolation Forest multi-feature boundary. 
          <span className="text-amber-400 font-semibold ml-1">High</span> severity indicates rapid simultaneous thermal and moisture spikes lasting &gt; 15 seconds; 
          <span className="text-yellow-400 font-semibold ml-1">Medium</span> indicates noticeable single-channel excursions; 
          <span className="text-blue-400 font-semibold ml-1">Low</span> represents brief transitional fluctuations.
        </div>
      )}

      {events && events.length > 0 ? (
        <div className="w-full overflow-x-auto mt-4">
          <table className="w-full min-w-[640px] border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-slate-800 text-xs font-medium text-slate-400">
                <th className="py-2.5 px-3">Event</th>
                <th className="py-2.5 px-3">Start Time</th>
                <th className="py-2.5 px-3">Duration</th>
                <th className="py-2.5 px-3">Excursion Details</th>
                <th className="py-2.5 px-3 text-right">Peak Temp</th>
                <th className="py-2.5 px-3 text-right">Peak RH</th>
                <th className="py-2.5 px-3 text-center">Severity</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {events.map((ev, idx) => {
                const eventNum = ev.id || idx + 1;
                const startTimeStr = ev.start_time && ev.start_time.length >= 19 ? ev.start_time.slice(11, 19) : ev.start_time || "—";
                const durStr = ev.duration_sec ? `${Math.round(ev.duration_sec)}s` : "—";
                const peakTempStr = ev.peak_temp !== undefined && ev.peak_temp !== null ? `${Number(ev.peak_temp).toFixed(1)} °C` : "—";
                const peakHumStr = ev.peak_hum !== undefined && ev.peak_hum !== null ? `${Number(ev.peak_hum).toFixed(1)}%` : "—";
                const whatChanged = ev.what_changed || ev.sentence || "Unusual reading detected";
                const isSelected = highlightedEvent && (highlightedEvent.id === ev.id || highlightedEvent === ev);

                return (
                  <tr
                    key={`log-${eventNum}-${idx}`}
                    onClick={() => onSelectEvent?.(ev)}
                    className={`cursor-pointer transition-colors ${
                      isSelected ? "bg-amber-500/10 border-l-2 border-amber-500" : "hover:bg-slate-800/40"
                    }`}
                  >
                    <td className="py-3 px-3 font-bold text-slate-200">#{eventNum}</td>
                    <td className="py-3 px-3 text-slate-300">{startTimeStr}</td>
                    <td className="py-3 px-3 text-slate-400">{durStr}</td>
                    <td className="py-3 px-3 font-sans text-xs text-slate-200">{whatChanged}</td>
                    <td className="py-3 px-3 text-right text-rose-400 font-semibold">{peakTempStr}</td>
                    <td className="py-3 px-3 text-right text-sky-400 font-semibold">{peakHumStr}</td>
                    <td className="py-3 px-3 text-center">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-sans font-semibold tracking-wide ${
                          ev.severity === "High"
                            ? "bg-rose-500/15 text-rose-400 border border-rose-500/30"
                            : ev.severity === "Medium"
                            ? "bg-amber-500/15 text-amber-400 border border-amber-500/30"
                            : "bg-blue-500/15 text-blue-400 border border-blue-500/30"
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
        <div className="mt-6 py-10 flex flex-col items-center justify-center text-center text-slate-500">
          <p className="text-sm font-medium text-slate-400">Zero active anomalous excursions detected.</p>
          <p className="text-xs text-slate-500 mt-1">Telemetry stream is operating within normal baseline boundaries.</p>
        </div>
      )}
    </div>
  );
}
