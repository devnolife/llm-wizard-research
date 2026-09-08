"""Skrip experiments/consensus_gaps.py: produsen resmi gaps_union.jsonl."""

import shutil
from pathlib import Path

import pytest

from app.core.pipeline.io import read_jsonl, write_jsonl
from experiments import consensus_gaps

SCRATCH = Path(__file__).parent / ".scratch_consensus_gaps"

STMT_A = "Penelitian ini masih terbatas pada satu institusi."
STMT_B = "Studi lanjutan disarankan."
STMT_C = "Dataset publik belum tersedia untuk kasus ini."


def _gap(source, stmt, score=1.0, **extra):
    return {"source": source, "gap_statement": stmt, "gap_type": "stated_limitation",
            "topic": "other", "grounding_score": score, **extra}


@pytest.fixture(autouse=True)
def _scratch():
    shutil.rmtree(SCRATCH, ignore_errors=True)
    SCRATCH.mkdir(parents=True)
    yield
    shutil.rmtree(SCRATCH, ignore_errors=True)


def _write_runs():
    runs = [
        [_gap("a.pdf", STMT_A, 0.9), _gap("a.pdf", STMT_B), _gap("b.pdf", STMT_C)],
        [_gap("a.pdf", STMT_A, 1.0), _gap("b.pdf", STMT_C)],
        [_gap("a.pdf", STMT_A, 0.95), _gap("a.pdf", STMT_A.upper())],  # duplikat dalam run
    ]
    paths = []
    for i, gaps in enumerate(runs, 1):
        p = SCRATCH / f"gaps_run{i}.jsonl"
        write_jsonl(str(p), [{"record": "meta", "job_id": f"run{i}"}] + gaps)
        paths.append(str(p))
    return paths


class TestConsensusScript:
    def test_union_carries_k_of_n_with_default_threshold(self, capsys):
        out = SCRATCH / "gaps_union.jsonl"
        assert consensus_gaps.main(["--inputs", *_write_runs(), "--out", str(out)]) == 0

        rows = read_jsonl(str(out))
        meta = rows[0]
        gaps = {r["gap_statement"]: r for r in rows[1:]}
        assert meta["record"] == "meta" and meta["jumlah_gap_per_run"] == [3, 2, 2]
        assert meta["jumlah_gap_union"] == 3 and meta["jumlah_gap_stabil"] == 2
        assert meta["konsensus"]["min_run_hits"] == 2, "bawaan ceil(2·3/3) = 2"
        assert (gaps[STMT_A]["run_hits"], gaps[STMT_A]["stable"]) == (3, True)
        assert gaps[STMT_A]["grounding_score"] == 1.0, "maksimum lintas run"
        assert (gaps[STMT_C]["run_hits"], gaps[STMT_C]["run_ids"], gaps[STMT_C]["stable"]) == (
            2, [1, 2], True)
        assert (gaps[STMT_B]["run_hits"], gaps[STMT_B]["stable"]) == (1, False)
        assert all(r["run_total"] == 3 for r in rows[1:])

        printed = capsys.readouterr().out
        assert "Union      : 3 gap unik" in printed
        assert "3/3" in printed and "1/3" in printed, "tabel distribusi k/n tercetak"

    def test_stable_only_and_custom_threshold(self):
        out = SCRATCH / "gaps_stable.jsonl"
        consensus_gaps.main(["--inputs", *_write_runs(), "--out", str(out),
                             "--min-run-hits", "3", "--stable-only"])
        rows = read_jsonl(str(out))
        assert [r["gap_statement"] for r in rows[1:]] == [STMT_A]
        assert rows[0]["konsensus"]["min_run_hits"] == 3
        assert rows[0]["jumlah_gap_union"] == 3, "meta tetap melaporkan union penuh"

    def test_single_input_is_a_plain_dedup_with_annotation(self):
        out = SCRATCH / "gaps_one.jsonl"
        consensus_gaps.main(["--inputs", _write_runs()[2], "--out", str(out)])
        rows = read_jsonl(str(out))
        assert len(rows) == 2, "duplikat dalam satu run tetap dilebur"
        assert rows[1]["run_hits"] == 1 and rows[1]["run_total"] == 1 and rows[1]["stable"]
        assert rows[0]["konsensus"]["jaccard_between_runs"] is None

    def test_consensus_table_lists_every_k(self):
        gaps = [{"run_hits": 3}, {"run_hits": 3}, {"run_hits": 1}]
        table = consensus_gaps.consensus_table(gaps, runs=3)
        assert len(table) == 5  # header, garis, k=3,2,1
        assert "3/3" in table[2] and "2" in table[2].split("|")[1]
        assert "2/3" in table[3] and "0" in table[3].split("|")[1]
