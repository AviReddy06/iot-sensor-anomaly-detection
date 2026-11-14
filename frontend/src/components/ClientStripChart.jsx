import React, { useState, useEffect, useRef, useMemo } from "react";
import { min, max, extent } from "d3-array";
import { scaleLinear, scaleTime } from "d3-scale";
import { line, area, curveMonotoneX } from "d3-shape";

export default function ClientStripChart({
  readings = [],
  events = [],
  activeRange = "1 h",
  onRangeChange,
  highlightedEvent = null,
}) {
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 720, height: 380 });
  const [hoverData, setHoverData] = useState(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.floor(entry.contentRect.width);
        if (w > 0) setDimensions((prev) => ({ ...prev, width: w }));
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  const filteredReadings = useMemo(() => {
    if (!readings || readings.length === 0) return [];
    if (activeRange === "All") return readings;
    const latestTime = new Date(readings[readings.length - 1].timestamp).getTime();
    let windowMs = 60 * 60 * 1000;
    if (activeRange === "15 min") windowMs = 15 * 60 * 1000;
    else if (activeRange === "6 h") windowMs = 6 * 60 * 60 * 1000;
    const cutoff = latestTime - windowMs;
    const sliced = readings.filter((r) => new Date(r.timestamp).getTime() >= cutoff);
    return sliced.length > 0 ? sliced : readings;
  }, [readings, activeRange]);

  const ranges = ["15 min", "1 h", "6 h", "All"];
  const margin = { top: 20, right: 54, bottom: 32, left: 48 };
  const innerWidth = Math.max(10, dimensions.width - margin.left - margin.right);
  const innerHeight = Math.max(10, dimensions.height - margin.top - margin.bottom);
  const chartSplitY = innerHeight * 0.52;

  const { xScale, yTempScale, yHumScale, tempLine, humLine, tempArea, humArea, xTicks, yTempTicks, yHumTicks } =
    useMemo(() => {
      if (filteredReadings.length === 0) {
        return { xScale: null, yTempScale: null, yHumScale: null, tempLine: "", humLine: "", tempArea: "", humArea: "", xTicks: [], yTempTicks: [], yHumTicks: [] };
      }
      const xExtent = extent(filteredReadings, (d) => new Date(d.timestamp));
      const xs = scaleTime().domain(xExtent).range([0, innerWidth]);

      const tMin = min(filteredReadings, (d) => d.temperature) ?? 20;
      const tMax = max(filteredReadings, (d) => d.temperature) ?? 35;
      const ysTemp = scaleLinear().domain([Math.floor(tMin - 1), Math.ceil(tMax + 1)]).range([chartSplitY - 14, 0]);

      const hMin = min(filteredReadings, (d) => d.humidity) ?? 40;
      const hMax = max(filteredReadings, (d) => d.humidity) ?? 80;
      const ysHum = scaleLinear().domain([Math.floor(hMin - 2), Math.ceil(hMax + 2)]).range([innerHeight, chartSplitY + 16]);

      const lTemp = line().x((d) => xs(new Date(d.timestamp))).y((d) => ysTemp(d.temperature)).curve(curveMonotoneX);
      const lHum = line().x((d) => xs(new Date(d.timestamp))).y((d) => ysHum(d.humidity)).curve(curveMonotoneX);

      const aTemp = area().x((d) => xs(new Date(d.timestamp))).y0(chartSplitY - 14).y1((d) => ysTemp(d.temperature)).curve(curveMonotoneX);
      const aHum = area().x((d) => xs(new Date(d.timestamp))).y0(innerHeight).y1((d) => ysHum(d.humidity)).curve(curveMonotoneX);

      return {
        xScale: xs, yTempScale: ysTemp, yHumScale: ysHum,
        tempLine: lTemp(filteredReadings) || "",
        humLine: lHum(filteredReadings) || "",
        tempArea: aTemp(filteredReadings) || "",
        humArea: aHum(filteredReadings) || "",
        xTicks: xs.ticks(Math.max(3, Math.floor(innerWidth / 110))),
        yTempTicks: ysTemp.ticks(3),
        yHumTicks: ysHum.ticks(3),
      };
    }, [filteredReadings, innerWidth, innerHeight, chartSplitY]);

  const handlePointerMove = (e) => {
    if (!xScale || filteredReadings.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = e.clientX - rect.left - margin.left;
    if (mouseX < 0 || mouseX > innerWidth) { setHoverData(null); return; }
    const hoveredTime = xScale.invert(mouseX).getTime();
    let closest = filteredReadings[0];
    let minDiff = Infinity;
    for (const r of filteredReadings) {
      const diff = Math.abs(new Date(r.timestamp).getTime() - hoveredTime);
      if (diff < minDiff) { minDiff = diff; closest = r; }
    }
    setHoverData(closest);
  };

  const visibleEventBands = useMemo(() => {
    if (!xScale || !events || events.length === 0) return [];
    const [xStart, xEnd] = xScale.domain();
    const tMin = xStart.getTime();
    const tMax = xEnd.getTime();
    return events
      .filter((ev) => {
        const s = new Date(ev.start_time).getTime();
        const e = new Date(ev.end_time).getTime();
        return e >= tMin && s <= tMax;
      })
      .map((ev, idx) => {
        const s = Math.max(tMin, new Date(ev.start_time).getTime());
        const e = Math.min(tMax, new Date(ev.end_time).getTime());
        const x1 = xScale(new Date(s));
        const x2 = xScale(new Date(e));
        return {
          id: ev.id || idx + 1,
          x: x1,
          width: Math.max(6, x2 - x1),
          label: `Event ${idx + 1}`,
          isHighlighted: highlightedEvent && highlightedEvent.id === ev.id,
        };
      });
  }, [xScale, events, highlightedEvent]);

  return (
    <div className="w-full bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col shadow-lg" ref={containerRef}>
      <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#1F2937]">
        <div className="flex items-center gap-2.5">
          <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
          <h3 className="text-sm font-semibold text-slate-200 tracking-wide">Continuous Climate Waveform</h3>
          <span className="text-xs text-slate-400 font-mono">0.5 Hz Dual Trace</span>
        </div>
        <div className="flex items-center bg-[#0B0F19] p-0.5 rounded-lg border border-[#1F2937]">
          {ranges.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => onRangeChange?.(r)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                activeRange === r ? "bg-blue-600 text-white shadow" : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      <div className="relative w-full overflow-hidden mt-3">
        <svg
          width={dimensions.width}
          height={dimensions.height}
          onPointerMove={handlePointerMove}
          onPointerLeave={() => setHoverData(null)}
          className="block select-none cursor-crosshair"
        >
          <defs>
            <linearGradient id="tempGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#F43F5E" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#F43F5E" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="humGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0EA5E9" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#0EA5E9" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {/* Grid Lines */}
            {xTicks.map((tick, i) => (
              <line key={`xt-${i}`} x1={xScale(tick)} x2={xScale(tick)} y1={0} y2={innerHeight} stroke="#1F2937" strokeDasharray="3 3" />
            ))}
            {yTempTicks.map((tick, i) => (
              <line key={`yt-${i}`} x1={0} x2={innerWidth} y1={yTempScale(tick)} y2={yTempScale(tick)} stroke="#1F2937" />
            ))}
            <line x1={0} x2={innerWidth} y1={chartSplitY} y2={chartSplitY} stroke="#334155" strokeDasharray="2 2" />
            {yHumTicks.map((tick, i) => (
              <line key={`yh-${i}`} x1={0} x2={innerWidth} y1={yHumScale(tick)} y2={yHumScale(tick)} stroke="#1F2937" />
            ))}

            {/* Anomaly Event Shading */}
            {visibleEventBands.map((band) => (
              <g key={`band-${band.id}`}>
                <rect x={band.x} y={0} width={band.width} height={innerHeight} fill="rgba(245, 158, 11, 0.18)" stroke="#F59E0B" strokeWidth={band.isHighlighted ? "2" : "1"} strokeDasharray={band.isHighlighted ? "none" : "4 2"} />
                <rect x={band.x} y={4} width={Math.max(48, band.width)} height={16} fill="#F59E0B" rx="3" />
                <text x={band.x + 4} y={15} fill="#0F172A" fontSize="10" fontWeight="bold">{band.label}</text>
              </g>
            ))}

            {/* Traces */}
            {tempArea && <path d={tempArea} fill="url(#tempGrad)" />}
            {tempLine && <path d={tempLine} fill="none" stroke="#F43F5E" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />}
            {humArea && <path d={humArea} fill="url(#humGrad)" />}
            {humLine && <path d={humLine} fill="none" stroke="#38BDF8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />}

            {/* Right Axis Units */}
            <text x={innerWidth + 8} y={14} fill="#F43F5E" fontSize="11" fontWeight="bold">°C</text>
            <text x={innerWidth + 8} y={innerHeight} fill="#38BDF8" fontSize="11" fontWeight="bold">% RH</text>

            {/* Axis Tick Labels */}
            {yTempTicks.map((tick, i) => (
              <text key={`ytl-${i}`} x="-8" y={yTempScale(tick) + 4} textAnchor="end" fill="#64748B" fontSize="11">{tick}°</text>
            ))}
            {yHumTicks.map((tick, i) => (
              <text key={`yhl-${i}`} x="-8" y={yHumScale(tick) + 4} textAnchor="end" fill="#64748B" fontSize="11">{tick}%</text>
            ))}
            {xTicks.map((tick, i) => {
              const d = new Date(tick);
              const timeStr = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
              return <text key={`xtl-${i}`} x={xScale(tick)} y={innerHeight + 20} textAnchor="middle" fill="#64748B" fontSize="11">{timeStr}</text>;
            })}

            {/* Crosshair */}
            {hoverData && xScale && yTempScale && yHumScale && (
              <g>
                <line x1={xScale(new Date(hoverData.timestamp))} x2={xScale(new Date(hoverData.timestamp))} y1={0} y2={innerHeight} stroke="#94A3B8" strokeWidth="1" strokeDasharray="2 2" />
                <circle cx={xScale(new Date(hoverData.timestamp))} cy={yTempScale(hoverData.temperature)} r="4" fill="#F43F5E" stroke="#FFFFFF" strokeWidth="2" />
                <circle cx={xScale(new Date(hoverData.timestamp))} cy={yHumScale(hoverData.humidity)} r="4" fill="#38BDF8" stroke="#FFFFFF" strokeWidth="2" />
              </g>
            )}
          </g>
        </svg>

        {hoverData && (
          <div className="absolute top-2 right-2 px-3 py-1.5 bg-[#0F172A]/90 border border-slate-700 rounded-lg shadow-xl text-xs backdrop-blur-sm pointer-events-none flex items-center gap-3">
            <span className="text-slate-400 font-mono">{hoverData.timestamp.slice(11, 19)}</span>
            <span className="text-rose-400 font-semibold">{Number(hoverData.temperature).toFixed(1)} °C</span>
            <span className="text-sky-400 font-semibold">{Number(hoverData.humidity).toFixed(1)}% RH</span>
          </div>
        )}
      </div>
    </div>
  );
}
