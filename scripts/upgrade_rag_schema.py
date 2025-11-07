#!/usr/bin/env python3
"""Ensure the new RAG tables exist in the database."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config.settings import get_config
from database.connection import close_db, init_db
from database.models import Base, RAGCorpus, RAGDocument, RAGChunk


async def ensure_rag_tables(force_recreate: bool = False) -> None:
    print("Loading configuration...")
    config = get_config()
    if not config.database.enabled:
        raise RuntimeError("Database is disabled in configuration")

    print("Initializing database engine...")
    engine = await init_db(config.database, echo=False)
    if engine is None:
        raise RuntimeError("Failed to initialize database engine")

    if force_recreate:
        print("Dropping existing RAG tables...")
    if force_recreate:
        async with engine.begin() as conn:
            await conn.run_sync(RAGChunk.__table__.drop, checkfirst=True)
            await conn.run_sync(RAGDocument.__table__.drop, checkfirst=True)
            await conn.run_sync(RAGCorpus.__table__.drop, checkfirst=True)

    print("Ensuring RAG tables exist...")
    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                RAGCorpus.__table__,
                RAGDocument.__table__,
                RAGChunk.__table__,
            ],
            checkfirst=True,
        )

    await close_db()
    print("✅ RAG tables are ready")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create/upgrade RAG metadata tables")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Drop the RAG tables first (destroys all RAG metadata)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(ensure_rag_tables(force_recreate=args.recreate))
    except Exception as exc:
        print(f"❌ Failed to upgrade RAG schema: {exc}")
        sys.exit(1)

    print("Done.")


if __name__ == "__main__":
    main()

