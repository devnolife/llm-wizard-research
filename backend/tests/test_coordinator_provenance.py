"""Provenance of facts extracted in the coordinator's OBSERVE node.

RAG passages carry ``source``/``title`` top-level (no ``doc_id``), so the
paper id handed to the fact extractor must fall back to them — otherwise every
fact in the table is attributed to "unknown" and the UI cannot tell which
uploaded journal a triple came from.
"""

from app.core.agents.coordinator import CoordinatorAgent
from app.core.agents.tools.paper_analyzer_tool import PaperAnalyzerTool


class _RecordingExtractor:
    def __init__(self):
        self.calls = []

    def extract_from_text(self, content, paper_id, fact_table):
        self.calls.append((content, paper_id))
        return {}


class _StubRAG:
    def __init__(self, passages):
        self._passages = passages

    def run(self, query, top_k=5):
        return {"results": list(self._passages), "total": len(self._passages)}


class _StubFactTable:
    def get_statistics(self):
        return {"total_facts": 0, "total_entities": 0}


def _observe(passages):
    extractor = _RecordingExtractor()
    agent = CoordinatorAgent(
        rag_tool=_StubRAG(passages),
        fact_extractor=extractor,
        fact_table=_StubFactTable(),
    )
    agent._node_observe({"query": "topik", "context": {}})
    return [pid for _, pid in extractor.calls]


def test_rag_passage_source_becomes_fact_paper_id():
    ids = _observe([
        {"content": "Kalimat pertama yang cukup panjang.", "title": "Unknown", "source": "a.pdf"},
        {"content": "Kalimat kedua yang cukup panjang.", "title": "Judul B", "source": ""},
    ])
    assert ids == ["a.pdf", "Judul B"]


def test_doc_id_still_wins_and_unknown_is_last_resort():
    ids = _observe([
        {"content": "Ada doc_id.", "doc_id": "doc-1", "source": "a.pdf"},
        {"content": "Tanpa apa pun.", "title": "Unknown", "source": ""},
    ])
    assert ids == ["doc-1", "unknown"]


def test_paper_analyzer_enrichment_uses_same_paper_id():
    # Step 4 of OBSERVE re-extracts via PaperAnalyzerTool; it must not fall back
    # to "unknown" while the fact extractor path already resolved the source.
    extractor = _RecordingExtractor()
    table = _StubFactTable()
    passages = [{"content": "Kalimat yang cukup panjang.", "title": "Unknown", "source": "a.pdf"}]
    agent = CoordinatorAgent(
        rag_tool=_StubRAG(passages),
        fact_extractor=extractor,
        fact_table=table,
        paper_analyzer_tool=PaperAnalyzerTool(fact_extractor=extractor, fact_table=table),
    )
    agent._node_observe({"query": "topik", "context": {}})
    assert [pid for _, pid in extractor.calls] == ["a.pdf", "a.pdf"]
