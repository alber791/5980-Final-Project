#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR_IP="${1:-}"
WORKER_COUNT="${2:-4}"
ORCHESTRATOR_PORT="${3:-8000}"
COMPUTER_NAME="${4:-$(hostname)}"

if [[ -z "$ORCHESTRATOR_IP" ]]; then
  echo "Usage: ./scripts/linux/start-workers-node.sh <orchestrator-ip> [worker-count:1-8] [orchestrator-port] [computer-name]"
  exit 1
fi

if ! [[ "$WORKER_COUNT" =~ ^[1-8]$ ]]; then
  echo "WorkerCount must be an integer between 1 and 8"
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

LAN_IP="$(hostname -I | awk '{print $1}')"
if [[ -z "$LAN_IP" ]]; then
  echo "Unable to auto-detect LAN IPv4 address."
  exit 1
fi

export ORCHESTRATOR_URL="http://${ORCHESTRATOR_IP}:${ORCHESTRATOR_PORT}"
export WORKER_HOST_IP="$LAN_IP"
export COMPUTER_NAME="$COMPUTER_NAME"

worker_services=()
for i in $(seq 1 "$WORKER_COUNT"); do
  worker_services+=("worker${i}")
done

echo "Starting worker-only node with ${WORKER_COUNT} worker(s)..."
echo "  ORCHESTRATOR_URL=${ORCHESTRATOR_URL}"
echo "  WORKER_HOST_IP=${WORKER_HOST_IP}"
echo "  COMPUTER_NAME=${COMPUTER_NAME}"

cd "$REPO_ROOT"
docker compose -f docker-compose.workers-only.yml up -d --build "${worker_services[@]}"
echo "Done. Workers should appear in orchestrator /workers within a few seconds."