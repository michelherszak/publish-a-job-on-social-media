#!/usr/bin/env bash
# Start the local MH backend and frontend.
# Applies missing SQLite tables and columns in backend/mh.db, then keeps both servers running.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

BACKEND_HOST="127.0.0.1"
BACKEND_PORT="8011"
FRONTEND_HOST="127.0.0.1"
FRONTEND_PORT="5181"

if [[ -f backend/.env.local ]]; then
  set -a
  # shellcheck disable=SC1091
  source backend/.env.local
  set +a
  echo "Loaded private backend/.env.local"
fi

if ! python3 -c "import fastapi, uvicorn, pydantic, cryptography, PIL" >/dev/null 2>&1; then
  echo "Installing Python dependencies"
  python3 -m pip install -r backend/requirements.txt
fi

if [[ ! -d frontend/node_modules ]]; then
  echo "Installing frontend dependencies"
  npm install --prefix frontend
fi

echo "Checking database schema"
python3 - <<'PY'
import sqlite3
from pathlib import Path

db_path = Path("backend/mh.db")

def snapshot(path: Path) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    conn = sqlite3.connect(path)
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            table: [row[1] for row in conn.execute(f'PRAGMA table_info("{table}")')]
            for table in tables
        }
    finally:
        conn.close()

before = snapshot(db_path)
from backend.main import init_db

init_db()
after = snapshot(db_path)

added_tables = [name for name in after if name not in before]
added_columns = [
    f"{table}.{column}"
    for table, columns in after.items()
    if table in before
    for column in columns
    if column not in before[table]
]
if added_tables or added_columns:
    if added_tables:
        print("Added tables:", ", ".join(added_tables))
    if added_columns:
        print("Added columns:", ", ".join(added_columns))
else:
    print("Schema already current")
print(f"Database: {db_path.resolve()}")
PY

port_busy() {
  python3 - "$1" <<'PY'
import socket, sys
sock = socket.socket()
sock.settimeout(0.2)
code = sock.connect_ex(("127.0.0.1", int(sys.argv[1])))
raise SystemExit(0 if code == 0 else 1)
PY
}

if port_busy "$BACKEND_PORT"; then
  echo "Backend port ${BACKEND_PORT} is already in use." >&2
  exit 1
fi
if port_busy "$FRONTEND_PORT"; then
  echo "Frontend port ${FRONTEND_PORT} is already in use." >&2
  exit 1
fi

set -m
backend_pid=""
frontend_pid=""
listener_pid=""
listener_ready=""

stop_servers() {
  trap - EXIT INT TERM
  for mh_pid in "$backend_pid" "$frontend_pid" "$listener_pid"; do
    if [[ -n "$mh_pid" ]]; then
      kill -TERM -- "-$mh_pid" 2>/dev/null || kill -TERM "$mh_pid" 2>/dev/null || true
      wait "$mh_pid" 2>/dev/null || true
    fi
  done
  if [[ -n "$listener_ready" ]]; then rm -f "$listener_ready"; fi
}
trap stop_servers EXIT
trap 'stop_servers; exit 130' INT
trap 'stop_servers; exit 143' TERM

# Local Stripe Checkout also needs its signed event receiver. Start it before
# the API so the newly saved signing secret is loaded by the backend.
if [[ "${STRIPE_SECRET_KEY:-}" == sk_test_* ]]; then
  if ! command -v stripe >/dev/null 2>&1; then
    echo "Stripe CLI is required for local test payments. See BILLING_SETUP.md." >&2
    exit 1
  fi
  listener_ready="$(mktemp "${TMPDIR:-/tmp}/mh-stripe-ready.XXXXXX")"
  python3 -m backend.stripe_test listen --ready-file "$listener_ready" &
  listener_pid=$!
  for _ in {1..40}; do
    if [[ -s "$listener_ready" ]] || ! kill -0 "$listener_pid" 2>/dev/null; then break; fi
    sleep 0.5
  done
  if [[ ! -s "$listener_ready" ]]; then
    echo "Stripe listener is not ready; local Checkout cannot be confirmed." >&2
    exit 1
  fi
  set -a
  source backend/.env.local
  set +a
fi

python3 -m uvicorn backend.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT" &
backend_pid=$!
npm run dev --prefix frontend -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" --strictPort &
frontend_pid=$!

ready=0
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
  if ! kill -0 "$backend_pid" 2>/dev/null || ! kill -0 "$frontend_pid" 2>/dev/null; then
    echo "A server exited during startup." >&2
    exit 1
  fi
  if python3 - <<PY >/dev/null 2>&1
import urllib.request
urllib.request.urlopen("http://${BACKEND_HOST}:${BACKEND_PORT}/health", timeout=0.5).read()
PY
  then
    ready=1
    break
  fi
  sleep 0.4
done

if [[ "$ready" -ne 1 ]]; then
  echo "Backend did not become healthy on http://${BACKEND_HOST}:${BACKEND_PORT}/health" >&2
  exit 1
fi

echo "Landing:   http://${FRONTEND_HOST}:${FRONTEND_PORT}/"
echo "Workspace: http://${FRONTEND_HOST}:${FRONTEND_PORT}/app"
echo "Health:    http://${BACKEND_HOST}:${BACKEND_PORT}/health"
echo "Press Ctrl+C to stop both servers."

while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  if [[ -n "$listener_pid" ]] && ! kill -0 "$listener_pid" 2>/dev/null; then
    echo "Stripe listener stopped; restart MH to restore payment confirmation." >&2
    exit 1
  fi
  sleep 1
done
echo "A server stopped." >&2
exit 1
