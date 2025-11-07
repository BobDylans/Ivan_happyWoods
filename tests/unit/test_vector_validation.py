"""
Unit tests for vector validation enhancements in RAG ingestion pipeline.

Tests cover:
- Empty vector detection
- Dimension mismatch detection
- Invalid numeric values (NaN, Inf)
- Embedding service error handling
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
from typing import List

from rag.ingestion import _flush_batch, create_chunks_for_file
from rag.qdrant_store import DocumentChunk, QdrantVectorStore
from rag.embedding_client import EmbeddingClient
from config.models import RAGConfig


@pytest.fixture
def mock_rag_config():
    """Create a mock RAG configuration."""
    config = MagicMock(spec=RAGConfig)
    config.embed_dim = 1536
    config.embed_model = "text-embedding-3-small"
    config.chunk_size = 300
    config.chunk_overlap = 60
    config.collection = "test_collection"
    config.qdrant_url = "http://localhost:6333"
    config.qdrant_api_key = None
    config.request_timeout = 30
    return config


@pytest.fixture
def mock_vector_store(mock_rag_config):
    """Create a mock vector store."""
    store = MagicMock(spec=QdrantVectorStore)
    store.config = mock_rag_config
    store.upsert_chunks = AsyncMock()
    return store


@pytest.fixture
def mock_embedding_client():
    """Create a mock embedding client."""
    client = MagicMock(spec=EmbeddingClient)
    client.embed_texts = AsyncMock()
    return client


@pytest.fixture
def sample_chunks():
    """Create sample document chunks for testing."""
    return [
        DocumentChunk(
            id="chunk_1",
            text="This is test chunk 1",
            embedding=[],  # Will be populated by embedding service
            metadata={"source": "test.txt", "chunk_index": 0}
        ),
        DocumentChunk(
            id="chunk_2",
            text="This is test chunk 2",
            embedding=[],
            metadata={"source": "test.txt", "chunk_index": 1}
        ),
    ]


class TestFlushBatchValidation:
    """Tests for _flush_batch function validation logic."""

    @pytest.mark.asyncio
    async def test_empty_batch_handling(self, mock_embedding_client, mock_vector_store):
        """Test that empty batches are handled gracefully."""
        await _flush_batch([], mock_embedding_client, mock_vector_store)
        
        # Should not call embedding service or vector store
        mock_embedding_client.embed_texts.assert_not_called()
        mock_vector_store.upsert_chunks.assert_not_called()

    @pytest.mark.asyncio
    async def test_embedding_service_returns_none(
        self, sample_chunks, mock_embedding_client, mock_vector_store
    ):
        """Test error handling when embedding service returns None."""
        mock_embedding_client.embed_texts.return_value = None
        
        with pytest.raises(ValueError, match="Embedding service returned None"):
            await _flush_batch(sample_chunks, mock_embedding_client, mock_vector_store)

    @pytest.mark.asyncio
    async def test_embedding_count_mismatch(
        self, sample_chunks, mock_embedding_client, mock_vector_store
    ):
        """Test error handling when embedding count doesn't match chunk count."""
        # Return only 1 embedding for 2 chunks
        mock_embedding_client.embed_texts.return_value = [
            [0.1] * 1536,  # Only one embedding
        ]
        
        with pytest.raises(ValueError, match="unexpected number of vectors"):
            await _flush_batch(sample_chunks, mock_embedding_client, mock_vector_store)

    @pytest.mark.asyncio
    async def test_empty_embedding_vector(
        self, sample_chunks, mock_embedding_client, mock_vector_store
    ):
        """Test error handling when embedding service returns empty vectors."""
        mock_embedding_client.embed_texts.return_value = [
            [],  # Empty vector
            [],  # Empty vector
        ]
        
        with pytest.raises(ValueError, match="zero-dimensional embedding"):
            await _flush_batch(sample_chunks, mock_embedding_client, mock_vector_store)

    @pytest.mark.asyncio
    async def test_dimension_mismatch(
        self, sample_chunks, mock_embedding_client, mock_vector_store
    ):
        """Test error handling when embedding dimensions don't match expected."""
        # Return vectors with wrong dimension
        mock_embedding_client.embed_texts.return_value = [
            [0.1] * 768,  # Expected 1536, got 768
            [0.2] * 768,
        ]
        
        with pytest.raises(ValueError, match="dimension mismatch"):
            await _flush_batch(sample_chunks, mock_embedding_client, mock_vector_store)

    @pytest.mark.asyncio
    async def test_nan_values_in_embedding(
        self, sample_chunks, mock_embedding_client, mock_vector_store
    ):
        """Test error handling when embeddings contain NaN values."""
        mock_embedding_client.embed_texts.return_value = [
            [float('nan')] * 1536,  # Vector with NaN
            [0.2] * 1536,
        ]
        
        with pytest.raises(ValueError, match="NaN value"):
            await _flush_batch(sample_chunks, mock_embedding_client, mock_vector_store)

    @pytest.mark.asyncio
    async def test_infinite_values_in_embedding(
        self, sample_chunks, mock_embedding_client, mock_vector_store
    ):
        """Test error handling when embeddings contain infinite values."""
        mock_embedding_client.embed_texts.return_value = [
            [float('inf')] * 1536,  # Vector with Inf
            [0.2] * 1536,
        ]
        
        with pytest.raises(ValueError, match="Infinite value"):
            await _flush_batch(sample_chunks, mock_embedding_client, mock_vector_store)

    @pytest.mark.asyncio
    async def test_non_numeric_values(
        self, sample_chunks, mock_embedding_client, mock_vector_store
    ):
        """Test error handling when embeddings contain non-numeric values."""
        mock_embedding_client.embed_texts.return_value = [
            ["string"] + [0.1] * 1535,  # Non-numeric value
            [0.2] * 1536,
        ]
        
        with pytest.raises(ValueError, match="Non-numeric value"):
            await _flush_batch(sample_chunks, mock_embedding_client, mock_vector_store)

    @pytest.mark.asyncio
    async def test_successful_validation_and_upsert(
        self, sample_chunks, mock_embedding_client, mock_vector_store
    ):
        """Test successful validation with valid embeddings."""
        # Return valid embeddings
        mock_embedding_client.embed_texts.return_value = [
            [0.1] * 1536,
            [0.2] * 1536,
        ]
        
        await _flush_batch(sample_chunks, mock_embedding_client, mock_vector_store)
        
        # Should call upsert with validated chunks
        mock_vector_store.upsert_chunks.assert_called_once()
        
        # Verify embeddings were assigned
        assert sample_chunks[0].embedding == [0.1] * 1536
        assert sample_chunks[1].embedding == [0.2] * 1536

    @pytest.mark.asyncio
    async def test_empty_text_chunk(
        self, mock_embedding_client, mock_vector_store
    ):
        """Test error handling for chunks with empty text."""
        chunks = [
            DocumentChunk(
                id="chunk_empty",
                text="",  # Empty text
                embedding=[],
                metadata={}
            )
        ]
        
        with pytest.raises(ValueError, match="has empty text"):
            await _flush_batch(chunks, mock_embedding_client, mock_vector_store)

    @pytest.mark.asyncio
    async def test_whitespace_only_text(
        self, mock_embedding_client, mock_vector_store
    ):
        """Test error handling for chunks with only whitespace."""
        chunks = [
            DocumentChunk(
                id="chunk_whitespace",
                text="   \n\t  ",  # Only whitespace
                embedding=[],
                metadata={}
            )
        ]
        
        with pytest.raises(ValueError, match="has empty text"):
            await _flush_batch(chunks, mock_embedding_client, mock_vector_store)


