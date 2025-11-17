#!/bin/bash
cd "$(dirname "$0")"
export PYTHONPATH="${PWD}:${PYTHONPATH}"
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
