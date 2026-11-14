import React, { useMemo } from "react";
import { min, max } from "d3-array";
import { scaleLinear } from "d3-scale";
import { line, curveMonotoneX } from "d3-shape";

export default function RoomMap({ readings = [], isUnusual = false }) {
  // Dimensions for room map phase space
  const width = 340;
  const height = 360;
  const margin = { top: 24, right: 20, bottom: 44, left: 50 };
  const innerWidth = width - margin.left - margin.right;
  const innerHeight = height - margin.top - margin.bottom;

  // Process data for the 3 visual time horizons:
  // 1. Last 6 hours: faint dots
  // 2. Last 30 minutes: connected trail
  // 3. Now: filled active dot
  const { sixHourReadings, thirtyMinReadings, latestReading, xDomain, yDomain } =
    useMemo(() => {
      if (!readings || readings.length === 0) {
        return {
          sixHourReadings: [],
          thirtyMinReadings: [],
          latestReading: null,
          xDomain: [18, 34],
          yDomain: [40, 85],
        };
      }

      const latest = readings[readings.length - 1];
      const latestTs = new Date(latest.timestamp).getTime();

      const sixHourCutoff = latestTs - 6 * 60 * 60 * 1000;
      const thirtyMinCutoff = latestTs - 30 * 60 * 1000;

      const sixH = readings.filter(
        (r) => new Date(r.timestamp).getTime() >= sixHourCutoff
      );
      const thirtyM = readings.filter(
        (r) => new Date(r.timestamp).getTime() >= thirtyMinCutoff
      );

      // Temperature (X) domain
      const tMin = min(sixH.length ? sixH : readings, (d) => d.temperature) ?? 20;
      const tMax = max(sixH.length ? sixH : readings, (d) => d.temperature) ?? 32;

      // Humidity (Y) domain
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

  // Scales
  const xScale = useMemo(
    () => scaleLinear().domain(xDomain).range([0, innerWidth]),
    [xDomain, innerWidth]
  );
  const yScale = useMemo(
    () => scaleLinear().domain(yDomain).range([innerHeight, 0]),
    [yDomain, innerHeight]
  );

  // Line generator for 30-minute trail
  const trailPath = useMemo(() => {
    if (thirtyMinReadings.length < 2) return "";
    const l = line()
      .x((d) => xScale(d.temperature))
      .y((d) => yScale(d.humidity))
      .curve(curveMonotoneX);
    return l(thirtyMinReadings) || "";
  }, [thirtyMinReadings, xScale, yScale]);

  const xTicks = xScale.ticks(4);
  const yTicks = yScale.ticks(4);

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
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto block select-none"
          aria-label="Room state space: temperature vs humidity"
        >
          <g transform={`translate(${margin.left}, ${margin.top})`}>
            {/* Background Rect */}
            <rect
              x="0"
              y="0"
              width={innerWidth}
              height={innerHeight}
              fill="#EEF1EF"
            />

            {/* Vertical grid lines (Temperature) */}
            {xTicks.map((tick, i) => {
              const xPos = xScale(tick);
              return (
                <line
                  key={`rx-${i}`}
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

            {/* Horizontal grid lines (Humidity) */}
            {yTicks.map((tick, i) => {
              const yPos = yScale(tick);
              return (
                <line
                  key={`ry-${i}`}
                  x1={0}
                  x2={innerWidth}
                  y1={yPos}
                  y2={yPos}
                  stroke="#CBD5D0"
                  strokeWidth="1"
                  strokeDasharray="2,2"
                />
              );
            })}

            {/* 1. Last 6 hours: faint historical dots */}
            {sixHourReadings.map((r, i) => (
              <circle
                key={`hist-${i}`}
                cx={xScale(r.temperature)}
                cy={yScale(r.humidity)}
                r="1.5"
                fill="#CBD5D0"
                opacity="0.8"
              />
            ))}

            {/* 2. Last 30 minutes: connected trail */}
            {trailPath && (
              <path
                d={trailPath}
                fill="none"
                stroke="#4F5F69"
                strokeWidth="1.25"
                strokeDasharray="2,2"
                opacity="0.9"
              />
            )}

            {/* 3. Latest reading: filled dot */}
            {latestReading && (
              <g>
                <circle
                  cx={xScale(latestReading.temperature)}
                  cy={yScale(latestReading.humidity)}
                  r="5"
                  fill={isUnusual ? "#7A4B00" : "#28704A"}
                  stroke="#EEF1EF"
                  strokeWidth="1.5"
                />
                <circle
                  cx={xScale(latestReading.temperature)}
                  cy={yScale(latestReading.humidity)}
                  r="8"
                  fill="none"
                  stroke={isUnusual ? "#7A4B00" : "#28704A"}
                  strokeWidth="1"
                  opacity="0.5"
                />
              </g>
            )}

            {/* X-axis tick labels (Temperature °C) */}
            {xTicks.map((tick, i) => (
              <text
                key={`rxt-${i}`}
                x={xScale(tick)}
                y={innerHeight + 18}
                textAnchor="middle"
                fill="#4F5F69"
                fontSize="11"
                fontFamily="'Atkinson Hyperlegible', sans-serif"
              >
                {tick}°
              </text>
            ))}

            {/* X-axis title */}
            <text
              x={innerWidth / 2}
              y={innerHeight + 34}
              textAnchor="middle"
              fill="#1C2A33"
              fontSize="12"
              fontFamily="'Atkinson Hyperlegible', sans-serif"
            >
              Temperature (°C)
            </text>

            {/* Y-axis tick labels (Humidity % RH) */}
            {yTicks.map((tick, i) => (
              <text
                key={`ryt-${i}`}
                x="-8"
                y={yScale(tick) + 4}
                textAnchor="end"
                fill="#4F5F69"
                fontSize="11"
                fontFamily="'Atkinson Hyperlegible', sans-serif"
              >
                {tick}%
              </text>
            ))}

            {/* Y-axis title */}
            <text
              transform="rotate(-90)"
              x={-innerHeight / 2}
              y="-36"
              textAnchor="middle"
              fill="#1C2A33"
              fontSize="12"
              fontFamily="'Atkinson Hyperlegible', sans-serif"
            >
              Humidity (% RH)
            </text>
          </g>
        </svg>

        {/* Legend / Caption directly below chart paper */}
        <div className="p-2.5 border-t border-[#CBD5D0] bg-[#EEF1EF] text-[12px] text-[#4F5F69] font-sans">
          Where the room has been
        </div>
      </div>
    </div>
  );
}
