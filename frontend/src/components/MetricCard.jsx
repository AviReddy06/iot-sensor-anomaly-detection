import React from "react";

export default function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  color = "cognac",
  className = "",
  badge,
}) {
  const colorMap = {
    cognac: {
      accent: "text-cognac-600 dark:text-cognac-400",
      bg: "bg-cognac-500/10",
      border: "border-cognac-500/25",
      indicator: "bg-cognac-500",
    },
    arctic: {
      accent: "text-arctic-600 dark:text-arctic-400",
      bg: "bg-arctic-500/10",
      border: "border-arctic-500/25",
      indicator: "bg-arctic-500",
    },
    sage: {
      accent: "text-sage-600 dark:text-sage-400",
      bg: "bg-sage-500/10",
      border: "border-sage-500/25",
      indicator: "bg-sage-500",
    },
    amber: {
      accent: "text-amber-600 dark:text-amber-400",
      bg: "bg-amber-500/10",
      border: "border-amber-500/25",
      indicator: "bg-amber-500",
    },
    crimson: {
      accent: "text-crimson-600 dark:text-crimson-400",
      bg: "bg-crimson-500/10",
      border: "border-crimson-500/25",
      indicator: "bg-crimson-500",
    },
    orange: {
      accent: "text-cognac-600 dark:text-cognac-400",
      bg: "bg-cognac-500/10",
      border: "border-cognac-500/25",
      indicator: "bg-cognac-500",
    },
    glacier: {
      accent: "text-arctic-600 dark:text-arctic-400",
      bg: "bg-arctic-500/10",
      border: "border-arctic-500/25",
      indicator: "bg-arctic-500",
    },
    jade: {
      accent: "text-sage-600 dark:text-sage-400",
      bg: "bg-sage-500/10",
      border: "border-sage-500/25",
      indicator: "bg-sage-500",
    },
    coral: {
      accent: "text-crimson-600 dark:text-crimson-400",
      bg: "bg-crimson-500/10",
      border: "border-crimson-500/25",
      indicator: "bg-crimson-500",
    },
  };

  const scheme = colorMap[color] || colorMap.cognac;

  return (
    <div
      className={`bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl p-4 shadow-card dark:shadow-card-dark relative overflow-hidden transition-all duration-150 hover:border-paper-300 dark:hover:border-obsidian-600 ${className}`}
    >
      {/* Top Header */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className={`w-1.5 h-1.5 rounded-full ${scheme.indicator}`} />
          <span className="text-[11px] font-mono uppercase tracking-wider text-paper-500 dark:text-obsidian-400 font-semibold truncate">
            {title}
          </span>
        </div>
        {Icon && (
          <div
            className={`p-1.5 rounded-md ${scheme.bg} ${scheme.accent} border ${scheme.border} flex-shrink-0`}
          >
            <Icon className="w-3.5 h-3.5 stroke-[2.2]" />
          </div>
        )}
      </div>

      {/* Main Metric Value */}
      <div className="flex items-baseline gap-2 mt-1">
        <div className="text-2xl font-bold font-mono tracking-tight text-paper-900 dark:text-obsidian-50 truncate">
          {value}
        </div>
        {badge && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-paper-100 dark:bg-obsidian-800 text-paper-600 dark:text-obsidian-300 border border-paper-200 dark:border-obsidian-700">
            {badge}
          </span>
        )}
      </div>

      {/* Footer / Trend Info */}
      <div className="flex items-center justify-between gap-2 mt-2 pt-2 border-t border-paper-100 dark:border-obsidian-800/80">
        <span className="text-xs text-paper-500 dark:text-obsidian-400 font-sans truncate">
          {subtitle}
        </span>
        {trend && (
          <span
            className={`text-[10px] font-mono font-medium px-1.5 py-0.5 rounded ${scheme.bg} ${scheme.accent}`}
          >
            {trend}
          </span>
        )}
      </div>
    </div>
  );
}
