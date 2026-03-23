//This is how frontend componets will communicate with python

import axios from "axios";

const BASE = import.meta.env.VITE_API_URL ?? "/api";

const client = axios.create({ baseURL: BASE });

// Get problems available
export async function fetchProblems() {
  const { data } = await client.get("/problems");
  return data.problems; // string[]
}

//submit jobs
export async function submitJob(problemType, inputData, numWorkers, cpuBudgetLabel) {
  const { data } = await client.post("/jobs", {
    problem_type: problemType,
    input_data: inputData,
    num_workers: numWorkers,
    cpu_budget_label: cpuBudgetLabel,
  });
  return data;
}

//fetch single job
export async function fetchJob(jobId) {
  const { data } = await client.get(`/jobs/${jobId}`);
  return data;
}

//get perfomances
export async function fetchMetrics(problemType) {
  const params = problemType ? { problem_type: problemType } : {};
  const { data } = await client.get("/metrics", { params });
  return data;
}

//clear metrics for new benchmarking
export async function clearMetrics() {
  await client.delete("/metrics");
}
