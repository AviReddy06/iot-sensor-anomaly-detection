import React from "react";

export default function StripChartGrid({
  dimensions,
  margin,
  innerWidth,
  innerHeight,
  chartSplitY,
  xScale,
  yTempScale,
  yHumScale,
  tempPath,
  humPath,
  xTicks,
  yTempTicks,
  yHumTicks,
  visibleEventBands,
  hoverData,
  onPointerMove,
  onPointerLeave,
}) {
  // Step 1: Compute coordinates for ASHRAE 55 thermal comfort envelopes
  const tempTop = yTempScale ? Math.min(yTempScale(26), yTempScale(20)) : 0;
  const tempBottom = yTempScale ? Math.max(yTempScale(26), yTempScale(20)) : 0;
  const humTop = yHumScale ? Math.min(yHumScale(60), yHumScale(30)) : 0;
  const humBottom = yHumScale ? Math.max(yHumScale(60), yHumScale(30)) : 0;

  return (
    <svg
      width={dimensions.width}
      height={dimensions.height}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      className="block select-none cursor-crosshair"
      aria-label="Continuous temperature and relative humidity chart"
    >
      <g transform={`translate(${margin.left}, ${margin.top})`}>
        {/* Step 2: Background Paper & Time Grids */}
        <rect x="0" y="0" width={innerWidth} height={innerHeight} fill="#EEF1EF" />
        {xTicks.map((tick, i) => (
          <line
            key={`xt-${i}`}
            x1={xScale ? xScale(tick) : 0}
            x2={xScale ? xScale(tick) : 0}
            y1={0}
            y2={innerHeight}
            stroke="#CBD5D0"
            strokeWidth="1"
            strokeDasharray="2,2"
          />
        ))}

        {/* Step 3: Temperature Comfort Band (20 - 26 °C) & Grid */}
        {yTempScale && tempBottom > tempTop && (
          <g>
            <rect x="0" y={tempTop} width={innerWidth} height={tempBottom - tempTop} fill="rgba(40, 112, 74, 0.05)" />
            <line x1="0" x2={innerWidth} y1={tempTop} y2={tempTop} stroke="#28704A" strokeWidth="1" strokeDasharray="3,3" opacity="0.35" />
            <line x1="0" x2={innerWidth} y1={tempBottom} y2={tempBottom} stroke="#28704A" strokeWidth="1" strokeDasharray="3,3" opacity="0.35" />
          </g>
        )}
        {yTempTicks.map((t, i) => (
          <line key={`yt-${i}`} x1={0} x2={innerWidth} y1={yTempScale(t)} y2={yTempScale(t)} stroke="#CBD5D0" strokeWidth="1" />
        ))}

        {/* Step 4: Separator hairline between channels */}
        <line x1={0} x2={innerWidth} y1={chartSplitY} y2={chartSplitY} stroke="#CBD5D0" strokeWidth="1" />

        {/* Step 5: Humidity Comfort Band (30 - 60 % RH) & Grid */}
        {yHumScale && humBottom > humTop && (
          <g>
            <rect x="0" y={humTop} width={innerWidth} height={humBottom - humTop} fill="rgba(40, 112, 74, 0.05)" />
            <line x1="0" x2={innerWidth} y1={humTop} y2={humTop} stroke="#28704A" strokeWidth="1" strokeDasharray="3,3" opacity="0.35" />
            <line x1="0" x2={innerWidth} y1={humBottom} y2={humBottom} stroke="#28704A" strokeWidth="1" strokeDasharray="3,3" opacity="0.35" />
          </g>
        )}
        {yHumTicks.map((t, i) => (
          <line key={`yh-${i}`} x1={0} x2={innerWidth} y1={yHumScale(t)} y2={yHumScale(t)} stroke="#CBD5D0" strokeWidth="1" />
        ))}

        {/* Step 6: Shaded Unusual Event Highlight Bands */}
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
            <text x={band.x + 3} y={12} fill="#7A4B00" fontSize="11" fontFamily="'Atkinson Hyperlegible', sans-serif" fontWeight="bold">
              {band.label}
            </text>
          </g>
        ))}

        {/* Step 7: Dual Ink Traces (Oxblood & Navy) */}
        {tempPath && <path d={tempPath} fill="none" stroke="#9B2C2C" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />}
        {humPath && <path d={humPath} fill="none" stroke="#1D5C8C" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />}

        {/* Step 8: Unit Headers on Right Margin */}
        <text x={innerWidth + 8} y={yTempScale ? yTempScale.range()[1] + 14 : 14} fill="#9B2C2C" fontSize="12" fontWeight="bold" fontFamily="'Atkinson Hyperlegible', sans-serif">
          °C
        </text>
        <text x={innerWidth + 8} y={yHumScale ? yHumScale.range()[0] : innerHeight} fill="#1D5C8C" fontSize="12" fontWeight="bold" fontFamily="'Atkinson Hyperlegible', sans-serif">
          % RH
        </text>

        {/* Step 9: Left Axis Tick Labels */}
        {yTempTicks.map((t, i) => (
          <text key={`ytl-${i}`} x="-8" y={yTempScale(t) + 4} textAnchor="end" fill="#4F5F69" fontSize="11" fontFamily="'Atkinson Hyperlegible', sans-serif">
            {t}°
          </text>
        ))}
        {yHumTicks.map((t, i) => (
          <text key={`yhl-${i}`} x="-8" y={yHumScale(t) + 4} textAnchor="end" fill="#4F5F69" fontSize="11" fontFamily="'Atkinson Hyperlegible', sans-serif">
            {t}%
          </text>
        ))}

        {/* Step 10: Time Axis Labels */}
        {xTicks.map((tick, i) => {
          const d = new Date(tick);
          const timeStr = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
          return (
            <text key={`xtl-${i}`} x={xScale(tick)} y={innerHeight + 20} textAnchor="middle" fill="#4F5F69" fontSize="11" fontFamily="'Atkinson Hyperlegible', sans-serif">
              {timeStr}
            </text>
          );
        })}

        {/* Step 11: Hover Crosshair and Dual Trace Markers */}
        {hoverData && xScale && yTempScale && yHumScale && (
          <g>
            <line
              x1={xScale(new Date(hoverData.timestamp))}
              x2={xScale(new Date(hoverData.timestamp))}
              y1={0}
              y2={innerHeight}
              stroke="#1C2A33"
              strokeWidth="1"
              strokeDasharray="3,3"
            />
            <circle cx={xScale(new Date(hoverData.timestamp))} cy={yTempScale(hoverData.temperature)} r="3.5" fill="#9B2C2C" stroke="#EEF1EF" strokeWidth="1.5" />
            <circle cx={xScale(new Date(hoverData.timestamp))} cy={yHumScale(hoverData.humidity)} r="3.5" fill="#1D5C8C" stroke="#EEF1EF" strokeWidth="1.5" />
          </g>
        )}
      </g>
    </svg>
  );
}
