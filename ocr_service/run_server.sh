#!/bin/bash
# ---------------------------------------------------------------------------
# Launch the Unlimited-OCR SGLang server (OpenAI-compatible API).
#
# Usage:
#   bash ocr_service/run_server.sh
#
# Env overrides:
#   OCR_MODEL_DIR   Model path (default: ./models/Unlimited-OCR)
#   OCR_GPU         CUDA_VISIBLE_DEVICES value (default: 1)
#   OCR_PORT        Port to serve on (default: 10000)
#   OCR_MEM_FRAC    Static GPU mem fraction (default: 0.8)
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

# shellcheck disable=SC1091
source .venv/bin/activate

MODEL_DIR="${OCR_MODEL_DIR:-$PWD/models/Unlimited-OCR}"
export CUDA_VISIBLE_DEVICES="${OCR_GPU:-1}"

echo "Launching Unlimited-OCR SGLang server"
echo "  model = ${MODEL_DIR}"
echo "  gpu   = ${CUDA_VISIBLE_DEVICES}"
echo "  port  = ${OCR_PORT:-10000}"

exec python -m sglang.launch_server \
    --model "${MODEL_DIR}" \
    --served-model-name Unlimited-OCR \
    --attention-backend fa3 \
    --page-size 1 \
    --mem-fraction-static "${OCR_MEM_FRAC:-0.8}" \
    --context-length 32768 \
    --enable-custom-logit-processor \
    --disable-overlap-schedule \
    --skip-server-warmup \
    --host 0.0.0.0 \
    --port "${OCR_PORT:-10000}"
