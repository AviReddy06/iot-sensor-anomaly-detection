import React, { useState, useMemo } from "react";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function LiveChart({ data = [], height = 300, theme = "dark" }) {
  const [windowSize, setWindowSize] = useState(60);
  const [showTemp, setShowTemp] = useState(true);
  const [showHum, setShowHum] = useState(true);

  const isLight = theme === "light";

  // Filter slice based on windowSize
  const displayedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    if (windowSize === 0 || data.length <= windowSize) return data;
    return data.slice(-windowSize);
  }, [data, windowSize]);

  if (!displayedData || displayedData.length === 0) {
    return (
      <div
        style={{ height: `${height}px` }}
        className="flex flex-col items-center justify-center border border-dashed border-paper-300 dark:border-obsidian-750 rounded-xl text-paper-500 dark:text-obsidian-400 text-xs font-mono bg-paper-100/50 dark:bg-obsidian-900/40"
      >
        <span className="text-paper-700 dark:text-obsidian-300 font-semibold">Telemetry Buffer Empty</span>
        <span className="text-[11px] text-paper-500 dark:text-obsidian-500 mt-1">
          Initiate ESP32 serial acquisition or trigger simulated replay to inspect live traces.
        </span>
      </div>
    );
  }

  const labels = displayedData.map((d) => {
    try {
      const dt = new Date(d.timestamp);
      return isNaN(dt.getTime())
        ? String(d.timestamp).slice(11, 19)
        : dt.toLocaleTimeString();
    } catch {
      return String(d.timestamp);
    }
  });

  const temperatures = displayedData.map((d) => Number(d.temperature));
  const humidities = displayedData.map((d) => Number(d.humidity));
  const anomalyFlags = displayedData.map((d) => Boolean(d.is_anomaly || d.hybrid_anomaly));

  // Visual anomaly marker points
  const tempColors = anomalyFlags.map((anom) =>
    anom ? "#e11d48" : "rgba(234, 88, 12, 0)"
  );
  const tempRadii = anomalyFlags.map((anom) => (anom ? 6 : 1.5));
  const tempStyles = anomalyFlags.map((anom) => (anom ? "rectRot" : "circle"));

  const humColors = anomalyFlags.map((anom) =>
    anom ? "#e11d48" : "rgba(2, 132, 199, 0)"
  );
  const humRadii = anomalyFlags.map((anom) => (anom ? 6 : 1.5));
  const humStyles = anomalyFlags.map((anom) => (anom ? "rectRot" : "circle"));

  const datasets = [];

  const tempBorder = isLight ? "#ea580c" : "#f97316";
  const tempBg = isLight ? "rgba(234, 88, 12, 0.08)" : "rgba(249, 115, 22, 0.12)";
  const humBorder = isLight ? "#0284c7" : "#38bdf8";
  const humBg = isLight ? "rgba(2, 132, 199, 0.08)" : "rgba(56, 189, 248, 0.1)";

  if (showTemp) {
    datasets.push({
      label: "Temperature (°C)",
      data: temperatures,
      borderColor: tempBorder,
      backgroundColor: tempBg,
      borderWidth: 2,
      tension: 0.2,
      fill: true,
      yAxisID: "yTemp",
      pointBackgroundColor: tempColors,
      pointBorderColor: tempColors,
      pointRadius: tempRadii,
      pointPointStyle: tempStyles,
      pointHoverRadius: 7,
    });
  }

  if (showHum) {
    datasets.push({
      label: "Humidity (% RH)",
      data: humidities,
      borderColor: humBorder,
      backgroundColor: humBg,
      borderWidth: 2,
      tension: 0.2,
      fill: true,
      yAxisID: "yHum",
      pointBackgroundColor: humColors,
      pointBorderColor: humColors,
      pointRadius: humRadii,
      pointPointStyle: humStyles,
      pointHoverRadius: 7,
    });
  }

  const chartData = {
    labels,
    datasets,
  };

  const gridLineColor = isLight ? "rgba(0, 0, 0, 0.06)" : "rgba(255, 255, 255, 0.06)";
  const tickLabelColor = isLight ? "#646054" : "#808eb5";

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: {
      mode: "index",
      intersect: false,
    },
    scales: {
      x: {
        grid: {
          color: gridLineColor,
        },
        ticks: {
          color: tickLabelColor,
          font: { size: 10, family: "JetBrains Mono, monospace" },
          maxRotation: 0,
          autoSkip: true,
          maxTicksLimit: 8,
        },
      },
      yTemp: {
        type: "linear",
        display: showTemp,
        position: "left",
        title: {
          display: true,
          text: "Temperature (°C)",
          color: tempBorder,
          font: { size: 11, weight: "bold", family: "JetBrains Mono, monospace" },
        },
        grid: {
          color: gridLineColor,
        },
        ticks: {
          color: tempBorder,
          font: { size: 10, family: "JetBrains Mono, monospace" },
        },
      },
      yHum: {
        type: "linear",
        display: showHum,
        position: "right",
        title: {
          display: true,
          text: "Humidity (% RH)",
          color: humBorder,
          font: { size: 11, weight: "bold", family: "JetBrains Mono, monospace" },
        },
        grid: {
          drawOnChartArea: false,
        },
        ticks: {
          color: humBorder,
          font: { size: 10, family: "JetBrains Mono, monospace" },
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: isLight ? "#ffffff" : "#151822",
        titleColor: isLight ? "#171613" : "#edf1f8",
        bodyColor: isLight ? "#444139" : "#ccd5e7",
        borderColor: isLight ? "#e8e5dc" : "#2e354b",
        borderWidth: 1,
        padding: 10,
        boxPadding: 4,
        usePointStyle: true,
        callbacks: {
          afterTitle: (items) => {
            const idx = items[0]?.dataIndex;
            if (idx !== undefined && displayedData[idx]) {
              const row = displayedData[idx];
              if (row.is_anomaly || row.hybrid_anomaly) {
                return `⚠️ ANOMALY: ${row.trigger || "Hybrid Ensemble"}`;
              }
            }
            return "";
          },
          footer: (items) => {
            const idx = items[0]?.dataIndex;
            if (idx !== undefined && displayedData[idx]) {
              const row = displayedData[idx];
              const parts = [];
              if (row.hybrid_score !== undefined) {
                parts.push(`Score: ${Number(row.hybrid_score).toFixed(2)}`);
              }
              if (row.temp_rate !== undefined) {
                parts.push(`Rate: ${Number(row.temp_rate).toFixed(2)}°C/s`);
              }
              return parts.join(" • ");
            }
            return "";
          },
        },
      },
    },
  };

  return (
    <div className="space-y-3">
      {/* Oscilloscope Mini-Toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowTemp(!showTemp)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold border transition ${
              showTemp
                ? "bg-cognac-500/15 text-cognac-700 dark:text-cognac-400 border-cognac-500/40"
                : "bg-paper-100 dark:bg-obsidian-850 text-paper-400 dark:text-obsidian-500 border-paper-300 dark:border-obsidian-750 line-through"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-cognac-600 dark:bg-cognac-400" />
            <span>Temp (°C)</span>
          </button>

          <button
            onClick={() => setShowHum(!showHum)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[11px] font-semibold border transition ${
              showHum
                ? "bg-arctic-500/15 text-arctic-700 dark:text-arctic-400 border-arctic-500/40"
                : "bg-paper-100 dark:bg-obsidian-850 text-paper-400 dark:text-obsidian-500 border-paper-300 dark:border-obsidian-750 line-through"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-arctic-600 dark:bg-arctic-400" />
            <span>Humidity (% RH)</span>
          </button>
        </div>

        {/* Window buffer buttons */}
        <div className="flex items-center gap-1 bg-paper-100 dark:bg-obsidian-850 p-0.5 rounded-lg border border-paper-300 dark:border-obsidian-750 text-[10px]">
          {[
            { label: "30 pts", val: 30 },
            { label: "60 pts", val: 60 },
            { label: "120 pts", val: 120 },
            { label: "All Buffer", val: 0 },
          ].map((w) => (
            <button
              key={w.val}
              onClick={() => setWindowSize(w.val)}
              className={`px-2 py-0.5 rounded transition ${
                windowSize === w.val
                  ? "bg-white dark:bg-obsidian-700 text-paper-900 dark:text-white font-bold shadow-sm"
                  : "text-paper-500 dark:text-obsidian-400 hover:text-paper-900 dark:hover:text-obsidian-200"
              }`}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Canvas */}
      <div style={{ height: `${height}px` }} className="w-full relative">
        <Line data={chartData} options={options} />
      </div>
    </div>
  );
}
