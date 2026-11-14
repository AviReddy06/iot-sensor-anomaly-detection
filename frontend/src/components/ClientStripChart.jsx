import React, { useState, useEffect, useRef, useMemo } from "react";
import { min, max, extent } from "d3-array";
import { scaleLinear, scaleTime } from "d3-scale";
import { line, curveMonotoneX } from "d3-shape";
import StripChartGrid from "./StripChartGrid";

export default function ClientStripChart({
  readings = [],
  events = [],
  activeRange = "1 h",
  onRangeChange,
  highlightedEvent = null,
}) {
  // Step 1: Responsive container measuring
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 680, height: 360 });
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

  // Step 2: Time window filtering
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
  const margin = { top: 24, right: 54, bottom: 32, left: 44 };
  const innerWidth = Math.max(10, dimensions.width - margin.left - margin.right);
  const innerHeight = Math.max(10, dimensions.height - margin.top - margin.bottom);
  const chartSplitY = innerHeight * 0.52;

  // Step 3: D3 scales & line generators
  const { xScale, yTempScale, yHumScale, tempPath, humPath, xTicks, yTempTicks, yHumTicks } =
    useMemo(() => {
      if (filteredReadings.length === 0) {
        return {
          xScale: null, yTempScale: null, yHumScale: null,
          tempPath: "", humPath: "", xTicks: [], yTempTicks: [], yHumTicks: []
        };
      }
      const xExtent = extent(filteredReadings, (d) => new Date(d.timestamp));
      const xs = scaleTime().domain(xExtent).range([0, innerWidth]);

      const tMin = min(filteredReadings, (d) => d.temperature) ?? 20;
      const tMax = max(filteredReadings, (d) => d.temperature) ?? 35;
      const ysTemp = scaleLinear()
        .domain([Math.min(18, Math.floor(tMin - 1)), Math.max(30, Math.ceil(tMax + 1))])
        .range([chartSplitY - 14, 0]);

      const hMin = min(filteredReadings, (d) => d.humidity) ?? 40;
      const hMax = max(filteredReadings, (d) => d.humidity) ?? 80;
      const ysHum = scaleLinear()
        .domain([Math.min(25, Math.floor(hMin - 2)), Math.max(70, Math.ceil(hMax + 2))])
        .range([innerHeight, chartSplitY + 16]);

      const lineTemp = line().x((d) => xs(new Date(d.timestamp))).y((d) => ysTemp(d.temperature)).curve(curveMonotoneX);
      const lineHum = line().x((d) => xs(new Date(d.timestamp))).y((d) => ysHum(d.humidity)).curve(curveMonotoneX);

      return {
        xScale: xs, yTempScale: ysTemp, yHumScale: ysHum,
        tempPath: lineTemp(filteredReadings) || "",
        humPath: lineHum(filteredReadings) || "",
        xTicks: xs.ticks(Math.max(3, Math.floor(innerWidth / 110))),
        yTempTicks: ysTemp.ticks(3),
        yHumTicks: ysHum.ticks(3),
      };
    }, [filteredReadings, innerWidth, innerHeight, chartSplitY]);

  // Step 4: Hover pointer inspection
  const handlePointerMove = (e) => {
    if (!xScale || filteredReadings.length === 0) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const mouseX = e.clientX - rect.left - margin.left;
    if (mouseX < 0 || mouseX > innerWidth) {
      setHoverData(null);
      return;
    }
    const hoveredTime = xScale.invert(mouseX).getTime();
    let closest = filteredReadings[0];
    let minDiff = Infinity;
    for (const r of filteredReadings) {
      const diff = Math.abs(new Date(r.timestamp).getTime() - hoveredTime);
      if (diff < minDiff) {
        minDiff = diff;
        closest = r;
      }
    }
    setHoverData(closest);
  };

  // Step 5: Visible unusual event highlight bands
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
        return {
          id: ev.id || idx + 1,
          x: xScale(new Date(s)),
          width: Math.max(4, xScale(new Date(e)) - xScale(new Date(s))),
          label: `Event ${idx + 1}`,
          isHighlighted: highlightedEvent && highlightedEvent.id === ev.id,
        };
      });
  }, [xScale, events, highlightedEvent]);

  return (
    <div className="w-full flex flex-col" ref={containerRef}>
      {/* Range Selection Bar */}
      <div className="flex items-center justify-between pb-2 border-b border-[#CBD5D0]">
        <div className="text-[13px] text-[#4F5F69] font-sans">
          Dual-trace continuous strip chart
        </div>
        <div className="flex items-center gap-4 text-[13px] font-sans">
          {ranges.map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => onRangeChange?.(r)}
              className={`py-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-[#1C2A33] ${
                activeRange === r ? "text-[#1C2A33] font-bold border-b-2 border-[#1C2A33]" : "text-[#4F5F69] hover:text-[#1C2A33]"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Thermohygrograph Paper */}
      <div className="relative w-full overflow-hidden bg-[#EEF1EF] border border-[#CBD5D0] mt-2">
        <StripChartGrid
          dimensions={dimensions}
          margin={margin}
          innerWidth={innerWidth}
          innerHeight={innerHeight}
          chartSplitY={chartSplitY}
          xScale={xScale}
          yTempScale={yTempScale}
          yHumScale={yHumScale}
          tempPath={tempPath}
          humPath={humPath}
          xTicks={xTicks}
          yTempTicks={yTempTicks}
          yHumTicks={yHumTicks}
          visibleEventBands={visibleEventBands}
          hoverData={hoverData}
          onPointerMove={handlePointerMove}
          onPointerLeave={() => setHoverData(null)}
        />

        {/* Hover Reading Badge */}
        {hoverData && (
          <div className="absolute top-2 right-2 px-2.5 py-1 bg-[#EEF1EF] border border-[#CBD5D0] text-[12px] font-sans text-[#1C2A33] pointer-events-none shadow-none">
            <span className="text-[#4F5F69]">{hoverData.timestamp.slice(11, 19)}:</span>{" "}
            <span className="text-[#9B2C2C] font-bold">{Number(hoverData.temperature).toFixed(1)} °C</span>,{" "}
            <span className="text-[#1D5C8C] font-bold">{Number(hoverData.humidity).toFixed(1)}% RH</span>
          </div>
        )}
      </div>
    </div>
  );
}
