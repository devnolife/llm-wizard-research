#!/usr/bin/env python3
"""
Dataset Downloader — Wizard Research Experiments

Downloads the benchmark paper dataset (CS, 2015-2025 + foundational papers)
from arXiv into research_papers/ and writes a metadata manifest.

The dataset is organised into 4 topic groups (3-10 papers each, per the
thesis scope constraints) used by run_experiment.py:

    T1  Deep learning architectures & optimization
    T2  Computer vision & object detection
    T3  NLP & attention mechanisms
    T4  Efficient deployment & model compression  (adversarial-friendly:
        resource constraints exercise Rule F1-F3)

Usage:
    cd backend
    python experiments/download_papers.py            # download missing papers
    python experiments/download_papers.py --list     # show dataset status
"""

import argparse
import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

PROJECT_DIR = Path(__file__).resolve().parent.parent.parent
PAPERS_DIR = PROJECT_DIR / "research_papers"
MANIFEST_PATH = PAPERS_DIR / "papers_manifest.json"

ARXIV_PDF_URL = "https://export.arxiv.org/pdf/{arxiv_id}"
USER_AGENT = "WizardResearch-Thesis/1.0 (academic experiment dataset)"
DOWNLOAD_DELAY_S = 3.0  # be polite to arXiv

# ---------------------------------------------------------------------------
# Benchmark dataset definition
# ---------------------------------------------------------------------------

PAPERS = [
    # --- T1: Deep learning architectures & optimization ---
    {"file": "resnet_paper.pdf", "arxiv_id": "1512.03385", "topic": "T1",
     "title": "Deep Residual Learning for Image Recognition",
     "authors": "He et al.", "year": 2016},
    {"file": "densenet_paper.pdf", "arxiv_id": "1608.06993", "topic": "T1",
     "title": "Densely Connected Convolutional Networks",
     "authors": "Huang et al.", "year": 2017},
    {"file": "adam_paper.pdf", "arxiv_id": "1412.6980", "topic": "T1",
     "title": "Adam: A Method for Stochastic Optimization",
     "authors": "Kingma & Ba", "year": 2015},
    {"file": "batchnorm_paper.pdf", "arxiv_id": "1502.03167", "topic": "T1",
     "title": "Batch Normalization: Accelerating Deep Network Training",
     "authors": "Ioffe & Szegedy", "year": 2015},
    {"file": "layernorm_paper.pdf", "arxiv_id": "1607.06450", "topic": "T1",
     "title": "Layer Normalization",
     "authors": "Ba et al.", "year": 2016},
    {"file": "gan_paper.pdf", "arxiv_id": "1406.2661", "topic": "T1",
     "title": "Generative Adversarial Nets",
     "authors": "Goodfellow et al.", "year": 2014},

    # --- T2: Computer vision & object detection ---
    {"file": "yolo_paper.pdf", "arxiv_id": "1506.02640", "topic": "T2",
     "title": "You Only Look Once: Unified, Real-Time Object Detection",
     "authors": "Redmon et al.", "year": 2016},
    {"file": "faster_rcnn_paper.pdf", "arxiv_id": "1506.01497", "topic": "T2",
     "title": "Faster R-CNN: Towards Real-Time Object Detection",
     "authors": "Ren et al.", "year": 2015},
    {"file": "ssd_paper.pdf", "arxiv_id": "1512.02325", "topic": "T2",
     "title": "SSD: Single Shot MultiBox Detector",
     "authors": "Liu et al.", "year": 2016},
    {"file": "mask_rcnn_paper.pdf", "arxiv_id": "1703.06870", "topic": "T2",
     "title": "Mask R-CNN",
     "authors": "He et al.", "year": 2017},
    {"file": "efficientnet_paper.pdf", "arxiv_id": "1905.11946", "topic": "T2",
     "title": "EfficientNet: Rethinking Model Scaling for CNNs",
     "authors": "Tan & Le", "year": 2019},
    {"file": "vit_paper.pdf", "arxiv_id": "2010.11929", "topic": "T2",
     "title": "An Image is Worth 16x16 Words: Transformers for Image Recognition",
     "authors": "Dosovitskiy et al.", "year": 2021},

    # --- T3: NLP & attention mechanisms ---
    {"file": "attention_is_all_you_need.pdf", "arxiv_id": "1706.03762", "topic": "T3",
     "title": "Attention Is All You Need",
     "authors": "Vaswani et al.", "year": 2017},
    {"file": "bert_paper.pdf", "arxiv_id": "1810.04805", "topic": "T3",
     "title": "BERT: Pre-training of Deep Bidirectional Transformers",
     "authors": "Devlin et al.", "year": 2019},
    {"file": "gpt3_paper.pdf", "arxiv_id": "2005.14165", "topic": "T3",
     "title": "Language Models are Few-Shot Learners (GPT-3)",
     "authors": "Brown et al.", "year": 2020},
    {"file": "t5_paper.pdf", "arxiv_id": "1910.10683", "topic": "T3",
     "title": "Exploring the Limits of Transfer Learning with T5",
     "authors": "Raffel et al.", "year": 2020},
    {"file": "roberta_paper.pdf", "arxiv_id": "1907.11692", "topic": "T3",
     "title": "RoBERTa: A Robustly Optimized BERT Pretraining Approach",
     "authors": "Liu et al.", "year": 2019},
    {"file": "electra_paper.pdf", "arxiv_id": "2003.10555", "topic": "T3",
     "title": "ELECTRA: Pre-training Text Encoders as Discriminators",
     "authors": "Clark et al.", "year": 2020},

    # --- T4: Efficient deployment & model compression ---
    {"file": "mobilenet_paper.pdf", "arxiv_id": "1704.04861", "topic": "T4",
     "title": "MobileNets: Efficient CNNs for Mobile Vision Applications",
     "authors": "Howard et al.", "year": 2017},
    {"file": "mobilenetv2_paper.pdf", "arxiv_id": "1801.04381", "topic": "T4",
     "title": "MobileNetV2: Inverted Residuals and Linear Bottlenecks",
     "authors": "Sandler et al.", "year": 2018},
    {"file": "distilbert_paper.pdf", "arxiv_id": "1910.01108", "topic": "T4",
     "title": "DistilBERT, a distilled version of BERT",
     "authors": "Sanh et al.", "year": 2019},
    {"file": "distillation_paper.pdf", "arxiv_id": "1503.02531", "topic": "T4",
     "title": "Distilling the Knowledge in a Neural Network",
     "authors": "Hinton et al.", "year": 2015},
    {"file": "squeezenet_paper.pdf", "arxiv_id": "1602.07360", "topic": "T4",
     "title": "SqueezeNet: AlexNet-level accuracy with 50x fewer parameters",
     "authors": "Iandola et al.", "year": 2016},
]

