import React, { useMemo } from "react";
import { min, max } from "d3-array";
import { scaleLinear } from "d3-scale";
import { line, curveMonotoneX } from "d3-shape";

export default function RoomMap({ readings = [], isUnusual = false }) {
  // Step 1: Dimensions and margins
  const width = 340;
  const height = 360;
  const margin = { top: 24, right: 20, bottom: 44, left: 50 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  // Step 2: Time horizons (6-hour dots, 30-min trail, latest dot)
  const { sixHourReadings, thirtyMinReadings, latestReading, xDomain, yDomain } =
    useMemo(() => {
      if (!readings || readings.length === 0) {
        return {
          sixHourReadings: [], thirtyMinReadings: [], latestReading: null,
          xDomain: [18, 34], yDomain: [30, 85],
        };
      }
      const latest = readings[readings.length - 1];
      const latestTs = new Date(latest.timestamp).getTime();
      const sixHourCutoff = latestTs - 6 * 60 * 60 * 1000;
      const thirtyMinCutoff = latestTs - 30 * 60 * 1000;

      const sixH = readings.filter((r) => new Date(r.timestamp).getTime() >= sixHourCutoff);
      const thirtyM = readings.filter((r) => new Date(r.timestamp).getTime() >= thirtyMinCutoff);

      const tMin = min(sixH.length ? sixH : readings, (d) => d.temperature) ?? 20;
      const tMax = max(sixH.length ? sixH : readings, (d) => d.temperature) ?? 32;
      const hMin = min(sixH.length ? sixH : readings, (d) => d.humidity) ?? 45;
      const hMax = max(sixH.length ? sixH : readings, (d) => d.humidity) ?? 75;

      return {
        sixHourReadings: sixH.length ? sixH : readings,
        thirtyMinReadings: thirtyM.length ? thirtyM : readings.slice(-15),
        latestReading: latest,
        xDomain: [Math.min(18, Math.floor(tMin - 1)), Math.max(34, Math.ceil(tMax + 1))],
        yDomain: [Math.min(25, Math.floor(hMin - 2)), Math.max(80, Math.ceil(hMax + 2))],
      };
    }, [readings]);

  // Step 3: D3 linear scales
  const xScale = useMemo(() => scaleLinear().domain(xDomain).range([0, innerWidth]), [xDomain, innerWidth]);
  const yScale = useMemo(() => scaleLinear().domain(yDomain).range([innerHeight, 0]), [yDomain, innerHeight]);

  // Step 4: 30-minute state trajectory line
  const trailPath = useMemo(() => {
    if (thirtyMinReadings.length < 2) return "";
    const l = line().x((d) => xScale(d.temperature)).y((d) => yScale(d.humidity)).curve(curveMonotoneX);
    return l(thirtyMinReadings) || "";
  }, [thirtyMinReadings, xScale, yScale]);

  const xTicks = xScale.ticks(4);
  const yTicks = yScale.ticks(4);

  // Comfort box boundaries (20-26 °C, 30-60% RH)
  const cX1 = xScale(20);
  const cX2 = xScale(26);
  const cY1 = yScale(60);
  const cY2 = yScale(30);

  return (
    <div className="w-full flex flex-col">
      {/* Header bar */}
      <div className="flex items-center justify-between pb-2 border-b border-[#CBD5D0]">
        <div className="text-[13px] text-[#4F5F69] font-sans">
          Temperature and humidity state space
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full overflow-hidden bg-[#EEF1EF] border border-[#CBD5D0] mt-2">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto block select-none" aria-label="Room state space">
          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {/* Background Rect */}
            <rect x="0" y="0" width={innerWidth} height={innerHeight} fill="#EEF1EF" />

            {/* Thermal Comfort Target Box (20-26 °C, 30-60% RH) */}
            {cX2 > cX1 && cY2 > cY1 && (
              <g>
                <rect
                  x={Math.max(0, cX1)}
                  y={Math.max(0, cY1)}
                  width={Math.min(innerWidth, cX2) - Math.max(0, cX1)}
                  height={Math.min(innerHeight, cY2) - Math.max(0, cY1)}
                  fill="rgba(40, 112, 74, 0.05)"
                  stroke="#28704A"
                  strokeWidth="1"
                  strokeDasharray="3,3"
                  opacity="0.45"
                />
                <text
                  x={Math.max(0, cX1) + 4}
                  y={Math.max(0, cY1) + 12}
                  fill="#28704A"
                  fontSize="10"
                  fontFamily="'Atkinson Hyperlegible', sans-serif"
                  opacity="0.8"
                >
                  Comfort zone
                </text>
              </g>
            )}

            {/* Vertical grid lines (Temperature) */}
            {xTicks.map((tick, i) => (
              <line key={`rx-${i}`} x1={xScale(tick)} x2={xScale(tick)} y1={0} y2={innerHeight} stroke="#CBD5D0" strokeWidth="1" strokeDasharray="2,2" />
            ))}

            {/* Horizontal grid lines (Humidity) */}
            {yTicks.map((tick, i) => (
              <line key={`ry-${i}`} x1={0} x2={innerWidth} y1={yScale(tick)} y2={yScale(tick)} stroke="#CBD5D0" strokeWidth="1" strokeDasharray="2,2" />
            ))}

            {/* 1. Last 6 hours: faint historical dots */}
            {sixHourReadings.map((r, i) => (
              <circle key={`hist-${i}`} cx={xScale(r.temperature)} cy={yScale(r.humidity)} r="1.5" fill="#CBD5D0" opacity="0.8" />
            ))}

            {/* 2. Last 30 minutes: connected trail */}
            {trailPath && (
              <path d={trailPath} fill="none" stroke="#4F5F69" strokeWidth="1.25" strokeDasharray="2,2" opacity="0.9" />
            )}

            {/* 3. Latest reading: filled dot */}
            {latestReading && (
              <g>
                <circle cx={xScale(latestReading.temperature)} cy={yScale(latestReading.humidity)} r="5" fill={isUnusual ? "#7A4B00" : "#28704A"} stroke="#EEF1EF" strokeWidth="1.5" />
                <circle cx={xScale(latestReading.temperature)} cy={yScale(latestReading.humidity)} r="8" fill="none" stroke={isUnusual ? "#7A4B00" : "#28704A"} strokeWidth="1" opacity="0.5" />
              </g>
            )}

            {/* X-axis tick labels */}
            {xTicks.map((tick, i) => (
              <text key={`rxt-${i}`} x={xScale(tick)} y={innerHeight + 18} textAnchor="middle" fill="#4F5F69" fontSize="11" fontFamily="'Atkinson Hyperlegible', sans-serif">
                {tick}°
              </text>
            ))}
            <text x={innerWidth / 2} y={innerHeight + 34} textAnchor="middle" fill="#1C2A33" fontSize="12" fontFamily="'Atkinson Hyperlegible', sans-serif">
              Temperature (°C)
            </text>

            {/* Y-axis tick labels */}
            {yTicks.map((tick, i) => (
              <text key={`ryt-${i}`} x="-8" y={yScale(tick) + 4} textAnchor="end" fill="#4F5F69" fontSize="11" fontFamily="'Atkinson Hyperlegible', sans-serif">
                {tick}%
              </text>
            ))}
            <text transform="rotate(-90)" x={-innerHeight / 2} y="-36" textAnchor="middle" fill="#1C2A33" fontSize="12" fontFamily="'Atkinson Hyperlegible', sans-serif">
              Humidity (% RH)
            </text>
          </g>
        </svg>

        {/* Legend / Caption */}
        <div className="p-2.5 border-t border-[#CBD5D0] bg-[#EEF1EF] text-[12px] text-[#4F5F69] font-sans">
          Where the room has been
        </div>
      </div>
    </div>
  );
}
