#!/bin/bash

# Start Ollama
open -a Terminal "$(pwd)/scripts/start_ollama.sh"
sleep 5

# Start Llama2
open -a Terminal "$(pwd)/start_llama2.sh"
sleep 5

# Start Backend
open -a Terminal "$(pwd)/scripts/start_backend.sh"
sleep 5

# Start Frontend
open -a Terminal "$(pwd)/scripts/start_frontend.sh"
sleep 5

echo "All services starting in separate terminals..."