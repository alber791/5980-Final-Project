#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$REPO_ROOT"
docker compose -f docker-compose.workers-only.yml down

if command -v ufw >/dev/null 2>&1; then
	for port in $(seq 8101 8108); do
		if [[ "$EUID" -eq 0 ]]; then
			ufw delete allow "${port}/tcp" >/dev/null || true
		elif command -v sudo >/dev/null 2>&1; then
			sudo -n ufw delete allow "${port}/tcp" >/dev/null 2>&1 || true
		fi
	done
	echo "Firewall (ufw) cleanup attempted for TCP ports: 8101-8108"
else
	echo "Warning: ufw not found; no firewall cleanup applied."
fi

echo "Worker-only node stopped."