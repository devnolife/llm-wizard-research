#!/bin/bash
# ---------------------------------------------------------------------------
# Setup the Unlimited-OCR SGLang service in an ISOLATED uv virtualenv.
#
# This venv is intentionally separate from the backend (which uses
# torch 2.4.1). Unlimited-OCR / SGLang require torch 2.10 and a vendored
# SGLang wheel, so they must never share the backend environment.
#
# Usage:
#   bash ocr_service/setup.sh
#
# Env overrides:
#   OCR_MODEL_DIR   Where to download the model (default: ./models/Unlimited-OCR)
#   PYTHON_VERSION  Python for the venv (default: 3.12)
# ---------------------------------------------------------------------------
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
MODEL_ID="baidu/Unlimited-OCR"
MODEL_DIR="${OCR_MODEL_DIR:-$PWD/models/Unlimited-OCR}"
WHEEL_FILE="sglang-0.0.0.dev11416+g92e8bb79e-py3-none-any.whl"
WHEEL_URL="https://huggingface.co/${MODEL_ID}/resolve/main/wheel/${WHEEL_FILE}"

echo "==> Creating uv venv (.venv, python ${PYTHON_VERSION}) ..."
uv venv --python "${PYTHON_VERSION}" .venv

# shellcheck disable=SC1091
source .venv/bin/activate

if [ ! -f "${WHEEL_FILE}" ]; then
    echo "==> Downloading SGLang wheel ..."
    curl -fL -o "${WHEEL_FILE}" "${WHEEL_URL}"
fi

echo "==> Installing SGLang wheel + pinned deps ..."
uv pip install "${WHEEL_FILE}"
uv pip install kernels==0.11.7
uv pip install pymupdf==1.27.2.2
uv pip install "huggingface_hub[cli]"

echo "==> Downloading model ${MODEL_ID} -> ${MODEL_DIR} ..."
mkdir -p "${MODEL_DIR}"
hf download "${MODEL_ID}" --local-dir "${MODEL_DIR}"

echo "==> Generating no-repeat-ngram logit processor string ..."
python gen_ngram_processor.py || echo "WARN: could not generate ngram processor (OCR still works without it)"

echo ""
echo "Setup complete."
echo "  Model:  ${MODEL_DIR}"
echo "  Start the server with:  bash ocr_service/run_server.sh"
