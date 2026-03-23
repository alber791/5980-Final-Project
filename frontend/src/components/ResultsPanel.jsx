/**
 * ResultsPanel
 */

import React, { useState } from "react";

export default function ResultsPanel({ job }) {
  const [showFull, setShowFull] = useState(false);

  if (!job) {
    return (
      <div className="text-center text-gray-400 py-16">
        No results yet — submit a job using the form on the left.
      </div>
    );
  }

  //-- Word frequency
  if (job.problem_type === "word_frequency") {
    const entries = Object.entries(job.result ?? {});
    const visible = showFull ? entries : entries.slice(0, 20);

    return (
      <div className="space-y-4">
        <Stats job={job} />
        <h3 className="font-semibold text-gray-700">Top word frequencies</h3>
        <div className="overflow-auto max-h-96 border border-gray-200 rounded-md">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-100 sticky top-0">
              <tr>
                <th className="text-left px-3 py-2">Word</th>
                <th className="text-right px-3 py-2">Count</th>
              </tr>
            </thead>
            <tbody>
              {visible.map(([word, count], i) => (
                <tr key={word} className={i % 2 === 0 ? "bg-white" : "bg-gray-50"}>
                  <td className="px-3 py-1 font-mono">{word}</td>
                  <td className="px-3 py-1 text-right tabular-nums">{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {entries.length > 20 && (
          <button
            onClick={() => setShowFull((f) => !f)}
            className="text-indigo-600 text-sm hover:underline"
          >
            {showFull ? "Show less" : `Show all ${entries.length} words`}
          </button>
        )}
      </div>
    );
  }

  //--prime count
  if (job.problem_type === "prime_count") {
    const { total_primes, primes } = job.result ?? {};
    const visible = showFull ? primes : primes?.slice(0, 100);

    return (
      <div className="space-y-4">
        <Stats job={job} />
        <p className="text-lg font-semibold text-gray-700">
          Total primes found: <span className="text-indigo-600">{total_primes}</span>
        </p>
        <div className="font-mono text-xs text-gray-600 flex flex-wrap gap-1 max-h-64 overflow-auto">
          {visible?.map((p) => (
            <span key={p} className="bg-gray-100 rounded px-1">
              {p}
            </span>
          ))}
        </div>
        {primes?.length > 100 && (
          <button
            onClick={() => setShowFull((f) => !f)}
            className="text-indigo-600 text-sm hover:underline"
          >
            {showFull ? "Show less" : `Show all ${primes.length} primes`}
          </button>
        )}
      </div>
    );
  }

  // fallback
  return (
    <div className="space-y-4">
      <Stats job={job} />
      <pre className="bg-gray-50 border border-gray-200 rounded-md p-4 text-xs overflow-auto max-h-96">
        {JSON.stringify(job.result, null, 2)}
      </pre>
    </div>
  );
}

// time stats
function Stats({ job }) {
  const avgWorker =
    job.worker_times_ms?.length
      ? (
          job.worker_times_ms.reduce((a, b) => a + b, 0) /
          job.worker_times_ms.length
        ).toFixed(1)
      : "—";

  const maxWorker = job.worker_times_ms?.length
    ? Math.max(...job.worker_times_ms).toFixed(1)
    : "—";

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[
        { label: "Workers used", value: job.num_workers },
        { label: "Chunks", value: job.chunk_count ?? "—" },
        { label: "Total time", value: `${job.total_time_ms?.toFixed(1)} ms` },
        { label: "Slowest worker", value: `${maxWorker} ms` },
      ].map(({ label, value }) => (
        <div key={label} className="bg-indigo-50 rounded-md p-3 text-center">
          <div className="text-xl font-bold text-indigo-700">{value}</div>
          <div className="text-xs text-gray-500 mt-1">{label}</div>
        </div>
      ))}
    </div>
  );
}
