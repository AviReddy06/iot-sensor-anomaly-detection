import React, { useMemo } from "react";
import { min, max } from "d3-array";
import { scaleLinear } from "d3-scale";
import { line, curveMonotoneX } from "d3-shape";

export default function RoomMap({ readings = [], events = [], isUnusual = false, isOffline = false }) {
  // Step 1: Geometry & strictly square 1:1 plot area
  const plotSize = 270;
  const margin = { top: 18, right: 18, bottom: 52, left: 52 };
  const width = plotSize + margin.left + margin.right; // 340
  const height = plotSize + margin.top + margin.bottom; // 340

  // Step 2: Time horizons & domains with 2 °C x 10 % RH noise guard
  const { historyReadings, trajectoryReadings, latestReading, unusualHistoricalPoints, xDomain, yDomain } =
    useMemo(() => {
      const MIN_T_SPAN = 2.0, MIN_H_SPAN = 10.0;
      if (!readings || readings.length === 0) {
        return { historyReadings: [], trajectoryReadings: [], latestReading: null, unusualHistoricalPoints: [], xDomain: [20, 26], yDomain: [35, 65] };
      }
      const latest = readings[readings.length - 1];
      const latestTs = new Date(latest.timestamp).getTime();
      const sixH = readings.filter((r) => new Date(r.timestamp).getTime() >= latestTs - 6 * 3600000);
      const hist = sixH.length > 0 ? sixH : readings;
      const thirtyM = readings.filter((r) => new Date(r.timestamp).getTime() >= latestTs - 1800000);
      const traj = thirtyM.length > 0 ? thirtyM : readings.slice(-15);

      // Locate historical unusual event points
      const unusualPts = [];
      if (events?.length > 0) {
        const ranges = events.map((e) => ({
          s: new Date(e.start_time).getTime(),
          e: new Date(e.end_time || e.start_time).getTime() + (e.duration_sec ? e.duration_sec * 1000 : 30000),
        }));
        for (const r of hist) {
          const t = new Date(r.timestamp).getTime();
          if (ranges.some((rg) => t >= rg.s && t <= rg.e)) unusualPts.push(r);
        }
      }

      // Compute raw bounds with padding (0.5 °C, 2.5 % RH)
      let tMin = (min(hist, (d) => d.temperature) ?? latest.temperature) - 0.5;
      let tMax = (max(hist, (d) => d.temperature) ?? latest.temperature) + 0.5;
      let hMin = (min(hist, (d) => d.humidity) ?? latest.humidity) - 2.5;
      let hMax = (max(hist, (d) => d.humidity) ?? latest.humidity) + 2.5;

      // Enforce noise guard minimum span (>= 2 °C by 10 % RH)
      if (tMax - tMin < MIN_T_SPAN) {
        const mid = (tMin + tMax) / 2;
        tMin = mid - MIN_T_SPAN / 2;
        tMax = mid + MIN_T_SPAN / 2;
      }
      if (hMax - hMin < MIN_H_SPAN) {
        const mid = (hMin + hMax) / 2;
        hMin = mid - MIN_H_SPAN / 2;
        hMax = mid + MIN_H_SPAN / 2;
      }

      const xD = [Math.floor(tMin * 2) / 2, Math.ceil(tMax * 2) / 2];
      const yD = [Math.floor(hMin / 5) * 5, Math.ceil(hMax / 5) * 5];
      if (xD[1] - xD[0] < MIN_T_SPAN) xD[1] = xD[0] + MIN_T_SPAN;
      if (yD[1] - yD[0] < MIN_H_SPAN) yD[1] = yD[0] + MIN_H_SPAN;

      return { historyReadings: hist, trajectoryReadings: traj, latestReading: latest, unusualHistoricalPoints: unusualPts, xDomain: xD, yDomain: yD };
    }, [readings, events]);

  // Step 3: D3 scales & trajectory path
  const xScale = useMemo(() => scaleLinear().domain(xDomain).range([0, plotSize]), [xDomain]);
  const yScale = useMemo(() => scaleLinear().domain(yDomain).range([plotSize, 0]), [yDomain]);
  const trailPath = useMemo(() => {
    if (trajectoryReadings.length < 2) return "";
    const l = line().x((d) => xScale(d.temperature)).y((d) => yScale(d.humidity)).curve(curveMonotoneX);
    return l(trajectoryReadings) || "";
  }, [trajectoryReadings, xScale, yScale]);

  const xTicks = xScale.ticks(4);
  const yTicks = yScale.ticks(4);
  const cX1 = xScale(20), cX2 = xScale(26), cY1 = yScale(60), cY2 = yScale(30);
  const nowX = latestReading ? xScale(latestReading.temperature) : null;
  const nowY = latestReading ? yScale(latestReading.humidity) : null;

  // Step 4: Render square 1:1 phase-space SVG canvas
  return (
    <div className="w-full flex flex-col">
      <div className="flex items-center justify-between pb-2 border-b border-[#CBD5D0]">
        <div className="text-[13px] text-[#4F5F69] font-sans">Room map</div>
      </div>
      <div className="relative w-full overflow-hidden bg-[#EEF1EF] border border-[#CBD5D0] mt-6">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className={`w-full aspect-square block select-none ${isOffline ? "opacity-60" : ""}`}
          role="img"
          aria-label={latestReading ? `Room map: ${latestReading.temperature.toFixed(1)}\u2009°C, ${latestReading.humidity.toFixed(1)}\u2009% RH` : "Room map"}
        >
          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {/* Background canvas */}
            <rect x="0" y="0" width={plotSize} height={plotSize} fill="#EEF1EF" />

            {/* Layer 1: Comfort target box (20-26 °C, 30-60 % RH) quiet background reference */}
            {cX2 > cX1 && cY2 > cY1 && (
              <g aria-hidden="true">
                <rect
                  x={Math.max(0, cX1)} y={Math.max(0, cY1)}
                  width={Math.min(plotSize, cX2) - Math.max(0, cX1)}
                  height={Math.min(plotSize, cY2) - Math.max(0, cY1)}
                  fill="rgba(40, 112, 74, 0.04)" stroke="#28704A" strokeWidth="1" strokeDasharray="3,3" opacity="0.35"
                />
                {cX2 - cX1 > 50 && cY2 - cY1 > 22 && (
                  <text x={Math.max(0, cX1) + 6} y={Math.max(0, cY1) + 16} fill="#28704A" fontSize="13" fontFamily="'Atkinson Hyperlegible', sans-serif">
                    Comfort target
                  </text>
                )}
              </g>
            )}

            {/* Grid rulings */}
            {xTicks.map((t, i) => (
              <line key={`rx-${i}`} x1={xScale(t)} x2={xScale(t)} y1={0} y2={plotSize} stroke="#CBD5D0" strokeWidth="1" strokeDasharray="2,2" />
            ))}
            {yTicks.map((t, i) => (
              <line key={`ry-${i}`} x1={0} x2={plotSize} y1={yScale(t)} y2={yScale(t)} stroke="#CBD5D0" strokeWidth="1" strokeDasharray="2,2" />
            ))}

            {/* Layer 2: 6-hour history (faint dots: 2 px diameter, 25 % opacity) */}
            {historyReadings.map((r, i) => (
              <circle key={`hist-${i}`} cx={xScale(r.temperature)} cy={yScale(r.humidity)} r="1" fill="#1C2A33" opacity="0.25" />
            ))}

            {/* Layer 3: 30-minute trajectory (1.5 px continuous trail) */}
            {trailPath && <path d={trailPath} fill="none" stroke="#4F5F69" strokeWidth="1.5" opacity="0.75" />}

            {/* Layer 4: Unusual readings (straw-colored outer ring: #7A4B00 / #E8B04A) */}
            {unusualHistoricalPoints.map((pt, i) => (
              <circle key={`unusual-${i}`} cx={xScale(pt.temperature)} cy={yScale(pt.humidity)} r="6" fill="rgba(232, 176, 74, 0.25)" stroke="#7A4B00" strokeWidth="1" />
            ))}
            {isUnusual && nowX !== null && nowY !== null && (
              <circle cx={nowX} cy={nowY} r="9" fill="rgba(232, 176, 74, 0.35)" stroke="#7A4B00" strokeWidth="1.5" />
            )}

            {/* Layer 5: Now reading (6 px filled dot with label) */}
            {nowX !== null && nowY !== null && (
              <g>
                <circle cx={nowX} cy={nowY} r="3" fill={isUnusual ? "#7A4B00" : "#1C2A33"} stroke="#EEF1EF" strokeWidth="1" />
                <text
                  x={nowX > plotSize - 55 ? nowX - 8 : nowX + 8}
                  y={nowY < 20 ? nowY + 16 : nowY - 6}
                  textAnchor={nowX > plotSize - 55 ? "end" : "start"}
                  fill="#1C2A33" fontSize="13" fontWeight="700" fontFamily="'Atkinson Hyperlegible', sans-serif"
                >
                  Now
                </text>
              </g>
            )}

            {/* X-axis tick labels and explicit unit */}
            {xTicks.map((t, i) => (
              <text key={`rxt-${i}`} x={xScale(t)} y={plotSize + 18} textAnchor="middle" fill="#4F5F69" fontSize="13" fontFamily="'Atkinson Hyperlegible', sans-serif">
                {t}°
              </text>
            ))}
            <text x={plotSize / 2} y={plotSize + 40} textAnchor="middle" fill="#1C2A33" fontSize="13" fontWeight="500" fontFamily="'Atkinson Hyperlegible', sans-serif">
              Temperature (°C)
            </text>

            {/* Y-axis tick labels and explicit unit */}
            {yTicks.map((t, i) => (
              <text key={`ryt-${i}`} x="-10" y={yScale(t) + 4} textAnchor="end" fill="#4F5F69" fontSize="13" fontFamily="'Atkinson Hyperlegible', sans-serif">
                {t}%
              </text>
            ))}
            <text transform="rotate(-90)" x={-plotSize / 2} y="-38" textAnchor="middle" fill="#1C2A33" fontSize="13" fontWeight="500" fontFamily="'Atkinson Hyperlegible', sans-serif">
              Humidity (% RH)
            </text>
          </g>
        </svg>

        {/* Step 5: Exact verbatim caption */}
        <div className="p-3 border-t border-[#CBD5D0] bg-[#EEF1EF] text-[13px] text-[#4F5F69] font-sans">
          Where the room has been: last 6 hours, last 30 minutes, now
        </div>
      </div>
    </div>
  );
}
