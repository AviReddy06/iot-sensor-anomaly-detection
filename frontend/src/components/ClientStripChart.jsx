import React, { useState, useEffect, useRef, useMemo, useCallback } from "react";
import { min, max, extent } from "d3-array";
import { scaleLinear, scaleTime } from "d3-scale";
import { line, curveMonotoneX } from "d3-shape";
import StripChartGrid from "./StripChartGrid";

// Helper: Min-Max downsampler preserving independent temperature and humidity extrema
function downsampleMinMax(data, targetBuckets = 180) {
  if (!data || data.length <= targetBuckets * 2) return data;
  const bSize = data.length / targetBuckets, res = [];
  for (let b = 0; b < targetBuckets; b++) {
    const s = Math.floor(b * bSize), e = Math.min(data.length, Math.floor((b + 1) * bSize));
    if (s >= e) continue;
    let tMinR = data[s], tMaxR = data[s], hMinR = data[s], hMaxR = data[s];
    for (let i = s + 1; i < e; i++) {
      const d = data[i];
      if (d.temperature < tMinR.temperature) tMinR = d;
      if (d.temperature > tMaxR.temperature) tMaxR = d;
      if (d.humidity < hMinR.humidity) hMinR = d;
      if (d.humidity > hMaxR.humidity) hMaxR = d;
    }
    const bucketPoints = Array.from(new Set([data[s], tMinR, tMaxR, hMinR, hMaxR, data[e - 1]]));
    bucketPoints.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
    for (const pt of bucketPoints) {
      if (res.length === 0 || res[res.length - 1] !== pt) res.push(pt);
    }
  }
  return res;
}

