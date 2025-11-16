#!/bin/sh
set -eu

# Respect existing environment (.env injected by provider)
# Start backend (FastAPI) with Uvicorn in production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 &
BACKEND_PID=$!

# Start frontend (Next.js) on Node LTS
cd frontend
npm run build >/dev/null 2>&1 || npm run build
npm run start -- -p 3000 &
FRONTEND_PID=$!

trap 'kill $BACKEND_PID $FRONTEND_PID' INT TERM
wait