import React, { useState, useEffect, useRef, useMemo } from "react";
import { min, max, extent } from "d3-array";
import { scaleLinear, scaleTime } from "d3-scale";
import { line, curveMonotoneX } from "d3-shape";

export default function ClientStripChart({
  readings = [],
  events = [],
  activeRange = "1 h",
  onRangeChange,
  highlightedEvent = null,
}) {
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 680, height: 360 });
  const [hoverData, setHoverData] = useState(null);

  // Measure container width responsively
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = Math.floor(entry.contentRect.width);
        if (w > 0) {
          setDimensions((prev) => ({ ...prev, width: w }));
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Filter readings based on active range
  const filteredReadings = useMemo(() => {
    if (!readings || readings.length === 0) return [];
    if (activeRange === "All") return readings;

    const latestTime = new Date(readings[readings.length - 1].timestamp).getTime();
    let windowMs = 60 * 60 * 1000; // 1 h default
    if (activeRange === "15 min") windowMs = 15 * 60 * 1000;
    else if (activeRange === "6 h") windowMs = 6 * 60 * 60 * 1000;

    const cutoff = latestTime - windowMs;
    const sliced = readings.filter((r) => new Date(r.timestamp).getTime() >= cutoff);
    return sliced.length > 0 ? sliced : readings;
  }, [readings, activeRange]);

  const ranges = ["15 min", "1 h", "6 h", "All"];

  // D3 Scales & Layout
  const margin = { top: 24, right: 54, bottom: 32, left: 44 };
  const innerWidth = Math.max(10, dimensions.width - margin.left - margin.right);
  const innerHeight = Math.max(10, dimensions.height - margin.top - margin.bottom);
  const chartSplitY = innerHeight * 0.52; // top 52% for temp, bottom for hum

  const { xScale, yTempScale, yHumScale, tempPath, humPath, xTicks, yTempTicks, yHumTicks } =
    useMemo(() => {
      if (filteredReadings.length === 0) {
        return {
          xScale: null,
          yTempScale: null,
          yHumScale: null,
          tempPath: "",
          humPath: "",
          xTicks: [],
          yTempTicks: [],
          yHumTicks: [],
        };
      }

      const xExtent = extent(filteredReadings, (d) => new Date(d.timestamp));
      const xs = scaleTime().domain(xExtent).range([0, innerWidth]);

      // Temperature scale (top half)
      const tMin = min(filteredReadings, (d) => d.temperature) ?? 20;
      const tMax = max(filteredReadings, (d) => d.temperature) ?? 35;
      const ysTemp = scaleLinear()
        .domain([Math.floor(tMin - 1), Math.ceil(tMax + 1)])
        .range([chartSplitY - 14, 0]);

      // Humidity scale (bottom half)
      const hMin = min(filteredReadings, (d) => d.humidity) ?? 40;
      const hMax = max(filteredReadings, (d) => d.humidity) ?? 80;
      const ysHum = scaleLinear()
        .domain([Math.floor(hMin - 2), Math.ceil(hMax + 2)])
        .range([innerHeight, chartSplitY + 16]);

      // Line generators
      const lineTemp = line()
        .x((d) => xs(new Date(d.timestamp)))
        .y((d) => ysTemp(d.temperature))
        .curve(curveMonotoneX);

      const lineHum = line()
        .x((d) => xs(new Date(d.timestamp)))
        .y((d) => ysHum(d.humidity))
        .curve(curveMonotoneX);

      return {
        xScale: xs,
        yTempScale: ysTemp,
        yHumScale: ysHum,
        tempPath: lineTemp(filteredReadings) || "",
        humPath: lineHum(filteredReadings) || "",
        xTicks: xs.ticks(Math.max(3, Math.floor(innerWidth / 110))),
        yTempTicks: ysTemp.ticks(3),
        yHumTicks: ysHum.ticks(3),
      };
    }, [filteredReadings, innerWidth, innerHeight, chartSplitY]);

  // Pointer move handler for inspection crosshair
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

  const handlePointerLeave = () => setHoverData(null);

  // Compute straw yellow highlight rectangles for events in view
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
        const width = Math.max(4, x2 - x1);
        return {
          id: ev.id || idx + 1,
          x: x1,
          width,
          start: ev.start_time,
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
          {ranges.map((r) => {
            const isActive = activeRange === r;
            return (
              <button
                key={r}
                type="button"
                onClick={() => onRangeChange?.(r)}
                className={`py-0.5 transition-colors focus:outline-none focus:ring-2 focus:ring-[#1C2A33] ${
                  isActive
                    ? "text-[#1C2A33] font-bold border-b-2 border-[#1C2A33]"
                    : "text-[#4F5F69] hover:text-[#1C2A33]"
                }`}
              >
                {r}
              </button>
            );
          })}
        </div>
      </div>

      {/* SVG Thermohygrograph Paper */}
      <div className="relative w-full overflow-hidden bg-[#EEF1EF] border border-[#CBD5D0] mt-2">
        <svg
          width={dimensions.width}
          height={dimensions.height}
          onPointerMove={handlePointerMove}
          onPointerLeave={handlePointerLeave}
          className="block select-none cursor-crosshair"
          aria-label="Continuous temperature and relative humidity chart"
        >
          {/* Main Paper Grid Pattern */}
          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {/* Background Rect */}
            <rect
              x="0"
              y="0"
              width={innerWidth}
              height={innerHeight}
              fill="#EEF1EF"
            />

            {/* Vertical Time Grid Lines */}
            {xTicks.map((tick, i) => {
              const xPos = xScale ? xScale(tick) : 0;
              return (
                <line
                  key={`xt-${i}`}
                  x1={xPos}
                  x2={xPos}
                  y1={0}
                  y2={innerHeight}
                  stroke="#CBD5D0"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
              );
            })}

            {/* Horizontal Grid Lines - Temperature section */}
            {yTempTicks.map((tick, i) => {
              const yPos = yTempScale ? yTempScale(tick) : 0;
              return (
                <line
                  key={`yt-${i}`}
                  x1={0}
                  x2={innerWidth}
                  y1={yPos}
                  y2={yPos}
                  stroke="#CBD5D0"
                  strokeWidth="1"
                />
              );
            })}

            {/* Separator hairline between temperature and humidity ink channels */}
            <line
              x1={0}
              x2={innerWidth}
              y1={chartSplitY}
              y2={chartSplitY}
              stroke="#CBD5D0"
              strokeWidth="1"
            />

            {/* Horizontal Grid Lines - Humidity section */}
            {yHumTicks.map((tick, i) => {
              const yPos = yHumScale ? yHumScale(tick) : 0;
              return (
                <line
                  key={`yh-${i}`}
                  x1={0}
                  x2={innerWidth}
                  y1={yPos}
                  y2={yPos}
                  stroke="#CBD5D0"
                  strokeWidth="1"
                />
              );
            })}

            {/* Shaded Yellow Bands for Unusual Readings */}
            {visibleEventBands.map((band) => (
              <g key={`band-${band.id}`}>
                <rect
                  x={band.x}
                  y={0}
                  width={band.width}
                  height={innerHeight}
                  fill="rgba(232, 176, 74, 0.35)"
                  stroke={band.isHighlighted ? "#7A4B00" : "none"}
                  strokeWidth={band.isHighlighted ? "1.5" : "0"}
                />
                <text
                  x={band.x + 3}
                  y={12}
                  fill="#7A4B00"
                  fontSize="11"
                  fontFamily="'Atkinson Hyperlegible', sans-serif"
                  fontWeight="bold"
                >
                  {band.label}
                </text>
              </g>
            ))}

            {/* Temperature Ink Trace (#9B2C2C, oxblood) */}
            {tempPath && (
              <path
                d={tempPath}
                fill="none"
                stroke="#9B2C2C"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* Humidity Ink Trace (#1D5C8C, navy blue) */}
            {humPath && (
              <path
                d={humPath}
                fill="none"
                stroke="#1D5C8C"
                strokeWidth="1.75"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            )}

            {/* Channel Labels on Right Axis */}
            <text
              x={innerWidth + 8}
              y={yTempScale ? yTempScale.range()[1] + 14 : 14}
              fill="#9B2C2C"
              fontSize="12"
              fontWeight="bold"
              fontFamily="'Atkinson Hyperlegible', sans-serif"
            >
              °C
            </text>
            <text
              x={innerWidth + 8}
              y={yHumScale ? yHumScale.range()[0] : innerHeight}
              fill="#1D5C8C"
              fontSize="12"
              fontWeight="bold"
              fontFamily="'Atkinson Hyperlegible', sans-serif"
            >
              % RH
            </text>

            {/* Left Axis Tick Labels - Temperature */}
            {yTempTicks.map((tick, i) => (
              <text
                key={`ytl-${i}`}
                x="-8"
                y={yTempScale(tick) + 4}
                textAnchor="end"
                fill="#4F5F69"
                fontSize="11"
                fontFamily="'Atkinson Hyperlegible', sans-serif"
              >
                {tick}°
              </text>
            ))}

            {/* Left Axis Tick Labels - Humidity */}
            {yHumTicks.map((tick, i) => (
              <text
                key={`yhl-${i}`}
                x="-8"
                y={yHumScale(tick) + 4}
                textAnchor="end"
                fill="#4F5F69"
                fontSize="11"
                fontFamily="'Atkinson Hyperlegible', sans-serif"
              >
                {tick}%
              </text>
            ))}

            {/* Bottom Axis Tick Labels - Time */}
            {xTicks.map((tick, i) => {
              const xPos = xScale(tick);
              const d = new Date(tick);
              const timeStr = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
              return (
                <text
                  key={`xtl-${i}`}
                  x={xPos}
                  y={innerHeight + 20}
                  textAnchor="middle"
                  fill="#4F5F69"
                  fontSize="11"
                  fontFamily="'Atkinson Hyperlegible', sans-serif"
                >
                  {timeStr}
                </text>
              );
            })}

            {/* Interactive Hover Crosshair & Values */}
            {hoverData && xScale && yTempScale && yHumScale && (
              <g>
                {/* Vertical hairline */}
                <line
                  x1={xScale(new Date(hoverData.timestamp))}
                  x2={xScale(new Date(hoverData.timestamp))}
                  y1={0}
                  y2={innerHeight}
                  stroke="#1C2A33"
                  strokeWidth="1"
                  strokeDasharray="3,3"
                />
                {/* Temperature dot */}
                <circle
                  cx={xScale(new Date(hoverData.timestamp))}
                  cy={yTempScale(hoverData.temperature)}
                  r="3.5"
                  fill="#9B2C2C"
                  stroke="#EEF1EF"
                  strokeWidth="1.5"
                />
                {/* Humidity dot */}
                <circle
                  cx={xScale(new Date(hoverData.timestamp))}
                  cy={yHumScale(hoverData.humidity)}
                  r="3.5"
                  fill="#1D5C8C"
                  stroke="#EEF1EF"
                  strokeWidth="1.5"
                />
              </g>
            )}
          </g>
        </svg>

        {/* Hover Reading Badge */}
        {hoverData && (
          <div className="absolute top-2 right-2 px-2.5 py-1 bg-[#EEF1EF] border border-[#CBD5D0] text-[12px] font-sans text-[#1C2A33] pointer-events-none">
            <span className="text-[#4F5F69]">
              {hoverData.timestamp.slice(11, 19)}:
            </span>{" "}
            <span className="text-[#9B2C2C] font-bold">
              {Number(hoverData.temperature).toFixed(1)} °C
            </span>
            ,{" "}
            <span className="text-[#1D5C8C] font-bold">
              {Number(hoverData.humidity).toFixed(1)}% RH
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
