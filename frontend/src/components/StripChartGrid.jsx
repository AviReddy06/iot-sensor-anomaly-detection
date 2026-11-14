import React from "react";

export default function StripChartGrid({
  width,
  totalHeight,
  margin,
  innerWidth,
  innerHeight,
  panelHeight,
  panelGap,
  xScale,
  yTempScale,
  yHumScale,
  tempPath,
  humPath,
  xTicks,
  xMinorTicks,
  yTempTicks,
  yHumTicks,
  gaps,
  directLabels,
  visibleEventBands,
  hoverData,
  onPointerDown,
  onPointerMove,
  onPointerUp,
  onPointerLeave,
}) {
  // Step 1: Coordinates for ASHRAE 55 thermal comfort bands
  const tempTop = yTempScale ? Math.min(yTempScale(26), yTempScale(20)) : 0;
  const tempBottom = yTempScale ? Math.max(yTempScale(26), yTempScale(20)) : 0;
  const humTop = yHumScale ? Math.min(yHumScale(60), yHumScale(30)) : 0;
  const humBottom = yHumScale ? Math.max(yHumScale(60), yHumScale(30)) : 0;

  return (
    <div className="relative w-full">
      <svg
        width={width}
        height={totalHeight}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerLeave}
        className="block select-none cursor-crosshair touch-none"
      >
        <defs>
          {/* Step 2: Light diagonal hatching pattern for data gaps (>10s) */}
          <pattern id="data-gap-hatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="8" stroke="#CBD5D0" strokeWidth="1" opacity="0.6" />
          </pattern>
          {/* Diagonal hatching pattern for unusual bands in print / high-contrast modes */}
          <pattern id="unusual-band-hatch" width="8" height="8" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="8" stroke="#1C2A33" strokeWidth="1.2" opacity="0.45" />
          </pattern>
        </defs>

        <g transform={`translate(${margin.left}, ${margin.top})`}>
          {/* Step 3: Two discrete panel backgrounds with 8px gap */}
          <rect x="0" y="0" width={innerWidth} height={panelHeight} fill="#EEF1EF" />
          <rect x="0" y={panelHeight + panelGap} width={innerWidth} height={panelHeight} fill="#EEF1EF" />

          {/* Step 4: Render data gap breaks with diagonal hatching */}
          {gaps && gaps.map((gap, i) => (
            <rect key={`gap-${i}`} x={gap.x} y={0} width={gap.width} height={innerHeight} fill="url(#data-gap-hatch)" />
          ))}

          {/* Step 5: Minor 15-minute grid rulings at lower opacity */}
          {xMinorTicks && xMinorTicks.map((tick, i) => (
            <line key={`xtm-${i}`} x1={xScale ? xScale(tick) : 0} x2={xScale ? xScale(tick) : 0} y1={0} y2={innerHeight} stroke="#CBD5D0" strokeWidth="1" strokeDasharray="1,3" opacity="0.35" />
          ))}

          {/* Step 6: Hourly major grid rulings */}
          {xTicks && xTicks.map((tick, i) => (
            <line key={`xt-${i}`} x1={xScale ? xScale(tick) : 0} x2={xScale ? xScale(tick) : 0} y1={0} y2={innerHeight} stroke="#CBD5D0" strokeWidth="1" strokeDasharray="2,2" opacity="0.8" />
          ))}

          {/* Step 7: Comfort bands and horizontal grid hairlines */}
          {yTempScale && tempBottom > tempTop && (
            <g>
              <rect x="0" y={tempTop} width={innerWidth} height={tempBottom - tempTop} fill="rgba(40, 112, 74, 0.05)" />
              <line x1="0" x2={innerWidth} y1={tempTop} y2={tempTop} stroke="#28704A" strokeWidth="1" strokeDasharray="3,3" opacity="0.35" />
              <line x1="0" x2={innerWidth} y1={tempBottom} y2={tempBottom} stroke="#28704A" strokeWidth="1" strokeDasharray="3,3" opacity="0.35" />
            </g>
          )}
          {yTempTicks && yTempTicks.map((t, i) => (
            <line key={`yt-${i}`} x1={0} x2={innerWidth} y1={yTempScale(t)} y2={yTempScale(t)} stroke="#CBD5D0" strokeWidth="1" />
          ))}

          {/* Step 8: Hairlines bounding the 8px dividing gap */}
          <line x1={0} x2={innerWidth} y1={panelHeight} y2={panelHeight} stroke="#CBD5D0" strokeWidth="1" />
          <line x1={0} x2={innerWidth} y1={panelHeight + panelGap} y2={panelHeight + panelGap} stroke="#CBD5D0" strokeWidth="1" />

          {yHumScale && humBottom > humTop && (
            <g>
              <rect x="0" y={humTop} width={innerWidth} height={humBottom - humTop} fill="rgba(40, 112, 74, 0.05)" />
              <line x1="0" x2={innerWidth} y1={humTop} y2={humTop} stroke="#28704A" strokeWidth="1" strokeDasharray="3,3" opacity="0.35" />
              <line x1="0" x2={innerWidth} y1={humBottom} y2={humBottom} stroke="#28704A" strokeWidth="1" strokeDasharray="3,3" opacity="0.35" />
            </g>
          )}
          {yHumTicks && yHumTicks.map((t, i) => (
            <line key={`yh-${i}`} x1={0} x2={innerWidth} y1={yHumScale(t)} y2={yHumScale(t)} stroke="#CBD5D0" strokeWidth="1" />
          ))}

          {/* Step 9: Shaded unusual event bands with darker top edge, boundary hairlines, and '#1' numbering */}
          {visibleEventBands && visibleEventBands.map((band) => (
            <g key={`band-${band.id}`}>
              <rect className="unusual-band-rect" x={band.x} y={0} width={band.width} height={innerHeight} fill="rgba(232, 176, 74, 0.35)" />
              <line className="unusual-band-top" x1={band.x} x2={band.x + band.width} y1={0} y2={0} stroke="#7A4B00" strokeWidth="2" />
              <line x1={band.x} x2={band.x} y1={0} y2={innerHeight} stroke="#7A4B00" strokeWidth="0.75" opacity="0.4" />
              <line x1={band.x + band.width} x2={band.x + band.width} y1={0} y2={innerHeight} stroke="#7A4B00" strokeWidth="0.75" opacity="0.4" />
              <text className="unusual-band-text" x={band.x + 3} y={13} fill="#7A4B00" fontSize="13" fontFamily="'Atkinson Hyperlegible', sans-serif" fontWeight="bold">
                {band.label}
              </text>
            </g>
          ))}

          {/* Step 10: Continuous ink traces (strictly 1.5px trace weight, no markers) */}
          {tempPath && <path d={tempPath} fill="none" stroke="#9B2C2C" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />}
          {humPath && <path d={humPath} fill="none" stroke="#1D5C8C" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />}

          {/* Step 11: Direct line-end reading labels with non-overlapping bounds */}
          {directLabels && (
            <g>
              <text x={innerWidth + 6} y={directLabels.tempY + 4} fill="#9B2C2C" fontSize="13" fontWeight="bold" fontFamily="'Atkinson Hyperlegible', sans-serif" className="num-tabular">
                {directLabels.tempVal.toFixed(1)}{"\u2009"}°C
              </text>
              <text x={innerWidth + 6} y={directLabels.humY + 4} fill="#1D5C8C" fontSize="13" fontWeight="bold" fontFamily="'Atkinson Hyperlegible', sans-serif" className="num-tabular">
                {directLabels.humVal.toFixed(1)}{"\u2009"}% RH
              </text>
            </g>
          )}

          {/* Step 12: Left axis tick labels (13px Atkinson Hyperlegible) */}
          {yTempTicks && yTempTicks.map((t, i) => (
            <text key={`ytl-${i}`} x="-8" y={yTempScale(t) + 4} textAnchor="end" fill="#4F5F69" fontSize="13" fontFamily="'Atkinson Hyperlegible', sans-serif" className="num-tabular">
              {t}°
            </text>
          ))}
          {yHumTicks && yHumTicks.map((t, i) => (
            <text key={`yhl-${i}`} x="-8" y={yHumScale(t) + 4} textAnchor="end" fill="#4F5F69" fontSize="13" fontFamily="'Atkinson Hyperlegible', sans-serif" className="num-tabular">
              {t}%
            </text>
          ))}

          {/* Step 13: 24-Hour time axis labels (date only on midnight / day change) */}
          {xTicks && xTicks.map((tick, i) => {
            const d = new Date(tick);
            const isMidnight = d.getHours() === 0 && d.getMinutes() === 0;
            const isDayChange = i > 0 && d.getDate() !== new Date(xTicks[i - 1]).getDate();
            const timeStr = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
            const showDate = isMidnight || isDayChange;
            const dateStr = d.toLocaleDateString("en-GB", { day: "numeric", month: "short" });
            return (
              <g key={`xtl-${i}`} transform={`translate(${xScale(tick)}, ${innerHeight + 18})`}>
                <text textAnchor="middle" fill="#4F5F69" fontSize="13" fontFamily="'Atkinson Hyperlegible', sans-serif" className="num-tabular">
                  {timeStr}
                </text>
                {showDate && (
                  <text y="14" textAnchor="middle" fill="#1C2A33" fontSize="13" fontWeight="bold" fontFamily="'Atkinson Hyperlegible', sans-serif">
                    {dateStr}
                  </text>
                )}
              </g>
            );
          })}

          {/* Step 14: Synchronized crosshair across both panels */}
          {hoverData && xScale && yTempScale && yHumScale && (
            <g className="pointer-events-none">
              <line
                x1={xScale(new Date(hoverData.timestamp))}
                x2={xScale(new Date(hoverData.timestamp))}
                y1={0}
                y2={innerHeight}
                stroke="#1C2A33"
                strokeWidth="1"
                strokeDasharray="2,2"
                opacity="0.8"
              />
              <circle cx={xScale(new Date(hoverData.timestamp))} cy={yTempScale(hoverData.temperature)} r="3.5" fill="#9B2C2C" stroke="#EEF1EF" strokeWidth="1.5" />
              <circle cx={xScale(new Date(hoverData.timestamp))} cy={yHumScale(hoverData.humidity)} r="3.5" fill="#1D5C8C" stroke="#EEF1EF" strokeWidth="1.5" />
            </g>
          )}
        </g>
      </svg>

      {/* Step 15: Synchronized unified floating tooltip */}
      {hoverData && xScale && (
        <div
          className="absolute pointer-events-none bg-[#EEF1EF] border border-[#CBD5D0] px-2.5 py-1 text-[13px] font-sans text-[#1C2A33] z-10"
          style={{
            top: 6,
            left: Math.min(
              Math.max(margin.left + 4, margin.left + xScale(new Date(hoverData.timestamp)) - 90),
              Math.max(margin.left + 4, width - margin.right - 200)
            ),
          }}
        >
          <div className="flex items-center gap-2.5">
            <span className="text-[#4F5F69] num-tabular">{hoverData.timestamp.slice(11, 19)}</span>
            <span className="text-[#9B2C2C] font-bold num-tabular">{Number(hoverData.temperature).toFixed(1)}{"\u2009"}°C</span>
            <span className="text-[#1D5C8C] font-bold num-tabular">{Number(hoverData.humidity).toFixed(1)}{"\u2009"}% RH</span>
          </div>
        </div>
      )}
    </div>
  );
}
