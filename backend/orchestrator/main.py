import asyncio
import os
import time
import uuid
import logging
import json
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
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
    "",
)
STATIC_WORKER_URLS: List[str] = [u.strip() for u in _raw_urls.split(",") if u.strip()]
WORKER_HEARTBEAT_TTL_SEC = int(os.environ.get("WORKER_HEARTBEAT_TTL_SEC", "30"))

# worker_id -> registry entry
registered_workers: Dict[str, Dict[str, Any]] = {}

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
    selected_worker_ids: Optional[List[str]] = Field(
        None,
        description="Optional worker IDs to use as candidate pool. Benchmark loops can send subsets.",
    )


class WorkerRegistrationRequest(BaseModel):
    worker_id: str
    worker_url: str
    computer_name: Optional[str] = None


class WorkerInfo(BaseModel):
    worker_id: str
    worker_url: str
    computer_name: str
    source: str
    last_seen_ago_sec: Optional[float] = None
    is_active: bool


class ProblemInfo(BaseModel):
    name: str
    input_spec: Dict[str, Any]


class JobResponse(BaseModel):
    job_id: str
    status: str
    problem_type: str
    num_workers: int
    result: Optional[Any] = None
    error: Optional[str] = None
    total_time_ms: Optional[float] = None
    worker_times_ms: Optional[List[float]] = None
    chunk_count: Optional[int] = None
    selected_worker_ids: Optional[List[str]] = None
    chunk_profiles: Optional[List[Dict[str, Any]]] = None
    timing_breakdown_ms: Optional[Dict[str, float]] = None


class MetricRecord(BaseModel):
    job_id: str
    problem_type: str
    num_workers: int
    total_time_ms: float
    worker_times_ms: List[float]
    chunk_count: int
    input_size: int            # characters / elements as a proxy


def _parse_selected_worker_ids(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item) for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
        return [item.strip() for item in raw.split(",") if item.strip()]
    return None


