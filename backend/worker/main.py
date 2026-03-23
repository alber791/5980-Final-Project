"""
Worker service.

POST /solve
  Body: { "problem_type": str, "chunk": any, "chunk_index": int }
  Returns: { "chunk_index": int, "result": any }

GET /health
  Returns: { "status": "ok", "worker_id": str }
"""

import os
import time
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any

from shared.problems import PROBLEM_REGISTRY

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

app = FastAPI(title="Worker Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WORKER_ID = os.environ.get("WORKER_ID", "worker-unknown")


# ------------------------------------------------------------------ #
# models


class SolveRequest(BaseModel):
    problem_type: str
    chunk: Any
    chunk_index: int


class SolveResponse(BaseModel):
    chunk_index: int
    result: Any
    worker_id: str
    processing_time_ms: float



@app.get("/health")
def health():
    return {"status": "ok", "worker_id": WORKER_ID}


@app.post("/solve", response_model=SolveResponse)
def solve(req: SolveRequest):
    problem = PROBLEM_REGISTRY.get(req.problem_type)
    if problem is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown problem type '{req.problem_type}'. "
                   f"Available: {list(PROBLEM_REGISTRY.keys())}",
        )

    logger.info(
        "[%s] Solving chunk %d for problem '%s'",
        WORKER_ID,
        req.chunk_index,
        req.problem_type,
    )

    t0 = time.perf_counter()
    result = problem.solve(req.chunk)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    logger.info(
        "[%s] Chunk %d done in %.1f ms",
        WORKER_ID,
        req.chunk_index,
        elapsed_ms,
    )

    return SolveResponse(
        chunk_index=req.chunk_index,
        result=result,
        worker_id=WORKER_ID,
        processing_time_ms=elapsed_ms,
    )
