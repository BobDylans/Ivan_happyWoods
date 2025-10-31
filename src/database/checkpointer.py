"""
PostgreSQL Checkpointer for LangGraph

Implements BaseCheckpointSaver to persist LangGraph state to PostgreSQL.
"""

import logging
import pickle
from typing import Optional, Dict, Any, Iterator, Tuple
from datetime import datetime

from langgraph.checkpoint.base import BaseCheckpointSaver, Checkpoint, CheckpointMetadata

from .connection import get_async_session
from sqlalchemy import Column, String, DateTime, LargeBinary, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from .models import Base

logger = logging.getLogger(__name__)

# 也就是graph在运行时，会保存一些状态，这些状态会保存在数据库中
# 可以保证对话的流畅
class CheckpointModel(Base):
    """Database model for storing LangGraph checkpoints."""
    
    __tablename__ = "langgraph_checkpoints"
    
    # Composite key: thread_id + checkpoint_id
    thread_id = Column(String(255), primary_key=True, index=True)
    checkpoint_id = Column(String(255), primary_key=True)
    
    # Checkpoint data
    checkpoint_data = Column(LargeBinary, nullable=False)  # Pickled checkpoint
    # 使用 meta_data 作为属性名，映射到数据库的 metadata 列（因为 metadata 是 SQLAlchemy 保留字）
    meta_data = Column("metadata", JSONB, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, server_default="now()", nullable=False, index=True)
    
    def __repr__(self):
        return f"<Checkpoint(thread_id={self.thread_id}, checkpoint_id={self.checkpoint_id})>"


