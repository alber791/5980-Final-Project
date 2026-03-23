/**
 * PerformanceChart
 * one line chart showing each job run.
 */

import React, { useMemo } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const SERIES_COLORS = [
  "#6366f1",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#3b82f6",
  "#8b5cf6",
  "#14b8a6",
  "#f97316",
];

export default function PerformanceChart({
  metrics,
  problemType,
  onClear,
}) {
  const { chartData, seriesKeys } = useMemo(() => {
    const labels = [];
    const groupedByWorkers = new Map();

    const sortedMetrics = [...metrics].sort((a, b) => {
      const labelA = a.cpu_budget_label ?? "Unlabeled";
      const labelB = b.cpu_budget_label ?? "Unlabeled";
      if (labelA !== labelB) return labelA.localeCompare(labelB);
      return a.num_workers - b.num_workers;
    });

    for (const metric of sortedMetrics) {
      const label = metric.cpu_budget_label ?? "Unlabeled";
      if (!labels.includes(label)) {
        labels.push(label);
      }

      if (!groupedByWorkers.has(metric.num_workers)) {
        groupedByWorkers.set(metric.num_workers, { workers: metric.num_workers });
      }

      const row = groupedByWorkers.get(metric.num_workers);
      const bucketKey = `${label}__values`;
      const jobsKey = `${label}__jobs`;
      row[bucketKey] = row[bucketKey] ?? [];
      row[jobsKey] = row[jobsKey] ?? [];
      row[bucketKey].push(metric.total_time_ms);
      row[jobsKey].push(metric.job_id.slice(0, 8));
    }

    const chartData = Array.from(groupedByWorkers.values())
      .map((row) => {
        const nextRow = { workers: row.workers };
        for (const label of labels) {
          const values = row[`${label}__values`] ?? [];
          const jobs = row[`${label}__jobs`] ?? [];
          if (values.length > 0) {
            nextRow[label] = Number(
              (values.reduce((sum, value) => sum + value, 0) / values.length).toFixed(2)
            );
            nextRow[`${label}__job`] = jobs.join(", ");
          }
        }
        return nextRow;
      })
      .sort((a, b) => a.workers - b.workers);

    return {
      chartData,
      seriesKeys: labels,
    };
  }, [metrics]);

  if (metrics.length === 0) {
    return (
      <div className="text-center text-gray-400 py-16 space-y-2">
        <p>No metrics yet.</p>
        <p className="text-sm">Run a benchmark to generate chart data.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
        <span className="text-sm text-gray-500">
          {metrics.length} run{metrics.length !== 1 ? "s" : ""} for{" "}
          <span className="font-medium text-indigo-600">{problemType}</span>
        </span>
        <span className="text-xs text-gray-400">
          {seriesKeys.length} CPU profile line{seriesKeys.length !== 1 ? "s" : ""}
        </span>
        <button
          onClick={onClear}
          className="ml-auto px-3 py-1 rounded text-sm bg-red-50 text-red-600 hover:bg-red-100"
        >
          Clear data
        </button>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={chartData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="workers"
            label={{ value: "Workers", position: "insideBottom", offset: -2 }}
            type="number"
            domain={["dataMin", "dataMax"]}
          />
          <YAxis
            label={{ value: "Time (ms)", angle: -90, position: "insideLeft", offset: 8 }}
          />
          <Tooltip
            formatter={(v, name) => [`${v} ms`, name]}
            labelFormatter={(label, payload) => {
              const jobs = (payload ?? [])
                .map((item) => {
                  const jobId = item?.payload?.[`${item.dataKey}__job`];
                  return jobId ? `${item.name}: ${jobId}` : null;
                })
                .filter(Boolean)
                .join(" • ");
              return jobs ? `Workers: ${label} • ${jobs}` : `Workers: ${label}`;
            }}
          />
          <Legend />
          {seriesKeys.map((seriesKey, index) => (
            <Line
              key={seriesKey}
              type="monotone"
              dataKey={seriesKey}
              name={seriesKey}
              stroke={SERIES_COLORS[index % SERIES_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 4 }}
              activeDot={{ r: 6 }}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
