//Componet for submitting job requests

import React, { useState, useRef } from "react";
import { submitJob, fetchJob } from "../api";

const POLL_INTERVAL_MS = 800;

const SAMPLE_TEXT = `To be, or not to be, that is the question:
Whether 'tis nobler in the mind to suffer
The slings and arrows of outrageous fortune,
Or to take arms against a sea of troubles
And by opposing end them. To die—to sleep,
No more; and by a sleep to say we end
The heartache and the thousand natural shocks
That flesh is heir to: 'tis a consummation
Devoutly to be wish'd.`;

export default function JobSubmitter({ problems, onJobDone, maxWorkers = 8 }) {
  const [problemType, setProblemType] = useState(problems[0] ?? "word_frequency");
  const [inputText, setInputText] = useState(SAMPLE_TEXT);
  const [cpuBudgetLabel, setCpuBudgetLabel] = useState("10 CPU");
  const [status, setStatus] = useState(null); // null ,"running" , "done" ,"error"
  const [message, setMessage] = useState("");
  const pollRef = useRef(null);


  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function pollUntilDone(jobId) {
    pollRef.current = setInterval(async () => {
      try {
        const job = await fetchJob(jobId);
        if (job.status === "done") {
          stopPolling();
          setStatus("done");
          setMessage(`Finished in ${job.total_time_ms?.toFixed(1)} ms`);
          onJobDone(job);
        } else if (job.status === "failed") {
          stopPolling();
          setStatus("error");
          setMessage(`Job failed: ${job.error}`);
        }
      } catch (e) {
        stopPolling();
        setStatus("error");
        setMessage(`Polling error: ${e.message}`);
      }
    }, POLL_INTERVAL_MS);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    await handleBenchmark();
  }

  async function handleBenchmark() {
    // Submit jobs for 1..maxWorkers sequentially so metrics accumulate
    stopPolling();
    setStatus("running");

    let input = inputText;
    if (problemType === "prime_count") {
      const n = parseInt(inputText, 10);
      if (isNaN(n) || n < 2) {
        setStatus("error");
        setMessage("For prime_count, enter an integer N ≥ 2");
        return;
      }
      input = { n };
    }

    for (let w = 1; w <= maxWorkers; w++) {
      setMessage(`Benchmarking ${cpuBudgetLabel || "default"} with ${w} worker(s)…`);
      try {
        const job = await submitJob(problemType, input, w, cpuBudgetLabel.trim() || null);
        // Poll synchronously until done
        await new Promise((resolve, reject) => {
          const id = setInterval(async () => {
            try {
              const j = await fetchJob(job.job_id);
              if (j.status === "done" || j.status === "failed") {
                clearInterval(id);
                resolve(j);
              }
            } catch (err) {
              clearInterval(id);
              reject(err);
            }
          }, POLL_INTERVAL_MS);
        });
      } catch (err) {
        setStatus("error");
        setMessage(`Benchmark error at w=${w}: ${err.message}`);
        return;
      }
    }
    setStatus("done");
    setMessage("Benchmark complete — check the Performance Chart tab.");
    onJobDone(null); // trigger metrics refresh without a specific job result
  }

  //--render

  const inputLabel =
    problemType === "prime_count"
      ? "Upper bound N (find all primes up to N)"
      : "Input text (paste or type)";

  const inputPlaceholder =
    problemType === "prime_count" ? "e.g. 500000" : "Paste text here…";

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Problem type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Problem type
        </label>
        <select
          value={problemType}
          onChange={(e) => setProblemType(e.target.value)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {problems.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      {/* Input */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {inputLabel}
        </label>
        <textarea
          rows={8}
          placeholder={inputPlaceholder}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          className="w-full border border-gray-300 rounded-md px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      {/* CPU profile label */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          CPU benchmark label
        </label>
        <input
          type="text"
          value={cpuBudgetLabel}
          onChange={(e) => setCpuBudgetLabel(e.target.value)}
          placeholder="e.g. 10 CPU, 8 CPU, Balanced, Aggressive"
          className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Use a different label for each CPU/resource setting. The graph draws one line per label.
        </p>
      </div>

      {/* Status */}
      {status && (
        <div
          className={`text-sm px-3 py-2 rounded-md ${
            status === "error"
              ? "bg-red-50 text-red-700"
              : status === "running"
              ? "bg-yellow-50 text-yellow-700"
              : "bg-green-50 text-green-700"
          }`}
        >
          {message}
        </div>
      )}

      {/* Buttons */}
      <div>
        <button
          type="submit"
          disabled={status === "running"}
          className="w-full bg-emerald-600 text-white rounded-md py-2 font-medium hover:bg-emerald-700 disabled:opacity-50 transition-colors"
        >
          {status === "running" ? "Running…" : `Run benchmark for ${cpuBudgetLabel || "current CPU profile"} (1 → ${maxWorkers} workers)`}
        </button>
      </div>
    </form>
  );
}
