//Componet for submitting job requests

import React, { useEffect, useMemo, useState, useRef } from "react";
import { submitJob, fetchJob, fetchWorkers } from "../api";

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

export default function JobSubmitter({ problems, onJobDone, onProblemTypeChange }) {
  const [problemType, setProblemType] = useState(problems[0]?.name ?? "word_frequency");
  const [inputText, setInputText] = useState(SAMPLE_TEXT);
  const [inputNumber, setInputNumber] = useState("500000");
  const [inputFile, setInputFile] = useState(null);
  const [workers, setWorkers] = useState([]);
  const [selectedWorkerIds, setSelectedWorkerIds] = useState([]);
  const [runsPerWorker, setRunsPerWorker] = useState(3);
  const [status, setStatus] = useState(null); // null ,"running" , "done" ,"error"
  const [message, setMessage] = useState("");
  const pollRef = useRef(null);

  const workerGroups = useMemo(() => {
    const groups = {};
    for (const worker of workers) {
      const key = worker.computer_name || "unknown-computer";
      if (!groups[key]) groups[key] = [];
      groups[key].push(worker);
    }

    return Object.entries(groups)
      .map(([computerName, groupWorkers]) => ({
        computerName,
        workers: groupWorkers.sort((a, b) => a.worker_id.localeCompare(b.worker_id)),
      }))
      .sort((a, b) => a.computerName.localeCompare(b.computerName));
  }, [workers]);

  const selectedWorkers = useMemo(() => {
    const selectedSet = new Set(selectedWorkerIds);
    const ordered = workers
      .filter((worker) => selectedSet.has(worker.worker_id))
      .sort((a, b) => {
        if (a.computer_name !== b.computer_name) {
          return (a.computer_name || "").localeCompare(b.computer_name || "");
        }
        return a.worker_id.localeCompare(b.worker_id);
      });
    return ordered;
  }, [workers, selectedWorkerIds]);

  const selectedProblem = useMemo(
    () => problems.find((problem) => problem.name === problemType) ?? null,
    [problems, problemType]
  );

  const inputSpec = selectedProblem?.input_spec ?? {
    type: "text",
    label: "Input",
    placeholder: "Enter input",
  };

  useEffect(() => {
    if (problems.length === 0) return;
    const exists = problems.some((problem) => problem.name === problemType);
    if (!exists) {
      setProblemType(problems[0].name);
    }
  }, [problems, problemType]);

  useEffect(() => {
    if (onProblemTypeChange) {
      onProblemTypeChange(problemType);
    }
  }, [problemType, onProblemTypeChange]);

  async function refreshWorkers() {
    try {
      const data = await fetchWorkers();
      setWorkers(data);

      const availableIds = new Set(data.map((worker) => worker.worker_id));
      setSelectedWorkerIds((previous) => {
        const stillAvailable = previous.filter((workerId) => availableIds.has(workerId));
        if (stillAvailable.length > 0) return stillAvailable;
        return data.map((worker) => worker.worker_id);
      });
    } catch (error) {
      setMessage(`Failed to load workers: ${error.message}`);
      setStatus("error");
    }
  }

  useEffect(() => {
    refreshWorkers();
  }, []);


  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  async function handleSubmit(e) {
    e.preventDefault();
    await handleBenchmark();
  }

  async function handleBenchmark() {
    // Submit jobs for 1..n selected workers sequentially so metrics accumulate
    stopPolling();
    setStatus("running");

    if (selectedWorkers.length === 0) {
      setStatus("error");
      setMessage("Select at least one worker before benchmarking.");
      return;
    }

    let input;
    if (inputSpec.type === "number") {
      const value = Number(inputNumber);
      const min = Number(inputSpec.min ?? Number.NEGATIVE_INFINITY);
      if (!Number.isFinite(value) || value < min) {
        setStatus("error");
        setMessage(`${inputSpec.label ?? "Number input"} must be >= ${inputSpec.min ?? 0}`);
        return;
      }
      input = value;
    } else if (inputSpec.type === "file") {
      if (!inputFile) {
        setStatus("error");
        setMessage(`Please upload a file for ${problemType}.`);
        return;
      }
      input = inputFile;
    } else {
      input = inputText;
    }

    const orderedWorkerIds = selectedWorkers.map((worker) => worker.worker_id);
    const totalJobs = orderedWorkerIds.length * runsPerWorker;
    let jobsDone = 0;

    const benchmarkJobs = [];

    for (let w = 1; w <= orderedWorkerIds.length; w++) {
      const workerSubset = orderedWorkerIds.slice(0, w);
      for (let run = 1; run <= runsPerWorker; run++) {
        jobsDone++;
        setMessage(
          `Worker count ${w}/${orderedWorkerIds.length} — run ${run}/${runsPerWorker} (job ${jobsDone}/${totalJobs})…`
        );
        try {
          const job = await submitJob(problemType, input, w, workerSubset);
          const completedJob = await new Promise((resolve, reject) => {
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

          if (completedJob.status === "failed") {
            throw new Error(completedJob.error || "Job failed");
          }

          benchmarkJobs.push({
            job_id: completedJob.job_id,
            num_workers: completedJob.num_workers,
            total_time_ms: completedJob.total_time_ms,
            status: completedJob.status,
            run_index: run,
          });
        } catch (err) {
          setStatus("error");
          setMessage(`Benchmark error at w=${w} run=${run}: ${err.message}`);
          return;
        }
      }
    }
    setStatus("done");
    setMessage(
      `Benchmark complete — tested 1..${orderedWorkerIds.length} workers × ${runsPerWorker} run(s) each.`
    );
    onJobDone({
      benchmark_id: `benchmark-${Date.now()}`,
      problem_type: problemType,
      created_at: new Date().toISOString(),
      max_workers: orderedWorkerIds.length,
      runs_per_worker: runsPerWorker,
      metrics: benchmarkJobs,
    });
  }

  //--render

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Problem type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Problem type
        </label>
        <select
          value={problemType}
          onChange={(e) => {
            setProblemType(e.target.value);
          }}
          className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
        >
          {problems.map((p) => (
            <option key={p.name} value={p.name}>
              {p.name}
            </option>
          ))}
        </select>
      </div>

      {/* Input */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {inputSpec.label ?? "Input"}
        </label>
        {inputSpec.type === "number" ? (
          <input
            type="number"
            min={inputSpec.min ?? 0}
            value={inputNumber}
            onChange={(e) => setInputNumber(e.target.value)}
            placeholder={inputSpec.placeholder ?? "Enter number"}
            className="w-full border border-gray-300 rounded-md px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        ) : inputSpec.type === "file" ? (
          <div className="space-y-2">
            <input
              type="file"
              accept={(inputSpec.accept ?? []).join(",")}
              onChange={(e) => setInputFile(e.target.files?.[0] ?? null)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <p className="text-xs text-gray-500">
              {inputFile ? `Selected: ${inputFile.name}` : inputSpec.placeholder ?? "Choose a file"}
            </p>
          </div>
        ) : (
          <textarea
            rows={8}
            placeholder={inputSpec.placeholder ?? "Paste text here…"}
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-2 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        )}
        {inputSpec.description && (
          <p className="text-xs text-gray-500 mt-1">{inputSpec.description}</p>
        )}
      </div>

      {/* Workers */}
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <label className="block text-sm font-medium text-gray-700">
            Available workers ({workers.length})
          </label>
          <button
            type="button"
            onClick={refreshWorkers}
            className="ml-auto px-2 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
          >
            Refresh workers
          </button>
        </div>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setSelectedWorkerIds(workers.map((worker) => worker.worker_id))}
            className="px-2 py-1 text-xs rounded bg-indigo-50 text-indigo-600 hover:bg-indigo-100"
          >
            Select all
          </button>
          <button
            type="button"
            onClick={() => setSelectedWorkerIds([])}
            className="px-2 py-1 text-xs rounded bg-gray-100 text-gray-600 hover:bg-gray-200"
          >
            Unselect all
          </button>
        </div>

        <div className="border border-gray-200 rounded-md p-3 max-h-56 overflow-auto space-y-3">
          {workerGroups.length === 0 ? (
            <p className="text-sm text-gray-400">No workers discovered yet.</p>
          ) : (
            workerGroups.map((group) => (
              <div key={group.computerName} className="space-y-1">
                <div className="text-xs font-semibold uppercase text-gray-500">
                  {group.computerName}
                </div>
                {group.workers.map((worker) => {
                  const checked = selectedWorkerIds.includes(worker.worker_id);
                  return (
                    <label key={worker.worker_id} className="flex items-center gap-2 text-sm text-gray-700">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => {
                          setSelectedWorkerIds((previous) => {
                            if (previous.includes(worker.worker_id)) {
                              return previous.filter((id) => id !== worker.worker_id);
                            }
                            return [...previous, worker.worker_id];
                          });
                        }}
                      />
                      <span className="font-mono">{worker.worker_id}</span>
                      <span className="text-xs text-gray-400">{worker.worker_url}</span>
                    </label>
                  );
                })}
              </div>
            ))
          )}
        </div>

        <p className="text-xs text-gray-500">
          Benchmark range is 1..n where n = selected workers ({selectedWorkers.length}).
        </p>
      </div>

      {/* Runs per worker */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Runs per worker count
        </label>
        <input
          type="number"
          min={1}
          max={20}
          value={runsPerWorker}
          onChange={(e) => setRunsPerWorker(Math.max(1, Math.min(20, Number(e.target.value))))}
          className="w-24 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
        <p className="mt-1 text-xs text-gray-500">
          Each worker count (1→{selectedWorkers.length}) will run this many times; the chart shows the average.
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
          {status === "running"
            ? "Running…"
            : `Run benchmark (1 → ${Math.max(1, selectedWorkers.length)} workers × ${runsPerWorker} run${runsPerWorker !== 1 ? "s" : ""})`}
        </button>
      </div>
    </form>
  );
}
