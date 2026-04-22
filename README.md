# Distributed Compute Benchmark

A **FastAPI + React + Docker** project that demonstrates how distributing computation across multiple containers affects performance.

---

## About Problems

Every problem implements three methods in `backend/shared/problems/`:

```python
class BaseProblem(ABC):
    def split(self, input_data, num_chunks) -> List[chunk]
    # Runs in ORCHESTRATOR — divides work

    def solve(self, chunk) -> partial_result
    # Runs in WORKER — processes one piece

    def aggregate(self, partial_results) -> final_result
    # Runs in ORCHESTRATOR — merges all pieces
```

### Problems

| Problem | Input | What it does |
|---|---|---|
| `word_frequency` | Plain text string | Counts word occurrences across chunks |
| `prime_count` | `{"n": 500000}` | Finds all primes up to N using segmented |


## Quick Start

### Prerequisites
- docker (currently running) 
- nodejs
- python

### Run everything

| Service | URL |
|---|---|
| Frontend (React) | http://localhost:3000 |
| Orchestrator API | http://localhost:8000 |

**Orchestrator + local workers (single machine)**

This will run the orchestrator, frontend, and 1-8 workers (depending on the number you pass).  You can run the benchmarks with the local workers or optionally also run with additional workers from another machine (see workers-only machine setup).

Windows: `./scripts/windows/start-main.ps1 -WorkerCount 5`

Linux: `./scripts/linux/start-main.sh 5`

**Workers-only machine setup**

On a seperate machine connected in the same LAN of the running orchestrator, you can run these scripts to add additional (1-8) workers that the orchestrator can use.  In order to run this, first you MUST obtain the ip address of the orchestrator.  This allows the workers to register with the orchestrator

This requires that the orchestator machine allows inbound TCP on port 8000.

Windows (Orchestrator): `New-NetFirewallRule -DisplayName "DistributedCompute-Orchestrator-8000" -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8000`

Windows (Worker): `./scripts/windows/start-workers-node.ps1 -OrchestratorIp <orchestrator-ip> -WorkerCount 4 -ComputerName Remote-Machine-1`

Linux (Worker): `./scripts/linux/start-workers-node.sh <orchestrator-ip> 4 8000 Remote-Machine-1`

stop:
  - Windows: `./scripts/windows/stop-workers-node.ps1`
  - Linux: `./scripts/linux/stop-workers-node.sh`

---

## Running a Benchmark

1. Open **http://localhost:3000**
2. Select a problem type and paste/type input
3. Select the number of registered workers you want to run the benchmark on
4. Click **"Full benchmark"**
5. Switch to the **Performance Chart** tab to view timing graphs

---

## API Reference

### `POST /jobs`

Submit a new job (returns immediately, processes in background).

```json
{
  "problem_type": "word_frequency",
  "input_data": "the quick brown fox jumps over the lazy dog ...",
  "num_workers": 4
}
```

Response `202 Accepted`:

```json
{
  "job_id": "...",
  "status": "pending",
  "problem_type": "word_frequency",
  "num_workers": 4
}
```

### `GET /jobs/{job_id}`

Poll for results. `status` transitions: `pending, running, done or failed`.

### `GET /metrics?problem_type=word_frequency`

Returns all performance records for graphing:

```json
[
  {
    "job_id": "...",
    "problem_type": "word_frequency",
    "num_workers": 4,
    "total_time_ms": 38.7,
    "worker_times_ms": [35.1, 37.2, 38.7, 36.0],
    "chunk_count": 4,
    "input_size": 52843
  }
]
```

### `GET /problems`

List registered problem types.

### `DELETE /metrics`

Clear all stored metrics (fresh benchmark run).
