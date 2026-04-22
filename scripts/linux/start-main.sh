#!/usr/bin/env bash
set -euo pipefail

WORKER_COUNT="${1:-8}"

if ! [[ "$WORKER_COUNT" =~ ^[1-8]$ ]]; then
  echo "WorkerCount must be an integer between 1 and 8"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

worker_services=()
for i in $(seq 1 "$WORKER_COUNT"); do
  worker_services+=("worker${i}")
done

services=("orchestrator" "frontend" "${worker_services[@]}")

cd "$REPO_ROOT"
echo "Starting main stack with ${WORKER_COUNT} worker(s)..."
docker compose up -d --build "${services[@]}"
echo "Done. UI: http://localhost:3000  API: http://localhost:8000"