import React, { useMemo } from "react";
import { min, max } from "d3-array";
import { scaleLinear } from "d3-scale";
import { line, curveMonotoneX } from "d3-shape";

export default function RoomMap({ readings = [], isUnusual = false }) {
  const width = 340;
  const height = 380;
  const margin = { top: 20, right: 20, bottom: 44, left: 48 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  const { sixHourReadings, thirtyMinReadings, latestReading, xDomain, yDomain } =
    useMemo(() => {
      if (!readings || readings.length === 0) {
        return { sixHourReadings: [], thirtyMinReadings: [], latestReading: null, xDomain: [18, 36], yDomain: [35, 85] };
      }
      const latest = readings[readings.length - 1];
      const latestTs = new Date(latest.timestamp).getTime();
      const sixHourCutoff = latestTs - 6 * 60 * 60 * 1000;
      const thirtyMinCutoff = latestTs - 30 * 60 * 1000;

      const sixH = readings.filter((r) => new Date(r.timestamp).getTime() >= sixHourCutoff);
      const thirtyM = readings.filter((r) => new Date(r.timestamp).getTime() >= thirtyMinCutoff);

      const tMin = min(sixH.length ? sixH : readings, (d) => d.temperature) ?? 20;
      const tMax = max(sixH.length ? sixH : readings, (d) => d.temperature) ?? 34;
      const hMin = min(sixH.length ? sixH : readings, (d) => d.humidity) ?? 45;
      const hMax = max(sixH.length ? sixH : readings, (d) => d.humidity) ?? 75;

      return {
        sixHourReadings: sixH.length ? sixH : readings,
        thirtyMinReadings: thirtyM.length ? thirtyM : readings.slice(-15),
        latestReading: latest,
        xDomain: [Math.floor(tMin - 1), Math.ceil(tMax + 1)],
        yDomain: [Math.floor(hMin - 2), Math.ceil(hMax + 2)],
      };
    }, [readings]);

  const xScale = useMemo(() => scaleLinear().domain(xDomain).range([0, innerWidth]), [xDomain, innerWidth]);
  const yScale = useMemo(() => scaleLinear().domain(yDomain).range([innerHeight, 0]), [yDomain, innerHeight]);

  const trailPath = useMemo(() => {
    if (thirtyMinReadings.length < 2) return "";
    const l = line().x((d) => xScale(d.temperature)).y((d) => yScale(d.humidity)).curve(curveMonotoneX);
    return l(thirtyMinReadings) || "";
  }, [thirtyMinReadings, xScale, yScale]);

  const xTicks = xScale.ticks(4);
  const yTicks = yScale.ticks(4);

  // Comfort zone boundaries (21°C - 26°C, 40% - 60% RH)
  const comfortBox = {
    x1: Math.max(0, xScale(21)),
    x2: Math.min(innerWidth, xScale(26)),
    y1: Math.max(0, yScale(60)),
    y2: Math.min(innerHeight, yScale(40)),
  };

  return (
    <div className="w-full bg-[#111827] border border-[#1F2937] rounded-xl p-4 flex flex-col shadow-lg">
      <div className="flex items-center justify-between pb-3 border-b border-[#1F2937]">
        <div className="flex items-center gap-2">
          <span className="w-2.5 h-2.5 rounded-full bg-cyan-500" />
          <h3 className="text-sm font-semibold text-slate-200 tracking-wide">Phase-Space Orbit</h3>
        </div>
        <span className="text-xs text-slate-400 font-mono">Temp vs RH</span>
      </div>

      <div className="relative w-full overflow-hidden mt-3">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto block select-none">
          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {/* Comfort zone guideline */}
            {comfortBox.x2 > comfortBox.x1 && comfortBox.y2 > comfortBox.y1 && (
              <rect
                x={comfortBox.x1}
                y={comfortBox.y1}
                width={comfortBox.x2 - comfortBox.x1}
                height={comfortBox.y2 - comfortBox.y1}
                fill="rgba(16, 185, 129, 0.08)"
                stroke="rgba(16, 185, 129, 0.25)"
                strokeDasharray="3 3"
                rx="4"
              />
            )}

            {/* Grid */}
            {xTicks.map((tick, i) => (
              <line key={`rxt-${i}`} x1={xScale(tick)} x2={xScale(tick)} y1={0} y2={innerHeight} stroke="#1F2937" strokeDasharray="2 2" />
            ))}
            {yTicks.map((tick, i) => (
              <line key={`ryt-${i}`} x1={0} x2={innerWidth} y1={yScale(tick)} y2={yScale(tick)} stroke="#1F2937" strokeDasharray="2 2" />
            ))}

            {/* Faint dots: 6h history */}
            {sixHourReadings.map((r, idx) => (
              <circle key={`sh-${idx}`} cx={xScale(r.temperature)} cy={yScale(r.humidity)} r="2" fill="#475569" opacity="0.5" />
            ))}

            {/* 30-min connected trail */}
            {trailPath && (
              <path d={trailPath} fill="none" stroke="#38BDF8" strokeWidth="1.5" strokeDasharray="3 2" opacity="0.85" />
            )}

            {/* Active latest point */}
            {latestReading && (
              <g>
                <circle cx={xScale(latestReading.temperature)} cy={yScale(latestReading.humidity)} r="8" fill="none" stroke={isUnusual ? "#F59E0B" : "#10B981"} strokeWidth="1.5" className="animate-ping opacity-60" />
                <circle cx={xScale(latestReading.temperature)} cy={yScale(latestReading.humidity)} r="5" fill={isUnusual ? "#F59E0B" : "#10B981"} stroke="#FFFFFF" strokeWidth="1.5" />
              </g>
            )}

            {/* Axis labels */}
            {xTicks.map((tick, i) => (
              <text key={`rxtl-${i}`} x={xScale(tick)} y={innerHeight + 16} textAnchor="middle" fill="#64748B" fontSize="10">{tick}°</text>
            ))}
            <text x={innerWidth / 2} y={innerHeight + 32} textAnchor="middle" fill="#94A3B8" fontSize="11" fontWeight="500">Temperature (°C)</text>

            {yTicks.map((tick, i) => (
              <text key={`rytl-${i}`} x="-6" y={yScale(tick) + 4} textAnchor="end" fill="#64748B" fontSize="10">{tick}%</text>
            ))}
            <text transform="rotate(-90)" x={-innerHeight / 2} y="-32" textAnchor="middle" fill="#94A3B8" fontSize="11" fontWeight="500">Humidity (% RH)</text>
          </g>
        </svg>

        <div className="mt-2 py-2 px-3 bg-[#0B0F19] rounded-lg border border-[#1F2937] text-xs text-slate-400 flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" /> Comfort zone
          </span>
          <span className="font-mono text-slate-500">Recent 30m trail</span>
        </div>
      </div>
    </div>
  );
}
