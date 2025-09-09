#!/bin/sh
set -e
# Allow overriding RUN_ID to keep outputs isolated
export RUN_ID=${RUN_ID:-docker}

# Load .env if present, stripping Windows CR (\r) and ignoring comments/blank lines
if [ -f /app/.env ]; then
  # Remove trailing CR, drop comments/empty, and export KEY=VALUE pairs safely
  ENV_VARS=$(sed -e 's/\r$//' -e 's/^export \{0,1\}//' -e '/^\s*#/d' -e '/^\s*$/d' /app/.env | xargs)
  if [ -n "$ENV_VARS" ]; then
    export $ENV_VARS
  fi
fi

if [ "$RUN_MODE" = "ui" ]; then
  echo "Starting Streamlit UI..."
  exec streamlit run /app/streamlit.app.py --server.port=8501 --server.address=0.0.0.0
else
  echo "Starting FastAPI (uvicorn)..."
  exec uvicorn main:app --host 0.0.0.0 --port 8000
fi
