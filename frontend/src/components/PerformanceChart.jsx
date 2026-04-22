/**
 * PerformanceChart
 * Groups runs by worker count and shows average time with min/max range.
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

export default function PerformanceChart({ metrics, problemType, onClear }) {
  const lineData = useMemo(() => {
    // Group all runs by num_workers
    const groups = {};
    for (const m of metrics) {
      const key = m.num_workers;
      if (!groups[key]) groups[key] = [];
      groups[key].push(m.total_time_ms);
    }
    return Object.entries(groups)
      .map(([workers, times]) => {
        const avg = times.reduce((a, b) => a + b, 0) / times.length;
        const min = Math.min(...times);
        const max = Math.max(...times);
        return {
          workers: Number(workers),
          avg: parseFloat(avg.toFixed(2)),
          min: parseFloat(min.toFixed(2)),
          max: parseFloat(max.toFixed(2)),
          runs: times.length,
        };
      })
      .sort((a, b) => a.workers - b.workers);
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
        <span>
          {lineData.length} worker-count{lineData.length !== 1 ? "s" : ""} ·{" "}
          {metrics.length} total run{metrics.length !== 1 ? "s" : ""} for{" "}
          <span className="font-medium text-indigo-600">{problemType}</span>
        </span>
        <button
          onClick={onClear}
          className="ml-auto px-3 py-1 rounded text-sm bg-red-50 text-red-600 hover:bg-red-100"
        >
          Clear data
        </button>
      </div>

      <ResponsiveContainer width="100%" height={340}>
        <LineChart data={lineData} margin={{ top: 8, right: 24, left: 8, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis
            dataKey="workers"
            label={{ value: "Workers", position: "insideBottom", offset: -12 }}
            type="number"
            domain={["dataMin", "dataMax"]}
            allowDecimals={false}
          />
          <YAxis
            label={{ value: "Time (ms)", angle: -90, position: "insideLeft", offset: 8 }}
          />
          <Tooltip
            content={({ active, payload }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0].payload;
              return (
                <div className="bg-white border border-gray-200 rounded shadow p-2 text-xs space-y-0.5">
                  <p className="font-semibold">{d.workers} worker{d.workers !== 1 ? "s" : ""}</p>
                  <p>Avg: <span className="text-indigo-600 font-medium">{d.avg} ms</span></p>
                  <p>Min: {d.min} ms · Max: {d.max} ms</p>
                  <p className="text-gray-400">{d.runs} run{d.runs !== 1 ? "s" : ""}</p>
                </div>
              );
            }}
          />
          {/* min line */}
          <Line
            type="monotone"
            dataKey="min"
            name="Min"
            stroke="#86efac"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
          />
          {/* max line */}
          <Line
            type="monotone"
            dataKey="max"
            name="Max"
            stroke="#fca5a5"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
          />
          {/* avg line */}
          <Line
            type="monotone"
            dataKey="avg"
            name="Avg"
            stroke="#6366f1"
            strokeWidth={2.5}
            dot={{ r: 4, fill: "#6366f1" }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex gap-4 text-xs text-gray-500 justify-center">
        <span className="flex items-center gap-1">
          <span className="inline-block w-6 h-0.5 bg-indigo-500" /> Avg
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-6 h-0.5 bg-green-400" /> Min
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-6 h-0.5 bg-red-400" /> Max
        </span>
      </div>
    </div>
  );
}

