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

# Pick the first non-Docker/non-loopback LAN IP
LAN_IP=""
while IFS= read -r ip; do
  case "$ip" in
    127.*|169.254.*|172.1[6-9].*|172.2[0-9].*|172.3[0-1].*) continue;;
  esac
  LAN_IP="$ip"
  break
done < <(hostname -I | tr ' ' '\n' | grep -v '^$')

if [[ -z "$LAN_IP" ]]; then
  echo "Unable to auto-detect a non-Docker LAN IPv4 address."
  echo "Set WORKER_HOST_IP manually and re-run: WORKER_HOST_IP=<your-lan-ip> $0 $*"
  exit 1
fi

export ORCHESTRATOR_URL="http://${ORCHESTRATOR_IP}:${ORCHESTRATOR_PORT}"
export WORKER_HOST_IP="$LAN_IP"
export COMPUTER_NAME="$COMPUTER_NAME"

worker_ports=()
for i in $(seq 1 "$WORKER_COUNT"); do
  worker_ports+=("$((8100 + i))")
done

if command -v ufw >/dev/null 2>&1; then
  for port in "${worker_ports[@]}"; do
    if [[ "$EUID" -eq 0 ]]; then
      ufw allow "${port}/tcp" >/dev/null || true
    elif command -v sudo >/dev/null 2>&1; then
      sudo -n ufw allow "${port}/tcp" >/dev/null 2>&1 || true
    fi
  done
  echo "  Firewall (ufw) allow attempted for TCP ports: ${worker_ports[*]}"
else
  echo "  Warning: ufw not found; open TCP ports ${worker_ports[*]} manually if workers are unreachable."
fi

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