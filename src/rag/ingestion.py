"""Shared ingestion utilities for feeding documents into Qdrant."""

from __future__ import annotations

import logging
import os
import re
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse
from uuid import UUID

try:  # Optional dependencies handled gracefully
    from pypdf import PdfReader  # type: ignore
except ImportError:  # pragma: no cover - runtime fallback
    PdfReader = None  # type: ignore

try:
    from docx import Document  # type: ignore
except ImportError:  # pragma: no cover - runtime fallback
    Document = None  # type: ignore

from config.models import VoiceAgentConfig, RAGConfig

from .embedding_client import EmbeddingClient
from .qdrant_store import DocumentChunk, QdrantVectorStore
from .service import resolve_collection_name_from_config


logger = logging.getLogger(__name__)


DEFAULT_DOC_GLOBS = [
    "docs/**/*.md",
    "docs/**/*.pdf",
    "docs/**/*.docx",
]

SUPPORTED_SUFFIXES = {
    ".md",
    ".markdown",
    ".mdx",
    ".txt",
    ".pdf",
    ".docx",
}

GLOB_DELIMITER = re.compile(r"[;,\s]+")


@dataclass
class IngestionResult:
    """Aggregated statistics after an ingestion run."""

    processed_files: int = 0
    stored_chunks: int = 0
    skipped_files: List[str] = field(default_factory=list)
    failed_files: List[Tuple[str, str]] = field(default_factory=list)

    def merge(self, other: "IngestionResult") -> "IngestionResult":
        self.processed_files += other.processed_files
        self.stored_chunks += other.stored_chunks
        self.skipped_files.extend(other.skipped_files)
        self.failed_files.extend(other.failed_files)
        return self


def configure_proxy_bypass(qdrant_url: str) -> None:
    """Ensure localhost Qdrant traffic bypasses HTTP proxies."""

    parsed = urlparse(qdrant_url)
    host = parsed.hostname
    if not host:
        return

    entries = {host, "localhost", "127.0.0.1"}
    if parsed.port:
        entries.add(f"{host}:{parsed.port}")

    existing = os.environ.get("NO_PROXY") or os.environ.get("no_proxy")
    if existing:
        for item in existing.split(","):
            item = item.strip()
            if item:
                entries.add(item)

    value = ",".join(sorted(entries))
    os.environ["NO_PROXY"] = value
    os.environ["no_proxy"] = value
    logger.debug("NO_PROXY configured for Qdrant: %s", value)


def parse_glob_patterns(value: Optional[str]) -> List[str]:
    if not value:
        return DEFAULT_DOC_GLOBS.copy()
    if isinstance(value, str):
        patterns = [item.strip() for item in GLOB_DELIMITER.split(value) if item.strip()]
        return patterns or DEFAULT_DOC_GLOBS.copy()
    raise TypeError("doc_glob must be a string or None")


def load_documents(patterns: Sequence[str]) -> List[Path]:
    seen: Dict[Path, None] = {}
    cwd = Path.cwd()
    for pattern in patterns:
        for path in sorted(cwd.glob(pattern)):
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_SUFFIXES:
                logger.debug("Skipping unsupported file type: %s", path)
                continue
            seen[path.resolve()] = None
    return sorted(seen.keys())


def _ensure_dependency(name: str, available: bool) -> None:
    if not available:
        raise RuntimeError(
            f"Dependency '{name}' is required for this operation. "
            f"Install it via 'pip install {name}'."
        )


def _read_text_file(path: Path) -> Tuple[str, Dict[str, Any]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    metadata = {
        "source_type": path.suffix.lower().lstrip("."),
        "source_name": path.name,
    }
    return text, metadata


def _extract_pdf_text(path: Path, max_pages: Optional[int]) -> Tuple[str, Dict[str, Any]]:
    _ensure_dependency("pypdf", PdfReader is not None)
    try:
        reader = PdfReader(str(path), strict=False)  # Use non-strict mode to handle malformed PDFs
    except Exception as exc:
        raise ValueError(f"Failed to open PDF file: {exc}") from exc
    
    total_pages = len(reader.pages)
    limit = max_pages if max_pages is not None else total_pages
    limit = max(0, min(total_pages, limit))

    collected: List[str] = []
    for index in range(limit):
        try:
            page = reader.pages[index]
            text = page.extract_text() or ""
            collected.append(text)
        except Exception as exc:
            logger.warning("Failed to extract text from page %s of %s: %s", index + 1, path.name, exc)
            continue  # Skip problematic pages but continue with others

    metadata = {
        "source_type": "pdf",
        "source_name": path.name,
        "page_range": f"1-{limit}" if limit else "0",
        "page_count": len(collected),
        "total_pages": total_pages,
    }
    return "\n\n".join(collected), metadata


def _extract_docx_text(path: Path, max_paragraphs: Optional[int]) -> Tuple[str, Dict[str, Any]]:
    _ensure_dependency("python-docx", Document is not None)
    doc = Document(str(path))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text and p.text.strip()]
    total_paragraphs = len(paragraphs)
    if max_paragraphs is not None:
        paragraphs = paragraphs[:max_paragraphs]
    metadata = {
        "source_type": "docx",
        "source_name": path.name,
        "paragraph_count": len(paragraphs),
        "total_paragraphs": total_paragraphs,
    }
    return "\n\n".join(paragraphs), metadata


