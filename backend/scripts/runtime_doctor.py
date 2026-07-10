#!/usr/bin/env python3
"""Print the redacted effective runtime configuration and optionally probe OCR."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.dependencies import get_document_processor
from app.utils.config_loader import get_effective_config_summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Wizard Research runtime configuration doctor")
    parser.add_argument("--check-ocr", action="store_true", help="Probe the OCR service when OCR is enabled")
    args = parser.parse_args()

    summary = get_effective_config_summary()
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))

    if args.check_ocr:
        ocr = summary["ocr"]
        if not ocr["enabled"]:
            print("OCR disabled; no service probe performed.")
            return 0
        processor = get_document_processor()
        client = processor.ocr_client
        available = bool(client and client.is_available())
        print(f"OCR service available: {available}")
        return 0 if available else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