TOPIC_QUERIES = {
    "T1": "deep learning architectures and optimization techniques",
    "T2": "computer vision object detection and image recognition",
    "T3": "natural language processing and attention mechanisms",
    "T4": "efficient deep learning deployment on resource-constrained edge devices",
}


def download_paper(paper: dict) -> bool:
    """Download a single paper PDF from arXiv. Returns True on success."""
    target = PAPERS_DIR / paper["file"]
    url = ARXIV_PDF_URL.format(arxiv_id=paper["arxiv_id"])

    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=60) as resp:
            data = resp.read()
        if not data.startswith(b"%PDF"):
            print(f"  [SKIP] {paper['file']}: response is not a PDF")
            return False
        target.write_bytes(data)
        size_mb = len(data) / 1e6
        print(f"  [OK]   {paper['file']} ({size_mb:.1f} MB)")
        return True
    except Exception as e:
        print(f"  [FAIL] {paper['file']}: {e}")
        return False


def write_manifest():
    """Write the dataset manifest (metadata for BAB IV tables)."""
    manifest = {
        "description": "Benchmark dataset — Wizard Research thesis experiments",
        "topics": TOPIC_QUERIES,
        "papers": [
            {**p, "downloaded": (PAPERS_DIR / p["file"]).exists()}
            for p in PAPERS
        ],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    print(f"\nManifest written: {MANIFEST_PATH}")


def main():
    parser = argparse.ArgumentParser(description="Download benchmark papers from arXiv")
    parser.add_argument("--list", action="store_true", help="Show dataset status only")
    args = parser.parse_args()

    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    present = [p for p in PAPERS if (PAPERS_DIR / p["file"]).exists()]
    missing = [p for p in PAPERS if not (PAPERS_DIR / p["file"]).exists()]

    print(f"Dataset: {len(PAPERS)} papers in {len(TOPIC_QUERIES)} topics")
    print(f"Present: {len(present)} | Missing: {len(missing)}\n")

    if args.list:
        for p in PAPERS:
            status = "✓" if (PAPERS_DIR / p["file"]).exists() else "✗"
            print(f"  [{status}] {p['topic']} {p['file']:35s} {p['title'][:55]}")
        write_manifest()
        return

    if not missing:
        print("All papers already downloaded.")
        write_manifest()
        return

    print(f"Downloading {len(missing)} missing papers from arXiv...\n")
    ok = 0
    for i, paper in enumerate(missing):
        ok += download_paper(paper)
        if i < len(missing) - 1:
            time.sleep(DOWNLOAD_DELAY_S)

    print(f"\nDownloaded {ok}/{len(missing)} papers")
    write_manifest()

    if ok < len(missing):
        sys.exit(1)


if __name__ == "__main__":
    main()
