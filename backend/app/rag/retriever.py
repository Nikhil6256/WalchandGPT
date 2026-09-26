"""
Hybrid retriever: combines pgvector ANN search + PostgreSQL trigram keyword search.
Results are deduplicated and reranked before returning to the LangGraph agent.
"""
import time
import uuid
from typing import Optional

import structlog
from langchain_core.documents import Document
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.llm.provider import get_embeddings
from app.models.document import DocumentChunk

log = structlog.get_logger(__name__)


class HybridRetriever:
    """
    Production retriever combining:
    1. Vector similarity search (pgvector cosine distance)
    2. Full-text keyword search (pg_trgm)
    3. Reciprocal Rank Fusion (RRF) reranking
    4. Metadata filtering (department, document_type)
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embeddings = get_embeddings()

    async def aretrieve(
        self,
        query: str,
        k: int = 5,
        department: Optional[str] = None,
        document_type: Optional[str] = None,
    ) -> list[Document]:
        """
        Retrieve top-k relevant chunks using hybrid search.
        Returns LangChain Document objects with metadata.
        """
        t0 = time.perf_counter()

        # 1. Embed the query
        try:
            query_embedding = await self.embeddings.aembed_query(query)
        except Exception as e:
            log.error("Embedding failed", error=str(e))
            return []

        # 2. Vector similarity search
        vector_results = await self._vector_search(
            query_embedding, k=k * 2, department=department, document_type=document_type
        )

        # 3. Keyword search using trigram similarity
        keyword_results = await self._keyword_search(
            query, k=k * 2, department=department
        )

        # 4. Reciprocal Rank Fusion
        merged = self._reciprocal_rank_fusion(
            [vector_results, keyword_results], k=k
        )

        elapsed = (time.perf_counter() - t0) * 1000
        log.info(
            "Retrieval complete",
            vector_count=len(vector_results),
            keyword_count=len(keyword_results),
            merged_count=len(merged),
            latency_ms=elapsed,
        )

        return merged[:k]

    async def _vector_search(
        self,
        embedding: list[float],
        k: int,
        department: Optional[str],
        document_type: Optional[str],
    ) -> list[Document]:
        """pgvector cosine similarity search."""
        # Build dynamic filter clause
        filters = ["dc.embedding IS NOT NULL"]
        if department:
            filters.append(f"d.department = '{department}'")
        if document_type:
            filters.append(f"d.document_type = '{document_type}'")

        where_clause = " AND ".join(filters)
        embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

        sql = text(f"""
            SELECT
                dc.id,
                dc.content,
                dc.chunk_metadata,
                dc.page_number,
                d.title as doc_title,
                d.id as doc_id,
                d.department,
                d.document_type,
                1 - (dc.embedding <=> '{embedding_str}'::vector) as similarity_score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE {where_clause}
                AND d.indexing_status = 'completed'
                AND 1 - (dc.embedding <=> '{embedding_str}'::vector) > :threshold
            ORDER BY dc.embedding <=> '{embedding_str}'::vector
            LIMIT :k
        """)

        result = await self.db.execute(
            sql, {"threshold": settings.SIMILARITY_THRESHOLD, "k": k}
        )
        rows = result.fetchall()

        return [
            Document(
                page_content=row.content,
                metadata={
                    "chunk_id": str(row.id),
                    "document_id": str(row.doc_id),
                    "title": row.doc_title,
                    "page_number": row.page_number,
                    "department": row.department,
                    "document_type": row.document_type,
                    "score": float(row.similarity_score),
                    "retrieval_method": "vector",
                },
            )
            for row in rows
        ]

    async def _keyword_search(
        self,
        query: str,
        k: int,
        department: Optional[str],
    ) -> list[Document]:
        """pg_trgm trigram keyword search for exact term matching."""
        filters = ["dc.embedding IS NOT NULL", "d.indexing_status = 'completed'"]
        params: dict = {"query": query, "k": k}

        if department:
            filters.append("d.department = :department")
            params["department"] = department

        where_clause = " AND ".join(filters)

        sql = text(f"""
            SELECT
                dc.id,
                dc.content,
                dc.chunk_metadata,
                dc.page_number,
                d.title as doc_title,
                d.id as doc_id,
                d.department,
                d.document_type,
                similarity(dc.content, :query) as sim_score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE {where_clause}
                AND similarity(dc.content, :query) > 0.1
            ORDER BY sim_score DESC
            LIMIT :k
        """)

        try:
            result = await self.db.execute(sql, params)
            rows = result.fetchall()
        except Exception as e:
            log.warning("Keyword search failed", error=str(e))
            return []

        return [
            Document(
                page_content=row.content,
                metadata={
                    "chunk_id": str(row.id),
                    "document_id": str(row.doc_id),
                    "title": row.doc_title,
                    "page_number": row.page_number,
                    "department": row.department,
                    "document_type": row.document_type,
                    "score": float(row.sim_score),
                    "retrieval_method": "keyword",
                },
            )
            for row in rows
        ]

    @staticmethod
    def _reciprocal_rank_fusion(
        result_lists: list[list[Document]],
        k: int = 5,
        rrf_k: int = 60,
    ) -> list[Document]:
        """
        Reciprocal Rank Fusion: merges multiple ranked lists into one.
        RRF score = sum(1 / (rank + rrf_k)) across all lists.
        Deduplicates by chunk_id.
        """
        scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}

        for result_list in result_lists:
            for rank, doc in enumerate(result_list):
                chunk_id = doc.metadata.get("chunk_id", doc.page_content[:50])
                rrf_score = 1.0 / (rank + 1 + rrf_k)
                scores[chunk_id] = scores.get(chunk_id, 0.0) + rrf_score
                doc_map[chunk_id] = doc

        # Sort by RRF score descending
        sorted_ids = sorted(scores, key=lambda x: scores[x], reverse=True)

        results = []
        for chunk_id in sorted_ids[:k]:
            doc = doc_map[chunk_id]
            doc.metadata["rrf_score"] = scores[chunk_id]
            results.append(doc)

        return results
