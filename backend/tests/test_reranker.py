"""
Unit tests for the cross-encoder reranker and its integration with the
RAG retriever's two-stage retrieval — all without downloading model weights
(the CrossEncoder is mocked).
"""

from unittest.mock import MagicMock

from app.core.retrieval.reranker import CrossEncoderReranker
from app.core.retrieval.rag_retriever import RAGRetriever, RetrievalResult
from app.core.retrieval.vector_store import Document


# ===================================================================
# CrossEncoderReranker
# ===================================================================

class TestCrossEncoderReranker:
    def test_unavailable_returns_none(self):
        """When the model can't load, scoring/reranking degrade to None."""
        rr = CrossEncoderReranker(model_name="does-not-exist/model")
        # Force the load attempt to fail deterministically.
        rr._loaded = True
        rr._model = None
        assert rr.available is False
        assert rr.score("q", ["a", "b"]) is None
        assert rr.rerank("q", ["a", "b"]) is None

    def test_rerank_orders_by_score(self):
        """rerank() returns (orig_index, score) sorted by descending relevance."""
        rr = CrossEncoderReranker()
        rr._loaded = True
        rr._model = MagicMock()
        # Passage 1 is most relevant, passage 0 least.
        rr._model.predict.return_value = [0.1, 0.9, 0.5]

        ranked = rr.rerank("query", ["p0", "p1", "p2"])
        assert [idx for idx, _ in ranked] == [1, 2, 0]
        assert ranked[0][1] == 0.9

    def test_rerank_top_k(self):
        rr = CrossEncoderReranker()
        rr._loaded = True
        rr._model = MagicMock()
        rr._model.predict.return_value = [0.2, 0.8, 0.5, 0.1]
        ranked = rr.rerank("query", ["a", "b", "c", "d"], top_k=2)
        assert len(ranked) == 2
        assert [idx for idx, _ in ranked] == [1, 2]

    def test_empty_passages(self):
        rr = CrossEncoderReranker()
        rr._loaded = True
        rr._model = MagicMock()
        assert rr.score("q", []) is None


# ===================================================================
# RAGRetriever integration
# ===================================================================

def _make_result(content, score, **metadata):
    return RetrievalResult(
        document=Document(id=metadata.get("id", content[:8]), content=content, metadata=metadata),
        score=score,
        rank=0,
    )


class TestRetrieverReranking:
    def test_cross_encoder_reorders_and_preserves_bi_score(self):
        """Cross-encoder path reorders results and records the bi-encoder score."""
        reranker = MagicMock()
        # Return order: original index 2 first, then 0, then 1.
        reranker.rerank.return_value = [(2, 9.0), (0, 5.0), (1, -3.0)]
        retriever = RAGRetriever(vector_store=MagicMock(), reranker=reranker)

        results = [
            _make_result("first", 0.40),
            _make_result("second", 0.35),
            _make_result("third", 0.30),
        ]
        out = retriever._rerank_results("query", results)

        assert [r.document.content for r in out] == ["third", "first", "second"]
        assert out[0].rank == 1 and out[0].score == 9.0
        # Original bi-encoder score preserved for traceability.
        assert out[0].document.metadata["bi_encoder_score"] == 0.30

    def test_falls_back_to_heuristic_when_reranker_none(self):
        """With no reranker, the heuristic reranker is used (no crash)."""
        retriever = RAGRetriever(vector_store=MagicMock(), reranker=None)
        results = [
            _make_result("alpha beta", 0.5, title="T", year=2020),
            _make_result("gamma", 0.4),
        ]
        out = retriever._rerank_results("alpha beta", results)
        assert len(out) == 2
        # Higher base score + term overlap + metadata bonus stays on top.
        assert out[0].document.content == "alpha beta"
        assert out[0].rank == 1

    def test_falls_back_when_cross_encoder_returns_none(self):
        """If the cross-encoder is unavailable at call time, use the heuristic."""
        reranker = MagicMock()
        reranker.rerank.return_value = None
        retriever = RAGRetriever(vector_store=MagicMock(), reranker=reranker)
        results = [_make_result("alpha", 0.6), _make_result("beta", 0.5)]
        out = retriever._rerank_results("alpha", results)
        assert len(out) == 2
        assert out[0].rank == 1