async def _build_job_request_from_http(request: Request) -> JobRequest:
    content_type = (request.headers.get("content-type") or "").lower()

    if "multipart/form-data" in content_type:
        form = await request.form()
        problem_type = str(form.get("problem_type", "")).strip()
        if not problem_type:
            raise HTTPException(status_code=400, detail="Missing required field: problem_type")

        raw_num_workers = form.get("num_workers", "1")
        try:
            num_workers = int(raw_num_workers)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="num_workers must be an integer")

        selected_worker_ids = _parse_selected_worker_ids(form.get("selected_worker_ids"))

        input_file = form.get("input_file")
        if input_file is not None and hasattr(input_file, "read"):
            raw_bytes = await input_file.read()
            raw_input_data: Any = raw_bytes.decode("utf-8", errors="ignore")
        else:
            raw_input_data = form.get("input_data")

    else:
        body = await request.json()
        if not isinstance(body, dict):
            raise HTTPException(status_code=400, detail="Request body must be a JSON object")

        problem_type = str(body.get("problem_type", "")).strip()
        if not problem_type:
            raise HTTPException(status_code=400, detail="Missing required field: problem_type")

        raw_num_workers = body.get("num_workers", 1)
        try:
            num_workers = int(raw_num_workers)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="num_workers must be an integer")

        selected_worker_ids = _parse_selected_worker_ids(body.get("selected_worker_ids"))
        raw_input_data = body.get("input_data")

    problem = PROBLEM_REGISTRY.get(problem_type)
    if problem is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown problem type '{problem_type}'. Available: {list(PROBLEM_REGISTRY.keys())}",
        )

    try:
        parsed_input_data = problem.parse_input(raw_input_data)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid input for {problem_type}: {exc}")

    try:
        return JobRequest(
            problem_type=problem_type,
            input_data=parsed_input_data,
            num_workers=num_workers,
            selected_worker_ids=selected_worker_ids,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid job request: {exc}")


def _upsert_worker_registration(worker_id: str, worker_url: str, computer_name: Optional[str]) -> None:
    now = time.time()
    registered_workers[worker_id] = {
        "worker_id": worker_id,
        "worker_url": worker_url,
        "computer_name": computer_name or "unknown-computer",
        "source": "self-registered",
        "last_seen_epoch": now,
    }


def _get_worker_pool() -> List[Dict[str, Any]]:
    now = time.time()
    pool: List[Dict[str, Any]] = []

    for entry in registered_workers.values():
        last_seen_ago = now - entry["last_seen_epoch"]
        if last_seen_ago <= WORKER_HEARTBEAT_TTL_SEC:
            pool.append(
                {
                    "worker_id": entry["worker_id"],
                    "worker_url": entry["worker_url"],
                    "computer_name": entry["computer_name"],
                    "source": entry["source"],
                    "last_seen_ago_sec": round(last_seen_ago, 1),
                    "is_active": True,
                }
            )

    # Include static workers as fallback if they are not already represented by URL
    known_urls = {w["worker_url"] for w in pool}
    for idx, url in enumerate(STATIC_WORKER_URLS, start=1):
        if url in known_urls:
            continue
        pool.append(
            {
                "worker_id": f"static-{idx}",
                "worker_url": url,
                "computer_name": "static-config",
                "source": "static",
                "last_seen_ago_sec": None,
                "is_active": True,
            }
        )

    # Deterministic ordering for UI and benchmark subsets
    pool.sort(key=lambda w: (w["computer_name"], w["worker_id"]))
    return pool


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

        worker_pool = _get_worker_pool()
        if req.selected_worker_ids:
            allowed_ids = set(req.selected_worker_ids)
            worker_pool = [w for w in worker_pool if w["worker_id"] in allowed_ids]

        if not worker_pool:
            raise RuntimeError("No active workers available for this job request")

        if req.num_workers > len(worker_pool):
            raise RuntimeError(
                f"Requested {req.num_workers} workers but only {len(worker_pool)} active worker(s) are available"
            )

        num_workers = req.num_workers

        # ----split 
        t_split_start = time.perf_counter()
        chunks: List[Any] = problem.split(req.input_data, num_workers)
        num_chunks = len(chunks)
        split_time_ms = (time.perf_counter() - t_split_start) * 1000
        logger.info("[%s] Split into %d chunks for %d workers", job_id, num_chunks, num_workers)

        selected_workers = worker_pool[:num_workers]

        # --- dispatch
        t_dispatch_start = time.perf_counter()
        async with httpx.AsyncClient() as client:
            tasks = [
                dispatch_chunk(
                    client,
                    selected_workers[i % len(selected_workers)]["worker_url"],
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
            "total_time_ms": round(total_time_ms, 2),
            "worker_times_ms": [round(t, 2) for t in worker_times_ms],
            "chunk_count": num_chunks,
            "input_size": input_size,
        }
        metrics_log.append(metric)

        job.update(
            status=JobStatus.DONE,
            result=final_result,
            total_time_ms=round(total_time_ms, 2),
            worker_times_ms=metric["worker_times_ms"],
            chunk_count=num_chunks,
            selected_worker_ids=[w["worker_id"] for w in selected_workers],
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
    pool = _get_worker_pool()
    return {
        "status": "ok",
        "worker_pool": [w["worker_url"] for w in pool],
        "active_workers": len(pool),
        "available_problems": list(PROBLEM_REGISTRY.keys()),
    }


@app.post("/workers/register")
def register_worker(req: WorkerRegistrationRequest):
    _upsert_worker_registration(req.worker_id, req.worker_url, req.computer_name)
    return {"registered": True, "worker_id": req.worker_id}


@app.post("/workers/heartbeat")
def worker_heartbeat(req: WorkerRegistrationRequest):
    _upsert_worker_registration(req.worker_id, req.worker_url, req.computer_name)
    return {"ok": True}


@app.get("/workers", response_model=List[WorkerInfo])
def list_workers():
    return [WorkerInfo(**worker) for worker in _get_worker_pool()]

#get problems
@app.get("/problems")
def list_problems():
    """Return all registered problems with input metadata for dynamic UI rendering."""
    return {
        "problems": [
            ProblemInfo(name=problem.name, input_spec=problem.input_spec).model_dump()
            for problem in PROBLEM_REGISTRY.values()
        ]
    }

#Submit a new job
@app.post("/jobs", response_model=JobResponse, status_code=202)
async def submit_job(background_tasks: BackgroundTasks, request: Request):
    req = await _build_job_request_from_http(request)
    if req.problem_type not in PROBLEM_REGISTRY:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown problem type '{req.problem_type}'. "
                   f"Available: {list(PROBLEM_REGISTRY.keys())}",
        )
    worker_pool = _get_worker_pool()
    if not worker_pool:
        raise HTTPException(
            status_code=400,
            detail="No active workers available. Start workers and ensure registration/heartbeat is running.",
        )

    if req.selected_worker_ids:
        available_worker_ids = {worker["worker_id"] for worker in worker_pool}
        missing_ids = [worker_id for worker_id in req.selected_worker_ids if worker_id not in available_worker_ids]
        if missing_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown/inactive worker IDs: {missing_ids}",
            )
        candidate_count = len(req.selected_worker_ids)
    else:
        candidate_count = len(worker_pool)

    if req.num_workers > candidate_count:
        raise HTTPException(
            status_code=400,
            detail=f"Requested {req.num_workers} workers but only {candidate_count} selected/active worker(s) are available.",
        )

    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "problem_type": req.problem_type,
        "num_workers": req.num_workers,
        "selected_worker_ids": req.selected_worker_ids,
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
