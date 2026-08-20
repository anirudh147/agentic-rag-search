#!/usr/bin/env bash
# Checks whether the full stack (Postgres, Ollama, Phoenix, backend,
# OpenWebUI) is up and reachable, and whether documents have been ingested.
set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
PASS="✅"
FAIL="❌"
ok=true

check() {
  local name="$1" cmd="$2"
  if eval "$cmd" >/dev/null 2>&1; then
    echo "  $PASS $name"
  else
    echo "  $FAIL $name"
    ok=false
  fi
}

echo "Container status:"
docker compose ps --format 'table {{.Service}}\t{{.Status}}' 2>/dev/null || echo "  (docker compose not available or stack not started)"

echo
echo "Service checks:"
check "Postgres accepting connections"   "docker compose exec -T postgres pg_isready -U \${POSTGRES_USER:-raguser} -d \${POSTGRES_DB:-ragdb}"
check "Ollama models present"            "docker compose exec -T ollama ollama list | grep -q qwen"
check "Phoenix UI reachable"             "curl -sf http://localhost:6006 -o /dev/null"
check "Backend health endpoint"          "curl -sf ${BASE_URL}/api/v1/health -o /dev/null"
check "OpenWebUI reachable"              "curl -sf http://localhost:3000 -o /dev/null"

echo
echo "Backend health detail:"
curl -sS "${BASE_URL}/api/v1/health" 2>/dev/null | python3 -m json.tool || echo "  (backend not reachable)"

echo
echo "Ingestion status:"
curl -sS "${BASE_URL}/api/v1/ingest/status" 2>/dev/null | python3 -m json.tool || echo "  (backend not reachable)"

echo
if $ok; then
  echo "$PASS Stack is up. Try: curl -X POST ${BASE_URL}/api/v1/query -H 'Content-Type: application/json' -d '{\"question\": \"...\"}'"
  echo "   OpenWebUI chat: http://localhost:3000  |  Swagger: ${BASE_URL}/docs  |  Phoenix traces: http://localhost:6006"
else
  echo "$FAIL One or more checks failed — see above. Try: docker compose logs -f <service>"
fi
