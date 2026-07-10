#!/bin/bash
# Development launcher. It deliberately enables Uvicorn reload even though the
# production `api.reload` config is false; API_HOST/API_PORT can override the
# documented config defaults (0.0.0.0:8001) for local development.
cd "$(dirname "$0")"
export PYTHONPATH="${PWD}:${PYTHONPATH}"
cd backend
python -m uvicorn app.main:app --host "${API_HOST:-0.0.0.0}" --port "${API_PORT:-8001}" --reload
