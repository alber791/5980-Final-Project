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
import socket
import asyncio

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
import httpx

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
WORKER_PORT = int(os.environ.get("WORKER_PORT", "8001"))
ORCHESTRATOR_URL = os.environ.get("ORCHESTRATOR_URL")
COMPUTER_NAME = os.environ.get("COMPUTER_NAME") or socket.gethostname()
WORKER_PUBLIC_URL = os.environ.get("WORKER_PUBLIC_URL") or f"http://{socket.gethostname()}:{WORKER_PORT}"
HEARTBEAT_INTERVAL_SEC = int(os.environ.get("HEARTBEAT_INTERVAL_SEC", "10"))

_heartbeat_task: asyncio.Task | None = None


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


class WorkerRegisterRequest(BaseModel):
    worker_id: str
    worker_url: str
    computer_name: str


async def _register_or_heartbeat_once() -> None:
    if not ORCHESTRATOR_URL:
        return

    payload = WorkerRegisterRequest(
        worker_id=WORKER_ID,
        worker_url=WORKER_PUBLIC_URL,
        computer_name=COMPUTER_NAME,
    ).model_dump()

    async with httpx.AsyncClient(timeout=5.0) as client:
        await client.post(f"{ORCHESTRATOR_URL}/workers/register", json=payload)


async def _heartbeat_loop() -> None:
    if not ORCHESTRATOR_URL:
        logger.info("ORCHESTRATOR_URL not set; worker self-registration disabled")
        return

    while True:
        try:
            await _register_or_heartbeat_once()
            logger.info(
                "[%s] Registered/heartbeat sent to %s as %s on %s",
                WORKER_ID,
                ORCHESTRATOR_URL,
                COMPUTER_NAME,
                WORKER_PUBLIC_URL,
            )
        except Exception as exc:
            logger.warning("[%s] Heartbeat failed: %s", WORKER_ID, exc)

        await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)


@app.on_event("startup")
async def startup_event() -> None:
    global _heartbeat_task
    _heartbeat_task = asyncio.create_task(_heartbeat_loop())


@app.on_event("shutdown")
async def shutdown_event() -> None:
    global _heartbeat_task
    if _heartbeat_task:
        _heartbeat_task.cancel()
        _heartbeat_task = None



@app.get("/health")
def health():
    return {
        "status": "ok",
        "worker_id": WORKER_ID,
        "computer_name": COMPUTER_NAME,
        "worker_url": WORKER_PUBLIC_URL,
        "orchestrator_url": ORCHESTRATOR_URL,
    }


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
