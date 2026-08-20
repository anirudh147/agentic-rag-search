#!/usr/bin/env bash
# Triggers ingestion of ./sample_docs (or SOURCE_DOCUMENTS_DIR) via the
# running backend's REST API and waits for it to finish.
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "Starting ingestion (synchronous) against ${BASE_URL} ..."
curl -sS -X POST "${BASE_URL}/api/v1/ingest" \
  -H "Content-Type: application/json" \
  -d '{"run_async": false}' | python3 -m json.tool
