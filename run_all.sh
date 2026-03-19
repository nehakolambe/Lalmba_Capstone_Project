#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p /tmp/lalmba-capstone-logs

nohup "${SCRIPT_DIR}/scripts/start_llama_cpp.sh" >/tmp/lalmba-capstone-logs/llama_cpp.log 2>&1 &
nohup "${SCRIPT_DIR}/scripts/start_backend.sh" >/tmp/lalmba-capstone-logs/backend.log 2>&1 &
nohup "${SCRIPT_DIR}/scripts/start_frontend.sh" >/tmp/lalmba-capstone-logs/frontend.log 2>&1 &

echo "Started llama.cpp, backend, and frontend in the background."
echo "Logs:"
echo "  /tmp/lalmba-capstone-logs/llama_cpp.log"
echo "  /tmp/lalmba-capstone-logs/backend.log"
echo "  /tmp/lalmba-capstone-logs/frontend.log"
