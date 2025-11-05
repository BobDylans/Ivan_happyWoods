"""Offline ingestion script that populates Qdrant with documents from docs/."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from config.settings import get_config
from rag.ingestion import (
    DEFAULT_DOC_GLOBS,
    configure_proxy_bypass,
    ingest_files,
    load_documents,
    parse_glob_patterns,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("rag_ingest")


async def ingest_documents(args: argparse.Namespace) -> None:
    config = get_config()
    rag_cfg = config.rag

    if not rag_cfg.enabled:
        logger.error("RAG is disabled in configuration. Enable VOICE_AGENT_RAG__ENABLED first.")
        return

    configure_proxy_bypass(rag_cfg.qdrant_url)

    if args.docs_glob:
        patterns = parse_glob_patterns(args.docs_glob)
    elif getattr(rag_cfg, "doc_globs", None):
        patterns = [p for p in rag_cfg.doc_globs if p]
    else:
        patterns = parse_glob_patterns(rag_cfg.doc_glob)

    if not patterns:
        patterns = DEFAULT_DOC_GLOBS.copy()
    docs = load_documents(patterns)
    if not docs:
        logger.warning("No documents found for patterns: %s", ", ".join(patterns))
        return

    logger.info("Discovered %s documents for ingestion", len(docs))

    try:
        result = await ingest_files(
            config,
            docs,
            recreate=args.recreate,
            batch_size=args.batch_size,
        )
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc)
        raise
    else:
        logger.info(
            "Ingestion completed. Files=%s, chunks=%s, skipped=%s, failed=%s",
            result.processed_files,
            result.stored_chunks,
            len(result.skipped_files),
            len(result.failed_files),
        )
        for skipped in result.skipped_files:
            logger.warning("Skipped (no content): %s", skipped)
        for failed_path, error in result.failed_files:
            logger.error("Failed %s: %s", failed_path, error)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest documentation into Qdrant for RAG usage")
    parser.add_argument(
        "--docs-glob",
        type=str,
        help="Glob pattern(s) for documents. Separate multiple patterns with commas or semicolons.",
        default=None,
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=None,
        help="Embedding batch size override (defaults to VOICE_AGENT_RAG__INGEST_BATCH_SIZE)",
    )
    parser.add_argument("--recreate", action="store_true", help="Recreate the collection before ingesting")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(ingest_documents(args))


if __name__ == "__main__":
    main()


