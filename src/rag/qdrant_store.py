"""Utilities for interacting with Qdrant vector storage."""

from __future__ import annotations

import logging
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from qdrant_client import AsyncQdrantClient, models as qmodels

try:  # qdrant 1.15 moved exceptions to http.exceptions
    from qdrant_client.exceptions import UnexpectedResponse  # type: ignore
except ImportError:  # pragma: no cover
    from qdrant_client.http.exceptions import UnexpectedResponse  # type: ignore

from config.models import RAGConfig


logger = logging.getLogger(__name__)


@dataclass
class DocumentChunk:
    """Chunk of text ready to be stored in the vector database."""

    id: str
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]


@dataclass
class RetrievedChunk:
    """Result returned from the vector database."""

    text: str
    score: float
    metadata: Dict[str, Any]


class QdrantVectorStore:
    """High level wrapper around Qdrant client."""

    def __init__(self, config: RAGConfig, *, collection_name: Optional[str] = None):
        self.config = config
        self.collection_name = collection_name or config.collection
        self._client = AsyncQdrantClient(
            url=config.qdrant_url,
            api_key=config.qdrant_api_key or None,
            timeout=config.request_timeout,
        )

    def with_collection(self, name: str) -> "QdrantVectorStore":
        """Return a shallow clone bound to a different collection name."""

        clone = QdrantVectorStore(self.config, collection_name=name)
        clone._client = self._client  # share underlying client
        return clone

    async def ensure_collection(
        self,
        vector_size: int,
        *,
        collection_name: Optional[str] = None,
        recreate: bool = False,
    ) -> None:
        """Ensure the target collection exists with the expected vector size."""

        target_collection = collection_name or self.collection_name
        vector_params = qmodels.VectorParams(
            size=vector_size,
            distance=qmodels.Distance.COSINE,
        )

        if recreate:
            logger.info("♻️ Recreating Qdrant collection '%s'", target_collection)
            await self._client.recreate_collection(
                collection_name=target_collection,
                vectors_config=vector_params,
            )
            return

        try:
            await self._client.get_collection(target_collection)
        except UnexpectedResponse:
            logger.info("📦 Creating Qdrant collection '%s'", target_collection)
            await self._client.create_collection(
                collection_name=target_collection,
                vectors_config=vector_params,
            )

    async def upsert_chunks(
        self,
        chunks: Iterable[DocumentChunk],
        *,
        collection_name: Optional[str] = None,
    ) -> None:
        points = []
        for chunk in chunks:
            payload = {"text": chunk.text, **chunk.metadata}
            points.append(
                qmodels.PointStruct(
                    id=chunk.id,
                    vector=chunk.embedding,
                    payload=payload,
                )
            )

        if not points:
            return

        await self._client.upsert(
            collection_name=collection_name or self.collection_name,
            points=points,
        )

    async def search(
        self,
        query_embedding: List[float],
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        collection_name: Optional[str] = None,
    ) -> List[RetrievedChunk]:
        """Search similar vectors for the provided embedding."""

        result = await self._client.search(
            collection_name=collection_name or self.collection_name,
            query_vector=query_embedding,
            limit=top_k or self.config.top_k,
            score_threshold=min_score if min_score is not None else self.config.min_score,
            with_payload=True,
        )

        chunks: List[RetrievedChunk] = []
        for point in result:
            payload = point.payload or {}
            text = payload.get("text", "")
            chunks.append(
                RetrievedChunk(
                    text=text,
                    score=point.score or 0.0,
                    metadata=payload,
                )
            )

        return chunks

    async def close(self) -> None:
        close_method = getattr(self._client, "aclose", None)
        if callable(close_method):
            result = close_method()
            if asyncio.iscoroutine(result):
                await result
            return

        close_method = getattr(self._client, "close", None)
        if callable(close_method):
            result = close_method()
            if asyncio.iscoroutine(result):
                await result


