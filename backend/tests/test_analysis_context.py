from app.core.runtime.analysis_context import ScopedRAGRetriever
from app.core.retrieval.rag_retriever import RAGRetriever


def test_scoped_retriever_enforces_job_filter(monkeypatch):
    captured = {}

    def fake_retrieve(self, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(RAGRetriever, "retrieve", fake_retrieve)
    retriever = ScopedRAGRetriever(
        vector_store=object(),
        top_k=5,
        min_relevance_score=0.1,
        analysis_job_id="job-a",
    )

    retriever.retrieve("topic", filter_metadata={"source": "paper.pdf"})

    assert captured["filter_metadata"] == {
        "$and": [
            {"analysis_job_id": "job-a"},
            {"source": "paper.pdf"},
        ]
    }


def test_ephemeral_scoped_retriever_preserves_intentional_corpus_filter(monkeypatch):
    captured = {}

    def fake_retrieve(self, **kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(RAGRetriever, "retrieve", fake_retrieve)
    retriever = ScopedRAGRetriever(
        vector_store=object(),
        top_k=5,
        min_relevance_score=0.1,
        analysis_job_id=None,
    )

    retriever.retrieve("topic", filter_metadata={"year": 2025})

    assert captured["filter_metadata"] == {"year": 2025}
