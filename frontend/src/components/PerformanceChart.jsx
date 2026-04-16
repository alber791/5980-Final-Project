/**
 * PerformanceChart
 * one line chart showing each job run.
 */

import React, { useMemo } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export default function PerformanceChart({
  metrics,
  problemType,
  onClear,
}) {
  const lineData = useMemo(
    () =>
      metrics
        .map((m, index) => ({
          run: index + 1,
          workers: m.num_workers,
          time_ms: m.total_time_ms,
          job_id: m.job_id.slice(0, 8),
        }))
        .sort((a, b) => a.workers - b.workers),
    [metrics]
  );

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
        <button
          onClick={onClear}
          className="ml-auto px-3 py-1 rounded text-sm bg-red-50 text-red-600 hover:bg-red-100"
        >
          Clear data
        </button>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={lineData} margin={{ top: 8, right: 24, left: 8, bottom: 8 }}>
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
            formatter={(v, name) =>
              name === "time_ms" ? [`${v} ms`, "Time"] : [v, name]
            }
            labelFormatter={(label, payload) => {
              const point = payload?.[0]?.payload;
              return point ? `Workers: ${label} • Job: ${point.job_id}` : `Workers: ${label}`;
            }}
          />
          <Line
            type="monotone"
            dataKey="time_ms"
            name="Job time"
            stroke="#6366f1"
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
