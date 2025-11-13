#!/bin/bash
# Wizard Research - Server Startup Script

echo "🧙‍♂️ WIZARD RESEARCH - Starting Server"
echo "======================================"
echo ""
echo "Installing final dependencies (torch is ~900MB, may take a few minutes)..."
pip install 'transformers>=4.41.0,<5.0.0' --quiet

echo ""
echo "Starting FastAPI server..."
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