class TestQdrantUpsertValidation:
    """Tests for QdrantVectorStore.upsert_chunks validation logic."""

    @pytest.mark.asyncio
    async def test_invalid_chunk_id(self, mock_rag_config):
        """Test error handling for invalid chunk IDs."""
        store = QdrantVectorStore(mock_rag_config)
        store._client = MagicMock()
        store._client.upsert = AsyncMock()
        
        chunks = [
            DocumentChunk(
                id="",  # Empty ID
                text="Valid text",
                embedding=[0.1] * 1536,
                metadata={}
            )
        ]
        
        with pytest.raises(ValueError, match="invalid ID"):
            await store.upsert_chunks(chunks)

    @pytest.mark.asyncio
    async def test_empty_embedding_in_upsert(self, mock_rag_config):
        """Test that upsert catches empty embeddings."""
        store = QdrantVectorStore(mock_rag_config)
        store._client = MagicMock()
        store._client.upsert = AsyncMock()
        
        chunks = [
            DocumentChunk(
                id="chunk_1",
                text="Valid text",
                embedding=[],  # Empty embedding
                metadata={}
            )
        ]
        
        with pytest.raises(ValueError, match="empty embedding vector"):
            await store.upsert_chunks(chunks)

    @pytest.mark.asyncio
    async def test_dimension_check_in_upsert(self, mock_rag_config):
        """Test that upsert validates vector dimensions."""
        store = QdrantVectorStore(mock_rag_config)
        store._client = MagicMock()
        store._client.upsert = AsyncMock()
        
        chunks = [
            DocumentChunk(
                id="chunk_1",
                text="Valid text",
                embedding=[0.1] * 768,  # Wrong dimension
                metadata={}
            )
        ]
        
        with pytest.raises(ValueError, match="incorrect embedding dimension"):
            await store.upsert_chunks(chunks)

    @pytest.mark.asyncio
    async def test_successful_upsert_with_validation(self, mock_rag_config):
        """Test successful upsert with all validations passing."""
        store = QdrantVectorStore(mock_rag_config)
        store._client = MagicMock()
        store._client.upsert = AsyncMock()
        
        chunks = [
            DocumentChunk(
                id="chunk_1",
                text="Valid text",
                embedding=[0.1] * 1536,
                metadata={"source": "test.txt"}
            ),
            DocumentChunk(
                id="chunk_2",
                text="Another valid text",
                embedding=[0.2] * 1536,
                metadata={"source": "test.txt"}
            ),
        ]
        
        await store.upsert_chunks(chunks)
        
        # Verify upsert was called
        store._client.upsert.assert_called_once()
        
        # Verify the call arguments
        call_args = store._client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "test_collection"
        assert len(call_args.kwargs["points"]) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

