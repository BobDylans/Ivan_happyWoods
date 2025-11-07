#!/usr/bin/env python3
"""
DEPRECATED: Use Alembic migrations instead

This script is deprecated in favor of Alembic migrations.
Use the following command instead:
    alembic upgrade head

To create RAG tables specifically, ensure migration 002_add_rag_tables is applied.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print("=" * 70)
    print("⚠️  DEPRECATED: This script is no longer recommended")
    print("=" * 70)
    print()
    print("Please use Alembic migrations instead:")
    print()
    print("  1. To apply all migrations (including RAG tables):")
    print("     alembic upgrade head")
    print()
    print("  2. To check current migration status:")
    print("     alembic current")
    print()
    print("  3. To view migration history:")
    print("     alembic history")
    print()
    print("=" * 70)
    print()
    
    response = input("Do you want to run 'alembic upgrade head' now? (yes/no): ")
    
    if response.lower() == 'yes':
        print()
        print("Running Alembic migrations...")
        try:
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd=PROJECT_ROOT,
                check=True,
                capture_output=True,
                text=True
            )
            print("✅ Migrations completed successfully!")
            print()
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"❌ Migration failed: {e}")
            print(f"   stdout: {e.stdout}")
            print(f"   stderr: {e.stderr}")
            sys.exit(1)
        except FileNotFoundError:
            print("❌ Alembic not found. Please install: pip install alembic")
            sys.exit(1)
    else:
        print("Aborted by user.")
        sys.exit(0)


# Keep the old implementation but mark as deprecated
async def ensure_rag_tables_legacy(force_recreate: bool = False) -> None:
    """Legacy implementation - DO NOT USE"""
    sys.path.insert(0, str(PROJECT_ROOT / "src"))
    
    from config.settings import get_config
    from database.connection import close_db, init_db
    from database.models import Base, RAGCorpus, RAGDocument, RAGChunk
    
    print("⚠️  WARNING: Using legacy table creation method")
    print("   This bypasses Alembic migration tracking!")
    print()
    
    print("Loading configuration...")
    config = get_config()
    if not config.database.enabled:
        raise RuntimeError("Database is disabled in configuration")

    print("Initializing database engine...")
    engine, _ = await init_db(config, echo=False)
    if engine is None:
        raise RuntimeError("Failed to initialize database engine")

    if force_recreate:
        print("Dropping existing RAG tables...")
        async with engine.begin() as conn:
            await conn.run_sync(RAGChunk.__table__.drop, checkfirst=True)
            await conn.run_sync(RAGDocument.__table__.drop, checkfirst=True)
            await conn.run_sync(RAGCorpus.__table__.drop, checkfirst=True)

    print("Creating RAG tables...")
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

    await close_db(engine)
    print("✅ RAG tables are ready")


if __name__ == "__main__":
    main()

