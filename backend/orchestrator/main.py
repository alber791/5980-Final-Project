import asyncio
import os
import time
import uuid
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from shared.problems import PROBLEM_REGISTRY

# ------------------------------------------------------------------ #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("orchestrator")

app = FastAPI(title="Orchestrator Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------ #
# Worker pool 

_raw_urls = os.environ.get(
    "WORKER_URLS",
    "http://worker1:8001,http://worker2:8001,http://worker3:8001,"
    "http://worker4:8001,http://worker5:8001,http://worker6:8001,"
    "http://worker7:8001,http://worker8:8001",
)
ALL_WORKER_URLS: List[str] = [u.strip() for u in _raw_urls.split(",") if u.strip()]
MAX_WORKERS: int = len(ALL_WORKER_URLS)

# ------------------------------------------------------------------ #
# In-memory job store, todo: replace with more presistent solution

class JobStatus:
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


jobs: Dict[str, Dict[str, Any]] = {}       # job_id -> job dict
metrics_log: List[Dict[str, Any]] = []     # append-only performance records


# ------------------------------------------------------------------ #
# models

class JobRequest(BaseModel):
    problem_type: str = Field(..., description="Registered problem name, e.g. 'word_frequency'")
    input_data: Any = Field(..., description="Problem-specific input (string, dict, …)")
    num_workers: int = Field(1, ge=1, description="Number of worker containers to use")
    cpu_budget_label: Optional[str] = Field(None, description="User-supplied label for the CPU/resource profile, e.g. '10 CPU'")


class JobResponse(BaseModel):
    job_id: str
    status: str
    problem_type: str
    num_workers: int
    cpu_budget_label: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    total_time_ms: Optional[float] = None
    worker_times_ms: Optional[List[float]] = None
    chunk_count: Optional[int] = None
    chunk_profiles: Optional[List[Dict[str, Any]]] = None
    timing_breakdown_ms: Optional[Dict[str, float]] = None


class MetricRecord(BaseModel):
    job_id: str
    problem_type: str
    num_workers: int
    cpu_budget_label: Optional[str] = None
    total_time_ms: float
    worker_times_ms: List[float]
    chunk_count: int
    input_size: int            # characters / elements as a proxy


# ------------------------------------------------------------------ #
# problem solve lifecycle

# Dispatch one chunk to one worker and await the response
async def dispatch_chunk(
    client: httpx.AsyncClient,
    worker_url: str,
    problem_type: str,
    chunk: Any,
    chunk_index: int,
) -> Dict[str, Any]:
    dispatch_started_at = time.perf_counter()
    payload = {
        "problem_type": problem_type,
        "chunk": chunk,
        "chunk_index": chunk_index,
    }
    response = await client.post(
        f"{worker_url}/solve",
        json=payload,
        timeout=300.0,
    )
    response.raise_for_status()
    elapsed_ms = (time.perf_counter() - dispatch_started_at) * 1000
    payload = response.json()
    payload["round_trip_time_ms"] = elapsed_ms
    payload["worker_url"] = worker_url
    return payload

#Full job lifecycle
# split -> dispatch (parallel) -> aggregate -> persist metrics
async def run_job(job_id: str, req: JobRequest) -> None:
    job = jobs[job_id]
    job["status"] = JobStatus.RUNNING

    try:
        problem = PROBLEM_REGISTRY[req.problem_type]
        num_workers = min(req.num_workers, MAX_WORKERS)

        # ----split 
        t_split_start = time.perf_counter()
        chunks: List[Any] = problem.split(req.input_data, num_workers)
        num_chunks = len(chunks)
        split_time_ms = (time.perf_counter() - t_split_start) * 1000
        logger.info("[%s] Split into %d chunks for %d workers", job_id, num_chunks, num_workers)

        selected_workers = ALL_WORKER_URLS[:num_workers]

        # --- dispatch
        t_dispatch_start = time.perf_counter()
        async with httpx.AsyncClient() as client:
            tasks = [
                dispatch_chunk(
                    client,
                    selected_workers[i % len(selected_workers)],
                    req.problem_type,
                    chunk,
                    i,
                )
                for i, chunk in enumerate(chunks)
            ]
            responses = await asyncio.gather(*tasks)

        dispatch_total_ms = (time.perf_counter() - t_dispatch_start) * 1000
        worker_times_ms = [r["processing_time_ms"] for r in responses]

        # Sort responses by chunk_index to order for aggregate
        responses.sort(key=lambda r: r["chunk_index"])
        partial_results = [r["result"] for r in responses]

        chunk_profiles: List[Dict[str, Any]] = []
        for response in responses:
            worker_compute_ms = float(response["processing_time_ms"])
            round_trip_ms = float(response.get("round_trip_time_ms", worker_compute_ms))
            chunk_profiles.append(
                {
                    "chunk_index": response["chunk_index"],
                    "worker_id": response.get("worker_id"),
                    "worker_url": response.get("worker_url"),
                    "worker_compute_ms": round(worker_compute_ms, 2),
                    "round_trip_ms": round(round_trip_ms, 2),
                    "overhead_ms": round(max(0.0, round_trip_ms - worker_compute_ms), 2),
                }
            )

        # --- Aggregate
        t_aggregate_start = time.perf_counter()
        final_result = problem.aggregate(partial_results)
        aggregate_time_ms = (time.perf_counter() - t_aggregate_start) * 1000

        total_time_ms = split_time_ms + dispatch_total_ms + aggregate_time_ms
        timing_breakdown_ms = {
            "split_time_ms": round(split_time_ms, 2),
            "dispatch_phase_ms": round(dispatch_total_ms, 2),
            "aggregate_time_ms": round(aggregate_time_ms, 2),
            "total_time_ms": round(total_time_ms, 2),
        }

        # --- Persist the data
        input_size = len(req.input_data) if isinstance(req.input_data, str) else len(str(req.input_data))

        metric = {
            "job_id": job_id,
            "problem_type": req.problem_type,
            "num_workers": num_workers,
            "cpu_budget_label": req.cpu_budget_label,
            "total_time_ms": round(total_time_ms, 2),
            "worker_times_ms": [round(t, 2) for t in worker_times_ms],
            "chunk_count": num_chunks,
            "input_size": input_size,
        }
        metrics_log.append(metric)

        job.update(
            status=JobStatus.DONE,
            result=final_result,
            cpu_budget_label=req.cpu_budget_label,
            total_time_ms=round(total_time_ms, 2),
            worker_times_ms=metric["worker_times_ms"],
            chunk_count=num_chunks,
            chunk_profiles=chunk_profiles,
            timing_breakdown_ms=timing_breakdown_ms,
        )

        logger.info("[%s] Completed in %.1f ms", job_id, total_time_ms)

    except Exception as exc:
        logger.exception("[%s] Failed: %s", job_id, exc)
        job["status"] = JobStatus.FAILED
        job["error"] = str(exc)


# ------------------------------------------------------------------ #
# Routes
# ------------------------------------------------------------------ #


@app.get("/health")
def health():
    return {
        "status": "ok",
        "worker_pool": ALL_WORKER_URLS,
        "available_problems": list(PROBLEM_REGISTRY.keys()),
    }

#get problems
@app.get("/problems")
def list_problems():
    """Return the names of all registered problems."""
    return {"problems": list(PROBLEM_REGISTRY.keys())}

#Submit a new job
@app.post("/jobs", response_model=JobResponse, status_code=202)
async def submit_job(req: JobRequest, background_tasks: BackgroundTasks):
    if req.problem_type not in PROBLEM_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown problem type '{req.problem_type}'. "
                   f"Available: {list(PROBLEM_REGISTRY.keys())}",
        )
    if req.num_workers > MAX_WORKERS:
        raise HTTPException(
            status_code=400,
            detail=f"Requested {req.num_workers} workers but only {MAX_WORKERS} are available.",
        )

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "problem_type": req.problem_type,
        "num_workers": req.num_workers,
        "cpu_budget_label": req.cpu_budget_label,
        "result": None,
        "error": None,
        "total_time_ms": None,
        "worker_times_ms": None,
        "chunk_count": None,
        "chunk_profiles": None,
        "timing_breakdown_ms": None,
    }

    background_tasks.add_task(run_job, job_id, req)

    return JobResponse(**jobs[job_id])


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**jobs[job_id])


@app.get("/jobs/{job_id}/profile")
def get_job_profile(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "problem_type": job["problem_type"],
        "num_workers": job["num_workers"],
        "cpu_budget_label": job.get("cpu_budget_label"),
        "chunk_count": job.get("chunk_count"),
        "timing_breakdown_ms": job.get("timing_breakdown_ms"),
        "chunk_profiles": job.get("chunk_profiles"),
    }


#return all metrics or filter by problem type
@app.get("/metrics", response_model=List[MetricRecord])
def get_metrics(problem_type: Optional[str] = None):
    records = metrics_log
    if problem_type:
        records = [m for m in records if m["problem_type"] == problem_type]
    return records

#Reset metrics
@app.delete("/metrics")
def clear_metrics():
    metrics_log.clear()
    return {"cleared": True}
