"""RAG service that ties together embedding and vector store operations."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from config.models import VoiceAgentConfig

from .embedding_client import EmbeddingClient
from .qdrant_store import QdrantVectorStore, RetrievedChunk


def _sanitize_component(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-_")
    return cleaned or fallback


def resolve_collection_name_from_config(
    rag_cfg,
    *,
    user_id: Optional[str],
    corpus_id: Optional[str] = None,
    collection_name: Optional[str] = None,
) -> str:
    if collection_name:
        return collection_name

    if not rag_cfg.per_user_collections:
        return rag_cfg.collection

    if not user_id:
        raise ValueError("user_id is required when per_user_collections is enabled")

    sanitized_user = _sanitize_component(user_id, "anon")
    sanitized_corpus = _sanitize_component(
        corpus_id or rag_cfg.default_corpus_name,
        rag_cfg.default_corpus_name,
    )

    name = rag_cfg.collection_name_template.format(
        collection=rag_cfg.collection,
        user_id=sanitized_user,
        corpus_id=sanitized_corpus,
    )
    return name.lower()


logger = logging.getLogger(__name__)


@dataclass
class RAGResult:
    """Normalized RAG retrieval result for the agent."""

    text: str
    score: float
    source: Optional[str]
    metadata: Dict[str, Optional[str]]

    def to_metadata(self) -> Dict[str, Optional[str]]:
        data = {
            "score": round(self.score, 4),
            "source": self.source,
        }
        data.update(self.metadata)
        return data


class RAGService:
    """High level interface combining embedding generation and vector search."""

    def __init__(self, config: VoiceAgentConfig):
        self._config = config.rag
        self._enabled = self._config.enabled
        if not self._enabled:
            logger.info("RAG service disabled via configuration")
            self._embedding_client = None
            self._vector_store = None
            return

        logger.info(
            "Initializing RAG service with model '%s' and collection '%s'",
            self._config.embed_model,
            self._config.collection,
        )

        self._embedding_client = EmbeddingClient(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key,
            model=self._config.embed_model,
            timeout=self._config.request_timeout,
        )

        self._vector_store = QdrantVectorStore(self._config)

    # ------------------------------------------------------------------
    # Collection helpers
    # ------------------------------------------------------------------
    def resolve_collection_name(
        self,
        *,
        user_id: Optional[str],
        corpus_id: Optional[str] = None,
        collection_name: Optional[str] = None,
    ) -> str:
        return resolve_collection_name_from_config(
            self._config,
            user_id=user_id,
            corpus_id=corpus_id,
            collection_name=collection_name,
        )

    async def ensure_collection(
        self,
        *,
        user_id: Optional[str],
        corpus_id: Optional[str] = None,
        collection_name: Optional[str] = None,
        recreate: bool = False,
    ) -> str:
        resolved = self.resolve_collection_name(
            user_id=user_id,
            corpus_id=corpus_id,
            collection_name=collection_name,
        )
        await self._vector_store.ensure_collection(
            self._config.embed_dim,
            collection_name=resolved,
            recreate=recreate,
        )
        return resolved

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def retrieve(
        self,
        query: str,
        *,
        user_id: Optional[str],
        corpus_id: Optional[str] = None,
        collection_name: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> List[RAGResult]:
        if not self.enabled or not query.strip():
            return []

        embeddings = await self._embedding_client.embed_texts([query])
        if not embeddings:
            logger.warning("Embedding API returned no vectors for query")
            return []

        expected_dim = self._config.embed_dim
        query_vector = embeddings[0]
        if not query_vector:
            raise ValueError("Embedding API returned an empty vector for the query")
        if expected_dim and len(query_vector) != expected_dim:
            raise ValueError(
                "Embedding dimensionality mismatch for query: "
                f"expected {expected_dim}, got {len(query_vector)}"
            )

        resolved_collection = await self.ensure_collection(
            user_id=user_id,
            corpus_id=corpus_id,
            collection_name=collection_name,
            recreate=False,
        )

        results = await self._vector_store.search(
            query_embedding=query_vector,
            top_k=top_k or self._config.top_k,
            min_score=self._config.min_score,
            collection_name=resolved_collection,
        )

        formatted: List[RAGResult] = []
        for item in results:
            source = item.metadata.get("source") if item.metadata else None
            formatted.append(
                RAGResult(
                    text=item.text,
                    score=item.score,
                    source=source,
                    metadata={k: str(v) for k, v in (item.metadata or {}).items() if k != "text"},
                )
            )

        return formatted

    async def close(self) -> None:
        if self._embedding_client:
            await self._embedding_client.aclose()
        if self._vector_store:
            await self._vector_store.close()

    # ------------------------------------------------------------------
    # Prompt helpers
    # ------------------------------------------------------------------

    def build_prompt(self, results: List[RAGResult]) -> str:
        """Format retrieved snippets into a prompt for the LLM."""

        if not results:
            return ""

        lines: List[str] = [
            "你可以参考以下知识片段进行回答。如信息与实时事实冲突，请优先使用最新事实：",
        ]

        for idx, item in enumerate(results, start=1):
            header = f"[{idx}] 来源: {item.source or 'Unknown'} (score={item.score:.3f})"
            lines.append(header)
            lines.append(item.text.strip())
            lines.append("")

        return "\n".join(lines).strip()


