/**
layout 
 */

import React, { useCallback, useEffect, useState } from "react";
import JobSubmitter from "./components/JobSubmitter";
import ResultsPanel from "./components/ResultsPanel";
import PerformanceChart from "./components/PerformanceChart";
import { clearMetrics, fetchMetrics, fetchProblems } from "./api";

const MAX_WORKERS = 8;

export default function App() {
  const [problems, setProblems] = useState([]);
  const [activeTab, setActiveTab] = useState("results");
  const [lastJob, setLastJob] = useState(null);
  const [metrics, setMetrics] = useState([]);
  const [selectedProblem, setSelectedProblem] = useState("word_frequency");

  //---init
  useEffect(() => {
    fetchProblems()
      .then((ps) => {
        setProblems(ps);
        if (ps.length > 0) setSelectedProblem(ps[0]);
      })
      .catch(() => {
        // Fallback when API is not reachable during development
        setProblems(["word_frequency", "prime_count"]);
      });
  }, []);

  const refreshMetrics = useCallback(async () => {
    try {
      const data = await fetchMetrics(selectedProblem);
      setMetrics(data);
    } catch {
      /* ignore */
    }
  }, [selectedProblem]);

  useEffect(() => {
    refreshMetrics();
  }, [refreshMetrics]);

  //--callback
  function handleJobDone(job) {
    if (job) {
      setLastJob(job);
      setActiveTab("results");
    }
    refreshMetrics();
  }

  function handleProblemChange(p) {
    setSelectedProblem(p);
  }

  async function handleClearMetrics() {
    await clearMetrics();
    setMetrics([]);
  }

  //--rendering
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-indigo-700 text-white px-6 py-4 shadow">
        <h1 className="text-2xl font-bold tracking-tight">
          Distributed Compute Benchmark
        </h1>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* submission */}
        <section className="bg-white rounded-xl shadow p-6 space-y-2">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">
            Configure &amp; Run
          </h2>

          {/* problems */}
          {problems.length > 1 && (
            <div className="mb-2">
              <label className="text-xs text-gray-500 uppercase tracking-wide">
                Active problem
              </label>
              <div className="flex gap-2 mt-1">
                {problems.map((p) => (
                  <button
                    key={p}
                    onClick={() => handleProblemChange(p)}
                    className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                      selectedProblem === p
                        ? "bg-indigo-600 text-white"
                        : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                    }`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          <JobSubmitter
            problems={problems}
            onJobDone={handleJobDone}
            maxWorkers={MAX_WORKERS}
          />
        </section>

        {/* results and charts */}
        <section className="bg-white rounded-xl shadow p-6">
          {/* Tabs */}
          <div className="flex border-b border-gray-200 mb-6">
            {["results", "chart"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium capitalize border-b-2 transition-colors ${
                  activeTab === tab
                    ? "border-indigo-600 text-indigo-600"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {tab === "chart" ? "Performance Chart" : "Results"}
              </button>
            ))}
          </div>

          {activeTab === "results" ? (
            <ResultsPanel job={lastJob} />
          ) : (
            <PerformanceChart
              metrics={metrics}
              problemType={selectedProblem}
              onClear={handleClearMetrics}
            />
          )}
        </section>
      </main>
    </div>
  );
}