export default function ClientStripChart({
  readings = [], events = [], activeRange = "1 h", onRangeChange, highlightedEvent = null,
}) {
  const containerRef = useRef(null);
  const [width, setWidth] = useState(680);
  const [hoverData, setHoverData] = useState(null);

  // Step 1: Responsive container observer
  useEffect(() => {
    if (!containerRef.current) return;
    const obs = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.floor(entry.contentRect.width);
        if (w > 0) setWidth(w);
      }
    });
    obs.observe(containerRef.current);
    return () => obs.disconnect();
  }, []);

  // Step 2: Time window filtering for active range
  const filteredReadings = useMemo(() => {
    if (!readings || readings.length === 0) return [];
    if (activeRange === "All") return readings;
    const latestTime = new Date(readings[readings.length - 1].timestamp).getTime();
    const ms = activeRange === "15 min" ? 900000 : activeRange === "6 h" ? 21600000 : 3600000;
    const sliced = readings.filter((r) => new Date(r.timestamp).getTime() >= latestTime - ms);
    return sliced.length > 0 ? sliced : readings;
  }, [readings, activeRange]);

  // Step 3: Geometry metrics (equal-height 150px/140px panels with 8px gap)
  const isMobile = width < 640;
  const panelHeight = isMobile ? 140 : 150, panelGap = 8;
  const margin = { top: 20, right: 64, bottom: 36, left: 44 };
  const innerWidth = Math.max(10, width - margin.left - margin.right);
  const innerHeight = panelHeight * 2 + panelGap;
  const totalSvgHeight = innerHeight + margin.top + margin.bottom;

  // Step 4: D3 scales, domains (0.5 °C and 5 % rounding), raw gap detection, and paths
  const { xScale, yTempScale, yHumScale, tempPath, humPath, xTicks, xMinorTicks, yTempTicks, yHumTicks, gaps, directLabels } =
    useMemo(() => {
      if (!filteredReadings || filteredReadings.length === 0) {
        return { xScale: null, yTempScale: null, yHumScale: null, tempPath: "", humPath: "", xTicks: [], xMinorTicks: [], yTempTicks: [], yHumTicks: [], gaps: [], directLabels: null };
      }
      const xs = scaleTime().domain(extent(filteredReadings, (d) => new Date(d.timestamp))).range([0, innerWidth]);

      // Temperature domain: rounded to 0.5 °C with noise guard min span 3.0 °C
      const MIN_T = 3.0, tMin = min(filteredReadings, (d) => d.temperature) ?? 20, tMax = max(filteredReadings, (d) => d.temperature) ?? 28;
      const tSpan = Math.max(MIN_T, tMax - tMin), tPad = Math.max(0.5, tSpan * 0.08);
      let rTMin = tMin - tPad, rTMax = tMax + tPad;
      if (rTMax - rTMin < MIN_T) { const mid = (tMin + tMax) / 2; rTMin = mid - MIN_T / 2; rTMax = mid + MIN_T / 2; }
      let domTMin = Math.floor(rTMin * 2) / 2, domTMax = Math.ceil(rTMax * 2) / 2;
      if (domTMax - domTMin < MIN_T) domTMax = domTMin + MIN_T;
      const ysTemp = scaleLinear().domain([domTMin, domTMax]).range([panelHeight, 0]);

      // Humidity domain: rounded to 5 % RH with noise guard min span 15 %
      const MIN_H = 15, hMin = min(filteredReadings, (d) => d.humidity) ?? 40, hMax = max(filteredReadings, (d) => d.humidity) ?? 70;
      const hSpan = Math.max(MIN_H, hMax - hMin), hPad = Math.max(2.5, hSpan * 0.08);
      let rHMin = hMin - hPad, rHMax = hMax + hPad;
      if (rHMax - rHMin < MIN_H) { const mid = (hMin + hMax) / 2; rHMin = mid - MIN_H / 2; rHMax = mid + MIN_H / 2; }
      let domHMin = Math.max(0, Math.floor(rHMin / 5) * 5), domHMax = Math.min(100, Math.ceil(rHMax / 5) * 5);
      if (domHMax - domHMin < MIN_H) domHMax = Math.min(100, domHMin + MIN_H);
      const ysHum = scaleLinear().domain([domHMin, domHMax]).range([innerHeight, panelHeight + panelGap]);

      // Step 4b: True telemetry gap detection (> 10s) strictly on raw stream
      const rawSegments = [], detectedGaps = [];
      let curSeg = [filteredReadings[0]];
      for (let i = 1; i < filteredReadings.length; i++) {
        const prev = filteredReadings[i - 1], curr = filteredReadings[i];
        const dt = new Date(curr.timestamp).getTime() - new Date(prev.timestamp).getTime();
        if (dt > 10000) {
          rawSegments.push(curSeg);
          curSeg = [curr];
          detectedGaps.push({ x: xs(new Date(prev.timestamp)), width: Math.max(4, xs(new Date(curr.timestamp)) - xs(new Date(prev.timestamp))) });
        } else {
          curSeg.push(curr);
        }
      }
      if (curSeg.length > 0) rawSegments.push(curSeg);

      // Downsample within each continuous segment independently on wide ranges (6 h / All)
      const isDown = activeRange === "6 h" || activeRange === "All";
      const renderSegments = rawSegments.map((seg) => {
        if (!isDown || seg.length <= 360) return seg;
        const segBuckets = Math.max(10, Math.round(180 * (seg.length / filteredReadings.length)));
        return downsampleMinMax(seg, segBuckets);
      });

      const lTemp = line().x((d) => xs(new Date(d.timestamp))).y((d) => ysTemp(d.temperature)).curve(curveMonotoneX);
      const lHum = line().x((d) => xs(new Date(d.timestamp))).y((d) => ysHum(d.humidity)).curve(curveMonotoneX);

      // Direct line-end labels with non-overlapping bounds
      const latest = filteredReadings[filteredReadings.length - 1];
      let tY = Math.max(12, Math.min(panelHeight - 4, ysTemp(latest.temperature)));
      let hY = Math.max(panelHeight + panelGap + 12, Math.min(innerHeight - 4, ysHum(latest.humidity)));
      if (hY - tY < 18) { const push = (18 - (hY - tY)) / 2; tY = Math.max(12, tY - push); hY = Math.min(innerHeight - 4, hY + push); }

      return {
        xScale: xs, yTempScale: ysTemp, yHumScale: ysHum,
        tempPath: renderSegments.map((s) => lTemp(s)).filter(Boolean).join(" "),
        humPath: renderSegments.map((s) => lHum(s)).filter(Boolean).join(" "),
        xTicks: xs.ticks(Math.max(3, Math.floor(innerWidth / 110))),
        xMinorTicks: xs.ticks(Math.max(6, Math.floor(innerWidth / 35))),
        yTempTicks: ysTemp.ticks(3), yHumTicks: ysHum.ticks(3), gaps: detectedGaps,
        directLabels: { tempY: tY, humY: hY, tempVal: latest.temperature, humVal: latest.humidity },
      };
    }, [filteredReadings, activeRange, innerWidth, innerHeight, panelHeight, panelGap]);

  // Step 5: Keyboard navigation handler (left/right scrubbing, home/end)
  const handleKeyDown = useCallback((e) => {
    if (!filteredReadings || filteredReadings.length === 0) return;
    if (e.key === "ArrowLeft" || e.key === "ArrowRight" || e.key === "Home" || e.key === "End") {
      e.preventDefault();
      const curIdx = hoverData ? filteredReadings.findIndex((r) => r.timestamp === hoverData.timestamp) : filteredReadings.length - 1;
      let nextIdx = curIdx >= 0 ? curIdx : filteredReadings.length - 1;
      if (e.key === "ArrowLeft") nextIdx = Math.max(0, nextIdx - 1);
      else if (e.key === "ArrowRight") nextIdx = Math.min(filteredReadings.length - 1, nextIdx + 1);
      else if (e.key === "Home") nextIdx = 0;
      else if (e.key === "End") nextIdx = filteredReadings.length - 1;
      setHoverData(filteredReadings[nextIdx]);
    } else if (e.key === "Escape") { setHoverData(null); }
  }, [filteredReadings, hoverData]);

  // Step 6: Dynamic accessible aria-label
  const ariaDescription = useMemo(() => {
    if (!filteredReadings || filteredReadings.length === 0) return "Dual-trace strip chart: No readings available.";
    const latest = filteredReadings[filteredReadings.length - 1];
    const tMin = min(filteredReadings, (d) => d.temperature), tMax = max(filteredReadings, (d) => d.temperature);
    const hMin = min(filteredReadings, (d) => d.humidity), hMax = max(filteredReadings, (d) => d.humidity);
    const tTime = latest.timestamp.length >= 16 ? latest.timestamp.slice(11, 16) : latest.timestamp;
    return `Continuous dual-trace strip chart for ${activeRange} range. Temperature spans ${tMin.toFixed(1)} to ${tMax.toFixed(1)}\u2009°C. Humidity spans ${Math.round(hMin)} to ${Math.round(hMax)}\u2009% RH. Latest reading at ${tTime}: ${latest.temperature.toFixed(1)}\u2009°C and ${Math.round(latest.humidity)}\u2009% RH. Press Left and Right arrow keys to inspect values along the timeline.`;
  }, [filteredReadings, activeRange]);

  // Step 7: Visible event highlight bands with '#1' naming
  const visibleEventBands = useMemo(() => {
    if (!xScale || !events || events.length === 0) return [];
    const [xStart, xEnd] = xScale.domain();
    const tMin = xStart.getTime(), tMax = xEnd.getTime();
    return events
      .filter((ev) => new Date(ev.end_time).getTime() >= tMin && new Date(ev.start_time).getTime() <= tMax)
      .map((ev, idx) => ({
        id: ev.id || idx + 1,
        x: xScale(new Date(Math.max(tMin, new Date(ev.start_time).getTime()))),
        width: Math.max(4, xScale(new Date(Math.min(tMax, new Date(ev.end_time).getTime()))) - xScale(new Date(Math.max(tMin, new Date(ev.start_time).getTime())))),
        label: `#${idx + 1}`,
        isHighlighted: highlightedEvent && highlightedEvent.id === ev.id,
      }));
  }, [xScale, events, highlightedEvent]);

  return (
    <div className="w-full flex flex-col" ref={containerRef}>
      <div className="flex items-center justify-between pb-2 border-b border-[#CBD5D0]">
        <div className="text-[13px] text-[#4F5F69] font-sans">Dual-trace continuous strip chart</div>
        <div className="flex items-center gap-4 text-[13px] font-sans">
          {["15 min", "1 h", "6 h", "All"].map((r) => (
            <button
              key={r}
              type="button"
              onClick={() => onRangeChange?.(r)}
              className={`py-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-[#1C2A33] ${activeRange === r ? "text-[#1C2A33] font-bold border-b-2 border-[#1C2A33]" : "text-[#4F5F69] hover:text-[#1C2A33]"}`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>
      <div
        className="relative w-full overflow-hidden bg-[#EEF1EF] border border-[#CBD5D0] mt-6 focus:outline-none focus:ring-2 focus:ring-[#1C2A33]"
        tabIndex={0}
        role="region"
        aria-label={ariaDescription}
        onKeyDown={handleKeyDown}
      >
        <StripChartGrid
          width={width}
          totalHeight={totalSvgHeight}
          margin={margin}
          innerWidth={innerWidth}
          innerHeight={innerHeight}
          panelHeight={panelHeight}
          panelGap={panelGap}
          xScale={xScale}
          yTempScale={yTempScale}
          yHumScale={yHumScale}
          tempPath={tempPath}
          humPath={humPath}
          xTicks={xTicks}
          xMinorTicks={xMinorTicks}
          yTempTicks={yTempTicks}
          yHumTicks={yHumTicks}
          gaps={gaps}
          directLabels={directLabels}
          visibleEventBands={visibleEventBands}
          hoverData={hoverData}
          onPointerMove={(e) => {
            if (!xScale || filteredReadings.length === 0) return;
            const rect = e.currentTarget.getBoundingClientRect();
            const mouseX = e.clientX - rect.left - margin.left;
            if (mouseX < 0 || mouseX > innerWidth) { setHoverData(null); return; }
            const hoveredTime = xScale.invert(mouseX).getTime();
            let closest = filteredReadings[0], minDiff = Infinity;
            for (const r of filteredReadings) {
              const diff = Math.abs(new Date(r.timestamp).getTime() - hoveredTime);
              if (diff < minDiff) { minDiff = diff; closest = r; }
            }
            setHoverData(closest);
          }}
          onPointerLeave={() => setHoverData(null)}
        />
      </div>
    </div>
  );
}
