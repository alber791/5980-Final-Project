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

### Built-in problems

| Problem | Input | What it does |
|---|---|---|
| `word_frequency` | Plain text string | Counts word occurrences across chunks |
| `prime_count` | `{"n": 500000}` | Finds all primes up to N using segmented |


## Quick Start

### Prerequisites
- docker

### Run everything

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| Frontend (React) | http://localhost:3000 |
| Orchestrator API | http://localhost:8000 |

### Stop

```bash
docker compose down
```

---

## Running a Benchmark

1. Open **http://localhost:3000**
2. Select a problem type and paste/type input
3. Click **"Full benchmark (1 -> 8)"** — this automatically submits the same job with 1, 2, 3, … 8 workers sequentially
4. Switch to the **Performance Chart** tab to view timing graphs

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
