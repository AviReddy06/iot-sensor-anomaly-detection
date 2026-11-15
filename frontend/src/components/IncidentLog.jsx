import React, { useState } from "react";
import { AlertTriangle, Clock, Download } from "lucide-react";

export default function IncidentLog({ incidents = [] }) {
  const [filterSeverity, setFilterSeverity] = useState("all");

  const filteredIncidents = incidents.filter((inc) => {
    if (filterSeverity === "all") return true;
    return inc.severity?.toLowerCase() === filterSeverity.toLowerCase();
  });

  const exportCsv = () => {
    if (incidents.length === 0) return;
    const header = "timestamp,temperature,humidity,trigger,hybrid_score,severity\n";
    const body = incidents
      .map(
        (i) =>
          `"${i.timestamp}",${i.temperature},${i.humidity},"${i.trigger}",${i.hybrid_score},"${i.severity}"`
      )
      .join("\n");
    const blob = new Blob([header + body], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `anomaly_incidents_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getSeverityStyle = (sev) => {
    switch (sev?.toLowerCase()) {
      case "high":
        return "bg-crimson-500/15 text-crimson-700 dark:text-crimson-400 border-crimson-500/30";
      case "medium":
        return "bg-amber-500/15 text-amber-700 dark:text-amber-400 border-amber-500/30";
      default:
        return "bg-arctic-500/15 text-arctic-700 dark:text-arctic-400 border-arctic-500/30";
    }
  };

  return (
    <div className="bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl overflow-hidden shadow-card dark:shadow-card-dark transition-colors">
      {/* Header */}
      <div className="p-4 border-b border-paper-200 dark:border-obsidian-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-md bg-crimson-500/10 border border-crimson-500/25 text-crimson-600 dark:text-crimson-400">
            <AlertTriangle className="w-4 h-4 stroke-[2]" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-paper-900 dark:text-obsidian-100 font-mono uppercase tracking-wider">
              Real-Time Incident Ledger
            </h3>
            <p className="text-[11px] text-paper-500 dark:text-obsidian-400 font-mono">
              Live stream anomalies flagged by the hybrid logical union
            </p>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-2">
          {/* Severity filter pills */}
          <div className="flex items-center bg-paper-100 dark:bg-obsidian-900 p-0.5 rounded-lg border border-paper-200 dark:border-obsidian-750 text-[10px] font-mono">
            {["all", "high", "medium", "low"].map((sev) => (
              <button
                key={sev}
                onClick={() => setFilterSeverity(sev)}
                className={`px-2 py-0.5 rounded uppercase font-semibold transition ${
                  filterSeverity === sev
                    ? "bg-white dark:bg-obsidian-700 text-paper-900 dark:text-white shadow-sm"
                    : "text-paper-500 dark:text-obsidian-400 hover:text-paper-900 dark:hover:text-obsidian-200"
                }`}
              >
                {sev}
              </button>
            ))}
          </div>

          {incidents.length > 0 && (
            <button
              onClick={exportCsv}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-mono bg-paper-100 dark:bg-obsidian-800 hover:bg-paper-200 dark:hover:bg-obsidian-750 text-paper-700 dark:text-obsidian-300 border border-paper-300 dark:border-obsidian-700 transition"
              title="Download Incident CSV Log"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export CSV</span>
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {filteredIncidents.length === 0 ? (
        <div className="p-8 text-center text-xs font-mono text-paper-400 dark:text-obsidian-500 space-y-1.5">
          <Clock className="w-6 h-6 mx-auto text-paper-300 dark:text-obsidian-600 stroke-[1.8]" />
          <div className="text-paper-700 dark:text-obsidian-300 font-semibold">Zero Recorded Incidents</div>
          <div className="text-[11px] text-paper-400 dark:text-obsidian-500">
            Telemetry is either fully nominal or no stream has been dispatched.
          </div>
        </div>
      ) : (
        <div className="max-h-72 overflow-y-auto divide-y divide-paper-100 dark:divide-obsidian-800/80 font-mono text-xs">
          {filteredIncidents
            .slice(-20)
            .reverse()
            .map((inc, idx) => (
              <div
                key={idx}
                className="p-3.5 hover:bg-paper-50 dark:hover:bg-obsidian-800/40 transition flex flex-wrap items-center justify-between gap-3"
              >
                <div className="space-y-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-paper-900 dark:text-white font-semibold tabular-nums">
                      {inc.timestamp}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${getSeverityStyle(
                        inc.severity
                      )}`}
                    >
                      {inc.severity || "MEDIUM"}
                    </span>
                  </div>
                  <div className="text-[11px] text-paper-500 dark:text-obsidian-400 flex items-center gap-2 flex-wrap">
                    <span>
                      Trigger:{" "}
                      <strong className="text-amber-700 dark:text-amber-400 font-semibold">
                        {inc.trigger}
                      </strong>
                    </span>
                    <span>•</span>
                    <span>
                      Score:{" "}
                      <strong className="text-crimson-600 dark:text-crimson-400 font-semibold">
                        {Number(inc.hybrid_score || 0).toFixed(2)}
                      </strong>
                    </span>
                  </div>
                </div>

                <div className="text-right text-[11px] font-mono">
                  <div className="text-cognac-600 dark:text-cognac-400 font-bold">
                    {Number(inc.temperature || 0).toFixed(1)} °C
                  </div>
                  <div className="text-arctic-600 dark:text-arctic-400 font-bold">
                    {Number(inc.humidity || 0).toFixed(1)} % RH
                  </div>
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
