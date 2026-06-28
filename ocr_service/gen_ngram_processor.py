"""
Generate the serialized DeepSeek-OCR no-repeat-ngram custom logit processor
string and persist it to ``ngram_processor.txt``.

This MUST run inside the SGLang service venv (it imports ``sglang``). The
backend OCR client then reads the produced file and forwards the string in the
``custom_logit_processor`` field of each request, so the server applies the
anti-repetition logic on long-horizon generations. The backend itself never
needs SGLang installed.
"""

from pathlib import Path


def main() -> None:
    from sglang.srt.sampling.custom_logit_processor import (
        DeepseekOCRNoRepeatNGramLogitProcessor,
    )

    processor_str = DeepseekOCRNoRepeatNGramLogitProcessor.to_str()
    out_path = Path(__file__).resolve().parent / "ngram_processor.txt"
    out_path.write_text(processor_str, encoding="utf-8")
    print(f"Wrote no-repeat-ngram processor string -> {out_path}")


if __name__ == "__main__":
    main()
