#!/bin/sh
set -eu

cores="$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 1)"
workers=$((2 * cores + 1))

echo "Starting Gunicorn with ${workers} Uvicorn workers..."
exec gunicorn app.main:app \
    -k uvicorn.workers.UvicornWorker \
    -w "${workers}" \
    -b 0.0.0.0:8000