def extract_text_for_file(path: Path, rag_cfg: RAGConfig) -> Tuple[str, Dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".mdx", ".txt"}:
        return _read_text_file(path)
    if suffix == ".pdf":
        return _extract_pdf_text(path, rag_cfg.pdf_max_pages)
    if suffix == ".docx":
        return _extract_docx_text(path, rag_cfg.docx_max_paragraphs)
    raise ValueError(f"Unsupported file type for ingestion: {suffix}")


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    clean = re.sub(r"```[\s\S]*?```", "", text)
    clean = re.sub(r"[\r\t]", " ", clean)
    clean = re.sub(r"\s+", " ", clean)

    if not clean.strip():
        return []

    chunks: List[str] = []
    start = 0
    length = len(clean)
    while start < length:
        end = min(start + chunk_size, length)
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks


def create_chunks_for_file(path: Path, rag_cfg: RAGConfig) -> List[DocumentChunk]:
    text, metadata = extract_text_for_file(path, rag_cfg)

    if not text.strip():
        logger.warning("Skipping empty document: %s", path)
        return []

    metadata = {
        **metadata,
        "source": str(path),
        "source_name": path.name,
    }

    chunks = chunk_text(text, rag_cfg.chunk_size, rag_cfg.chunk_overlap)
    document_chunks: List[DocumentChunk] = []
    for idx, chunk_text_value in enumerate(chunks):
        document_chunks.append(
            DocumentChunk(
                id=str(uuid.uuid4()),
                text=chunk_text_value,
                embedding=[],
                metadata={**metadata, "chunk_index": idx},
            )
        )

    if not document_chunks:
        logger.warning("No chunks produced for %s", path)
    else:
        logger.debug("Prepared %s chunks from %s", len(document_chunks), path.name)

    return document_chunks


