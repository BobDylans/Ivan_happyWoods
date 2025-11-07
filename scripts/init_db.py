#!/usr/bin/env python3
"""
Database Initialization Script

This script initializes the PostgreSQL database for the Voice Agent system.
It uses Alembic for schema migrations and optionally loads test data.

Usage:
    python scripts/init_db.py [--drop] [--test-data]
    
Options:
    --drop: Drop existing tables before creating (WARNING: destroys all data)
    --test-data: Load sample test data after initialization
    
Note:
    This script now uses Alembic migrations for database schema management.
    Run `alembic upgrade head` to apply all migrations.
"""

import asyncio
import argparse
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from database.connection import init_db, drop_tables, close_db, check_db_health
from database.models import Base
from config.settings import get_config


async def initialize_database(drop_existing: bool = False, load_test_data: bool = False):
    """
    Initialize the database with all tables and optionally test data.
    
    Args:
        drop_existing: Whether to drop existing tables first
        load_test_data: Whether to load test data
    """
    print("=" * 70)
    print("Voice Agent Database Initialization")
    print("=" * 70)
    print()
    
    # Load configuration
    print("Loading configuration...")
    try:
        config = get_config()
        if not config.database.enabled:
            print("❌ Database is not enabled in configuration!")
            print("   Set database.enabled=true in config/base.yaml or")
            print("   set VOICE_AGENT_DATABASE__ENABLED=true in .env")
            return False
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return False
    
    print(f"✅ Configuration loaded")
    print(f"   Database: {config.database.database}")
    print(f"   Host: {config.database.host}:{config.database.port}")
    print(f"   User: {config.database.user}")
    print()
    
    # Initialize database connection
    print("Initializing database connection...")
    try:
        await init_db(config.database, echo=True)
        print("✅ Database connection initialized")
    except Exception as e:
        print(f"❌ Failed to initialize database connection: {e}")
        print()
        print("Make sure PostgreSQL is running:")
        print("  docker-compose up -d postgres")
        return False
    
    # Check database health
    print()
    print("Checking database connectivity...")
    try:
        is_healthy = await check_db_health()
        if not is_healthy:
            print("❌ Database health check failed")
            return False
        print("✅ Database is reachable")
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return False
    
    # Drop existing tables if requested
    if drop_existing:
        print()
        print("⚠️  Dropping existing tables...")
        confirmation = input("This will delete ALL data! Type 'yes' to confirm: ")
        if confirmation.lower() == 'yes':
            try:
                await drop_tables()
                print("✅ Existing tables dropped")
                print()
                print("Resetting Alembic migration history...")
                try:
                    # Reset alembic version table
                    subprocess.run(
                        ["alembic", "stamp", "base"],
                        cwd=project_root,
                        check=True,
                        capture_output=True
                    )
                    print("✅ Alembic history reset")
                except subprocess.CalledProcessError as e:
                    print(f"⚠️  Warning: Could not reset Alembic history: {e}")
            except Exception as e:
                print(f"❌ Failed to drop tables: {e}")
                return False
        else:
            print("❌ Aborted by user")
            return False
    
    # Create tables using Alembic migrations
    print()
    print("Running Alembic migrations...")
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=project_root,
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Database schema created successfully via Alembic")
        print()
        print("Applied migrations:")
        # Parse alembic output to show which migrations were applied
        for line in result.stdout.split('\n'):
            if 'Running upgrade' in line or 'INFO' in line:
                print(f"  {line.strip()}")
        print()
        print("Created tables:")
        print("  - users (with authentication fields)")
        print("  - sessions")
        print("  - messages")
        print("  - tool_calls")
        print("  - rag_corpora")
        print("  - rag_documents")
        print("  - rag_chunks")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to run Alembic migrations: {e}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        print()
        print("Troubleshooting:")
        print("1. Make sure Alembic is installed: pip install alembic")
        print("2. Check alembic.ini configuration")
        print("3. Run manually: alembic upgrade head")
        return False
    except FileNotFoundError:
        print("❌ Alembic not found. Please install: pip install alembic")
        return False
    
    # Load test data if requested
    if load_test_data:
        print()
        print("Loading test data...")
        try:
            await load_sample_data()
            print("✅ Test data loaded")
        except Exception as e:
            print(f"❌ Failed to load test data: {e}")
            return False
    
    # Close database connection
    await close_db()
    
    print()
    print("=" * 70)
    print("✅ Database initialization complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("1. Update .env file with database credentials")
    print("2. Set VOICE_AGENT_DATABASE__ENABLED=true")
    print("3. Set VOICE_AGENT_SESSION__STORAGE_TYPE=database")
    print("4. Start the application: python start_server.py")
    print()
    
    return True


async def load_sample_data():
    """Load sample test data into the database."""
    import uuid
    from datetime import datetime, timedelta
    from database.connection import get_async_session
    from database.models import User, Session, Message
    
    async with get_async_session() as session:
        # Create test user
        test_user = User(
            id=uuid.uuid4(),
            username="test_user",
            metadata={
                "email": "test@example.com",
                "preferences": {
                    "language": "zh-CN",
                    "voice": "x5_lingxiaoxuan_flow"
                }
            }
        )
        session.add(test_user)
        await session.flush()
        
        # Create test session
        test_session = Session(
            session_id="test_session_001",
            user_id=test_user.id,
            status="ACTIVE",
            metadata={"source": "test_data"}
        )
        session.add(test_session)
        await session.flush()
        
        # Create test messages
        messages = [
            Message(
                session_id=test_session.session_id,
                role="USER",
                content="你好，请介绍一下自己",
                timestamp=datetime.utcnow() - timedelta(minutes=5),
                metadata={"source": "test"}
            ),
            Message(
                session_id=test_session.session_id,
                role="ASSISTANT",
                content="你好！我是语音助手，可以帮助你进行语音对话。",
                timestamp=datetime.utcnow() - timedelta(minutes=4, seconds=50),
                metadata={"source": "test"}
            ),
            Message(
                session_id=test_session.session_id,
                role="USER",
                content="帮我计算 123 + 456",
                timestamp=datetime.utcnow() - timedelta(minutes=3),
                metadata={"source": "test"}
            ),
            Message(
                session_id=test_session.session_id,
                role="ASSISTANT",
                content="123 + 456 = 579",
                timestamp=datetime.utcnow() - timedelta(minutes=2, seconds=55),
                metadata={"source": "test", "tool_used": "calculator"}
            ),
        ]
        
        for msg in messages:
            session.add(msg)
        
        await session.commit()
        
        print(f"  Created 1 user: {test_user.username}")
        print(f"  Created 1 session: {test_session.session_id}")
        print(f"  Created {len(messages)} messages")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Initialize Voice Agent database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "--drop",
        action="store_true",
        help="Drop existing tables before creating (destroys all data)"
    )
    parser.add_argument(
        "--test-data",
        action="store_true",
        help="Load sample test data after initialization"
    )
    
    args = parser.parse_args()
    
    # Run async initialization
    success = asyncio.run(initialize_database(
        drop_existing=args.drop,
        load_test_data=args.test_data
    ))
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

