"""Shared ingestion utilities for feeding documents into Qdrant."""

from __future__ import annotations

import logging
import os
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

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
    reader = PdfReader(str(path))
    total_pages = len(reader.pages)
    limit = max_pages if max_pages is not None else total_pages
    limit = max(0, min(total_pages, limit))

    collected: List[str] = []
    for index in range(limit):
        page = reader.pages[index]
        text = page.extract_text() or ""
        collected.append(text)

    metadata = {
        "source_type": "pdf",
        "source_name": path.name,
        "page_range": f"1-{limit}" if limit else "0",
        "page_count": limit,
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
) -> None:
    texts = [item.text for item in batch]
    embeddings = await embedding_client.embed_texts(texts)
    for chunk, embedding in zip(batch, embeddings):
        chunk.embedding = embedding
    await vector_store.upsert_chunks(batch)


async def ingest_files(
    config: VoiceAgentConfig,
    files: Sequence[Path],
    *,
    recreate: bool = False,
    batch_size: Optional[int] = None,
) -> IngestionResult:
    """Ingest the provided files into Qdrant."""

    if not files:
        return IngestionResult()

    rag_cfg = config.rag
    if not rag_cfg.enabled:
        raise RuntimeError("RAG is disabled. Enable VOICE_AGENT_RAG__ENABLED to ingest documents.")

    batch_limit = batch_size or rag_cfg.ingest_batch_size or 16
    logger.info("Starting ingestion for %s files (batch=%s)", len(files), batch_limit)

    embedding_client = EmbeddingClient(
        base_url=config.llm.base_url,
        api_key=config.llm.api_key,
        model=rag_cfg.embed_model,
        timeout=rag_cfg.request_timeout,
    )
    vector_store = QdrantVectorStore(rag_cfg)

    result = IngestionResult()
    batch: List[DocumentChunk] = []

    try:
        await vector_store.ensure_collection(rag_cfg.embed_dim, recreate=recreate)

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

            batch.extend(chunks)
            result.processed_files += 1

            if len(batch) >= batch_limit:
                await _flush_batch(batch, embedding_client, vector_store)
                result.stored_chunks += len(batch)
                batch.clear()

        if batch:
            await _flush_batch(batch, embedding_client, vector_store)
            result.stored_chunks += len(batch)

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

