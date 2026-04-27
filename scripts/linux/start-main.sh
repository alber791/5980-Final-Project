#!/usr/bin/env bash
set -euo pipefail

WORKER_COUNT="${1:-8}"
ORCHESTRATOR_PORT="${2:-8000}"

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

if command -v ufw >/dev/null 2>&1; then
  if [[ "$EUID" -eq 0 ]]; then
    ufw allow "${ORCHESTRATOR_PORT}/tcp" >/dev/null || true
  elif command -v sudo >/dev/null 2>&1; then
    sudo -n ufw allow "${ORCHESTRATOR_PORT}/tcp" >/dev/null 2>&1 || true
  fi
  echo "Firewall (ufw) allow attempted for TCP port: ${ORCHESTRATOR_PORT}"
else
  echo "Warning: ufw not found; open TCP port ${ORCHESTRATOR_PORT} manually if remote workers are unreachable."
fi

cd "$REPO_ROOT"
echo "Starting main stack with ${WORKER_COUNT} worker(s)..."
docker compose up -d --build "${services[@]}"
echo "Done. UI: http://localhost:3000  API: http://localhost:8000"