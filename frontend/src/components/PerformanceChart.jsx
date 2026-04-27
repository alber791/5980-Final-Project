/**
 * PerformanceChart
 * Renders one chart per benchmark run from browser-only history.
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

function buildLineData(metrics) {
  const groups = {};
  for (const metric of metrics) {
    const key = metric.num_workers;
    if (!groups[key]) groups[key] = [];
    groups[key].push(metric.total_time_ms);
  }

  return Object.entries(groups)
    .map(([workers, times]) => {
      const avg = times.reduce((sum, value) => sum + value, 0) / times.length;
      const min = Math.min(...times);
      const max = Math.max(...times);
      return {
        workers: Number(workers),
        avg: Number(avg.toFixed(2)),
        min: Number(min.toFixed(2)),
        max: Number(max.toFixed(2)),
        runs: times.length,
      };
    })
    .sort((a, b) => a.workers - b.workers);
}

function BenchmarkChartCard({ benchmark }) {
  const lineData = useMemo(() => buildLineData(benchmark.metrics || []), [benchmark.metrics]);

  const created = new Date(benchmark.created_at);
  const createdLabel = Number.isNaN(created.getTime())
    ? benchmark.created_at
    : created.toLocaleString();

  return (
    <div className="border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
        <span className="font-medium text-indigo-600">{benchmark.problem_type}</span>
        <span>• {benchmark.max_workers} max worker{benchmark.max_workers !== 1 ? "s" : ""}</span>
        <span>• {benchmark.runs_per_worker} run{benchmark.runs_per_worker !== 1 ? "s" : ""}/worker</span>
        <span className="ml-auto text-xs text-gray-400">{createdLabel}</span>
      </div>

      <ResponsiveContainer width="100%" height={300}>
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
              const point = payload[0].payload;
              return (
                <div className="bg-white border border-gray-200 rounded shadow p-2 text-xs space-y-0.5">
                  <p className="font-semibold">
                    {point.workers} worker{point.workers !== 1 ? "s" : ""}
                  </p>
                  <p>
                    Avg: <span className="text-indigo-600 font-medium">{point.avg} ms</span>
                  </p>
                  <p>Min: {point.min} ms · Max: {point.max} ms</p>
                  <p className="text-gray-400">
                    {point.runs} run{point.runs !== 1 ? "s" : ""}
                  </p>
                </div>
              );
            }}
          />
          <Line
            type="monotone"
            dataKey="min"
            name="Min"
            stroke="#86efac"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
          />
          <Line
            type="monotone"
            dataKey="max"
            name="Max"
            stroke="#fca5a5"
            strokeWidth={1.5}
            strokeDasharray="4 3"
            dot={false}
          />
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
    </div>
  );
}

export default function PerformanceChart({ chartHistory, problemType, onClear }) {
  const filteredHistory = useMemo(
    () => (chartHistory || []).filter((benchmark) => benchmark.problem_type === problemType),
    [chartHistory, problemType]
  );

  if (filteredHistory.length === 0) {
    return (
      <div className="text-center text-gray-400 py-16 space-y-2">
        <p>No benchmark charts yet for {problemType}.</p>
        <p className="text-sm">Each time you click Run benchmark, a new chart is saved here.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
        <span>
          {filteredHistory.length} chart{filteredHistory.length !== 1 ? "s" : ""} for{" "}
          <span className="font-medium text-indigo-600">{problemType}</span>
        </span>
        <button
          onClick={onClear}
          className="ml-auto px-3 py-1 rounded text-sm bg-red-50 text-red-600 hover:bg-red-100"
        >
          Clear chart history
        </button>
      </div>

      {filteredHistory.map((benchmark) => (
        <BenchmarkChartCard key={benchmark.benchmark_id} benchmark={benchmark} />
      ))}

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
