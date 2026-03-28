#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

mkdir -p /tmp/lalmba-capstone-logs

if [[ ! -f "${SCRIPT_DIR}/matoso-chatbot/build/index.html" ]]; then
  echo "Frontend build not found. Run ./scripts/build_frontend.sh first."
  exit 1
fi

nohup "${SCRIPT_DIR}/scripts/start_llama_cpp.sh" >/tmp/lalmba-capstone-logs/llama_cpp.log 2>&1 &
nohup "${SCRIPT_DIR}/scripts/start_backend.sh" >/tmp/lalmba-capstone-logs/backend.log 2>&1 &

echo "Started llama.cpp and backend in the background."
echo "Logs:"
echo "  /tmp/lalmba-capstone-logs/llama_cpp.log"
echo "  /tmp/lalmba-capstone-logs/backend.log"
