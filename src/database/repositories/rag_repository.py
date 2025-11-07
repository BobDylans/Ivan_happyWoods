"""RAG repository helpers for per-user corpus management."""

from __future__ import annotations

import logging
from typing import Dict, Any, Iterable, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import RAGCorpus, RAGDocument, RAGChunk


logger = logging.getLogger(__name__)


class RAGRepository:
    """Data access layer for RAG metadata objects."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_corpus(
        self,
        *,
        user_id: UUID,
        name: str,
        collection_name: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RAGCorpus:
        query = select(RAGCorpus).where(
            RAGCorpus.user_id == user_id,
            RAGCorpus.collection_name == collection_name,
        )
        result = await self.session.execute(query)
        corpus = result.scalar_one_or_none()
        if corpus:
            return corpus

        corpus = RAGCorpus(
            corpus_id=uuid4(),
            user_id=user_id,
            name=name,
            description=description,
            collection_name=collection_name,
            meta_data=metadata or {},
        )
        self.session.add(corpus)
        await self.session.flush()
        logger.info("Created RAG corpus %s for user %s", corpus.corpus_id, user_id)
        return corpus

    async def create_document(
        self,
        *,
        corpus: RAGCorpus,
        user_id: UUID,
        display_name: str,
        source_path: Optional[str],
        source_url: Optional[str],
        checksum: Optional[str],
        size_bytes: Optional[int],
        mime_type: Optional[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RAGDocument:
        document = RAGDocument(
            document_id=uuid4(),
            corpus_id=corpus.corpus_id,
            user_id=user_id,
            display_name=display_name,
            source_path=source_path,
            source_url=source_url,
            checksum=checksum,
            size_bytes=size_bytes,
            mime_type=mime_type,
            meta_data=metadata or {},
        )
        self.session.add(document)
        await self.session.flush()
        logger.debug(
            "Recorded RAG document %s (%s) in corpus %s",
            document.document_id,
            display_name,
            corpus.corpus_id,
        )
        return document

    async def create_chunks(
        self,
        *,
        document: RAGDocument,
        corpus: RAGCorpus,
        user_id: UUID,
        points: Iterable[Dict[str, Any]],
    ) -> List[RAGChunk]:
        chunks: List[RAGChunk] = []
        for point in points:
            chunk = RAGChunk(
                chunk_id=uuid4(),
                document_id=document.document_id,
                corpus_id=corpus.corpus_id,
                user_id=user_id,
                point_id=str(point["id"]),
                chunk_index=int(point.get("chunk_index", 0)),
                text_preview=point.get("text_preview"),
                meta_data=point.get("metadata", {}),
            )
            self.session.add(chunk)
            chunks.append(chunk)

        if chunks:
            await self.session.flush()
        return chunks

