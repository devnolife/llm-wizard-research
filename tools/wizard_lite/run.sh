#!/usr/bin/env bash
# Jalankan Wizard Lite. Memakai .venv lokal bila ada, kalau tidak meminjam venv
# tools/process_monitor (sudah berisi streamlit + requests) agar tidak dobel unduh.
set -euo pipefail
cd "$(dirname "$0")"

if [[ -x .venv/bin/streamlit ]]; then
  STREAMLIT=.venv/bin/streamlit
elif [[ -x ../process_monitor/.venv/bin/streamlit ]]; then
  STREAMLIT=../process_monitor/.venv/bin/streamlit
else
  echo "streamlit belum terpasang. Buat venv dulu:" >&2
  echo "  python -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

# 50 MB = batas backend (config.yaml data.max_file_size_mb); tanpa ini UI menjanjikan 200 MB.
exec "$STREAMLIT" run app.py --server.port "${PORT:-8502}" --server.headless true \
  --server.maxUploadSize 50 "$@"
