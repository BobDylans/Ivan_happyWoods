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

    user_id = args.user_id
    if config.rag.per_user_collections and not user_id:
        logger.error(
            "per_user_collections is enabled; please supply --user-id (UUID string)"
        )
        return

    if user_id and args.validate_uuid:
        from uuid import UUID

        try:
            UUID(user_id)
        except ValueError as exc:
            logger.error("--user-id must be a valid UUID: %s", exc)
            return

    display_names = {str(path): path.name for path in docs}

    try:
        result = await ingest_files(
            config,
            docs,
            user_id=user_id,
            corpus_name=args.corpus_name,
            corpus_description=args.corpus_description,
            corpus_id=args.corpus_id,
            collection_name=args.collection_name,
            display_names=display_names,
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
    parser.add_argument(
        "--user-id",
        type=str,
        default=None,
        help="User UUID owning the corpus (required when per_user_collections is enabled)",
    )
    parser.add_argument(
        "--corpus-name",
        type=str,
        default=None,
        help="Logical corpus name for this ingestion run (defaults to config.default_corpus_name)",
    )
    parser.add_argument(
        "--corpus-description",
        type=str,
        default=None,
        help="Optional human readable description stored alongside corpus metadata",
    )
    parser.add_argument(
        "--corpus-id",
        type=str,
        default=None,
        help="Optional custom corpus identifier used when building collection names",
    )
    parser.add_argument(
        "--collection-name",
        type=str,
        default=None,
        help="Force ingestion into a specific Qdrant collection (overrides template)",
    )
    parser.add_argument(
        "--no-uuid-validation",
        dest="validate_uuid",
        action="store_false",
        help="Skip UUID format validation for --user-id",
    )
    parser.set_defaults(validate_uuid=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(ingest_documents(args))


if __name__ == "__main__":
    main()


