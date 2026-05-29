#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PREGNANCY_COPILOT_PROJECT_DIR:-$PWD}"
DATA_ROOT="${PREGNANCY_COPILOT_DATA_ROOT:-$HOME/pregnancy-data}"
LARK_PROFILE="${PREGNANCY_COPILOT_LARK_PROFILE:-pregnancy-bot}"
LOG_FILE="${PREGNANCY_COPILOT_WORKER_LOG:-$DATA_ROOT/worker.log}"
PID_FILE="${PREGNANCY_COPILOT_WORKER_PID:-$DATA_ROOT/worker.pid}"

mkdir -p "$DATA_ROOT"

cd "$PROJECT_DIR"

if [[ -f "$PID_FILE" ]]; then
  existing_pid="$(cat "$PID_FILE")"
  if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
    echo "Pregnancy Copilot worker already running: PID $existing_pid"
    exit 0
  fi
fi

nohup env PYTHONPATH=src \
  .venv/bin/python scripts/run_feishu_event_loop.py \
  --profile "$LARK_PROFILE" \
  --data-root "$DATA_ROOT" \
  >> "$LOG_FILE" 2>&1 &

pid="$!"
echo "$pid" > "$PID_FILE"
echo "Pregnancy Copilot worker started: PID $pid"
echo "Data root: $DATA_ROOT"
echo "Log file: $LOG_FILE"

