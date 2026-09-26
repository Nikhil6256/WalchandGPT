"""Unit tests for RAG retriever — Reciprocal Rank Fusion."""
import pytest
from langchain_core.documents import Document

from app.rag.retriever import HybridRetriever


def make_doc(chunk_id: str, score: float) -> Document:
    return Document(
        page_content=f"Content for {chunk_id}",
        metadata={"chunk_id": chunk_id, "score": score, "title": "Test", "document_id": "doc1"}
    )


class TestReciprocalRankFusion:
    def test_deduplicates_across_lists(self):
        """Same chunk appearing in both vector and keyword results should appear once."""
        vector_results = [make_doc("a", 0.9), make_doc("b", 0.7)]
        keyword_results = [make_doc("b", 0.8), make_doc("c", 0.6)]

        merged = HybridRetriever._reciprocal_rank_fusion(
            [vector_results, keyword_results], k=5
        )
        ids = [d.metadata["chunk_id"] for d in merged]
        assert len(ids) == len(set(ids)), "Duplicates should be removed"
        assert len(merged) == 3  # a, b, c

    def test_shared_document_gets_higher_score(self):
        """A doc appearing in both lists should rank higher than one in only one."""
        vector_results = [make_doc("a", 0.5), make_doc("shared", 0.4)]
        keyword_results = [make_doc("shared", 0.9), make_doc("c", 0.3)]

        merged = HybridRetriever._reciprocal_rank_fusion(
            [vector_results, keyword_results], k=5
        )
        ids = [d.metadata["chunk_id"] for d in merged]
        # "shared" appears in both lists so it should be first
        assert ids[0] == "shared"

    def test_respects_k_limit(self):
        docs = [make_doc(f"doc{i}", 0.9 - i * 0.1) for i in range(10)]
        merged = HybridRetriever._reciprocal_rank_fusion([docs], k=3)
        assert len(merged) <= 3

    def test_handles_empty_lists(self):
        merged = HybridRetriever._reciprocal_rank_fusion([[], []], k=5)
        assert merged == []