class PostgreSQLCheckpointer(BaseCheckpointSaver):
    """
    PostgreSQL-based checkpoint saver for LangGraph.
    
    Persists conversation state to PostgreSQL for cross-session continuity.
    """
    
    def __init__(self, session_factory=None):
        """
        Initialize the checkpointer.
        
        Args:
            session_factory: Optional async session factory (uses get_async_session if None)
        """
        super().__init__()
        self.session_factory = session_factory or get_async_session
        logger.info("PostgreSQL Checkpointer initialized")
    
    async def aget(
        self,
        config: Dict[str, Any]
    ) -> Optional[Checkpoint]:
        """
        Retrieve a checkpoint asynchronously.
        
        Args:
            config: Configuration dict with 'configurable' containing 'thread_id'
            
        Returns:
            Checkpoint object or None if not found
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("No thread_id in config, cannot retrieve checkpoint")
            return None
        
        try:
            async with self.session_factory() as session:
                # Get the most recent checkpoint for this thread
                result = await session.execute(
                    select(CheckpointModel)
                    .where(CheckpointModel.thread_id == thread_id)
                    .order_by(CheckpointModel.created_at.desc())
                    .limit(1)
                )
                
                checkpoint_model = result.scalar_one_or_none()
                
                if checkpoint_model is None:
                    logger.debug(f"No checkpoint found for thread {thread_id}")
                    return None
                
                # Deserialize checkpoint
                checkpoint = pickle.loads(checkpoint_model.checkpoint_data)
                logger.debug(f"Retrieved checkpoint for thread {thread_id}")
                
                return checkpoint
                
        except Exception as e:
            logger.error(f"Error retrieving checkpoint: {e}")
            return None
    
    async def aget_tuple(
        self,
        config: Dict[str, Any]
    ) -> Optional[Tuple[Checkpoint, CheckpointMetadata]]:
        """
        Get checkpoint and metadata as a tuple (required by LangGraph).
        
        This method is called by LangGraph's AsyncPregelLoop to restore
        conversation state from the database.
        
        Args:
            config: Configuration dict containing thread_id in config['configurable']['thread_id']
            
        Returns:
            Tuple of (Checkpoint, CheckpointMetadata) or None if not found
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("No thread_id in config, cannot retrieve checkpoint tuple")
            return None
        
        try:
            async with self.session_factory() as session:
                # Query the most recent checkpoint for this thread
                result = await session.execute(
                    select(CheckpointModel)
                    .where(CheckpointModel.thread_id == thread_id)
                    .order_by(CheckpointModel.created_at.desc())
                    .limit(1)
                )
                checkpoint_model = result.scalar_one_or_none()
                
                if checkpoint_model is None:
                    logger.debug(f"No checkpoint tuple found for thread {thread_id}")
                    return None
                
                # Deserialize the checkpoint data
                checkpoint = pickle.loads(checkpoint_model.checkpoint_data)
                
                # Extract metadata (meta_data 映射到数据库的 metadata 列)
                metadata_dict = checkpoint_model.meta_data or {}
                
                logger.debug(f"Retrieved checkpoint tuple for thread {thread_id}")
                return (checkpoint, metadata_dict)
                    
        except Exception as e:
            logger.error(f"Error retrieving checkpoint tuple: {e}")
            return None
    
    def get(
        self,
        config: Dict[str, Any]
    ) -> Optional[Checkpoint]:
        """
        Retrieve a checkpoint synchronously.
        
        Note: This calls the async version and runs it synchronously.
        
        Args:
            config: Configuration dict
            
        Returns:
            Checkpoint object or None if not found
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is already running, we can't use it
                logger.warning("Event loop is running, using new loop for get()")
                return asyncio.run(self.aget(config))
            return loop.run_until_complete(self.aget(config))
        except RuntimeError:
            # No event loop in current thread
            return asyncio.run(self.aget(config))
    
    async def aput(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        parent_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save a checkpoint asynchronously.
        
        Args:
            config: Configuration dict with 'configurable' containing 'thread_id'
            checkpoint: Checkpoint object to save
            metadata: Checkpoint metadata
            parent_config: Optional parent configuration (for checkpoint lineage)
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("No thread_id in config, cannot save checkpoint")
            return
        
        try:
            async with self.session_factory() as session:
                # Generate checkpoint ID (use timestamp + counter)
                checkpoint_id = f"{datetime.utcnow().isoformat()}_{checkpoint.get('step', 0)}"
                
                # Serialize checkpoint
                checkpoint_data = pickle.dumps(checkpoint)
                
                # Create checkpoint model
                checkpoint_model = CheckpointModel(
                    thread_id=thread_id,
                    checkpoint_id=checkpoint_id,
                    checkpoint_data=checkpoint_data,
                    metadata=metadata if metadata else {}
                )
                
                session.add(checkpoint_model)
                await session.commit()
                
                logger.debug(f"Saved checkpoint for thread {thread_id}")
                
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            raise
    
    def put(
        self,
        config: Dict[str, Any],
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        parent_config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save a checkpoint synchronously.
        
        Args:
            config: Configuration dict
            checkpoint: Checkpoint object
            metadata: Checkpoint metadata
            parent_config: Optional parent configuration (for checkpoint lineage)
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                logger.warning("Event loop is running, using new loop for put()")
                asyncio.run(self.aput(config, checkpoint, metadata, parent_config))
            else:
                loop.run_until_complete(self.aput(config, checkpoint, metadata, parent_config))
        except RuntimeError:
            asyncio.run(self.aput(config, checkpoint, metadata, parent_config))
    
    async def alist(
        self,
        config: Dict[str, Any],
        limit: Optional[int] = None,
        before: Optional[str] = None,
    ) -> Iterator[Tuple[Dict[str, Any], Checkpoint, CheckpointMetadata]]:
        """
        List checkpoints asynchronously.
        
        Args:
            config: Configuration dict
            limit: Maximum number of checkpoints to return
            before: Checkpoint ID to start from
            
        Yields:
            Tuples of (config, checkpoint, metadata)
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("No thread_id in config, cannot list checkpoints")
            return
        
        try:
            async with self.session_factory() as session:
                query = select(CheckpointModel).where(
                    CheckpointModel.thread_id == thread_id
                ).order_by(CheckpointModel.created_at.desc())
                
                if before:
                    query = query.where(CheckpointModel.checkpoint_id < before)
                
                if limit:
                    query = query.limit(limit)
                
                result = await session.execute(query)
                checkpoints = result.scalars().all()
                
                for checkpoint_model in checkpoints:
                    checkpoint = pickle.loads(checkpoint_model.checkpoint_data)
                    metadata_dict = checkpoint_model.meta_data or {}
                    
                    yield (
                        {"configurable": {"thread_id": checkpoint_model.thread_id}},
                        checkpoint,
                        metadata_dict
                    )
                    
        except Exception as e:
            logger.error(f"Error listing checkpoints: {e}")
    
    def list(
        self,
        config: Dict[str, Any],
        limit: Optional[int] = None,
        before: Optional[str] = None,
    ) -> Iterator[Tuple[Dict[str, Any], Checkpoint, CheckpointMetadata]]:
        """
        List checkpoints synchronously.
        
        Args:
            config: Configuration dict
            limit: Maximum number of checkpoints
            before: Checkpoint ID to start from
            
        Yields:
            Tuples of (config, checkpoint, metadata)
        """
        import asyncio
        
        async def _alist():
            results = []
            async for item in self.alist(config, limit, before):
                results.append(item)
            return results
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                results = asyncio.run(_alist())
            else:
                results = loop.run_until_complete(_alist())
            
            for item in results:
                yield item
                
        except RuntimeError:
            results = asyncio.run(_alist())
            for item in results:
                yield item
    
    async def adelete(
        self,
        config: Dict[str, Any]
    ) -> None:
        """
        Delete checkpoints for a thread asynchronously.
        
        Args:
            config: Configuration dict
        """
        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            logger.warning("No thread_id in config, cannot delete checkpoints")
            return
        
        try:
            async with self.session_factory() as session:
                await session.execute(
                    delete(CheckpointModel).where(
                        CheckpointModel.thread_id == thread_id
                    )
                )
                await session.commit()
                logger.info(f"Deleted checkpoints for thread {thread_id}")
                
        except Exception as e:
            logger.error(f"Error deleting checkpoints: {e}")
            raise
    
    async def aput_writes(
        self,
        config: Dict[str, Any],
        writes: list,
        task_id: str
    ) -> None:
        """
        Store intermediate writes from a checkpoint task.
        
        Args:
            config: Configuration dict with 'configurable' containing 'thread_id'
            writes: List of writes to store
            task_id: Task identifier
        """
        # For now, we'll store writes as part of checkpoint metadata
        # In a more sophisticated implementation, you might want a separate table
        logger.debug(f"Storing {len(writes)} writes for task {task_id}")
        # This is a minimal implementation - writes are typically handled by aput()
        pass


async def create_checkpoint_table():
    """
    Create the checkpoint table if it doesn't exist.
    
    This should be called during database initialization.
    """
    from .connection import get_db_engine
    
    try:
        engine = get_db_engine()
        async with engine.begin() as conn:
            await conn.run_sync(CheckpointModel.metadata.create_all)
        logger.info("Checkpoint table created successfully")
    except Exception as e:
        logger.error(f"Error creating checkpoint table: {e}")
        raise

