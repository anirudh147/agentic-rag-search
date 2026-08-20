#!/usr/bin/env bash
# Triggers the RAGAs evaluation harness via the REST API (synchronous) and
# pretty-prints the aggregate scores.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "Running RAGAs evaluation against ${BASE_URL} ... (this calls the LLM many times, may take a few minutes on CPU)"
curl -sS -X POST "${BASE_URL}/api/v1/eval/run" \
  -H "Content-Type: application/json" \
  -d '{"run_async": false}' | python3 -m json.tool
