#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

LLAMA_CPP_SERVER_BIN="${LLAMA_CPP_SERVER_BIN:-/home/lalmba/Documents/llama.cpp/build/bin/llama-server}"
LLAMA_CPP_MODEL_PATH="${LLAMA_CPP_MODEL_PATH:-}"
LLAMA_CPP_HOST="${LLAMA_CPP_HOST:-127.0.0.1}"
LLAMA_CPP_PORT="${LLAMA_CPP_PORT:-8080}"
LLAMA_CPP_MODEL_ALIAS="${LLAMA_CPP_MODEL_ALIAS:-local-model}"

if [[ -z "${LLAMA_CPP_MODEL_PATH}" ]]; then
    echo "LLAMA_CPP_MODEL_PATH must point to a chat-capable .gguf file."
    exit 1
fi

if [[ ! -x "${LLAMA_CPP_SERVER_BIN}" ]]; then
    echo "llama-server binary not found or not executable at ${LLAMA_CPP_SERVER_BIN}"
    exit 1
fi

if [[ ! -f "${LLAMA_CPP_MODEL_PATH}" ]]; then
    echo "Model file not found at ${LLAMA_CPP_MODEL_PATH}"
    exit 1
fi

cd "${PROJECT_ROOT}"
exec "${LLAMA_CPP_SERVER_BIN}" \
    --host "${LLAMA_CPP_HOST}" \
    --port "${LLAMA_CPP_PORT}" \
    --model "${LLAMA_CPP_MODEL_PATH}" \
    --alias "${LLAMA_CPP_MODEL_ALIAS}"
