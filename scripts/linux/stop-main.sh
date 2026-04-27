#!/usr/bin/env bash
set -euo pipefail

ORCHESTRATOR_PORT="${1:-8000}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"
docker compose down

if command -v ufw >/dev/null 2>&1; then
  if [[ "$EUID" -eq 0 ]]; then
    ufw delete allow "${ORCHESTRATOR_PORT}/tcp" >/dev/null || true
  elif command -v sudo >/dev/null 2>&1; then
    sudo -n ufw delete allow "${ORCHESTRATOR_PORT}/tcp" >/dev/null 2>&1 || true
  fi
  echo "Firewall (ufw) cleanup attempted for TCP port: ${ORCHESTRATOR_PORT}"
else
  echo "Warning: ufw not found; no firewall cleanup applied."
fi

echo "Main stack stopped."
