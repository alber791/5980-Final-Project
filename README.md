# Distributed Compute Benchmark

A **FastAPI + React + Docker** project that demonstrates how distributing computation across multiple containers affects performance.

---

## About Problems

Every problem implements these methods in `backend/shared/problems/`:

```python
class BaseProblem(ABC):

	@property
	def name(self) -> str:
	# UI name of problem

	@property
	def input_spec(self) -> Dict[str, Any]:
		return {
				"type": "file",
				"label": "Upload labeled text file",
				"accept": [".py" ],
				"placeholder": "Expects a file input",
				"description": "",
		}

	def parse_input(self, input_data: Any) -> Any:
	# Runs in ORCHESTRATOR - parses original input from frontend

	def split(self, input_data, num_chunks) -> List[chunk]:
	# Runs in ORCHESTRATOR — divides work

	def solve(self, chunk) -> partial_result:
	# Runs in WORKER — processes one piece

	def aggregate(self, partial_results) -> final_result:
	# Runs in ORCHESTRATOR — merges all pieces
```

### Problems

| Problem | Input | What it does |
|---|---|---|
| `word_frequency` | Text | Counts word occurrences across chunks |
| `prime_count` | number | Finds all primes up to N using segmented |
| `numeric_stats` | File (`.json`, `.txt`, `.csv`) | Computes count, mean, std dev, min, and max via distributed partial aggregates |
| `naive_bayes` | File (`.json`) | Tokenizes labeled documents and aggregates per-class feature counts for model training |

NOTE: Example test files for problems can be found in /test_inputs

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

Note: These scripts must be ran with elevated privileges as they open ports for the remote workers to communicate with the orchestrator.  Running the stop scripts will close these ports 

Windows: `./scripts/windows/start-main.ps1 -WorkerCount 5 -OrchestratorPort 8000`

Linux: `./scripts/linux/start-main.sh 5 8000`

Stop main stack:

- Windows: `./scripts/windows/stop-main.ps1`
- Linux: `./scripts/linux/stop-main.sh 8000`

**Workers-only machine setup**

On a seperate machine connected in the same LAN of the running orchestrator, you can run these scripts to add additional (1-8) workers that the orchestrator can use.  In order to run this, first you MUST obtain the ip address of the orchestrator.  This allows the workers to register with the orchestrator.  In the commands below replace <orchestrator-ip> with the ip address of your main machine

Note: These scripts must be ran with elevated privileges as they open ports for the remote workers to communicate with the orchestrator.  Running the stop scripts will close these ports 

Windows (Worker): `./scripts/windows/start-workers-node.ps1 -OrchestratorIp <orchestrator-ip> -WorkerCount 4 -ComputerName Remote-Machine-1`

Linux (Worker): `./scripts/linux/start-workers-node.sh <orchestrator-ip> 4 8000 Remote-Machine-1`

stop:
  - Windows: `./scripts/windows/stop-workers-node.ps1`
  - Linux: `./scripts/linux/stop-workers-node.sh`

---

## Running a Benchmark

1. Open **http://localhost:3000**
2. Select a problem type
3. Input the problem size (NOTE: Example inputs can be found in /test_inputs)
4. Select the number of registered workers you want to run the benchmark on
5. Select the number of times you want to run that benchmark

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
