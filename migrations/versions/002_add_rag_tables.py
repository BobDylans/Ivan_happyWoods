"""Add RAG corpus, document and chunk tables

Revision ID: 002_add_rag_tables
Revises: 001_add_auth_fields
Create Date: 2025-11-08

This migration adds the RAG (Retrieval-Augmented Generation) related tables:
- rag_corpora: User-specific document collections
- rag_documents: Individual documents in a corpus
- rag_chunks: Text chunks with metadata for vector search
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_add_rag_tables'
down_revision = '001_add_auth_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Add RAG tables to support per-user document collections."""
    
    # 1. Create rag_corpora table
    op.create_table(
        'rag_corpora',
        sa.Column('corpus_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('corpus_name', sa.String(length=255), nullable=False),
        sa.Column('collection_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('corpus_id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'corpus_name', name='uq_user_corpus_name'),
        sa.UniqueConstraint('collection_name', name='uq_collection_name')
    )
    
    # Create indexes for rag_corpora
    op.create_index('ix_rag_corpora_user_id', 'rag_corpora', ['user_id'])
    op.create_index('ix_rag_corpora_corpus_name', 'rag_corpora', ['corpus_name'])
    op.create_index('ix_rag_corpora_collection_name', 'rag_corpora', ['collection_name'])
    
    # 2. Create rag_documents table
    op.create_table(
        'rag_documents',
        sa.Column('doc_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('corpus_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=512), nullable=False),
        sa.Column('file_hash', sa.String(length=64), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('mime_type', sa.String(length=128), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('doc_id'),
        sa.ForeignKeyConstraint(['corpus_id'], ['rag_corpora.corpus_id'], ondelete='CASCADE')
    )
    
    # Create indexes for rag_documents
    op.create_index('ix_rag_documents_corpus_id', 'rag_documents', ['corpus_id'])
    op.create_index('ix_rag_documents_filename', 'rag_documents', ['filename'])
    op.create_index('ix_rag_documents_file_hash', 'rag_documents', ['file_hash'])
    
    # 3. Create rag_chunks table
    op.create_table(
        'rag_chunks',
        sa.Column('chunk_id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('doc_id', sa.Integer(), nullable=False),
        sa.Column('qdrant_point_id', sa.String(length=255), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('text_preview', sa.Text(), nullable=True),
        sa.Column('char_count', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('chunk_id'),
        sa.ForeignKeyConstraint(['doc_id'], ['rag_documents.doc_id'], ondelete='CASCADE'),
        sa.UniqueConstraint('qdrant_point_id', name='uq_qdrant_point_id')
    )
    
    # Create indexes for rag_chunks
    op.create_index('ix_rag_chunks_doc_id', 'rag_chunks', ['doc_id'])
    op.create_index('ix_rag_chunks_qdrant_point_id', 'rag_chunks', ['qdrant_point_id'])
    op.create_index('ix_rag_chunks_chunk_index', 'rag_chunks', ['chunk_index'])


def downgrade():
    """Remove RAG tables."""
    
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('rag_chunks')
    op.drop_table('rag_documents')
    op.drop_table('rag_corpora')