async def _flush_batch(
    batch: List[DocumentChunk],
    embedding_client: EmbeddingClient,
    vector_store: QdrantVectorStore,
    *,
    collection_name: Optional[str] = None,
    post_upsert: Optional[Callable[[List[DocumentChunk]], Awaitable[None]]] = None,
) -> None:
    """
    Embed a batch of chunks and upsert to Qdrant with comprehensive validation.
    
    This function performs multiple validation checks:
    1. Validates batch is not empty
    2. Validates embedding service returns correct number of vectors
    3. Validates each vector has correct dimensions and valid values
    4. Catches and logs detailed errors for debugging
    """
    if not batch:
        logger.warning("Empty batch provided to _flush_batch, skipping")
        return
    
    # Extract texts for embedding
    texts = [item.text for item in batch]
    
    # Validate all texts are non-empty
    for idx, text in enumerate(texts):
        if not text or not text.strip():
            raise ValueError(
                f"Chunk at index {idx} (ID: {batch[idx].id}) has empty text. "
                f"Cannot generate embedding for empty content."
            )
    
    logger.debug(f"Requesting embeddings for {len(texts)} text chunks")
    
    # Call embedding service
    try:
        embeddings = await embedding_client.embed_texts(texts)
    except Exception as e:
        logger.error(f"Embedding service failed: {e}")
        raise ValueError(f"Failed to generate embeddings: {e}") from e
    
    # Validate embedding service response
    if embeddings is None:
        raise ValueError("Embedding service returned None instead of a list of vectors")
    
    if not isinstance(embeddings, list):
        raise ValueError(
            f"Embedding service returned invalid type: {type(embeddings).__name__}. "
            f"Expected list of vectors."
        )
    
    if len(embeddings) != len(batch):
        raise ValueError(
            f"Embedding service returned unexpected number of vectors: "
            f"expected {len(batch)}, got {len(embeddings)}. "
            f"This indicates the embedding API may have failed silently."
        )
    
    # Validate and assign embeddings to chunks
    expected_dim = getattr(vector_store.config, "embed_dim", None)
    logger.debug(f"Expected embedding dimension: {expected_dim}")
    
    for idx, (chunk, embedding) in enumerate(zip(batch, embeddings)):
        # Check for None or empty embedding
        if embedding is None:
            raise ValueError(
                f"Chunk {chunk.id} (index {idx}) received None embedding from service. "
                f"Text preview: {chunk.text[:100]}..."
            )
        
        if not embedding:
            raise ValueError(
                f"Chunk {chunk.id} (index {idx}) received empty embedding vector from service. "
                f"Text length: {len(chunk.text)} chars"
            )
        
        if not isinstance(embedding, list):
            raise ValueError(
                f"Chunk {chunk.id} (index {idx}) received invalid embedding type: {type(embedding).__name__}"
            )
        
        # Check dimension
        actual_dim = len(embedding)
        if actual_dim == 0:
            raise ValueError(
                f"Chunk {chunk.id} (index {idx}) received zero-dimensional embedding. "
                f"This indicates embedding generation failed."
            )
        
        if expected_dim and actual_dim != expected_dim:
            raise ValueError(
                f"Chunk {chunk.id} (index {idx}) embedding dimension mismatch: "
                f"expected {expected_dim}, got {actual_dim}. "
                f"Model: {getattr(vector_store.config, 'embed_model', 'unknown')}"
            )
        
        # Validate embedding values
        try:
            for i, val in enumerate(embedding):
                if not isinstance(val, (int, float)):
                    raise ValueError(f"Non-numeric value at position {i}: {type(val).__name__}")
                # Check for NaN or Inf
                if val != val:  # NaN check
                    raise ValueError(f"NaN value at position {i}")
                if abs(val) == float('inf'):
                    raise ValueError(f"Infinite value at position {i}")
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Chunk {chunk.id} (index {idx}) has invalid embedding values: {e}"
            ) from e
        
        # Assign validated embedding
        chunk.embedding = embedding
        logger.debug(f"Validated embedding for chunk {chunk.id}: dim={actual_dim}")
    
    logger.info(f"All {len(batch)} embeddings validated successfully")
    
    # Upsert to Qdrant (this will perform additional validation)
    try:
        await vector_store.upsert_chunks(batch, collection_name=collection_name)
    except Exception as e:
        logger.error(
            f"Failed to upsert {len(batch)} chunks to Qdrant: {e}. "
            f"First chunk ID: {batch[0].id if batch else 'N/A'}"
        )
        raise
    
    # Call post-upsert callback if provided
    if post_upsert:
        try:
            await post_upsert(batch)
        except Exception as e:
            logger.warning(f"Post-upsert callback failed (non-fatal): {e}")


