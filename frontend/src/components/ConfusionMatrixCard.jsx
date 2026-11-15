import React from "react";

export default function ConfusionMatrixCard({ matrix }) {
  if (!matrix) return null;

  const {
    tp = 0,
    fp = 0,
    fn = 0,
    tn = 0,
    precision = 0,
    recall = 0,
    f1 = 0,
  } = matrix;
  const total = tp + fp + fn + tn;
  const specificity = tn + fp > 0 ? (tn / (tn + fp)) * 100 : 0;

  return (
    <div className="bg-white dark:bg-obsidian-850 border border-paper-200 dark:border-obsidian-750 rounded-xl p-5 shadow-card dark:shadow-card-dark transition-colors">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h4 className="text-sm font-bold text-paper-900 dark:text-obsidian-100 font-mono uppercase tracking-wider">
            Ground-Truth Evaluation Matrix
          </h4>
          <p className="text-xs text-paper-500 dark:text-obsidian-400 font-mono">
            Evaluated on {total.toLocaleString()} labeled test samples
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-cognac-500/15 text-cognac-700 dark:text-cognac-400 border border-cognac-500/30">
            F1: {(f1 * 100).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* 2x2 Grid */}
      <div className="grid grid-cols-2 gap-3 mb-4 font-mono">
        {/* TP */}
        <div className="p-3.5 rounded-lg bg-sage-500/10 border border-sage-500/30 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-sage-700 dark:text-sage-400 uppercase tracking-wider">
              True Positives (TP)
            </span>
            <span className="text-[10px] text-sage-600 dark:text-sage-300 font-semibold">
              {total > 0 ? `${((tp / total) * 100).toFixed(1)}%` : "0%"}
            </span>
          </div>
          <span className="text-2xl font-bold text-paper-900 dark:text-white mt-1 tabular-nums">
            {tp.toLocaleString()}
          </span>
          <span className="text-[10px] text-paper-500 dark:text-obsidian-400 mt-1">
            Correctly caught environmental anomalies
          </span>
        </div>

        {/* FP */}
        <div className="p-3.5 rounded-lg bg-crimson-500/10 border border-crimson-500/30 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-crimson-700 dark:text-crimson-400 uppercase tracking-wider">
              False Positives (FP)
            </span>
            <span className="text-[10px] text-crimson-600 dark:text-crimson-300 font-semibold">
              {total > 0 ? `${((fp / total) * 100).toFixed(1)}%` : "0%"}
            </span>
          </div>
          <span className="text-2xl font-bold text-paper-900 dark:text-white mt-1 tabular-nums">
            {fp.toLocaleString()}
          </span>
          <span className="text-[10px] text-paper-500 dark:text-obsidian-400 mt-1">
            False alarms triggered on normal ambient drift
          </span>
        </div>

        {/* FN */}
        <div className="p-3.5 rounded-lg bg-amber-500/10 border border-amber-500/30 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-amber-700 dark:text-amber-400 uppercase tracking-wider">
              False Negatives (FN)
            </span>
            <span className="text-[10px] text-amber-600 dark:text-amber-300 font-semibold">
              {total > 0 ? `${((fn / total) * 100).toFixed(1)}%` : "0%"}
            </span>
          </div>
          <span className="text-2xl font-bold text-paper-900 dark:text-white mt-1 tabular-nums">
            {fn.toLocaleString()}
          </span>
          <span className="text-[10px] text-paper-500 dark:text-obsidian-400 mt-1">
            Missed anomaly samples during recovery tails
          </span>
        </div>

        {/* TN */}
        <div className="p-3.5 rounded-lg bg-paper-100 dark:bg-obsidian-800 border border-paper-200 dark:border-obsidian-700 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-paper-700 dark:text-obsidian-300 uppercase tracking-wider">
              True Negatives (TN)
            </span>
            <span className="text-[10px] text-paper-500 dark:text-obsidian-400 font-semibold">
              {total > 0 ? `${((tn / total) * 100).toFixed(1)}%` : "0%"}
            </span>
          </div>
          <span className="text-2xl font-bold text-paper-900 dark:text-white mt-1 tabular-nums">
            {tn.toLocaleString()}
          </span>
          <span className="text-[10px] text-paper-500 dark:text-obsidian-400 mt-1">
            Correctly verified normal climate periods
          </span>
        </div>
      </div>

      {/* Summary Rates */}
      <div className="grid grid-cols-4 gap-2 pt-3 border-t border-paper-200 dark:border-obsidian-800 text-center font-mono">
        <div>
          <span className="text-[10px] text-paper-500 dark:text-obsidian-400 block uppercase">Precision</span>
          <span className="text-sm font-bold text-paper-900 dark:text-white">{(precision * 100).toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-[10px] text-paper-500 dark:text-obsidian-400 block uppercase">Recall</span>
          <span className="text-sm font-bold text-paper-900 dark:text-white">{(recall * 100).toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-[10px] text-paper-500 dark:text-obsidian-400 block uppercase">F1-Score</span>
          <span className="text-sm font-bold text-cognac-600 dark:text-cognac-400">{(f1 * 100).toFixed(1)}%</span>
        </div>
        <div>
          <span className="text-[10px] text-paper-500 dark:text-obsidian-400 block uppercase">Specificity</span>
          <span className="text-sm font-bold text-sage-600 dark:text-sage-400">{specificity.toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}
