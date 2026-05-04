#!/bin/bash
# Smoke test contra una instancia corriendo de netvalidate.
# Uso: ./scripts/smoke_test.sh [base_url]
# La API key se lee automáticamente desde .env

set -e

BASE_URL="${1:-http://localhost:8000}"

# Cargar API key desde .env si existe
if [ -f .env ]; then
    API_KEY=$(grep "^NETVALIDATE_API_KEY=" .env | cut -d '=' -f2-)
fi
API_KEY="${API_KEY:-dev-key-change-me}"

echo "→ Smoke test: $BASE_URL"

# 1. Health
echo -n "  /health ... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health")
[ "$STATUS" = "200" ] && echo "OK" || { echo "FAIL ($STATUS)"; exit 1; }

# 2. Auth rejection
echo -n "  POST /validate without auth ... "
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  "$BASE_URL/api/v1/validate" \
  -H "Content-Type: application/json" \
  -d '{"device_ip":"192.0.2.10","vendor":"cisco","profile":"cisco_basic"}')
[ "$STATUS" = "401" ] && echo "OK" || { echo "FAIL ($STATUS)"; exit 1; }

# 3. Create job
echo -n "  POST /validate with auth ... "
RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/validate" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"device_ip":"192.0.2.10","vendor":"cisco","profile":"cisco_basic"}')
JOB_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])" 2>/dev/null)
[ -n "$JOB_ID" ] && echo "OK ($JOB_ID)" || { echo "FAIL — response: $RESPONSE"; exit 1; }

# 4. Poll job until completion
echo -n "  GET /jobs/$JOB_ID ... "
sleep 1
STATUS_JOB=$(curl -s "$BASE_URL/api/v1/jobs/$JOB_ID" -H "X-API-Key: $API_KEY" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
[ "$STATUS_JOB" = "completed" ] && echo "OK" || { echo "FAIL (status=$STATUS_JOB)"; exit 1; }

echo "✓ Smoke test passed"