async def ingest_files(
    config: VoiceAgentConfig,
    files: Sequence[Path],
    *,
    user_id: Optional[str] = None,
    corpus_name: Optional[str] = None,
    corpus_description: Optional[str] = None,
    corpus_id: Optional[str] = None,
    collection_name: Optional[str] = None,
    display_names: Optional[Dict[str, str]] = None,
    recreate: bool = False,
    batch_size: Optional[int] = None,
    db_session: Optional[Any] = None,
) -> IngestionResult:
    """Ingest the provided files into Qdrant."""

    if not files:
        return IngestionResult()

    rag_cfg = config.rag
    if not rag_cfg.enabled:
        raise RuntimeError("RAG is disabled. Enable VOICE_AGENT_RAG__ENABLED to ingest documents.")

    batch_limit = batch_size or rag_cfg.ingest_batch_size or 16
    logger.info("Starting ingestion for %s files (batch=%s)", len(files), batch_limit)

    owner_uuid: Optional[UUID] = None
    if user_id:
        try:
            owner_uuid = UUID(user_id)
        except ValueError as exc:  # pragma: no cover - validation guard
            raise ValueError("user_id must be a valid UUID string") from exc
    elif rag_cfg.per_user_collections:
        raise ValueError("user_id is required when per-user collections are enabled")

    resolved_corpus_label = corpus_name or rag_cfg.default_corpus_name
    resolved_collection = resolve_collection_name_from_config(
        rag_cfg,
        user_id=user_id,
        corpus_id=corpus_id or resolved_corpus_label,
        collection_name=collection_name,
    )

    embedding_client = EmbeddingClient(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        model=rag_cfg.embed_model,
        timeout=rag_cfg.request_timeout,
    )
    vector_store = QdrantVectorStore(rag_cfg, collection_name=resolved_collection)

    result = IngestionResult()
    exit_stack = AsyncExitStack()
    rag_repo = None
    corpus_record = None
    ingestion_error: Optional[Exception] = None

    session = db_session  # Use provided session if available
    if owner_uuid and config.database.enabled and session:
        try:
            from database.repositories.rag_repository import RAGRepository  # type: ignore
            from database.repositories.user_repository import UserRepository  # type: ignore

            user_repo = UserRepository(session)
            existing_user = await user_repo.get_user_by_id(owner_uuid)
            if existing_user is None:
                ingestion_error = ValueError(
                    f"User {owner_uuid} does not exist; cannot ingest documents."
                )
                if session.in_transaction():
                    await session.rollback()
            else:
                rag_repo = RAGRepository(session)
                corpus_record = await rag_repo.get_or_create_corpus(
                    user_id=owner_uuid,
                    name=resolved_corpus_label,
                    description=corpus_description,
                    collection_name=resolved_collection,
                    metadata={"collection": resolved_collection},
                )
        except Exception as exc:  # pragma: no cover - optional DB path
            if session is not None and session.in_transaction():
                await session.rollback()
            if ingestion_error is None:
                logger.warning("RAG metadata persistence disabled: %s", exc)
            rag_repo = None
            corpus_record = None
    elif owner_uuid and config.database.enabled and not session:
        logger.info("RAG metadata persistence skipped: no database session provided")

    try:
        if ingestion_error:
            raise ingestion_error
        await vector_store.ensure_collection(
            rag_cfg.embed_dim,
            collection_name=resolved_collection,
            recreate=recreate,
        )

        for path in files:
            try:
                chunks = create_chunks_for_file(path, rag_cfg)
            except Exception as exc:  # pragma: no cover - runtime path
                logger.error("Failed to load %s: %s", path, exc)
                result.failed_files.append((str(path), str(exc)))
                continue

            if not chunks:
                result.skipped_files.append(str(path))
                continue

            display_name = None
            if display_names:
                display_name = display_names.get(str(path)) or display_names.get(path.name)
            display_name = display_name or path.name

            document_uuid = uuid.uuid4()
            resolved_document_id = str(document_uuid)
            resolved_corpus_id = (
                str(corpus_record.corpus_id)
                if corpus_record is not None
                else corpus_id
                if corpus_id is not None
                else resolved_corpus_label
            )

            for idx, chunk in enumerate(chunks):
                chunk.metadata.update(
                    {
                        "owner_id": user_id,
                        "corpus_id": resolved_corpus_id,
                        "collection_name": resolved_collection,
                        "document_id": resolved_document_id,
                        "chunk_index": chunk.metadata.get("chunk_index", idx),
                        "source_display": display_name,
                    }
                )

            document_record = None
            if rag_repo and corpus_record and owner_uuid:
                try:
                    document_record = await rag_repo.create_document(
                        corpus=corpus_record,
                        user_id=owner_uuid,
                        display_name=display_name,
                        source_path=str(path),
                        source_url=None,
                        checksum=None,
                        size_bytes=path.stat().st_size if path.exists() else None,
                        mime_type=path.suffix.lstrip(".") if path.suffix else None,
                        metadata={
                            "document_id": resolved_document_id,
                            "corpus_id": resolved_corpus_id,
                            "collection": resolved_collection,
                        },
                    )
                except Exception as exc:  # pragma: no cover
                    logger.warning("Failed to record RAG document metadata: %s", exc)
                    document_record = None

            async def persist_batch(batch_slice: List[DocumentChunk]) -> None:
                if not (rag_repo and corpus_record and document_record and owner_uuid):
                    return
                try:
                    points = [
                        {
                            "id": chunk.id,
                            "chunk_index": chunk.metadata.get("chunk_index", 0),
                            "text_preview": chunk.text[:200],
                            "metadata": chunk.metadata,
                        }
                        for chunk in batch_slice
                    ]
                    await rag_repo.create_chunks(
                        document=document_record,
                        corpus=corpus_record,
                        user_id=owner_uuid,
                        points=points,
                    )
                except Exception as exc:  # pragma: no cover
                    logger.warning("Failed to record chunk metadata: %s", exc)

            chunk_batches = [
                chunks[index : index + batch_limit] for index in range(0, len(chunks), batch_limit)
            ]
            for chunk_batch in chunk_batches:
                await _flush_batch(
                    chunk_batch,
                    embedding_client,
                    vector_store,
                    collection_name=resolved_collection,
                    post_upsert=persist_batch,
                )
                result.stored_chunks += len(chunk_batch)

            result.processed_files += 1

        logger.info(
            "Ingestion finished. Files=%s, chunks=%s, skipped=%s, failed=%s",
            result.processed_files,
            result.stored_chunks,
            len(result.skipped_files),
            len(result.failed_files),
        )

        return result

    finally:
        await embedding_client.aclose()
        await vector_store.close()
        await exit_stack.aclose()


__all__ = [
    "DEFAULT_DOC_GLOBS",
    "SUPPORTED_SUFFIXES",
    "IngestionResult",
    "configure_proxy_bypass",
    "parse_glob_patterns",
    "load_documents",
    "extract_text_for_file",
    "chunk_text",
    "create_chunks_for_file",
    "ingest_files",
]

